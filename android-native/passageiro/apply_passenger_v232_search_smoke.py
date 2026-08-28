from pathlib import Path

p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
t=p.read_text(encoding='utf-8')

if 'clickgo_search_timer_smoke' not in t:
    anchor='        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n'
    block='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_search_timer_smoke",false)){\n            trackingSmokeMode=true;\n            origin=new GeoPoint(-14.52472,-49.14083);\n            destination=new GeoPoint(-14.53210,-49.14760);\n            originLabel="Embarque teste";destinationLabel="Destino teste";\n            activeRideId="00000000-0000-0000-0000-000000000232";\n            activeRideStatus="searching";trackingUiActive=false;\n            callStartedAtMs=System.currentTimeMillis()-5000L;driverFoundElapsedMs=0L;\n            showActiveRide();\n            return;\n        }\n'''
    if anchor not in t:
        raise SystemExit('token anchor nao encontrado para smoke do cronometro')
    t=t.replace(anchor,block,1)

# O smoke antigo de corrida aceita agora passa primeiro pelo estado de busca.
accepted='''            activeRideId="00000000-0000-0000-0000-000000000219";activeRideStatus="accepted";trackingUiActive=true;\n            showActiveRide();\n            if(BuildConfig.DEBUG)android.util.Log.i("CLICKGO_TRACKING_SMOKE","accepted tracking screen rendered");\n'''
transition='''            activeRideId="00000000-0000-0000-0000-000000000219";activeRideStatus="searching";trackingUiActive=false;\n            callStartedAtMs=System.currentTimeMillis();driverFoundElapsedMs=0L;\n            showActiveRide();\n            if(BuildConfig.DEBUG)android.util.Log.i("CLICKGO_TRACKING_SMOKE","search popup rendered");\n            ui.postDelayed(()->{if(destroyed||isFinishing())return;activeRideStatus="accepted";trackingUiActive=true;showActiveRide();if(BuildConfig.DEBUG)android.util.Log.i("CLICKGO_TRACKING_SMOKE","accepted tracking screen rendered after search");},1800L);\n'''
if accepted in t:
    t=t.replace(accepted,transition,1)
elif 'accepted tracking screen rendered after search' not in t:
    raise SystemExit('bloco de smoke accepted v2.30 nao encontrado')

for required in ['clickgo_search_timer_smoke','clickgo_search_timer_popup','Procurando motorista','Cancelar chamada','search popup rendered','accepted tracking screen rendered after search']:
    if required not in t:
        raise SystemExit('smoke v2.32 incompleto: '+required)

p.write_text(t,encoding='utf-8')
print('Passageiro v2.32: smoke de busca circular e transicao para aceite aplicado.')
