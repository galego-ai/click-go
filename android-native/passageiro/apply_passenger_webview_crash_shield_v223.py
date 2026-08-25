from pathlib import Path
import re

build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')

# v2.23 PRIME
# - PassengerHomeMap and PassengerLiveMap now isolate WebView renderer failures;
# - renderer death no longer needs to terminate the Activity;
# - remote Leaflet bootstrap is bounded instead of retrying forever;
# - detached first-party ad banner no longer submits work to a stopped executor.

home = Path('app/src/main/java/com/clickgo/passageiro/PassengerHomeMap.java').read_text(encoding='utf-8')
live = Path('app/src/main/java/com/clickgo/passageiro/PassengerLiveMap.java').read_text(encoding='utf-8')
ad = Path('app/src/main/java/com/clickgo/passageiro/FirstPartyAdBannerView.java').read_text(encoding='utf-8')

if 'onRenderProcessGone' not in home or 'onRenderProcessGone' not in live:
    raise SystemExit('WebView crash shield is missing')
if 'RejectedExecutionException' not in ad or 'imageIo.isShutdown()' not in ad:
    raise SystemExit('ad executor crash guard is missing')

build = re.sub(r'versionCode\s+\d+', 'versionCode 223', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.23-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.23 PRIME: proteção contra falha do WebView/renderer e corrida do banner aplicada.')
