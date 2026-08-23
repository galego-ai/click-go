from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
text=main_path.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')

# RPCs de segurança no cliente nativo.
repo_marker='''    public static void advanceRide(String token, String rideId, String action) throws Exception {\n        ApiClient.rpc("advance_driver_ride", new JSONObject().put("p_ride_id", rideId).put("p_action", action), token);\n    }\n'''
repo_methods='''    public static JSONObject verifyRideStartPin(String token, String rideId, String pin) throws Exception {\n        return new JSONObject(ApiClient.rpc("verify_ride_start_pin", new JSONObject()\n                .put("p_ride_id", rideId).put("p_pin", pin), token));\n    }\n\n    public static JSONObject triggerRideSos(String token, String rideId, Double lat, Double lng) throws Exception {\n        JSONObject body = new JSONObject().put("p_ride_id", rideId)\n                .put("p_lat", lat == null ? JSONObject.NULL : lat)\n                .put("p_lng", lng == null ? JSONObject.NULL : lng)\n                .put("p_message", "SOS acionado pelo motorista no app Android CLICK-GO.");\n        return new JSONObject(ApiClient.rpc("trigger_ride_sos", body, token));\n    }\n\n    public static JSONObject reportRouteDeviation(String token, String rideId, double lat, double lng, double distanceM) throws Exception {\n        return new JSONObject(ApiClient.rpc("report_route_deviation", new JSONObject()\n                .put("p_ride_id", rideId).put("p_lat", lat).put("p_lng", lng)\n                .put("p_distance_m", Math.round(distanceM)), token));\n    }\n\n'''+repo_marker
if 'verifyRideStartPin' not in repo:
    if repo_marker not in repo: raise SystemExit('advanceRide não encontrado no DriverRepository')
    repo=repo.replace(repo_marker,repo_methods,1)
repo_path.write_text(repo,encoding='utf-8')

# Estado do monitoramento de rota planejada (origem -> destino).
field_anchor='''    private boolean showMoney = true;\n'''
fields='''    private boolean showMoney = true;\n    private List<GeoPoint> safetyRoutePoints = new ArrayList<>();\n    private String safetyRouteRideId = "";\n    private int safetyFarHits = 0;\n    private long safetyLastReport = 0L;\n    private double safetyThresholdM = 100.0;\n'''
if field_anchor in text and 'safetyRoutePoints' not in text:
    text=text.replace(field_anchor,fields,1)

# Cada atualização do GPS também verifica desvio da rota original da corrida.
# Aceita tanto o listener legado quanto o listener estabilizado que evita fila de envios.
legacy_listener='''locationListener = loc -> { currentLocation=loc; if(online) io.execute(() -> { try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); } catch(Exception ignored){} }); };'''
legacy_safety='''locationListener = loc -> { currentLocation=loc; checkSafetyRouteDeviation(loc); if(online) io.execute(() -> { try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); } catch(Exception ignored){} }); };'''
stable_listener='''        locationListener = loc -> {\n            currentLocation=loc;\n            if(online && sendingLocation.compareAndSet(false,true)) io.execute(() -> {\n                try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); }\n                catch(Exception ignored){}\n                finally { sendingLocation.set(false); }\n            });\n        };'''
stable_safety='''        locationListener = loc -> {\n            currentLocation=loc;\n            checkSafetyRouteDeviation(loc);\n            if(online && sendingLocation.compareAndSet(false,true)) io.execute(() -> {\n                try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); }\n                catch(Exception ignored){}\n                finally { sendingLocation.set(false); }\n            });\n        };'''
if stable_listener in text:
    text=text.replace(stable_listener,stable_safety,1)
elif legacy_listener in text:
    text=text.replace(legacy_listener,legacy_safety,1)
elif 'checkSafetyRouteDeviation(loc);' not in text:
    raise SystemExit('locationListener compatível não encontrado')

# Troca o botão de início direto por validação obrigatória do PIN e inclui SOS na corrida ativa.
old_arriving='''        }else if(s.equals("driver_arriving")){\n            int free=r.optInt("wait_free_seconds",300); double fee=r.optDouble("wait_fee_per_minute",0.50);\n            c.addView(text("⏱ Tolerância: "+Math.max(0,free/60)+" min",14,YELLOW,true));\n            c.addView(text("Depois: "+money(fee)+" por minuto iniciado",13,GRAY,false)); c.addView(space(8));\n            Button nav=darkButton("🧭 Abrir navegação"); c.addView(nav,match(dp(54))); c.addView(space(8));\n            Button start=primary("▶ Iniciar corrida"); c.addView(start,match(dp(58)));\n            nav.setOnClickListener(v->openNavigationToPassenger(r)); start.setOnClickListener(v->advance(r.optString("id"),"start"));\n        }else{'''
new_arriving='''        }else if(s.equals("driver_arriving")){\n            int free=r.optInt("wait_free_seconds",300); double fee=r.optDouble("wait_fee_per_minute",0.50);\n            c.addView(text("⏱ Tolerância: "+Math.max(0,free/60)+" min",14,YELLOW,true));\n            c.addView(text("Depois: "+money(fee)+" por minuto iniciado",13,GRAY,false)); c.addView(space(8));\n            Button nav=darkButton("🧭 Abrir navegação"); c.addView(nav,match(dp(54))); c.addView(space(8));\n            c.addView(text("🔐 Peça ao passageiro o PIN de 4 dígitos",13,YELLOW,true)); c.addView(space(6));\n            EditText pin=edit("PIN de 4 dígitos"); pin.setInputType(InputType.TYPE_CLASS_NUMBER);\n            pin.setFilters(new android.text.InputFilter[]{new android.text.InputFilter.LengthFilter(4)});\n            c.addView(pin,match(dp(56))); c.addView(space(8));\n            Button start=primary("🔐 Validar PIN e iniciar"); c.addView(start,match(dp(58)));\n            nav.setOnClickListener(v->openNavigationToPassenger(r)); start.setOnClickListener(v->verifyPinAndStart(r.optString("id"),pin.getText().toString().trim()));\n        }else{'''
if old_arriving not in text: raise SystemExit('bloco driver_arriving v1.7 não encontrado')
text=text.replace(old_arriving,new_arriving,1)

# SOS disponível nos três estados da corrida.
old_tail='''        operationBox.addView(c,wrap()); DriverMapRenderer.render(map,currentLocation,r,dp(5)); drawDriverRoadRoute(r);\n    }\n'''
new_tail='''        c.addView(space(10));\n        Button sos=darkButton("🆘 SOS"); sos.setTextColor(Color.WHITE); sos.setBackground(round(Color.rgb(185,28,28),16,Color.rgb(185,28,28)));\n        c.addView(sos,match(dp(54))); sos.setOnClickListener(v->confirmRideSos(r.optString("id")));\n        operationBox.addView(c,wrap()); DriverMapRenderer.render(map,currentLocation,r,dp(5)); drawDriverRoadRoute(r);\n        if(s.equals("in_progress")) ensureSafetyRoute(r); else resetSafetyRoute();\n    }\n'''
if old_tail not in text: raise SystemExit('final renderRide v1.7 não encontrado')
text=text.replace(old_tail,new_tail,1)

# Métodos PIN, SOS e desvio de rota.
anchor='''    private void markGoingAndNavigate(JSONObject ride) {\n'''
helpers=r'''    private void verifyPinAndStart(String rideId,String pin) {
        if(rideId==null||rideId.isBlank()){toast("Corrida inválida.");return;}
        if(pin==null||!pin.matches("\\d{4}")){toast("Digite os 4 números informados pelo passageiro.");return;}
        io.execute(()->{try{
            JSONObject result=DriverRepository.verifyRideStartPin(token,rideId,pin);
            if(!result.optBoolean("verified",false)){
                String notice=result.optBoolean("locked",false)?"Muitas tentativas incorretas. Aguarde alguns minutos.":"PIN incorreto. Tentativas restantes: "+result.optInt("remaining_attempts",0);
                ui.post(()->toast(notice));return;
            }
            DriverRepository.advanceRide(token,rideId,"start");
            ui.post(()->{toast("PIN confirmado. Corrida iniciada com segurança.");refreshOperation();});
        }catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

    private void confirmRideSos(String rideId) {
        if(rideId==null||rideId.isBlank()){toast("Corrida inválida.");return;}
        new android.app.AlertDialog.Builder(this)
                .setTitle("Acionar SOS?")
                .setMessage("O alerta será registrado com sua localização atual e ficará visível para a central de segurança.")
                .setNegativeButton("Cancelar",null)
                .setPositiveButton("Acionar SOS",(dialog,which)->triggerRideSos(rideId))
                .show();
    }

    private void triggerRideSos(String rideId) {
        Location loc=currentLocation;
        Double lat=loc==null?null:loc.getLatitude(),lng=loc==null?null:loc.getLongitude();
        io.execute(()->{try{
            JSONObject result=DriverRepository.triggerRideSos(token,rideId,lat,lng);
            ui.post(()->toast(result.optBoolean("ok",false)?"SOS registrado pela CLICK-GO.":"Não foi possível confirmar o SOS."));
        }catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

    private void resetSafetyRoute() {
        safetyRoutePoints.clear(); safetyRouteRideId=""; safetyFarHits=0; safetyThresholdM=100.0;
    }

    private void ensureSafetyRoute(JSONObject ride) {
        String rideId=ride.optString("id","");
        if(rideId.isBlank()||rideId.equals(safetyRouteRideId)&&safetyRoutePoints.size()>1)return;
        double oLat=ride.optDouble("origin_lat",Double.NaN),oLng=ride.optDouble("origin_lng",Double.NaN);
        double dLat=ride.optDouble("destination_lat",Double.NaN),dLng=ride.optDouble("destination_lng",Double.NaN);
        if(!Double.isFinite(oLat)||!Double.isFinite(oLng)||!Double.isFinite(dLat)||!Double.isFinite(dLng))return;
        safetyRouteRideId=rideId;safetyRoutePoints.clear();safetyFarHits=0;safetyThresholdM=100.0;
        io.execute(()->{try{
            String mb=mapboxToken();if(mb==null||mb.isBlank())return;
            String url="https://api.mapbox.com/directions/v5/mapbox/driving/"+oLng+","+oLat+";"+dLng+","+dLat+"?geometries=geojson&overview=full&steps=false&access_token="+URLEncoder.encode(mb,StandardCharsets.UTF_8);
            JSONObject root=new JSONObject(ApiClient.absoluteGet(url));JSONArray routes=root.optJSONArray("routes");if(routes==null||routes.length()==0)return;
            JSONObject geometry=routes.getJSONObject(0).optJSONObject("geometry");JSONArray coords=geometry==null?null:geometry.optJSONArray("coordinates");if(coords==null||coords.length()<2)return;
            List<GeoPoint> points=new ArrayList<>();int step=Math.max(1,coords.length()/500);
            for(int i=0;i<coords.length();i+=step){JSONArray p=coords.optJSONArray(i);if(p!=null&&p.length()>=2)points.add(new GeoPoint(p.optDouble(1),p.optDouble(0)));}
            JSONArray last=coords.optJSONArray(coords.length()-1);if(last!=null&&last.length()>=2)points.add(new GeoPoint(last.optDouble(1),last.optDouble(0)));
            if(rideId.equals(safetyRouteRideId))safetyRoutePoints=points;
        }catch(Exception ignored){}});
    }

    private void checkSafetyRouteDeviation(Location loc) {
        if(loc==null||safetyRouteRideId.isBlank()||safetyRoutePoints.size()<2)return;
        double min=Double.MAX_VALUE;
        for(int i=1;i<safetyRoutePoints.size();i++)min=Math.min(min,pointSegmentMeters(loc.getLatitude(),loc.getLongitude(),safetyRoutePoints.get(i-1),safetyRoutePoints.get(i)));
        if(min>=safetyThresholdM)safetyFarHits++;else safetyFarHits=0;
        long now=System.currentTimeMillis();
        if(safetyFarHits<3||now-safetyLastReport<300000)return;
        safetyFarHits=0;final double distance=min;final String rideId=safetyRouteRideId;
        io.execute(()->{try{
            JSONObject result=DriverRepository.reportRouteDeviation(token,rideId,loc.getLatitude(),loc.getLongitude(),distance);
            if(result.has("threshold_m"))safetyThresholdM=Math.max(100.0,result.optDouble("threshold_m",800));
            if(result.optBoolean("reported",false)){safetyLastReport=System.currentTimeMillis();ui.post(()->toast("⚠ Possível desvio de rota registrado pela CLICK-GO."));}
            else if(result.optBoolean("duplicate",false))safetyLastReport=System.currentTimeMillis();
        }catch(Exception ignored){}});
    }

    private double pointSegmentMeters(double pLat,double pLng,GeoPoint a,GeoPoint b) {
        double rad=Math.toRadians(pLat),kx=111320.0*Math.cos(rad),ky=110540.0;
        double ax=(a.getLongitude()-pLng)*kx,ay=(a.getLatitude()-pLat)*ky;
        double bx=(b.getLongitude()-pLng)*kx,by=(b.getLatitude()-pLat)*ky;
        double dx=bx-ax,dy=by-ay,len=dx*dx+dy*dy,t=len>0?Math.max(0,Math.min(1,-(ax*dx+ay*dy)/len)):0;
        double x=ax+t*dx,y=ay+t*dy;return Math.sqrt(x*x+y*y);
    }

'''
if anchor not in text: raise SystemExit('anchor de navegação não encontrado')
text=text.replace(anchor,helpers+anchor,1)

# v1.8 PRIME.
build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.8-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
main_path.write_text(text,encoding='utf-8')
print('Motorista v1.8 PRIME: PIN, SOS e monitoramento de desvio de rota aplicados.')
