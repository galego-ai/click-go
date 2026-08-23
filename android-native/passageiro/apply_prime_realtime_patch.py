from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

def add_import(anchor,value):
    global text
    if value.strip() not in text:
        text=text.replace(anchor,anchor+value,1)

add_import('import android.content.Context;\n','import android.content.Intent;\n')
add_import('import android.graphics.Color;\n','import android.graphics.Bitmap;\nimport android.graphics.BitmapFactory;\n')
add_import('import android.graphics.drawable.GradientDrawable;\n','import android.graphics.drawable.BitmapDrawable;\n')
add_import('import java.net.URLEncoder;\n','import java.net.URL;\nimport java.io.InputStream;\n')

field_anchor='''    private Runnable ridePoll;\n'''
fields='''    private Runnable ridePoll;\n    private String mapboxPublicToken;\n    private String activeDriverId;\n    private String activeShareToken;\n    private Marker activeDriverMarker;\n    private final List<Marker> nearbyDriverMarkers = new ArrayList<>();\n    private LocationManager passengerLiveLocationManager;\n    private LocationListener passengerLiveLocationListener;\n'''
if field_anchor in text and 'private String mapboxPublicToken;' not in text:
    text=text.replace(field_anchor,fields,1)

# Rota PRIME: Mapbox primeiro, OSRM como continuidade sem custo.
pattern=r'''    private void drawRoute\(\) \{.*?\n    \}\n\n    private void loadOptions\(\) \{'''
new_draw=r'''    private void drawRoute() {
        if (map == null || origin == null || destination == null) return;
        final MapView routeMap = map;
        final int seq = ++routeSeq;
        drawRouteOverlays(Arrays.asList(origin, destination));
        GeoPoint startPoint = new GeoPoint(origin.getLatitude(), origin.getLongitude());
        GeoPoint endPoint = new GeoPoint(destination.getLatitude(), destination.getLongitude());
        io.execute(() -> {
            List<GeoPoint> roadPoints = new ArrayList<>();
            try {
                String mb = mapboxToken();
                if (mb != null && !mb.isBlank()) {
                    String url = "https://api.mapbox.com/directions/v5/mapbox/driving/"
                            + startPoint.getLongitude() + "," + startPoint.getLatitude() + ";"
                            + endPoint.getLongitude() + "," + endPoint.getLatitude()
                            + "?geometries=geojson&overview=full&steps=false&access_token=" + URLEncoder.encode(mb, StandardCharsets.UTF_8);
                    JSONObject root = new JSONObject(ApiClient.absoluteGet(url));
                    JSONArray routes = root.optJSONArray("routes");
                    if (routes != null && routes.length() > 0) {
                        JSONObject geometry = routes.getJSONObject(0).optJSONObject("geometry");
                        JSONArray coords = geometry == null ? null : geometry.optJSONArray("coordinates");
                        if (coords != null) roadPoints = routePoints(coords);
                    }
                }
            } catch (Exception ignored) {}
            if (roadPoints.size() < 2) {
                try {
                    String url = "https://router.project-osrm.org/route/v1/driving/"
                            + startPoint.getLongitude() + "," + startPoint.getLatitude() + ";"
                            + endPoint.getLongitude() + "," + endPoint.getLatitude()
                            + "?overview=simplified&geometries=geojson&steps=false";
                    JSONObject root = new JSONObject(ApiClient.absoluteGet(url));
                    JSONArray routes = root.optJSONArray("routes");
                    if (routes != null && routes.length() > 0) {
                        JSONObject geometry = routes.getJSONObject(0).optJSONObject("geometry");
                        JSONArray coords = geometry == null ? null : geometry.optJSONArray("coordinates");
                        if (coords != null) roadPoints = routePoints(coords);
                    }
                } catch (Exception ignored) {}
            }
            List<GeoPoint> finalPoints = roadPoints;
            if (finalPoints.size() < 2) return;
            ui.post(() -> {
                if (destroyed || seq != routeSeq || map != routeMap) return;
                drawRouteOverlays(finalPoints);
                if (activeRideId == null) renderNearbyDrivers();
            });
        });
    }

    private List<GeoPoint> routePoints(JSONArray coords) {
        List<GeoPoint> points = new ArrayList<>();
        int step = Math.max(1, coords.length() / 550);
        for (int i = 0; i < coords.length(); i += step) {
            JSONArray pair = coords.optJSONArray(i);
            if (pair == null || pair.length() < 2) continue;
            points.add(new GeoPoint(pair.optDouble(1), pair.optDouble(0)));
        }
        JSONArray last = coords.optJSONArray(coords.length() - 1);
        if (last != null && last.length() >= 2) points.add(new GeoPoint(last.optDouble(1), last.optDouble(0)));
        return points;
    }

    private String mapboxToken() throws Exception {
        if (mapboxPublicToken != null && !mapboxPublicToken.isBlank()) return mapboxPublicToken;
        String raw = ApiClient.rpc("get_public_map_provider_config", new JSONObject(), token);
        JSONArray rows = new JSONArray(raw);
        if (rows.length() > 0) mapboxPublicToken = rows.getJSONObject(0).optString("mapbox_public_token", "");
        return mapboxPublicToken;
    }

    private void loadOptions() {'''
text,n=re.subn(pattern,new_draw,text,count=1,flags=re.S)
if n!=1: raise SystemExit('drawRoute/loadOptions final não encontrado')

# Ao trocar categoria, mostra os motoristas online daquela categoria.
anchor='''        requestRideButton.setText("Solicitar " + selectedOption.name + " · " + money(selectedOption.fare));\n'''
if anchor not in text: raise SystemExit('renderOptions anchor não encontrado')
text=text.replace(anchor,anchor+'        renderNearbyDrivers();\n',1)

# Compartilhamento na tela de corrida ativa.
old='''        Button cancel = secondaryLight("Cancelar corrida");\n        bottom.addView(cancel, lpMatch(dp(54)));\n        root.addView(bottom, new LinearLayout.LayoutParams(-1, dp(225)));\n        setContentView(root);\n        drawRoute();\n        cancel.setOnClickListener(v -> previewCancel());\n        startRidePolling();\n'''
new='''        Button share = primary("Compartilhar acompanhamento");\n        Button cancel = secondaryLight("Cancelar corrida");\n        bottom.addView(share, lpMatch(dp(54)));\n        bottom.addView(space(8));\n        bottom.addView(cancel, lpMatch(dp(54)));\n        root.addView(bottom, new LinearLayout.LayoutParams(-1, dp(285)));\n        setContentView(root);\n        drawRoute();\n        share.setOnClickListener(v -> shareActiveRide());\n        cancel.setOnClickListener(v -> previewCancel());\n        startPassengerLiveLocation();\n        startRidePolling();\n'''
if old not in text: raise SystemExit('showActiveRide ações não encontradas')
text=text.replace(old,new,1)

# Polling inclui motorista e atualiza marcador em tempo real.
pattern=r'''    private void startRidePolling\(\) \{.*?\n    \}\n\n    private void stopRidePolling\(\) \{'''
new_poll=r'''    private void startRidePolling() {
        stopRidePolling();
        ridePoll = new Runnable() {
            @Override public void run() {
                if (activeRideId == null || destroyed) return;
                String rideId = activeRideId;
                io.execute(() -> {
                    try {
                        JSONArray rows = new JSONArray(ApiClient.restGet("rides?id=eq." + rideId + "&select=id,status,estimated_fare,final_fare,driver_id", token));
                        if (rows.length() == 0) { ui.postDelayed(ridePoll, 3500); return; }
                        JSONObject ride = rows.getJSONObject(0);
                        String status = ride.optString("status");
                        String driverId = ride.optString("driver_id", "");
                        double fare = ride.isNull("final_fare") ? ride.optDouble("estimated_fare") : ride.optDouble("final_fare");
                        JSONObject driverLocation = null;
                        if (!driverId.isBlank()) {
                            JSONArray locs = new JSONArray(ApiClient.restGet("driver_locations?driver_id=eq." + driverId + "&select=lat,lng,heading,speed_kmh,updated_at&limit=1", token));
                            if (locs.length() > 0) driverLocation = locs.getJSONObject(0);
                        }
                        JSONObject finalDriverLocation = driverLocation;
                        ui.post(() -> {
                            activeDriverId = driverId;
                            if (activeStatus != null) activeStatus.setText(statusLabel(status));
                            if (activeFare != null) activeFare.setText(money(fare));
                            renderActiveDriver(finalDriverLocation);
                            if (status.equals("completed") || status.equals("cancelled")) {
                                activeRideId = null;
                                stopRidePolling();
                                stopPassengerLiveLocation();
                                showEndState(status, fare);
                            } else ui.postDelayed(ridePoll, 3000);
                        });
                    } catch (Exception e) { ui.postDelayed(ridePoll, 4500); }
                });
            }
        };
        ui.post(ridePoll);
    }

    private void stopRidePolling() {'''
text,n=re.subn(pattern,new_poll,text,count=1,flags=re.S)
if n!=1: raise SystemExit('startRidePolling final não encontrado')

# Métodos PRIME antes do estado final.
marker='''    private void showEndState(String status, double fare) {\n'''
if marker not in text: raise SystemExit('showEndState marker não encontrado')
methods=r'''    private void renderNearbyDrivers() {
        if (map == null || origin == null || selectedOption == null || activeRideId != null) return;
        final MapView targetMap = map;
        final String categoryId = selectedOption.id;
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("p_lat", origin.getLatitude()).put("p_lng", origin.getLongitude()).put("p_category_id", categoryId).put("p_radius_km", 12);
                JSONArray rows = new JSONArray(ApiClient.rpc("get_passenger_nearby_online_drivers", body, token));
                Bitmap custom = null;
                for (int i=0;i<rows.length() && custom==null;i++) {
                    String url = rows.getJSONObject(i).optString("marker_url", "");
                    if (!url.isBlank()) try (InputStream in = new URL(url).openStream()) { custom = BitmapFactory.decodeStream(in); }
                }
                Bitmap finalCustom = custom == null ? null : Bitmap.createScaledBitmap(custom, dp(46), dp(46), true);
                ui.post(() -> {
                    if (destroyed || map != targetMap || selectedOption == null || !categoryId.equals(selectedOption.id) || activeRideId != null) return;
                    for (Marker m : nearbyDriverMarkers) targetMap.getOverlays().remove(m);
                    nearbyDriverMarkers.clear();
                    for (int i=0;i<rows.length();i++) {
                        JSONObject row = rows.optJSONObject(i); if (row == null) continue;
                        double lat=row.optDouble("lat",Double.NaN), lng=row.optDouble("lng",Double.NaN); if(!Double.isFinite(lat)||!Double.isFinite(lng))continue;
                        Marker m=new Marker(targetMap); m.setPosition(new GeoPoint(lat,lng)); m.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_CENTER);
                        m.setTitle(row.optString("category_name","Motorista online") + " · " + String.format(Locale.getDefault(),"%.1f km",row.optDouble("distance_km",0)));
                        if(finalCustom!=null)m.setIcon(new BitmapDrawable(getResources(),finalCustom));
                        targetMap.getOverlays().add(m); nearbyDriverMarkers.add(m);
                    }
                    targetMap.invalidate();
                });
            } catch(Exception ignored) {}
        });
    }

    private void renderActiveDriver(JSONObject loc) {
        if (map == null) return;
        if (activeDriverMarker != null) map.getOverlays().remove(activeDriverMarker);
        activeDriverMarker = null;
        if (loc == null) { map.invalidate(); return; }
        double lat=loc.optDouble("lat",Double.NaN), lng=loc.optDouble("lng",Double.NaN);
        if(!Double.isFinite(lat)||!Double.isFinite(lng))return;
        activeDriverMarker=new Marker(map); activeDriverMarker.setPosition(new GeoPoint(lat,lng)); activeDriverMarker.setTitle("Motorista em tempo real"); activeDriverMarker.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_BOTTOM); map.getOverlays().add(activeDriverMarker); map.invalidate();
    }

    private void shareActiveRide() {
        if (activeRideId == null) { toast("Nenhuma corrida ativa para compartilhar."); return; }
        String rideId=activeRideId;
        io.execute(() -> {
            try {
                JSONObject result=new JSONObject(ApiClient.rpc("create_ride_share",new JSONObject().put("p_ride_id",rideId).put("p_valid_hours",8),token));
                String shareToken=result.optString("token",""); if(shareToken.isBlank())throw new Exception("Não foi possível criar o link."); activeShareToken=shareToken;
                String link="https://click-go-ten.vercel.app/acompanhar/"+shareToken;
                ui.post(() -> {
                    Intent send=new Intent(Intent.ACTION_SEND); send.setType("text/plain"); send.putExtra(Intent.EXTRA_SUBJECT,"Acompanhe minha corrida CLICK-GO"); send.putExtra(Intent.EXTRA_TEXT,"Acompanhe minha corrida CLICK-GO em tempo real:\n"+link); startActivity(Intent.createChooser(send,"Compartilhar por WhatsApp, SMS ou e-mail"));
                });
            } catch(Exception e){ui.post(()->toast(message(e)));}
        });
    }

    private void startPassengerLiveLocation() {
        stopPassengerLiveLocation();
        if (activeRideId == null) return;
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) return;
        try {
            passengerLiveLocationManager=(LocationManager)getSystemService(LOCATION_SERVICE);
            String provider=passengerLiveLocationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)?LocationManager.GPS_PROVIDER:LocationManager.NETWORK_PROVIDER;
            passengerLiveLocationListener=location -> sendPassengerLiveLocation(location);
            passengerLiveLocationManager.requestLocationUpdates(provider,4000,4f,passengerLiveLocationListener,Looper.getMainLooper());
            Location last=passengerLiveLocationManager.getLastKnownLocation(provider); if(last!=null)sendPassengerLiveLocation(last);
        } catch(Exception ignored) {}
    }

    private void sendPassengerLiveLocation(Location location) {
        String rideId=activeRideId; if(rideId==null||location==null)return;
        io.execute(() -> { try { ApiClient.rpc("update_passenger_live_location",new JSONObject().put("p_ride_id",rideId).put("p_lat",location.getLatitude()).put("p_lng",location.getLongitude()).put("p_accuracy_m",location.hasAccuracy()?location.getAccuracy():JSONObject.NULL),token); } catch(Exception ignored) {} });
    }

    private void stopPassengerLiveLocation() {
        if(passengerLiveLocationManager!=null&&passengerLiveLocationListener!=null)try{passengerLiveLocationManager.removeUpdates(passengerLiveLocationListener);}catch(Exception ignored){}
        passengerLiveLocationListener=null; passengerLiveLocationManager=null;
    }

'''
text=text.replace(marker,methods+marker,1)

# Ao voltar para a home, encerra compartilhamento de GPS antigo.
home='''    private void showHome() {\n'''
if home in text and 'stopPassengerLiveLocation();\n        cancelAddressSearch();' not in text:
    text=text.replace(home,home+'        stopPassengerLiveLocation();\n',1)

# Versão PRIME.
build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
# incrementa o versionCode atual de forma simples e marca PRIME
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.9-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro PRIME: Mapbox, motoristas online, rastreamento e compartilhamento aplicados.')
