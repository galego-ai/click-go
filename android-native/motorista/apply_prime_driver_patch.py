from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

def add_import(anchor,value):
 global text
 if value.strip() not in text:text=text.replace(anchor,anchor+value,1)

add_import('import org.json.JSONObject;\n','import org.json.JSONArray;\n')
add_import('import org.osmdroid.views.MapView;\n','import org.osmdroid.util.GeoPoint;\nimport org.osmdroid.views.overlay.Polyline;\n')
add_import('import java.text.NumberFormat;\n','import java.net.URLEncoder;\nimport java.nio.charset.StandardCharsets;\nimport java.util.ArrayList;\nimport java.util.List;\n')

if 'private String mapboxPublicToken;' not in text:
    text=text.replace('''    private String token, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";\n''','''    private String token, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";\n    private String mapboxPublicToken;\n    private int driverRouteSeq;\n''',1)

# Cadastro: senha com olho igual ao login.
old='''        for(EditText e:new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,type,email,pass}){body.addView(e,match(dp(58)));body.addView(space(8));}\n        Button submit=primary("Enviar cadastro para aprovação");submit.setEnabled(false);body.addView(space(8));body.addView(submit,match(dp(60)));\n'''
new='''        for(EditText e:new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,type,email}){body.addView(e,match(dp(58)));body.addView(space(8));}\n        Button registrationEye=darkButton("👁");registrationEye.setContentDescription("Mostrar ou ocultar senha");final boolean[] registrationVisible={false};\n        registrationEye.setOnClickListener(v->{int pos=pass.getSelectionStart();registrationVisible[0]=!registrationVisible[0];pass.setTransformationMethod(registrationVisible[0]?null:PasswordTransformationMethod.getInstance());registrationEye.setText(registrationVisible[0]?"🙈":"👁");pass.setSelection(Math.max(0,Math.min(pos,pass.length())));});\n        LinearLayout registrationPasswordRow=horizontal();registrationPasswordRow.addView(pass,new LinearLayout.LayoutParams(0,dp(58),1));registrationPasswordRow.addView(spaceH(8));registrationPasswordRow.addView(registrationEye,new LinearLayout.LayoutParams(dp(58),dp(58)));body.addView(registrationPasswordRow,match(dp(58)));body.addView(space(8));\n        Button submit=primary("Enviar cadastro para aprovação");submit.setEnabled(false);body.addView(space(8));body.addView(submit,match(dp(60)));\n'''
if old not in text: raise SystemExit('Campo senha do cadastro motorista não encontrado')
text=text.replace(old,new,1)

# Liga rota real às ofertas e corridas ativas.
if 'DriverMapRenderer.render(map,currentLocation,o,dp(5));drawDriverRoadRoute(o);' not in text:
    text=text.replace('DriverMapRenderer.render(map,currentLocation,o,dp(5)); }','DriverMapRenderer.render(map,currentLocation,o,dp(5));drawDriverRoadRoute(o); }',1)
if 'DriverMapRenderer.render(map,currentLocation,r,dp(5));drawDriverRoadRoute(r);' not in text:
    text=text.replace('DriverMapRenderer.render(map,currentLocation,r,dp(5));}','DriverMapRenderer.render(map,currentLocation,r,dp(5));drawDriverRoadRoute(r);}',1)

marker='''    private void renderOffer(JSONObject o){'''
if marker not in text: raise SystemExit('renderOffer não encontrado')
methods=r'''    private String mapboxToken() throws Exception {
        if(mapboxPublicToken!=null&&!mapboxPublicToken.isBlank())return mapboxPublicToken;
        JSONArray rows=new JSONArray(ApiClient.publicRpc("get_public_map_provider_config",new JSONObject()));
        if(rows.length()>0)mapboxPublicToken=rows.getJSONObject(0).optString("mapbox_public_token","");
        return mapboxPublicToken;
    }

    private void drawDriverRoadRoute(JSONObject target){
        if(map==null||currentLocation==null||target==null)return;
        final MapView targetMap=map;final int seq=++driverRouteSeq;
        String status=target.optString("status","");boolean trip=status.equals("in_progress");
        double lat=trip?target.optDouble("destination_lat",Double.NaN):target.optDouble("origin_lat",Double.NaN);
        double lng=trip?target.optDouble("destination_lng",Double.NaN):target.optDouble("origin_lng",Double.NaN);
        if(!Double.isFinite(lat)||!Double.isFinite(lng))return;
        double fromLat=currentLocation.getLatitude(),fromLng=currentLocation.getLongitude();
        io.execute(()->{try{
            String mb=mapboxToken();if(mb==null||mb.isBlank())return;
            String url="https://api.mapbox.com/directions/v5/mapbox/driving/"+fromLng+","+fromLat+";"+lng+","+lat+"?geometries=geojson&overview=full&steps=false&access_token="+URLEncoder.encode(mb, StandardCharsets.UTF_8);
            JSONObject root=new JSONObject(ApiClient.absoluteGet(url));JSONArray routes=root.optJSONArray("routes");if(routes==null||routes.length()==0)return;JSONObject geometry=routes.getJSONObject(0).optJSONObject("geometry");JSONArray coords=geometry==null?null:geometry.optJSONArray("coordinates");if(coords==null||coords.length()<2)return;
            List<GeoPoint> points=new ArrayList<>();int step=Math.max(1,coords.length()/500);for(int i=0;i<coords.length();i+=step){JSONArray p=coords.optJSONArray(i);if(p!=null&&p.length()>=2)points.add(new GeoPoint(p.optDouble(1),p.optDouble(0)));}JSONArray last=coords.optJSONArray(coords.length()-1);if(last!=null&&last.length()>=2)points.add(new GeoPoint(last.optDouble(1),last.optDouble(0)));if(points.size()<2)return;
            ui.post(()->{if(destroyed||seq!=driverRouteSeq||map!=targetMap)return;List<org.osmdroid.views.overlay.Overlay> remove=new ArrayList<>();for(org.osmdroid.views.overlay.Overlay ov:targetMap.getOverlays())if(ov instanceof Polyline)remove.add(ov);targetMap.getOverlays().removeAll(remove);Polyline line=new Polyline();line.setPoints(points);line.getOutlinePaint().setStrokeWidth(dp(6));line.getOutlinePaint().setColor(YELLOW);targetMap.getOverlays().add(line);targetMap.invalidate();});
        }catch(Exception ignored){}});
    }

'''
text=text.replace(marker,methods+marker,1)

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8');m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '0.8-prime'",build,count=1);build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Motorista PRIME: olho no cadastro e rota Mapbox aplicados.')
