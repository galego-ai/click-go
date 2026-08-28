from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Todos os botões de cancelamento da corrida/chamada passam pelo fluxo confiável abaixo.
text=text.replace('setOnClickListener(v->previewCancel());','setOnClickListener(v->confirmCancelRideAndReturnHome());')
text=text.replace('setOnClickListener(v -> previewCancel());','setOnClickListener(v -> confirmCancelRideAndReturnHome());')

anchor='    private void showPayments() {\n'
helpers=r'''    private void confirmCancelRideAndReturnHome(){
        if(activeRideId==null||activeRideId.isBlank()){clearRideAndReturnHome();return;}
        new AlertDialog.Builder(this)
            .setTitle("Cancelar chamada?")
            .setMessage("A chamada/corrida será cancelada e você voltará para a tela inicial. Se houver taxa aplicável, ela será registrada conforme a regra exibida no app.")
            .setNegativeButton("Voltar",null)
            .setPositiveButton("Cancelar chamada",(d,w)->cancelRideAndReturnHome())
            .show();
    }

    private void cancelRideAndReturnHome(){
        final String rideId=activeRideId;
        if(rideId==null||rideId.isBlank()){clearRideAndReturnHome();return;}
        io.execute(()->{try{
            ApiClient.rpc("cancel_passenger_ride",new JSONObject().put("p_ride_id",rideId).put("p_confirm_fee",true),token);
            ui.post(()->{toast("Chamada cancelada.");clearRideAndReturnHome();});
        }catch(Exception e){ui.post(()->toast(message(e)));}});
    }

    private void clearRideAndReturnHome(){
        stopCallTimer();
        activeRideId=null;
        activeRideStatus="";
        trackingUiActive=false;
        callStartedAtMs=0L;
        driverFoundElapsedMs=0L;
        liveRoutePhase="";
        liveRouteUpdatedAtMs=0L;
        showHome();
    }

    private String jsEsc(String value){
        if(value==null)return "";
        return value.replace("\\","\\\\").replace("'","\\'").replace("\n"," ").replace("\r"," ");
    }

    private String historyMapHtml(JSONObject ride,JSONArray points){
        StringBuilder coords=new StringBuilder("[");
        boolean first=true;
        for(int i=0;i<points.length();i++){
            JSONObject p=points.optJSONObject(i);if(p==null)continue;
            double lat=p.optDouble("lat",Double.NaN),lng=p.optDouble("lng",Double.NaN);
            if(!Double.isFinite(lat)||!Double.isFinite(lng))continue;
            if(!first)coords.append(',');first=false;
            coords.append('[').append(lat).append(',').append(lng).append(']');
        }
        coords.append(']');
        double olat=ride.optDouble("origin_lat",Double.NaN),olng=ride.optDouble("origin_lng",Double.NaN);
        double dlat=ride.optDouble("destination_lat",Double.NaN),dlng=ride.optDouble("destination_lng",Double.NaN);
        String origin=jsEsc(ride.optString("origin_label","Embarque")),dest=jsEsc(ride.optString("destination_label","Destino"));
        return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta charset='utf-8'>"+
          "<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>"+
          "<style>html,body,#map{height:100%;margin:0}body{background:#f4f4f4}.leaflet-control-attribution{font-size:9px}</style></head><body><div id='map'></div>"+
          "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script><script>"+
          "const pts="+coords+";const map=L.map('map',{zoomControl:true});L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,attribution:'© OpenStreetMap'}).addTo(map);"+
          (Double.isFinite(olat)&&Double.isFinite(olng)?"const o=L.marker(["+olat+","+olng+"]).addTo(map).bindPopup('<b>Embarque</b><br>"+origin+"');":"")+
          (Double.isFinite(dlat)&&Double.isFinite(dlng)?"const d=L.marker(["+dlat+","+dlng+"]).addTo(map).bindPopup('<b>Destino</b><br>"+dest+"');":"")+
          "if(pts.length>1){const line=L.polyline(pts,{weight:6,opacity:.88}).addTo(map);map.fitBounds(line.getBounds(),{padding:[30,30]});}"+
          "else if("+(Double.isFinite(olat)&&Double.isFinite(olng)?"true":"false")+"){map.setView(["+(Double.isFinite(olat)?olat:-14.52472)+","+(Double.isFinite(olng)?olng:-49.14083)+"],14);}else{map.setView([-14.52472,-49.14083],12);}"+
          "</script></body></html>";
    }

'''
if 'private void confirmCancelRideAndReturnHome()' not in text:
    if anchor not in text: raise SystemExit('showPayments anchor não encontrado')
    text=text.replace(anchor,helpers+anchor,1)

# Troca qualquer versão anterior do detalhamento do trajeto por um mapa real interativo.
replacement=r'''    private void showPassengerRoutePoints(JSONObject ride) {
        String rideId=ride.optString("id","");
        if(rideId.isBlank()){toast("Corrida inválida.");return;}
        io.execute(()->{try{
            JSONArray points=new JSONArray(ApiClient.restGet("ride_location_points?ride_id=eq."+rideId+"&select=lat,lng,phase,recorded_at&order=recorded_at.asc",token));
            String html=historyMapHtml(ride,points);
            ui.post(()->{
                android.webkit.WebView web=new android.webkit.WebView(this);
                android.webkit.WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
                web.setWebViewClient(new android.webkit.WebViewClient());web.setContentDescription("clickgo_history_real_map");
                AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Mapa da corrida").setView(web).setPositiveButton("Fechar",null).create();
                dialog.setOnDismissListener(d->{try{web.destroy();}catch(Exception ignored){}});dialog.show();
                if(dialog.getWindow()!=null)dialog.getWindow().setLayout(-1,(int)(getResources().getDisplayMetrics().heightPixels*0.82));
                web.loadDataWithBaseURL("https://click-go-ten.vercel.app/",html,"text/html","UTF-8",null);
            });
        }catch(Exception e){ui.post(()->toast(message(e)));}});
    }
'''
if 'clickgo_history_real_map' not in text:
    pat=r'(?s)    private void showPassengerRoutePoints\(JSONObject ride\)\s*\{.*?\n    \}\n(?=\n    private )'
    text,n=re.subn(pat,replacement,text,count=1)
    if n!=1:
        # Fallback estrutural: localiza o início e o próximo método privado no mesmo nível.
        start=text.find('    private void showPassengerRoutePoints(JSONObject ride)')
        if start<0: raise SystemExit('showPassengerRoutePoints não encontrado para converter em mapa')
        nxt=re.search(r'\n    private [^\n]+\(',text[start+10:])
        if not nxt: raise SystemExit('fim de showPassengerRoutePoints não encontrado')
        end=start+10+nxt.start()+1
        text=text[:start]+replacement+'\n'+text[end:]

# Ajusta quaisquer rótulos anteriores para deixar claro que o histórico abre o mapa.
text=text.replace('📍 Ver todos os pontos GPS','🗺️ Ver mapa da corrida')
text=text.replace('Ver todos os pontos GPS','Ver mapa da corrida')

for required in ['confirmCancelRideAndReturnHome','cancel_passenger_ride','clearRideAndReturnHome','clickgo_history_real_map','Ver mapa da corrida']:
    if required not in text: raise SystemExit('Passageiro v2.36 incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(max(int(m.group(1))+1,236))+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.36-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.36 PRIME: cancelar chamada volta para home e histórico usa mapa real da corrida.')
