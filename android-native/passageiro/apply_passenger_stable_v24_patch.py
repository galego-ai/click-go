from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

# 1) A tela de opções não precisa redesenhar motoristas online. Eles já aparecem
# na home e, após o aceite, o motorista aceito é acompanhado em tempo real.
# Em alguns aparelhos/versões do osmdroid, alterações concorrentes de Marker +
# Polyline durante a montagem da tela podem derrubar a Activity fora do nosso try/catch.
pattern = r'''    private void renderNearbyDrivers\(\) \{.*?\n    \}\n\n    private void renderActiveDriver\(JSONObject loc\) \{'''
replacement = r'''    private void renderNearbyDrivers() {
        // v2.4 PRIME stable mode: não altera overlays de motoristas na tela de opções.
        // A home continua mostrando motoristas online próximos normalmente.
        // Depois do aceite, renderActiveDriver() assume o rastreamento do motorista.
        if (!optionDriverMarkers.isEmpty() && map != null) {
            try {
                for (Marker marker : new ArrayList<>(optionDriverMarkers.values())) {
                    if (marker != null) map.getOverlays().remove(marker);
                }
                optionDriverMarkers.clear();
                map.invalidate();
            } catch (RuntimeException ignored) {
                optionDriverMarkers.clear();
            }
        }
    }

    private void renderActiveDriver(JSONObject loc) {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('renderNearbyDrivers final não encontrado para modo estável')

# 2) Reduz a quantidade máxima de pontos desenhados da rota. Em rotas grandes,
# 550 pontos + tiles + UI de categorias é desnecessariamente pesado em aparelhos antigos.
text = text.replace('int step = Math.max(1, coords.length() / 550);',
                    'int step = Math.max(1, coords.length() / 180);', 1)

# 3) Antes de abrir a tela de opções, invalida respostas antigas de motoristas e
# garante que nenhum Marker dessa etapa anterior sobreviva.
old = '''    private void showOptions() {\n        cancelAddressSearch();\n        hideKeyboard();\n        releaseMap();\n        homePassengerMarker=null;\n        activeDriverMarker=null;\n        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n'''
new = '''    private void showOptions() {\n        cancelAddressSearch();\n        hideKeyboard();\n        nearbyDriversSeq++;\n        releaseMap();\n        homePassengerMarker=null;\n        activeDriverMarker=null;\n        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n'''
if old in text:
    text = text.replace(old, new, 1)
elif 'nearbyDriversSeq++;\n        releaseMap();' not in text:
    raise SystemExit('showOptions final não encontrado')

# 4) Diagnóstico local de crash. Não envia dados para servidor. No próximo início,
# mostra apenas classe + primeiro ponto do app no stack, suficiente para localizar
# um eventual fechamento restante durante esta fase de testes.
if 'private void installLocalCrashDiagnostic()' not in text:
    oncreate_anchor = '''    @Override protected void onCreate(Bundle savedInstanceState) {\n        super.onCreate(savedInstanceState);\n'''
    oncreate_new = '''    @Override protected void onCreate(Bundle savedInstanceState) {\n        super.onCreate(savedInstanceState);\n        installLocalCrashDiagnostic();\n'''
    if oncreate_anchor not in text:
        raise SystemExit('onCreate não encontrado para diagnóstico')
    text = text.replace(oncreate_anchor, oncreate_new, 1)

    method_anchor = '''    private void showLogin() {\n'''
    diagnostic_methods = r'''    private void installLocalCrashDiagnostic() {
        final android.content.Context appContext = getApplicationContext();
        final android.content.SharedPreferences crashPrefs = appContext.getSharedPreferences("clickgo_passenger_crash", MODE_PRIVATE);
        final Thread.UncaughtExceptionHandler previous = Thread.getDefaultUncaughtExceptionHandler();
        Thread.setDefaultUncaughtExceptionHandler((thread, error) -> {
            try {
                String where = "";
                if (error != null && error.getStackTrace() != null) {
                    for (StackTraceElement element : error.getStackTrace()) {
                        if (element != null && element.getClassName() != null && element.getClassName().startsWith("com.clickgo.passageiro")) {
                            where = element.getClassName().replace("com.clickgo.passageiro.", "") + ":" + element.getLineNumber();
                            break;
                        }
                    }
                }
                String type = error == null ? "Erro" : error.getClass().getSimpleName();
                crashPrefs.edit().putString("last_crash", type + (where.isBlank() ? "" : " @ " + where)).apply();
            } catch (Exception ignored) {}
            if (previous != null) previous.uncaughtException(thread, error);
        });
        String lastCrash = crashPrefs.getString("last_crash", "");
        if (lastCrash != null && !lastCrash.isBlank()) {
            crashPrefs.edit().remove("last_crash").apply();
            ui.postDelayed(() -> {
                if (!destroyed && !isFinishing()) toast("Diagnóstico do último fechamento: " + lastCrash);
            }, 900);
        }
    }

'''
    if method_anchor not in text:
        raise SystemExit('showLogin não encontrado para inserir diagnóstico')
    text = text.replace(method_anchor, diagnostic_methods + method_anchor, 1)

# 5) Versão v2.4 PRIME.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.4-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Passageiro v2.4 PRIME: mapa de opções em modo estável + diagnóstico local de crash.')
