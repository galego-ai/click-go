from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

# Estado da rota dinâmica do motorista durante a corrida ativa.
field='''    private Marker activeDriverMarker;\n'''
fields='''    private Marker activeDriverMarker;\n    private String activeRideStatus = "searching";\n    private int activeDriverRouteSeq;\n    private long activeDriverRouteLastAt;\n'''
if field in text and 'private int activeDriverRouteSeq;' not in text:
    text=text.replace(field,fields,1)

# Assim que a chamada é criada, a tela passa imediatamente para a experiência de corrida em andamento.
text=text.replace('''        activeStatus = text("Procurando motorista mais próximo…", 25, BLACK, true);''','''        activeStatus = text("Corrida em andamento · procurando motorista", 25, BLACK, true);''',1)

old_status='''                                activeStatus.setText(status.equals("accepted")?"Motorista a caminho":status.equals("driver_arriving")?"Motorista chegou ao embarque":status.equals("in_progress")?"Corrida em andamento":statusLabel(status));'''
new_status='''                                activeStatus.setText(status.equals("accepted")?"Corrida em andamento · motorista a caminho":status.equals("driver_arriving")?"Corrida em andamento · motorista no embarque":status.equals("in_progress")?"Corrida em andamento · a caminho do destino":"Corrida em andamento · "+statusLabel(status));'''
if old_status in text:
    text=text.replace(old_status,new_status,1)

# Mantém o estado da corrida sincronizado com o desenho da rota.
if 'activeRideStatus=status;\n                            renderActiveDriver(finalLocation);' not in text:
    text=text.replace('''                            renderActiveDriver(finalLocation);''','''                            activeRideStatus=status;\n                            renderActiveDriver(finalLocation);''',1)

# O marcador do motorista continua sendo atualizado e a linha passa a representar a rota viária
# motorista -> embarque antes do início e motorista -> destino durante a corrida.
pattern=r'''    private void renderActiveDriver\(JSONObject loc\) \{.*?\n    \}\n\n    private void shareActiveRide\(\) \{'''
replacement=r'''    private void renderActiveDriver(JSONObject loc) {
        if (map == null) return;
        if (activeDriverMarker != null) map.getOverlays().remove(activeDriverMarker);
        activeDriverMarker = null;
        if (loc == null) { map.invalidate(); return; }
        double lat=loc.optDouble("lat",Double.NaN), lng=loc.optDouble("lng",Double.NaN);
        if(!Double.isFinite(lat)||!Double.isFinite(lng))return;
        activeDriverMarker=new Marker(map);
        activeDriverMarker.setPosition(new GeoPoint(lat,lng));
        activeDriverMarker.setTitle("Motorista em tempo real");
        activeDriverMarker.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_BOTTOM);
        map.getOverlays().add(activeDriverMarker);
        map.invalidate();
        drawActiveDriverRoadRoute(loc);
    }

    private void drawActiveDriverRoadRoute(JSONObject loc) {
        if(map==null||loc==null||origin==null||destination==null)return;
        long now=System.currentTimeMillis();
        if(now-activeDriverRouteLastAt<6000)return;
        activeDriverRouteLastAt=now;
        double fromLat=loc.optDouble("lat",Double.NaN),fromLng=loc.optDouble("lng",Double.NaN);
        if(!Double.isFinite(fromLat)||!Double.isFinite(fromLng))return;
        Location target="in_progress".equals(activeRideStatus)?destination:origin;
        double toLat=target.getLatitude(),toLng=target.getLongitude();
        final MapView targetMap=map;final int seq=++activeDriverRouteSeq;
        io.execute(()->{
            List<GeoPoint> points=new ArrayList<>();
            try{
                String mb=mapboxToken();
                if(mb!=null&&!mb.isBlank()){
                    String url="https://api.mapbox.com/directions/v5/mapbox/driving/"+fromLng+","+fromLat+";"+toLng+","+toLat+"?geometries=geojson&overview=full&steps=false&access_token="+URLEncoder.encode(mb,StandardCharsets.UTF_8);
                    JSONObject root=new JSONObject(ApiClient.absoluteGet(url));
                    JSONArray routes=root.optJSONArray("routes");
                    if(routes!=null&&routes.length()>0){
                        JSONObject geometry=routes.getJSONObject(0).optJSONObject("geometry");
                        JSONArray coords=geometry==null?null:geometry.optJSONArray("coordinates");
                        if(coords!=null)points=routePoints(coords);
                    }
                }
            }catch(Exception ignored){}
            if(points.size()<2){
                try{
                    String url="https://router.project-osrm.org/route/v1/driving/"+fromLng+","+fromLat+";"+toLng+","+toLat+"?overview=full&geometries=geojson&steps=false";
                    JSONObject root=new JSONObject(ApiClient.absoluteGet(url));
                    JSONArray routes=root.optJSONArray("routes");
                    if(routes!=null&&routes.length()>0){
                        JSONObject geometry=routes.getJSONObject(0).optJSONObject("geometry");
                        JSONArray coords=geometry==null?null:geometry.optJSONArray("coordinates");
                        if(coords!=null)points=routePoints(coords);
                    }
                }catch(Exception ignored){}
            }
            List<GeoPoint> finalPoints=points;
            if(finalPoints.size()<2)return;
            ui.post(()->{
                if(destroyed||seq!=activeDriverRouteSeq||map!=targetMap)return;
                List<org.osmdroid.views.overlay.Overlay> remove=new ArrayList<>();
                for(org.osmdroid.views.overlay.Overlay ov:targetMap.getOverlays())
                    if(ov instanceof org.osmdroid.views.overlay.Polyline)remove.add(ov);
                targetMap.getOverlays().removeAll(remove);
                org.osmdroid.views.overlay.Polyline line=new org.osmdroid.views.overlay.Polyline();
                line.setPoints(finalPoints);
                line.getOutlinePaint().setStrokeWidth(dp(7));
                line.getOutlinePaint().setColor(Color.rgb(255,212,0));
                targetMap.getOverlays().add(0,line);
                targetMap.invalidate();
            });
        });
    }

    private void shareActiveRide() {'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1:
    raise SystemExit('renderActiveDriver não encontrado para aplicar rota dinâmica')

build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.11-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.11 PRIME: corrida ativa imediata, motorista ao vivo e rota dinâmica aplicados.')
