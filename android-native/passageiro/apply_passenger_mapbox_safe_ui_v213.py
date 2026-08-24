from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')


def add_import(anchor: str, value: str):
    global text
    if value.strip() not in text:
        if anchor not in text:
            raise SystemExit('Import anchor não encontrado: ' + anchor.strip())
        text = text.replace(anchor, anchor + value, 1)


add_import('import android.os.Bundle;\n', 'import android.os.Build;\n')
add_import('import android.view.Gravity;\n', 'import android.view.WindowInsets;\n')
if 'import org.osmdroid.tileprovider.tilesource.OnlineTileSourceBase;' not in text:
    add_import('import org.osmdroid.tileprovider.tilesource.TileSourceFactory;\n', 'import org.osmdroid.tileprovider.tilesource.OnlineTileSourceBase;\n')
if 'import org.osmdroid.util.MapTileIndex;' not in text:
    add_import('import org.osmdroid.util.BoundingBox;\n', 'import org.osmdroid.util.MapTileIndex;\n')

# -----------------------------------------------------------------------------
# CLICK-GO Passageiro v2.13 PRIME
# - corrige recorte causado pelo edge-to-edge do Android 15/targetSdk 35;
# - usa Mapbox Streets/Satellite como mapa base, mantendo MAPNIK como fallback;
# - reverse geocoding via endpoint CLICK-GO (Mapbox primeiro + fallbacks);
# - busca de endereço regionalizada pela coordenada atual.
# -----------------------------------------------------------------------------

# O card cresceu na v2.12, mas a altura antiga continuava fixa em 142dp.
text = text.replace(
    'FrameLayout.LayoutParams bottomLp=new FrameLayout.LayoutParams(-1,dp(142));',
    'FrameLayout.LayoutParams bottomLp=new FrameLayout.LayoutParams(-1,FrameLayout.LayoutParams.WRAP_CONTENT);',
    1,
)
text = text.replace('locateLp.bottomMargin=dp(164);', 'locateLp.bottomMargin=dp(226);', 1)

# MAPNIK continua como fallback imediato, Mapbox entra assim que o token público chega.
def mapbox_after_fallback(match: re.Match) -> str:
    var = match.group(1)
    indent = match.group(2)
    return f'{var}.setTileSource(TileSourceFactory.MAPNIK);\n{indent}loadMapboxBasemap({var}, "streets-v12");'

text = re.sub(
    r'\b(map|picker)\.setTileSource\(TileSourceFactory\.MAPNIK\);\n([ \t]*)',
    mapbox_after_fallback,
    text,
)

# Botão Satélite passa a usar Mapbox Satellite Streets; não dependemos mais do tile Esri.
text = text.replace(
    'target.setTileSource(SATELLITE_SOURCE);\n            target.invalidate();',
    'loadMapboxBasemap(target, "satellite-streets-v12");',
)

# Reverse geocode confiável via API web do CLICK-GO, que já consulta Mapbox e possui fallbacks.
pattern = r'''    private void reverseGeocodeOrigin\(Location location, TextView labelView, int seq\) \{.*?\n    \}\n\n    private String shortAddress\(Address address\) \{'''
replacement = r'''    private void reverseGeocodeOrigin(Location location, TextView labelView, int seq) {
        final double lat = location.getLatitude();
        final double lng = location.getLongitude();
        io.execute(() -> {
            try {
                String url = BuildConfig.GEOCODE_URL
                        + "?reverse=1&lat=" + lat
                        + "&lng=" + lng;
                JSONObject root = new JSONObject(ApiClient.absoluteGet(url));
                JSONArray rows = root.optJSONArray("results");
                if (rows == null || rows.length() == 0) return;
                String resolved = cleanLabel(rows.getJSONObject(0).optString("label", ""));
                if (resolved.isBlank()) return;
                ui.post(() -> {
                    if (destroyed || seq != locationSeq) return;
                    originLabel = resolved;
                    if (labelView != null && labelView.isAttachedToWindow()) {
                        labelView.setText(homeMapMode ? "📍 " + resolved : resolved);
                    }
                });
            } catch (Exception ignored) {
                // Mantém "Minha localização atual" se todos os provedores estiverem indisponíveis.
            }
        });
    }

    private String shortAddress(Address address) {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('reverseGeocodeOrigin não encontrado')

# A busca de destino passa latitude/longitude atuais ao backend, melhorando resultados locais.
old = '''                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8.toString());\n                JSONObject root = new JSONObject(ApiClient.absoluteGet(url));'''
new = '''                StringBuilder url = new StringBuilder(BuildConfig.GEOCODE_URL)
                        .append("?q=")
                        .append(URLEncoder.encode(query, StandardCharsets.UTF_8.toString()));
                GeoPoint near = origin;
                if (near != null) {
                    url.append("&lat=").append(near.getLatitude())
                       .append("&lng=").append(near.getLongitude());
                }
                JSONObject root = new JSONObject(ApiClient.absoluteGet(url.toString()));'''
if old not in text:
    raise SystemExit('URL da busca de endereço não encontrada')
text = text.replace(old, new, 1)

# Evita a home ficar eternamente em "Obtendo sua localização" quando o GPS demora.
needle = '''                ui.post(() -> requestFreshLocation(manager, labelView, seq, userAction));\n'''
if needle in text:
    text = text.replace(needle, needle + '''                ui.postDelayed(() -> {
                    if (destroyed || seq != locationSeq || origin != null || labelView == null || !labelView.isAttachedToWindow()) return;
                    labelView.setText("📍 Toque em localizar ou escolha o embarque");
                }, 8000);
''', 1)

# Helpers: safe area do Android 15 e tile source Mapbox.
marker = '''    private void showHome() {\n'''
helpers = r'''    private void applySafeInsets(View root) {
        if (root == null) return;
        root.setOnApplyWindowInsetsListener((v, insets) -> {
            int left;
            int top;
            int right;
            int bottom;
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
                android.graphics.Insets bars = insets.getInsets(WindowInsets.Type.systemBars());
                left = bars.left;
                top = bars.top;
                right = bars.right;
                bottom = bars.bottom;
            } else {
                left = insets.getSystemWindowInsetLeft();
                top = insets.getSystemWindowInsetTop();
                right = insets.getSystemWindowInsetRight();
                bottom = insets.getSystemWindowInsetBottom();
            }
            v.setPadding(left, top, right, bottom);
            return insets;
        });
        root.requestApplyInsets();
    }

    private OnlineTileSourceBase mapboxRasterSource(String styleId, String accessToken) {
        return new OnlineTileSourceBase(
                "Mapbox-" + styleId,
                0,
                19,
                256,
                ".png",
                new String[]{"https://api.mapbox.com/styles/v1/mapbox/" + styleId + "/tiles/256/"}) {
            @Override public String getTileURLString(long index) {
                int z = MapTileIndex.getZoom(index);
                int x = MapTileIndex.getX(index);
                int y = MapTileIndex.getY(index);
                return "https://api.mapbox.com/styles/v1/mapbox/" + styleId
                        + "/tiles/256/" + z + "/" + x + "/" + y
                        + "?access_token=" + accessToken;
            }
        };
    }

    private void loadMapboxBasemap(MapView target, String styleId) {
        if (target == null) return;
        io.execute(() -> {
            try {
                String accessToken = mapboxToken();
                if (accessToken == null || accessToken.isBlank()) return;
                OnlineTileSourceBase source = mapboxRasterSource(styleId, accessToken);
                ui.post(() -> {
                    if (destroyed || target == null) return;
                    target.setTileSource(source);
                    target.invalidate();
                });
            } catch (Exception ignored) {
                // MAPNIK permanece como fallback de continuidade.
            }
        });
    }

'''
if marker not in text:
    raise SystemExit('showHome não encontrado para helpers')
text = text.replace(marker, helpers + marker, 1)

# Safe insets especificamente nas telas com mapa full-screen.
home_pattern = r'''(    private void showHome\(\) \{.*?        setContentView\(root\);)(.*?\n    \}\n\n    private void renderHomePassengerMarker)'''
m = re.search(home_pattern, text, flags=re.S)
if not m:
    raise SystemExit('showHome final não localizado')
home_block = m.group(1)
if 'applySafeInsets(root);' not in home_block:
    home_block = home_block.replace('        setContentView(root);', '        setContentView(root);\n        applySafeInsets(root);', 1)
text = text[:m.start(1)] + home_block + text[m.end(1):]

# Outras telas FrameLayout/LinearLayout que usam mapa também respeitam barras do sistema.
# Fazemos apenas em raízes chamadas root, logo após setContentView, sem duplicar.
text = re.sub(r'        setContentView\(root\);\n(?!        applySafeInsets\(root\);)',
              '        setContentView(root);\n        applySafeInsets(root);\n', text)

# Versão 2.13 PRIME.
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.13-prime'", build, count=1)

path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.13 PRIME: safe-area, Mapbox base e geocodificação regional aplicados.')
