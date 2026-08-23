from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

def add_import(anchor,value):
    global text
    if value.strip() not in text:
        if anchor not in text: raise SystemExit('Import anchor não encontrado: '+anchor.strip())
        text=text.replace(anchor,anchor+value,1)

add_import('import java.util.HashSet;\n','import java.util.HashMap;\nimport java.util.Map;\n')

# Estado do mapa inicial e cache de marcadores.
anchor='''    private LocationListener passengerLiveLocationListener;\n'''
fields='''    private LocationListener passengerLiveLocationListener;\n    private Runnable homeDriverPoll;\n    private boolean homeMapMode;\n    private boolean homeCentered;\n    private TextView homeDriversStatus;\n    private TextView homeLocationText;\n    private Marker homePassengerMarker;\n    private final Map<String, Marker> homeDriverMarkers = new HashMap<>();\n    private final Map<String, Marker> optionDriverMarkers = new HashMap<>();\n    private final Map<String, BitmapDrawable> driverMarkerIconCache = new HashMap<>();\n'''
if anchor not in text: raise SystemExit('Campos PRIME não encontrados')
text=text.replace(anchor,fields,1)

# A tela antiga vira a etapa de destino. A nova showHome será o mapa.
if '    private void showHome() {' not in text: raise SystemExit('showHome original não encontrada')
text=text.replace('    private void showHome() {','    private void showDestinationSearch() {',1)
# Desliga o polling do mapa inicial quando entrar na busca.
text=text.replace('''    private void showDestinationSearch() {\n''','''    private void showDestinationSearch() {\n        homeMapMode=false;\n        stopHomeDriverPolling();\n''',1)

home_method=r'''    private void showHome() {
        cancelAddressSearch();
        stopRidePolling();
        stopPassengerLiveLocation();
        stopHomeDriverPolling();
        activeRideId = null;
        homeMapMode = true;
        homeCentered = false;
        homeDriverMarkers.clear();
        optionDriverMarkers.clear();

        FrameLayout root = new FrameLayout(this);
        root.setBackgroundColor(LIGHT);
        map = new MapView(this);
        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        map.getController().setZoom(15.0);
        root.addView(map, new FrameLayout.LayoutParams(-1,-1));

        Button menu = circleButton("☰",52);
        FrameLayout.LayoutParams menuLp=new FrameLayout.LayoutParams(dp(54),dp(54));
        menuLp.gravity=Gravity.TOP|Gravity.LEFT;menuLp.leftMargin=dp(16);menuLp.topMargin=dp(16);
        root.addView(menu,menuLp);

        TextView brand=text("CLICK-GO",16,BLACK,true);brand.setGravity(Gravity.CENTER);brand.setBackground(round(Color.WHITE,18,Color.WHITE));
        FrameLayout.LayoutParams brandLp=new FrameLayout.LayoutParams(dp(126),dp(50));brandLp.gravity=Gravity.TOP|Gravity.CENTER_HORIZONTAL;brandLp.topMargin=dp(17);root.addView(brand,brandLp);

        Button locate=circleButton("⌖",50);FrameLayout.LayoutParams locateLp=new FrameLayout.LayoutParams(dp(52),dp(52));locateLp.gravity=Gravity.RIGHT|Gravity.BOTTOM;locateLp.rightMargin=dp(16);locateLp.bottomMargin=dp(164);root.addView(locate,locateLp);

        LinearLayout bottom=vertical(Color.WHITE);bottom.setPadding(dp(18),dp(14),dp(18),dp(18));bottom.setBackground(round(Color.WHITE,24,Color.WHITE));
        homeLocationText=text(originLabel,13,GRAY,false);homeLocationText.setSingleLine(true);homeLocationText.setEllipsize(TextUtils.TruncateAt.END);bottom.addView(homeLocationText);
        homeDriversStatus=text("Localizando motoristas próximos…",13,GRAY,false);homeDriversStatus.setPadding(0,dp(4),0,dp(10));bottom.addView(homeDriversStatus);
        Button where=primary("Onde vamos?");bottom.addView(where,lpMatch(dp(60)));
        FrameLayout.LayoutParams bottomLp=new FrameLayout.LayoutParams(-1,dp(142));bottomLp.gravity=Gravity.BOTTOM;bottomLp.leftMargin=dp(12);bottomLp.rightMargin=dp(12);bottomLp.bottomMargin=dp(12);root.addView(bottom,bottomLp);

        menu.setOnClickListener(v->showMenu());
        where.setOnClickListener(v->showDestinationSearch());
        locate.setOnClickListener(v->obtainLocation(homeLocationText,true));
        setContentView(root);

        if(origin==null) obtainLocation(homeLocationText,false);
        else {
            homeLocationText.setText(originLabel);
            renderHomePassengerMarker();
            centerHomeMap();
            startHomeDriverPolling();
        }
    }

    private void renderHomePassengerMarker(){
        if(!homeMapMode||map==null||origin==null)return;
        if(homePassengerMarker==null){homePassengerMarker=new Marker(map);homePassengerMarker.setTitle("Você");homePassengerMarker.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_BOTTOM);map.getOverlays().add(homePassengerMarker);}
        else if(!map.getOverlays().contains(homePassengerMarker))map.getOverlays().add(homePassengerMarker);
        homePassengerMarker.setPosition(origin);map.invalidate();
    }

    private void centerHomeMap(){
        if(!homeMapMode||map==null||origin==null)return;
        renderHomePassengerMarker();
        if(!homeCentered){homeCentered=true;map.getController().setZoom(15.2);map.getController().animateTo(origin);}
    }

    private void startHomeDriverPolling(){
        stopHomeDriverPolling();
        if(!homeMapMode)return;
        homeDriverPoll=new Runnable(){@Override public void run(){if(destroyed||!homeMapMode)return;refreshHomeDrivers();ui.postDelayed(this,8000);}};
        ui.post(homeDriverPoll);
    }

    private void stopHomeDriverPolling(){if(homeDriverPoll!=null)ui.removeCallbacks(homeDriverPoll);homeDriverPoll=null;}

    private BitmapDrawable markerIconCached(String url){
        if(url==null||url.isBlank())return null;
        synchronized(driverMarkerIconCache){if(driverMarkerIconCache.containsKey(url))return driverMarkerIconCache.get(url);}
        try(InputStream in=new URL(url).openStream()){
            Bitmap b=BitmapFactory.decodeStream(in);if(b==null)return null;Bitmap scaled=Bitmap.createScaledBitmap(b,dp(44),dp(44),true);BitmapDrawable d=new BitmapDrawable(getResources(),scaled);synchronized(driverMarkerIconCache){driverMarkerIconCache.put(url,d);}return d;
        }catch(Exception ignored){return null;}
    }

    private void refreshHomeDrivers(){
        if(!homeMapMode||map==null||origin==null)return;
        final MapView target=map;final double lat=origin.getLatitude(),lng=origin.getLongitude();
        io.execute(()->{try{
            JSONObject body=new JSONObject().put("p_lat",lat).put("p_lng",lng).put("p_category_id",JSONObject.NULL).put("p_radius_km",12);
            JSONArray rows=new JSONArray(ApiClient.rpc("get_passenger_nearby_online_drivers",body,token));
            Map<String,BitmapDrawable> icons=new HashMap<>();for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;String u=r.optString("marker_url","");if(!u.isBlank()&&!icons.containsKey(u))icons.put(u,markerIconCached(u));}
            ui.post(()->{
                if(destroyed||!homeMapMode||map!=target)return;
                Set<String> seen=new HashSet<>();
                for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;String id=r.optString("driver_id","");double dlat=r.optDouble("lat",Double.NaN),dlng=r.optDouble("lng",Double.NaN);if(id.isBlank()||!Double.isFinite(dlat)||!Double.isFinite(dlng))continue;seen.add(id);Marker m=homeDriverMarkers.get(id);if(m==null){m=new Marker(target);m.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_CENTER);homeDriverMarkers.put(id,m);target.getOverlays().add(m);}else if(!target.getOverlays().contains(m))target.getOverlays().add(m);m.setPosition(new GeoPoint(dlat,dlng));m.setTitle(r.optString("category_name","Motorista online")+" · "+String.format(Locale.getDefault(),"%.1f km",r.optDouble("distance_km",0)));String u=r.optString("marker_url","");BitmapDrawable icon=icons.get(u);if(icon!=null)m.setIcon(icon);}
                List<String> stale=new ArrayList<>();for(String id:homeDriverMarkers.keySet())if(!seen.contains(id))stale.add(id);for(String id:stale){Marker m=homeDriverMarkers.remove(id);if(m!=null)target.getOverlays().remove(m);}renderHomePassengerMarker();target.invalidate();if(homeDriversStatus!=null)homeDriversStatus.setText(rows.length()==0?"Nenhum motorista online próximo agora":rows.length()+" motorista(s) online próximo(s)");
            });
        }catch(Exception e){ui.post(()->{if(homeMapMode&&homeDriversStatus!=null)homeDriversStatus.setText("Atualizando disponibilidade…");});}});
    }

'''
marker='''    private void showDestinationSearch() {\n'''
text=text.replace(marker,home_method+marker,1)

# GPS atualiza a posição do mapa inicial sem recriar a tela.
loc_anchor='''        originLabel = "Minha localização atual";\n        if (labelView != null) labelView.setText(originLabel);\n        reverseGeocodeOrigin(location, labelView, seq);\n'''
loc_new='''        originLabel = "Minha localização atual";\n        if (labelView != null) labelView.setText(originLabel);\n        if(homeMapMode){renderHomePassengerMarker();centerHomeMap();if(homeDriverPoll==null)startHomeDriverPolling();else refreshHomeDrivers();}\n        reverseGeocodeOrigin(location, labelView, seq);\n'''
if loc_anchor not in text: raise SystemExit('applyLocation não encontrado')
text=text.replace(loc_anchor,loc_new,1)

# Encerra polling ao sair/destruir.
text=text.replace('''        stopRidePolling();\n        io.shutdownNow();\n''','''        stopRidePolling();\n        stopHomeDriverPolling();\n        io.shutdownNow();\n''',1)
text=text.replace('''        cancelAddressSearch();\n        stopRidePolling();\n        map = null;\n''','''        cancelAddressSearch();\n        stopRidePolling();\n        stopHomeDriverPolling();\n        homeMapMode=false;\n        map = null;\n''',1)

# Categorias aparecem mesmo se a consulta de formas de pagamento falhar.
pattern=r'''    private void loadOptions\(\) \{.*?\n    \}\n\n    private void renderOptions\(JSONObject settings\) \{'''
new_load=r'''    private void loadOptions() {
        rideOptions.clear(); selectedOption=null; paymentValues.clear();
        io.execute(() -> {
            try {
                JSONObject body=new JSONObject().put("p_origin_lat",origin.getLatitude()).put("p_origin_lng",origin.getLongitude()).put("p_destination_lat",destination.getLatitude()).put("p_destination_lng",destination.getLongitude());
                JSONArray rows=new JSONArray(ApiClient.rpc("get_passenger_ride_options",body,token));
                List<RideOption> loaded=new ArrayList<>();
                for(int i=0;i<rows.length();i++){JSONObject row=rows.getJSONObject(i);if(row.isNull("category_id"))continue;loaded.add(new RideOption(row.optString("category_id"),row.optString("category_name"),row.optString("required_vehicle_type"),row.optDouble("distance_km"),row.optDouble("duration_min"),row.optDouble("fare"),row.optString("city_id"),row.optString("city_name"),row.optString("state")));}
                if(loaded.isEmpty()){ui.post(()->renderOptions(null));return;}
                RideOption first=loaded.get(0);
                ui.post(()->{rideOptions.clear();rideOptions.addAll(loaded);selectedOption=rideOptions.get(0);paymentValues.clear();renderOptions(null);});
                try {
                    JSONArray payRows=new JSONArray(ApiClient.rpc("get_effective_payment_settings",new JSONObject().put("p_city_id",first.cityId),token));
                    JSONObject settings=payRows.length()>0?payRows.getJSONObject(0):new JSONObject();List<String> payments=new ArrayList<>();if(settings.optBoolean("pix_enabled"))payments.add("pix");if(settings.optBoolean("card_app_enabled"))payments.add("card");if(settings.optBoolean("card_machine_enabled"))payments.add("card_machine");if(settings.optBoolean("cash_enabled"))payments.add("cash");
                    ui.post(()->{paymentValues.clear();paymentValues.addAll(payments);renderOptions(settings);});
                } catch(Exception ignored) {
                    ui.post(()->{if(optionsSubtitle!=null)optionsSubtitle.setText(optionsSubtitle.getText()+" · pagamentos indisponíveis temporariamente");});
                }
            } catch(Exception e) {
                ui.post(()->{if(categoryBox==null||optionsSubtitle==null)return;categoryBox.removeAllViews();categoryBox.addView(unavailable("Serviço indisponível",message(e)));optionsSubtitle.setText("");if(requestRideButton!=null)requestRideButton.setEnabled(false);});
            }
        });
    }

    private void renderOptions(JSONObject settings) {'''
text,n=re.subn(pattern,new_load,text,count=1,flags=re.S)
if n!=1: raise SystemExit('loadOptions final não encontrado')

# Motoristas das categorias: atualiza posição sem limpar/recriar overlays.
pattern=r'''    private void renderNearbyDrivers\(\) \{.*?\n    \}\n\n    private void renderActiveDriver\(JSONObject loc\) \{'''
new_near=r'''    private void renderNearbyDrivers() {
        if(map==null||origin==null||selectedOption==null||activeRideId!=null)return;
        final MapView target=map;final String categoryId=selectedOption.id;
        io.execute(()->{try{
            JSONObject body=new JSONObject().put("p_lat",origin.getLatitude()).put("p_lng",origin.getLongitude()).put("p_category_id",categoryId).put("p_radius_km",12);
            JSONArray rows=new JSONArray(ApiClient.rpc("get_passenger_nearby_online_drivers",body,token));Map<String,BitmapDrawable> icons=new HashMap<>();for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;String u=r.optString("marker_url","");if(!u.isBlank()&&!icons.containsKey(u))icons.put(u,markerIconCached(u));}
            ui.post(()->{if(destroyed||map!=target||selectedOption==null||!categoryId.equals(selectedOption.id)||activeRideId!=null)return;Set<String> seen=new HashSet<>();for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;String id=r.optString("driver_id","");double lat=r.optDouble("lat",Double.NaN),lng=r.optDouble("lng",Double.NaN);if(id.isBlank()||!Double.isFinite(lat)||!Double.isFinite(lng))continue;seen.add(id);Marker m=optionDriverMarkers.get(id);if(m==null){m=new Marker(target);m.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_CENTER);optionDriverMarkers.put(id,m);target.getOverlays().add(m);}else if(!target.getOverlays().contains(m))target.getOverlays().add(m);m.setPosition(new GeoPoint(lat,lng));m.setTitle(r.optString("category_name","Motorista online")+" · "+String.format(Locale.getDefault(),"%.1f km",r.optDouble("distance_km",0)));String u=r.optString("marker_url","");BitmapDrawable icon=icons.get(u);if(icon!=null)m.setIcon(icon);}List<String> stale=new ArrayList<>();for(String id:optionDriverMarkers.keySet())if(!seen.contains(id))stale.add(id);for(String id:stale){Marker m=optionDriverMarkers.remove(id);if(m!=null)target.getOverlays().remove(m);}target.invalidate();});
        }catch(Exception ignored){}});
    }

    private void renderActiveDriver(JSONObject loc) {'''
text,n=re.subn(pattern,new_near,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderNearbyDrivers final não encontrado')

# Remove carregamento automático de empresas/POIs que tornava o mapa pesado e duplicava overlays.
text=re.sub(r'(?m)^\s*loadNearbyBusinesses\([^;]+;\s*$','',text)
text=re.sub(r'(?m)^\s*addBusinessMarkers\([^;]+;\s*$','',text)

# Versão 2.0 PRIME.
build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.0-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.0 PRIME: home no mapa, motoristas online, categorias resilientes e mapa otimizado.')
