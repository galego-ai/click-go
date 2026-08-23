from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')

marker='''    public static JSONArray documents(String token, String userId) throws Exception {\n'''
method='''    public static JSONArray rideLocationPoints(String token, String rideId) throws Exception {\n        return new JSONArray(ApiClient.restGet("ride_location_points?ride_id=eq." + rideId + "&select=id,lat,lng,heading,speed_kmh,phase,recorded_at&order=recorded_at.asc", token));\n    }\n\n'''
if 'public static JSONArray rideLocationPoints' not in repo:
    if marker not in repo: raise SystemExit('marker DriverRepository não encontrado')
    repo=repo.replace(marker,method+marker,1)
repo_path.write_text(repo,encoding='utf-8')

old='''if(fare>0)c.addView(text("Valor: "+privateMoney(fare),15,YELLOW,true));body.addView(c);body.addView(space(9));'''
new='''if(fare>0)c.addView(text("Valor: "+privateMoney(fare),15,YELLOW,true));c.addView(space(8));Button gps=darkButton("📍 Ver todos os pontos GPS");c.addView(gps,match(dp(48)));gps.setOnClickListener(v->showFullRoutePoints(r));body.addView(c);body.addView(space(9));'''
if old not in text: raise SystemExit('histórico v1.6 não encontrado')
text=text.replace(old,new,1)

anchor='''    private void showEarnings(){\n'''
helper=r'''    private void showFullRoutePoints(JSONObject ride){
        String rideId=ride.optString("id","");
        if(rideId.isBlank()){toast("Corrida inválida.");return;}
        io.execute(()->{try{
            JSONArray rows=DriverRepository.rideLocationPoints(token,rideId);
            StringBuilder b=new StringBuilder();
            b.append("Origem: ").append(coords(ride,"origin_lat","origin_lng")).append("\n");
            b.append("Destino: ").append(coords(ride,"destination_lat","destination_lng")).append("\n");
            b.append("Chegada: ").append(coords(ride,"arrived_lat","arrived_lng")).append("\n");
            b.append("Início: ").append(coords(ride,"started_lat","started_lng")).append("\n");
            b.append("Fim: ").append(coords(ride,"completed_lat","completed_lng")).append("\n\n");
            b.append("Pontos GPS registrados: ").append(rows.length()).append("\n\n");
            for(int i=0;i<rows.length();i++){
                JSONObject p=rows.optJSONObject(i);if(p==null)continue;
                b.append(i+1).append(". ")
                 .append(String.format(Locale.getDefault(),"%.6f, %.6f",p.optDouble("lat"),p.optDouble("lng")))
                 .append(" · ").append(p.optString("phase",""));
                if(!p.isNull("speed_kmh"))b.append(" · ").append(String.format(Locale.getDefault(),"%.0f km/h",p.optDouble("speed_kmh")));
                b.append(" · ").append(shortDate(p.optString("recorded_at",""))).append("\n");
            }
            String result=b.toString();
            ui.post(()->new android.app.AlertDialog.Builder(this).setTitle("Trajeto e coordenadas").setMessage(result).setPositiveButton("Fechar",null).show());
        }catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

'''
if anchor not in text: raise SystemExit('showEarnings anchor não encontrado')
text=text.replace(anchor,helper+anchor,1)

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.7-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
main.write_text(text,encoding='utf-8')
print('Motorista v1.7 PRIME: histórico completo de pontos GPS aplicado.')
