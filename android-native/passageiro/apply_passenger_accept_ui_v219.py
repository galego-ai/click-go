from pathlib import Path
import re
p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
b=Path('app/build.gradle')
t=p.read_text(); g=b.read_text()

# fields
if 'private PassengerLiveMap liveTrackingMap;' not in t:
    t=t.replace('    private MapView map;\n','    private MapView map;\n    private PassengerLiveMap liveTrackingMap;\n    private boolean trackingSmokeMode;\n',1)

# release both map implementations
pat=r'''    private void releaseMap\(\) \{\n        \+\+routeSeq;\n        MapView old = map;\n        map = null;\n        if \(old != null\) \{\n            try \{ old\.onPause\(\); \} catch \(Exception ignored\) \{\}\n            try \{ old\.onDetach\(\); \} catch \(Exception ignored\) \{\}\n        \}\n    \}'''
rep='''    private void releaseMap() {\n        ++routeSeq;\n        PassengerLiveMap live=liveTrackingMap; liveTrackingMap=null;\n        if(live!=null)try{live.destroySafely();}catch(Exception ignored){}\n        MapView old=map; map=null;\n        if(old!=null){try{old.onPause();}catch(Exception ignored){} try{old.onDetach();}catch(Exception ignored){}}\n    }'''
t,n=re.subn(pat,rep,t,count=1)
if n!=1: raise SystemExit('releaseMap')

# one-shot inset helper, no persistent listener
anchor='    private void safeCenterMap(final MapView target, final GeoPoint point, final double zoom) {\n'
helper='''    private void applyRideInsetsOnce(final FrameLayout screen,final LinearLayout actions,final FrameLayout.LayoutParams lp,final LinearLayout body){\n        screen.post(new Runnable(){int tries=0;public void run(){if(destroyed||isFinishing()||!screen.isAttachedToWindow())return;WindowInsets i=screen.getRootWindowInsets();if(i==null){if(++tries<8)screen.postDelayed(this,80);return;}int bot=Build.VERSION.SDK_INT>=Build.VERSION_CODES.R?i.getInsets(WindowInsets.Type.systemBars()).bottom:i.getSystemWindowInsetBottom();int m=dp(8)+Math.max(0,bot);if(lp.bottomMargin!=m){lp.bottomMargin=m;actions.setLayoutParams(lp);}int pb=dp(126)+Math.max(0,bot);if(body.getPaddingBottom()!=pb)body.setPadding(dp(18),dp(18),dp(18),pb);}});\n    }\n\n'''
if 'private void applyRideInsetsOnce(' not in t:
    if anchor not in t: raise SystemExit('safeCenterMap')
    t=t.replace(anchor,helper+anchor,1)

# debug smoke route used only by CI
key='        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n'
smoke='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_tracking_smoke",false)){trackingSmokeMode=true;origin=new GeoPoint(-14.52472,-49.14083);destination=new GeoPoint(-14.53210,-49.14760);originLabel="Embarque teste";destinationLabel="Destino teste";activeRideId="00000000-0000-0000-0000-000000000219";activeRideStatus="accepted";trackingUiActive=true;showActiveRide();ui.postDelayed(()->{try{renderActiveDriver(new JSONObject().put("lat",-14.5254).put("lng",-49.1415).put("heading",35));}catch(Exception ignored){}},1200);ui.postDelayed(()->{try{renderActiveDriver(new JSONObject().put("lat",-14.5272).put("lng",-49.1432).put("heading",70));}catch(Exception ignored){}},3200);return;}\n'''
if 'clickgo_tracking_smoke' not in t:
    if key not in t: raise SystemExit('onCreate token')
    t=t.replace(key,smoke,1)

# accepted/searching screen. No osmdroid MapView is created after acceptance.
pat=r'''    private void showActiveRide\(\) \{.*?\n    \}\n\n    private void startRidePolling\(\) \{'''
rep=r'''    private void showActiveRide() {
        if(activeRideId==null||activeRideId.isBlank()){if(!trackingSmokeMode)restoreActiveRideIfNeeded(true);return;}
        stopRidePolling();stopHomeDriverPolling();stopPassengerLiveLocation();homeMapMode=false;releaseMap();activeRideScreenVisible=true;
        FrameLayout screen=new FrameLayout(this);screen.setBackgroundColor(LIGHT);screen.setContentDescription("clickgo_active_ride_screen");
        LinearLayout body=vertical(LIGHT);body.setPadding(dp(18),dp(18),dp(18),dp(126));body.addView(text("CLICK-GO",17,BLACK,true));body.addView(space(8));
        activeStatus=text(trackingUiActive?"Motorista a caminho":"Procurando motorista mais próximo…",25,BLACK,true);body.addView(activeStatus,lpMatchWrap());activeFare=text(selectedOption==null?"":money(selectedOption.fare),20,BLACK,true);body.addView(activeFare,lpMatchWrap());body.addView(space(12));
        final FrameLayout[] host={null};
        if(!trackingUiActive){LinearLayout c=card(Color.WHITE,Color.rgb(228,228,228),22,18);TextView i=text("⌖",46,YELLOW,true);i.setGravity(Gravity.CENTER);c.addView(i);TextView s=text("Sua chamada foi enviada. Assim que um motorista aceitar, o acompanhamento abrirá automaticamente.",15,GRAY,false);s.setGravity(Gravity.CENTER);c.addView(s);body.addView(c,lpMatchWrap());}
        else{LinearLayout dc=card(Color.WHITE,Color.rgb(226,226,226),20,14);LinearLayout row=horizontal();row.setGravity(Gravity.CENTER_VERTICAL);activeDriverPhoto=new ImageView(this);activeDriverPhoto.setScaleType(ImageView.ScaleType.CENTER_CROP);activeDriverPhoto.setImageDrawable(PassengerAvatar.markerDrawable(this));row.addView(activeDriverPhoto,new LinearLayout.LayoutParams(dp(72),dp(72)));LinearLayout cp=vertical(Color.TRANSPARENT);cp.setPadding(dp(12),0,0,0);activeDriverName=text(trackingSmokeMode?"Motorista teste":"Carregando motorista…",18,BLACK,true);activeDriverVehicle=text(trackingSmokeMode?"CLICK-GO Car · TESTE":"Carregando veículo…",13,GRAY,false);activeDriverRating=text(trackingSmokeMode?"★ 5,0":"",13,BLACK,true);cp.addView(activeDriverName);cp.addView(activeDriverVehicle);cp.addView(activeDriverRating);row.addView(cp,new LinearLayout.LayoutParams(0,dp(76),1));dc.addView(row);body.addView(dc,lpMatchWrap());body.addView(space(12));FrameLayout mf=new FrameLayout(this);mf.setBackgroundColor(Color.rgb(235,235,235));mf.setContentDescription("clickgo_live_tracking_map");TextView load=text("Carregando acompanhamento…",14,GRAY,true);load.setGravity(Gravity.CENTER);mf.addView(load,new FrameLayout.LayoutParams(-1,-1));host[0]=mf;body.addView(mf,lpMatch(dp(310)));body.addView(space(12));LinearLayout rc=card(Color.WHITE,Color.rgb(226,226,226),20,14);rc.addView(text("EMBARQUE",11,GRAY,true));rc.addView(text(cleanLabel(originLabel),14,BLACK,true));rc.addView(space(7));rc.addView(text("DESTINO",11,GRAY,true));rc.addView(text(cleanLabel(destinationLabel),14,BLACK,true));body.addView(rc,lpMatchWrap());activeWaitInfo=text("Acompanhando sua corrida em tempo real.",13,GRAY,false);LinearLayout wc=card(Color.rgb(255,248,219),Color.rgb(242,215,107),16,12);wc.addView(activeWaitInfo);body.addView(wc,lpMatchWrap());}
        ScrollView content=new ScrollView(this);content.setFillViewport(true);content.addView(body,new ScrollView.LayoutParams(-1,-2));screen.addView(content,new FrameLayout.LayoutParams(-1,-1));LinearLayout actions=horizontal();actions.setGravity(Gravity.CENTER_VERTICAL);actions.setPadding(dp(12),dp(10),dp(12),dp(10));actions.setBackground(round(Color.WHITE,22,Color.rgb(225,225,225)));Button chat=secondaryLight("💬");Button cancel=secondaryLight("CANCELAR CORRIDA");cancel.setTextColor(Color.rgb(185,45,45));actions.addView(chat,new LinearLayout.LayoutParams(dp(62),dp(58)));actions.addView(spaceH(9));actions.addView(cancel,new LinearLayout.LayoutParams(0,dp(58),1));FrameLayout.LayoutParams alp=new FrameLayout.LayoutParams(-1,FrameLayout.LayoutParams.WRAP_CONTENT);alp.gravity=Gravity.BOTTOM;alp.leftMargin=dp(10);alp.rightMargin=dp(10);alp.bottomMargin=dp(8);screen.addView(actions,alp);chat.setOnClickListener(v->{if(!trackingSmokeMode)openRideChat(activeRideId);});cancel.setOnClickListener(v->{if(!trackingSmokeMode)previewCancel();});setContentView(screen);applyRideInsetsOnce(screen,actions,alp,body);
        if(trackingUiActive&&host[0]!=null){FrameLayout h=host[0];h.post(()->{if(destroyed||isFinishing()||!trackingUiActive||activeRideId==null||!h.isAttachedToWindow())return;PassengerLiveMap live=new PassengerLiveMap(this);liveTrackingMap=live;h.removeAllViews();h.addView(live,new FrameLayout.LayoutParams(-1,-1));if(origin!=null&&destination!=null)live.setRoute(origin.getLatitude(),origin.getLongitude(),destination.getLatitude(),destination.getLongitude());if(!trackingSmokeMode)ui.postDelayed(this::startPassengerLiveLocation,300);});}
        if(!trackingSmokeMode)startRidePolling();
    }

    private void startRidePolling() {'''
t,n=re.subn(pat,rep,t,count=1,flags=re.S)
if n!=1: raise SystemExit('showActiveRide')

# active driver location goes to isolated WebView map
pat=r'''    private void renderActiveDriver\(JSONObject loc\) \{.*?\n    \}\n\n    private void drawActiveDriverRoadRoute'''
rep=r'''    private void renderActiveDriver(JSONObject loc) {
        if(loc==null)return;double lat=loc.optDouble("lat",Double.NaN),lng=loc.optDouble("lng",Double.NaN);if(!Double.isFinite(lat)||!Double.isFinite(lng))return;double heading=loc.optDouble("heading",0);if(liveTrackingMap!=null){liveTrackingMap.updateDriver(lat,lng,heading,activeDriverVehicleType);return;}if(map==null)return;if(activeDriverMarker==null){activeDriverMarker=new Marker(map);activeDriverMarker.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_CENTER);activeDriverMarker.setTitle("Motorista em tempo real");map.getOverlays().add(activeDriverMarker);}activeDriverMarker.setPosition(new GeoPoint(lat,lng));activeDriverMarker.setIcon(vehicleMarkerIcon(activeDriverVehicleType));try{activeDriverMarker.setRotation((float)heading);}catch(Exception ignored){}map.invalidate();
    }

    private void drawActiveDriverRoadRoute'''
t,n=re.subn(pat,rep,t,count=1,flags=re.S)
if n!=1: raise SystemExit('renderActiveDriver')

# passenger position on live map
old='''    private void sendPassengerLiveLocation(Location location) {\n        String rideId=activeRideId; if(rideId==null||location==null)return;'''
new='''    private void sendPassengerLiveLocation(Location location) {\n        String rideId=activeRideId; if(rideId==null||location==null)return;\n        if(liveTrackingMap!=null)liveTrackingMap.updatePassenger(location.getLatitude(),location.getLongitude());'''
if old not in t: raise SystemExit('sendPassengerLiveLocation')
t=t.replace(old,new,1)

# CI smoke never polls network
a='''    private void startRidePolling() {\n        stopRidePolling();'''
if a not in t: raise SystemExit('startRidePolling')
t=t.replace(a,'''    private void startRidePolling() {\n        stopRidePolling();\n        if(trackingSmokeMode)return;''',1)

m=re.search(r'    private void showActiveRide\(\) \{.*?\n    \}\n\n    private void startRidePolling',t,re.S)
if not m or 'new MapView(this)' in m.group(0) or 'setOnApplyWindowInsetsListener' in m.group(0): raise SystemExit('active screen still unsafe')
g=re.sub(r'versionCode\s+\d+','versionCode 219',g,count=1);g=re.sub(r"versionName\s+'[^']+'","versionName '2.19-prime'",g,count=1)
p.write_text(t);b.write_text(g)
print('Passageiro v2.19 UI: tela pos-aceite sem osmdroid e sem listener persistente de insets.')
