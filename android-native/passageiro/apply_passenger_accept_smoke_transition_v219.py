from pathlib import Path

p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
t=p.read_text(encoding='utf-8')
old='''        if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_tracking_smoke",false)){trackingSmokeMode=true;origin=new GeoPoint(-14.52472,-49.14083);destination=new GeoPoint(-14.53210,-49.14760);originLabel="Embarque teste";destinationLabel="Destino teste";activeRideId="00000000-0000-0000-0000-000000000219";activeRideStatus="accepted";trackingUiActive=true;showActiveRide();ui.postDelayed(()->{try{renderActiveDriver(new JSONObject().put("lat",-14.5254).put("lng",-49.1415).put("heading",35));}catch(Exception ignored){}},1200);ui.postDelayed(()->{try{renderActiveDriver(new JSONObject().put("lat",-14.5272).put("lng",-49.1432).put("heading",70));}catch(Exception ignored){}},3200);return;}\n'''
new='''        if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_tracking_smoke",false)){\n            trackingSmokeMode=true;\n            origin=new GeoPoint(-14.52472,-49.14083);destination=new GeoPoint(-14.53210,-49.14760);\n            originLabel="Embarque teste";destinationLabel="Destino teste";\n            activeRideId="00000000-0000-0000-0000-000000000219";activeRideStatus="searching";trackingUiActive=false;\n            showActiveRide();\n            ui.postDelayed(()->{if(destroyed||isFinishing())return;activeRideStatus="accepted";trackingUiActive=true;showActiveRide();},1400);\n            ui.postDelayed(()->{try{renderActiveDriver(new JSONObject().put("lat",-14.5254).put("lng",-49.1415).put("heading",35));}catch(Exception ignored){}},3200);\n            ui.postDelayed(()->{try{renderActiveDriver(new JSONObject().put("lat",-14.5272).put("lng",-49.1432).put("heading",70));}catch(Exception ignored){}},5600);\n            return;\n        }\n'''
if old not in t:
    raise SystemExit('smoke block not found')
t=t.replace(old,new,1)
p.write_text(t,encoding='utf-8')
print('Passageiro v2.19 smoke: transição searching -> accepted exercitada em CI.')
