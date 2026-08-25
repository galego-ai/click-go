from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# v2.23 PRIME
# - PassengerHomeMap and PassengerLiveMap now isolate WebView renderer failures;
# - renderer death no longer needs to terminate the Activity;
# - remote Leaflet bootstrap is bounded instead of retrying forever;
# - detached first-party ad banner no longer submits work to a stopped executor;
# - adds a CI home mode that keeps real background polling/ad requests enabled.

home = Path('app/src/main/java/com/clickgo/passageiro/PassengerHomeMap.java').read_text(encoding='utf-8')
live = Path('app/src/main/java/com/clickgo/passageiro/PassengerLiveMap.java').read_text(encoding='utf-8')
ad = Path('app/src/main/java/com/clickgo/passageiro/FirstPartyAdBannerView.java').read_text(encoding='utf-8')

if 'onRenderProcessGone' not in home or 'onRenderProcessGone' not in live:
    raise SystemExit('WebView crash shield is missing')
if 'RejectedExecutionException' not in ad or 'imageIo.isShutdown()' not in ad:
    raise SystemExit('ad executor crash guard is missing')

# Existing home smoke intentionally bypasses network. Add a second debug-only mode
# that opens the same Home with background services enabled and an invalid token.
# Calls may fail with 401, but all such failures must stay contained and the app
# process must remain alive.
smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_home_smoke",false)){homeSmokeMode=true;token="smoke";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Localização de teste";showHome();return;}'
network_smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_home_network_smoke",false)){token="network-smoke-invalid-token";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Localização de teste com serviços ativos";showHome();return;}'
if 'clickgo_home_network_smoke' not in text:
    if smoke not in text:
        raise SystemExit('home smoke anchor not found')
    text = text.replace(smoke, smoke + '\n        ' + network_smoke, 1)

build = re.sub(r'versionCode\s+\d+', 'versionCode 223', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.23-prime'", build, count=1)
main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.23 PRIME: proteção WebView/banner e smoke com serviços reais aplicados.')

# O workflow já executa este patch como o último estágio. Encadeia a correção v2.24
# sem alterar o arquivo de workflow nem tocar em secrets/credenciais.
v224 = Path('apply_passenger_address_results_v224.py')
if not v224.exists():
    raise SystemExit('apply_passenger_address_results_v224.py não encontrado')
exec(compile(v224.read_text(encoding='utf-8'), str(v224), 'exec'), {})

# v2.25: busca real resiliente + fallback nativo + Buscar no mapa dentro do app.
v225 = Path('apply_passenger_address_search_map_v225.py')
if not v225.exists():
    raise SystemExit('apply_passenger_address_search_map_v225.py não encontrado')
exec(compile(v225.read_text(encoding='utf-8'), str(v225), 'exec'), {})
