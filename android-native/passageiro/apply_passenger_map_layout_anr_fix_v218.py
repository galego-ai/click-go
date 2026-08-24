from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.18 PRIME
# Correção de ANR no mapa para aparelhos em que o primeiro layout demora mais.
# osmdroid pode entrar em loop dentro de zoomToBoundingBox quando chamado antes
# de MapView.onLayout. Toda centralização/zoom passa a aguardar layout real.

# Configuração conservadora do osmdroid antes de criar qualquer MapView.
ua = '        Configuration.getInstance().setUserAgentValue("CLICK-GO-Passageiro-Android/0.2");\n'
if ua in text and 'setMapViewHardwareAccelerated(false)' not in text:
    text = text.replace(
        ua,
        ua
        + '        Configuration.getInstance().setMapViewHardwareAccelerated(false);\n'
        + '        Configuration.getInstance().setMapViewRecyclerFriendly(false);\n',
        1,
    )

# Helpers: nunca chama zoomToBoundingBox/centralização antes de o mapa ter
# largura, altura, attachment e layout válidos. Tenta por até ~3 s e abandona
# silenciosamente se a Activity/tela já tiver mudado.
helper_marker = '    private void applySafeInsets(View root) {\n'
helpers = r'''    private void safeCenterMap(final MapView target, final GeoPoint point, final double zoom) {
        if (target == null || point == null) return;
        target.post(new Runnable() {
            int attempts = 0;
            @Override public void run() {
                if (destroyed || isFinishing()) return;
                boolean ready = target.isAttachedToWindow()
                        && target.isLayoutOccurred()
                        && target.getWidth() > 0
                        && target.getHeight() > 0
                        && Double.isFinite(target.getZoomLevelDouble());
                if (ready) {
                    try {
                        target.getController().setZoom(zoom);
                        target.getController().setCenter(point);
                        target.invalidate();
                    } catch (Exception ignored) {}
                    return;
                }
                if (++attempts <= 30) target.postDelayed(this, 100);
            }
        });
    }

    private void safeZoomToPoints(final MapView target, final List<GeoPoint> sourcePoints, final int borderPx) {
        if (target == null || sourcePoints == null || sourcePoints.size() < 2) return;
        final List<GeoPoint> points = new ArrayList<>(sourcePoints);
        target.post(new Runnable() {
            int attempts = 0;
            @Override public void run() {
                if (destroyed || isFinishing()) return;
                boolean ready = target.isAttachedToWindow()
                        && target.isLayoutOccurred()
                        && target.getWidth() > 0
                        && target.getHeight() > 0
                        && Double.isFinite(target.getZoomLevelDouble());
                if (ready) {
                    try {
                        BoundingBox box = BoundingBox.fromGeoPoints(points);
                        if (box != null
                                && Double.isFinite(box.getLatNorth())
                                && Double.isFinite(box.getLatSouth())
                                && Double.isFinite(box.getLonEast())
                                && Double.isFinite(box.getLonWest())) {
                            target.zoomToBoundingBox(box, false, borderPx);
                            target.invalidate();
                        }
                    } catch (Exception ignored) {}
                    return;
                }
                if (++attempts <= 30) target.postDelayed(this, 100);
            }
        });
    }

'''
if 'private void safeZoomToPoints(' not in text:
    if helper_marker not in text:
        raise SystemExit('v2.18: applySafeInsets não encontrado')
    text = text.replace(helper_marker, helpers + helper_marker, 1)

# MIUI/HyperOS: evita realimentar layout/insets quando o padding já está correto.
old_insets = '''            v.setPadding(left, top, right, bottom);\n            return insets;'''
new_insets = '''            if (v.getPaddingLeft() != left || v.getPaddingTop() != top ||\n                    v.getPaddingRight() != right || v.getPaddingBottom() != bottom) {\n                v.setPadding(left, top, right, bottom);\n            }\n            return insets;'''
if old_insets in text:
    text = text.replace(old_insets, new_insets, 1)
text = text.replace('        root.requestApplyInsets();\n', '        root.post(root::requestApplyInsets);\n', 1)

# Centralização da home: remove animateTo durante o primeiro layout.
center_pattern = r'''    private void centerHomeMap\(\)\{.*?\n    \}\n\n    private void startHomeDriverPolling\(\)\{'''
center_replacement = r'''    private void centerHomeMap(){
        if(!homeMapMode||map==null||origin==null)return;
        renderHomePassengerMarker();
        if(!homeCentered){
            homeCentered=true;
            safeCenterMap(map, origin, 15.2);
        }
    }

    private void startHomeDriverPolling(){'''
text, n = re.subn(center_pattern, center_replacement, text, count=1, flags=re.S)
if n != 1:
    # Formatação alternativa dos patches mais antigos.
    center_pattern2 = r'''    private void centerHomeMap\(\) \{.*?\n    \}\n\n    private void startHomeDriverPolling\(\) \{'''
    text, n = re.subn(center_pattern2, center_replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('v2.18: centerHomeMap final não encontrado')

# Não consulta/renderiza motoristas no mesmo frame em que o mapa nasce.
text = text.replace('        ui.post(homeDriverPoll);\n', '        ui.postDelayed(homeDriverPoll,700);\n', 1)

# Substitui TODAS as chamadas diretas conhecidas de zoomToBoundingBox geradas
# pela cadeia de patches. Esse é o ponto crítico do bug do osmdroid.
zoom_re = re.compile(
    r'(?P<target>\b(?:map|routeMap)\b)\.zoomToBoundingBox\('
    r'BoundingBox\.fromGeoPoints\((?P<points>\w+)\),\s*'
    r'(?:true|false),\s*(?P<border>dp\(\d+\)|\d+)\);'
)
text, zoom_count = zoom_re.subn(
    lambda m: f'safeZoomToPoints({m.group("target")}, {m.group("points")}, {m.group("border")});',
    text,
)

# A versão antiga do ANR hardening podia postar zoom imediatamente, ainda antes
# de onLayout em aparelhos mais lentos. Normaliza esse bloco se restar.
old_post_zoom = '''        final MapView routeMap = map;\n        final List<GeoPoint> safeRoute = new ArrayList<>(routePoints);\n        routeMap.post(() -> {\n            if (destroyed || map != routeMap) return;\n            try { routeMap.zoomToBoundingBox(BoundingBox.fromGeoPoints(safeRoute), true, dp(70)); } catch (Exception ignored) {}\n            routeMap.invalidate();\n        });'''
new_post_zoom = '''        final MapView routeMap = map;\n        final List<GeoPoint> safeRoute = new ArrayList<>(routePoints);\n        safeZoomToPoints(routeMap, safeRoute, dp(70));'''
if old_post_zoom in text:
    text = text.replace(old_post_zoom, new_post_zoom, 1)

# Se ainda existir alguma chamada direta, falha o build do patch para não
# publicar outra versão sujeita ao mesmo loop infinito.
remaining = [line.strip() for line in text.splitlines() if '.zoomToBoundingBox(' in line and 'target.zoomToBoundingBox(box' not in line]
if remaining:
    raise SystemExit('v2.18: zoomToBoundingBox direto ainda presente: ' + ' | '.join(remaining[:5]))

# Marca versão final, independentemente dos versionCodes intermediários.
build = re.sub(r'versionCode\s+\d+', 'versionCode 218', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.18-prime'", build, count=1)

main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print(f'Passageiro v2.18 PRIME: mapa protegido contra pré-layout; {zoom_count} zoom(s) normalizado(s).')
