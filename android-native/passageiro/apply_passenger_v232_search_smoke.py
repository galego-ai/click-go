from pathlib import Path

p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
t=p.read_text(encoding='utf-8')

if 'clickgo_search_timer_smoke' not in t:
    anchor='        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n'
    block='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_search_timer_smoke",false)){\n            trackingSmokeMode=true;\n            origin=new GeoPoint(-14.52472,-49.14083);\n            destination=new GeoPoint(-14.53210,-49.14760);\n            originLabel="Embarque teste";destinationLabel="Destino teste";\n            activeRideId="00000000-0000-0000-0000-000000000232";\n            activeRideStatus="searching";trackingUiActive=false;\n            callStartedAtMs=System.currentTimeMillis()-5000L;driverFoundElapsedMs=0L;\n            showActiveRide();\n            return;\n        }\n'''
    if anchor not in t:
        raise SystemExit('token anchor nao encontrado para smoke do cronometro')
    t=t.replace(anchor,block,1)

for required in ['clickgo_search_timer_smoke','clickgo_search_timer_popup','Procurando motorista','Cancelar chamada']:
    if required not in t:
        raise SystemExit('smoke v2.32 incompleto: '+required)

p.write_text(t,encoding='utf-8')
print('Passageiro v2.32: smoke isolado do popup circular de busca aplicado.')
