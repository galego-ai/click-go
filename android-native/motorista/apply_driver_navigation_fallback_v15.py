from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text = path.read_text(encoding='utf-8')

# v1.5 PRIME: não usar resolveActivity(), pois em Android 11+ a visibilidade de pacotes
# pode retornar null mesmo quando Google Maps/Waze/navegador estão instalados.
pattern = r'''    private void openNavigation\(double lat, double lng, String label\) \{.*?\n    \}\n\n'''
replacement = r'''    private void openNavigation(double lat, double lng, String label) {
        if (!Double.isFinite(lat) || !Double.isFinite(lng)) {
            toast("A localização desta corrida não está disponível.");
            return;
        }

        String destination = lat + "," + lng;
        Uri googleUri = Uri.parse("https://www.google.com/maps/dir/?api=1&destination="
                + Uri.encode(destination) + "&travelmode=driving");

        // 1) Google Maps instalado.
        try {
            Intent googleMaps = new Intent(Intent.ACTION_VIEW, googleUri);
            googleMaps.setPackage("com.google.android.apps.maps");
            startActivity(googleMaps);
            return;
        } catch (Exception ignored) {
        }

        // 2) Waze instalado.
        try {
            Uri wazeUri = Uri.parse("https://waze.com/ul?ll=" + lat + "," + lng + "&navigate=yes");
            Intent waze = new Intent(Intent.ACTION_VIEW, wazeUri);
            waze.setPackage("com.waze");
            startActivity(waze);
            return;
        } catch (Exception ignored) {
        }

        // 3) Qualquer app que aceite coordenadas geo:.
        try {
            String safeLabel = label == null || label.isBlank() ? "Destino CLICK-GO" : label;
            Uri geoUri = Uri.parse("geo:" + lat + "," + lng + "?q="
                    + Uri.encode(lat + "," + lng + " (" + safeLabel + ")"));
            startActivity(new Intent(Intent.ACTION_VIEW, geoUri));
            return;
        } catch (Exception ignored) {
        }

        // 4) Fallback universal: abre a rota HTTPS no navegador, sem depender de app de mapas.
        try {
            Intent browser = new Intent(Intent.ACTION_VIEW, googleUri);
            startActivity(browser);
            return;
        } catch (Exception ignored) {
        }

        toast("Não foi possível abrir a navegação. Verifique se há um navegador instalado.");
    }

'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('openNavigation v1.4 não encontrado para aplicar fallback v1.5')

path.write_text(text, encoding='utf-8')

# Declara visibilidade para Google Maps, Waze e handlers de navegação em Android 11+.
manifest_path = Path('app/src/main/AndroidManifest.xml')
manifest = manifest_path.read_text(encoding='utf-8')
if '<queries>' not in manifest:
    queries = '''\n    <queries>\n        <package android:name="com.google.android.apps.maps" />\n        <package android:name="com.waze" />\n        <intent>\n            <action android:name="android.intent.action.VIEW" />\n            <data android:scheme="geo" />\n        </intent>\n        <intent>\n            <action android:name="android.intent.action.VIEW" />\n            <data android:scheme="https" />\n        </intent>\n    </queries>\n'''
    manifest = manifest.replace('    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n',
                                '    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n' + queries,
                                1)
manifest_path.write_text(manifest, encoding='utf-8')

# Nova versão nativa do motorista.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '1.5-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

print('Motorista v1.5 PRIME: navegação Google Maps/Waze/geo/navegador com fallback robusto.')
