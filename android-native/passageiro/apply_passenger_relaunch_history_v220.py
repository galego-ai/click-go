from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# v2.20 PRIME
# - removes osmdroid from the startup/home screen (same WebView strategy that fixed post-accept ANR);
# - tears down every poller/location/map before executors are shut down;
# - all generic IO dispatches become rejection-safe during Activity destruction;
# - completed rides show a Canvas GPS-route preview without map/API requests per card.

# Dedicated home WebView state.
if 'private PassengerHomeMap homeLiveMap;' not in text:
    anchor='''    private PassengerLiveMap liveTrackingMap;\n'''
    if anchor not in text: raise SystemExit('PassengerLiveMap field not found')
    text=text.replace(anchor,anchor+'''    private PassengerHomeMap homeLiveMap;\n    private boolean homeSmokeMode;\n''',1)

# No delayed callback can submit work after shutdown. Do this before inserting runIo itself.
text=text.replace('io.execute(', 'runIo(')
helper_anchor='''    private void showLogin() {\n'''
helper=r'''    private void runIo(Runnable task) {
        if(task==null||destroyed||io.isShutdown())return;
        try{io.execute(task);}catch(java.util.concurrent.RejectedExecutionException ignored){}
    }

'''
if 'private void runIo(Runnable task)' not in text:
    if helper_anchor not in text: raise SystemExit('showLogin anchor not found')
    text=text.replace(helper_anchor,helper+helper_anchor,1)

# Release every map implementation, including startup map.
pat=r'''    private void releaseMap\(\) \{.*?\n    \}\n'''
rep=r'''    private void releaseMap() {
        ++routeSeq;
        PassengerHomeMap home=homeLiveMap;homeLiveMap=null;
        if(home!=null)try{home.destroySafely();}catch(Exception ignored){}
        PassengerLiveMap live=liveTrackingMap;liveTrackingMap=null;
        if(live!=null)try{live.destroySafely();}catch(Exception ignored){}
        MapView old=map;map=null;
        if(old!=null){try{old.onPause();}catch(Exception ignored){}try{old.onDetach();}catch(Exception ignored){}}
    }
'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('releaseMap not found')

# Strong lifecycle cleanup: important when the user clears the task and immediately reopens it.
pat=r'''    @Override protected void onDestroy\(\) \{.*?\n    \}\n'''
rep=r'''    @Override protected void onDestroy() {
        destroyed=true;
        try{cancelAddressSearch();}catch(Exception ignored){}
        try{stopRidePolling();}catch(Exception ignored){}
        try{stopHomeDriverPolling();}catch(Exception ignored){}
        try{stopPassengerLiveLocation();}catch(Exception ignored){}
        activeRideScreenVisible=false;homeMapMode=false;
        try{releaseMap();}catch(Exception ignored){}
        if(favoriteAddressSearch!=null)try{ui.removeCallbacks(favoriteAddressSearch);}catch(Exception ignored){}
        try{ui.removeCallbacksAndMessages(null);}catch(Exception ignored){}
        try{io.shutdownNow();}catch(Exception ignored){}
        try{addressIo.shutdownNow();}catch(Exception ignored){}
        super.onDestroy();
    }
'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('onDestroy not found')

# CI-only home mode to exercise Activity finish/relaunch without authentication/network dependency.
token_line='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n'''
home_smoke='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_home_smoke",false)){homeSmokeMode=true;token="smoke";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Localização de teste";showHome();return;}\n'''
if 'clickgo_home_smoke' not in text:
    if token_line not in text: raise SystemExit('token line not found')
    text=text.replace(token_line,home_smoke,1)

# Do not try active-ride restore in home smoke mode.
text=text.replace('''if(token!=null&&!token.isBlank()&&activeRideId==null&&!restoringActiveRide) ui.postDelayed''','''if(!homeSmokeMode&&token!=null&&!token.isBlank()&&activeRideId==null&&!restoringActiveRide) ui.postDelayed''',1)

# Startup/home no longer creates osmdroid MapView.
pat=r'''    private void showHome\(\) \{.*?\n    \}\n\n(?=    private void renderHomePassengerMarker\(\))'''
rep=r'''    private void showHome() {
        cancelAddressSearch();stopRidePolling();stopPassengerLiveLocation();stopHomeDriverPolling();
        if(activeRideId!=null&&!activeRideId.isBlank()){showActiveRide();return;}
        activeRideScreenVisible=false;homeMapMode=true;homeCentered=false;releaseMap();homeMapMode=true;
        homeDriverMarkers.clear();optionDriverMarkers.clear();
        FrameLayout root=new FrameLayout(this);root.setBackgroundColor(LIGHT);root.setContentDescription("clickgo_home_screen");
        PassengerHomeMap home=new PassengerHomeMap(this);homeLiveMap=home;root.addView(home,new FrameLayout.LayoutParams(-1,-1));
        Button menu=circleButton("☰",52);FrameLayout.LayoutParams menuLp=new FrameLayout.LayoutParams(dp(54),dp(54));menuLp.gravity=Gravity.TOP|Gravity.LEFT;menuLp.leftMargin=dp(16);menuLp.topMargin=dp(16);root.addView(menu,menuLp);
        TextView brand=text("CLICK-GO",16,BLACK,true);brand.setGravity(Gravity.CENTER);brand.setBackground(round(Color.WHITE,18,Color.WHITE));FrameLayout.LayoutParams brandLp=new FrameLayout.LayoutParams(dp(126),dp(50));brandLp.gravity=Gravity.TOP|Gravity.CENTER_HORIZONTAL;brandLp.topMargin=dp(17);root.addView(brand,brandLp);
        Button locate=circleButton("⌖",50);FrameLayout.LayoutParams locateLp=new FrameLayout.LayoutParams(dp(52),dp(52));locateLp.gravity=Gravity.RIGHT|Gravity.BOTTOM;locateLp.rightMargin=dp(16);locateLp.bottomMargin=dp(164);root.addView(locate,locateLp);
        LinearLayout bottom=vertical(Color.WHITE);bottom.setPadding(dp(18),dp(14),dp(18),dp(18));bottom.setBackground(round(Color.WHITE,24,Color.WHITE));homeLocationText=text(originLabel,13,GRAY,false);homeLocationText.setSingleLine(true);homeLocationText.setEllipsize(TextUtils.TruncateAt.END);bottom.addView(homeLocationText);homeDriversStatus=text(homeSmokeMode?"Mapa pronto":"Localizando motoristas próximos…",13,GRAY,false);homeDriversStatus.setPadding(0,dp(4),0,dp(10));bottom.addView(homeDriversStatus);Button where=primary("Onde vamos?");bottom.addView(where,lpMatch(dp(60)));FrameLayout.LayoutParams bottomLp=new FrameLayout.LayoutParams(-1,dp(142));bottomLp.gravity=Gravity.BOTTOM;bottomLp.leftMargin=dp(12);bottomLp.rightMargin=dp(12);bottomLp.bottomMargin=dp(12);root.addView(bottom,bottomLp);
        menu.setOnClickListener(v->showMenu());where.setOnClickListener(v->showDestinationSearch());locate.setOnClickListener(v->obtainLocation(homeLocationText,true));setContentView(root);applySafeInsets(root);
        if(origin==null&&!homeSmokeMode)obtainLocation(homeLocationText,false);else if(origin!=null){homeLocationText.setText(originLabel);renderHomePassengerMarker();centerHomeMap();if(!homeSmokeMode)startHomeDriverPolling();}
    }

'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showHome final not found')

# Home passenger and driver rendering now targets the stable WebView.
pat=r'''    private void renderHomePassengerMarker\(\)\{.*?\n    \}\n\n(?=    private void centerHomeMap\(\))'''
rep=r'''    private void renderHomePassengerMarker(){
        if(!homeMapMode||homeLiveMap==null||origin==null)return;
        homeLiveMap.setPassenger(origin.getLatitude(),origin.getLongitude());
    }

'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderHomePassengerMarker not found')

pat=r'''    private void centerHomeMap\(\)\{.*?\n    \}\n\n(?=    private void startHomeDriverPolling\(\))'''
rep=r'''    private void centerHomeMap(){
        if(!homeMapMode||homeLiveMap==null||origin==null)return;
        renderHomePassengerMarker();homeCentered=true;
    }

'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('centerHomeMap not found')

pat=r'''    private void startHomeDriverPolling\(\)\{.*?\n    \}\n\n(?=    private void stopHomeDriverPolling\(\))'''
rep=r'''    private void startHomeDriverPolling(){
        stopHomeDriverPolling();if(!homeMapMode||homeSmokeMode)return;
        homeDriverPoll=new Runnable(){@Override public void run(){if(destroyed||!homeMapMode||homeSmokeMode)return;refreshHomeDrivers();ui.postDelayed(this,8000);}};
        ui.postDelayed(homeDriverPoll,700);
    }

'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('startHomeDriverPolling not found')

pat=r'''    private void refreshHomeDrivers\(\)\{.*?\n    \}\n\n(?=    private void )'''
rep=r'''    private void refreshHomeDrivers(){
        if(!homeMapMode||homeLiveMap==null||origin==null||homeSmokeMode)return;
        final PassengerHomeMap target=homeLiveMap;final double lat=origin.getLatitude(),lng=origin.getLongitude();
        runIo(()->{try{JSONObject body=new JSONObject().put("p_lat",lat).put("p_lng",lng).put("p_category_id",JSONObject.NULL).put("p_radius_km",12);JSONArray rows=new JSONArray(ApiClient.rpc("get_passenger_nearby_online_drivers",body,token));ui.post(()->{if(destroyed||!homeMapMode||homeLiveMap!=target)return;target.setDrivers(rows);if(homeDriversStatus!=null)homeDriversStatus.setText(rows.length()==0?"Nenhum motorista online próximo agora":rows.length()+" motorista(s) online próximo(s)");});}catch(Exception e){ui.post(()->{if(!destroyed&&homeMapMode&&homeDriversStatus!=null)homeDriversStatus.setText("Atualizando disponibilidade…");});}});
    }

'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('refreshHomeDrivers not found')

# Section navigation must release the home WebView instead of leaving it behind.
text=text.replace('''        cancelAddressSearch();\n        stopRidePolling();\n        LinearLayout root = vertical(LIGHT);''','''        cancelAddressSearch();\n        stopRidePolling();\n        stopHomeDriverPolling();\n        stopPassengerLiveLocation();\n        homeMapMode=false;\n        releaseMap();\n        LinearLayout root = vertical(LIGHT);''',1)

# Replace history with batch GPS previews. The preview is a Canvas only: no tile/API cost.
pat=r'''    private void showHistory\(\) \{.*?\n    \}\n\n(?=    private void showPayments\(\))'''
rep=r'''    private void showHistory() {
        LinearLayout content=showSectionShell("Histórico de corridas");content.addView(loadingText("Carregando suas corridas…"));
        runIo(()->{try{
            JSONArray rows=new JSONArray(ApiClient.restGet("rides?select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,final_fare,requested_at,payment_method_preference&order=requested_at.desc&limit=50",token));
            JSONArray previewRows=new JSONArray(ApiClient.rpc("get_my_ride_route_previews",new JSONObject().put("p_limit",50).put("p_max_points",36),token));java.util.HashMap<String,JSONArray> previews=new java.util.HashMap<>();for(int i=0;i<previewRows.length();i++){JSONObject p=previewRows.optJSONObject(i);if(p!=null)previews.put(p.optString("ride_id",""),p.optJSONArray("points"));}
            for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;double ol=r.optDouble("origin_lat",Double.NaN),og=r.optDouble("origin_lng",Double.NaN),dl=r.optDouble("destination_lat",Double.NaN),dg=r.optDouble("destination_lng",Double.NaN);r.put("_origin_address",resolveHistoryAddress(r.optString("origin_label",""),ol,og));r.put("_destination_address",resolveHistoryAddress(r.optString("destination_label",""),dl,dg));}
            ui.post(()->{if(destroyed||!content.isAttachedToWindow())return;content.removeAllViews();if(rows.length()==0){content.addView(unavailable("Nenhuma corrida ainda","Quando você fizer uma corrida, ela aparecerá aqui."));return;}for(int i=0;i<rows.length();i++){JSONObject ride=rows.optJSONObject(i);if(ride==null)continue;LinearLayout card=card(Color.WHITE,Color.rgb(232,232,232),18,15);LinearLayout top=horizontal();String st=ride.optString("status","");top.addView(text(statusLabel(st),15,BLACK,true),new LinearLayout.LayoutParams(0,-2,1));double fare=ride.isNull("final_fare")?ride.optDouble("estimated_fare",0):ride.optDouble("final_fare",0);top.addView(text(money(fare),15,BLACK,true));card.addView(top);String route=ride.optString("_origin_address","Endereço não informado")+"\n→ "+ride.optString("_destination_address","Endereço não informado");TextView rv=text(route,13,GRAY,false);rv.setPadding(0,dp(7),0,dp(5));card.addView(rv);String when=ride.optString("requested_at","");if(when.length()>=16)when=when.substring(0,16).replace('T',' ');card.addView(text(when+" · "+paymentLabel(ride.optString("payment_method_preference","cash")),12,GRAY,false));JSONArray pts=previews.get(ride.optString("id",""));if("completed".equals(st)&&pts!=null&&pts.length()>1){card.addView(space(8));RideRoutePreviewView preview=new RideRoutePreviewView(this);preview.setPoints(pts);card.addView(preview,new LinearLayout.LayoutParams(-1,dp(118)));}Button mapBtn=smallButton("VER NO MAPA");double ol=ride.optDouble("origin_lat",Double.NaN),og=ride.optDouble("origin_lng",Double.NaN),dl=ride.optDouble("destination_lat",Double.NaN),dg=ride.optDouble("destination_lng",Double.NaN);mapBtn.setOnClickListener(v->openPassengerHistoryMap(ol,og,dl,dg));card.addView(space(8));card.addView(mapBtn,lpMatch(dp(46)));content.addView(card,lpMatchWrap());content.addView(space(9));}});
        }catch(Exception e){ui.post(()->{if(!destroyed&&content.isAttachedToWindow()){content.removeAllViews();content.addView(unavailable("Não foi possível carregar",message(e)));}});}});
    }

'''
text,n=re.subn(pat,rep,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showHistory final not found')

# Verify no osmdroid allocation remains inside the startup home method.
m=re.search(r'    private void showHome\(\) \{.*?\n    \}\n\n    private void renderHomePassengerMarker',text,re.S)
if not m or 'new MapView(this)' in m.group(0): raise SystemExit('home still allocates osmdroid MapView')

build=re.sub(r'versionCode\s+\d+','versionCode 220',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.20-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.20 PRIME: reabertura sem osmdroid, teardown completo e mini-rotas aplicados.')
