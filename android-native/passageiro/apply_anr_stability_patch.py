from pathlib import Path

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = main_path.read_text(encoding='utf-8')

def repl(old, new, name):
    global text
    if old not in text:
        raise SystemExit(f'Trecho não encontrado: {name}')
    text = text.replace(old, new, 1)

# Uma única fila para autocomplete. Evita duas buscas HTTP concorrentes disputando CPU/rede.
repl('''    private final ExecutorService addressIo = Executors.newFixedThreadPool(2);\n''', '''    private final ExecutorService addressIo = Executors.newSingleThreadExecutor();\n''', 'executor de endereços')

# O autocomplete não desmonta/remonta a lista a cada tecla. Só mexe na UI quando o debounce termina.
old_schedule = '''    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {\n        final int seq = ++searchSeq;\n        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);\n        if (addressFuture != null) addressFuture.cancel(true);\n        target.removeAllViews();\n        if (query.length() < 3) return;\n\n        TextView loading = text("Buscando endereços e locais próximos…", 13, GRAY, false);\n        loading.setPadding(dp(8), dp(10), dp(8), dp(6));\n        target.addView(loading, lpMatchWrap());\n\n        pendingAddressSearch = () -> {\n            if (seq != searchSeq || destroyed) return;\n            startAddressSearch(query, target, forOrigin, originView, dialog, seq);\n        };\n        ui.postDelayed(pendingAddressSearch, 650);\n    }\n'''
new_schedule = '''    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {\n        final int seq = ++searchSeq;\n        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);\n        if (query.length() < 3) {\n            target.removeAllViews();\n            return;\n        }\n\n        pendingAddressSearch = () -> {\n            if (seq != searchSeq || destroyed || !target.isAttachedToWindow()) return;\n            target.removeAllViews();\n            TextView loading = text("Buscando endereços e locais próximos…", 13, GRAY, false);\n            loading.setPadding(dp(8), dp(10), dp(8), dp(6));\n            target.addView(loading, lpMatchWrap());\n            startAddressSearch(query, target, forOrigin, originView, dialog, seq);\n        };\n        ui.postDelayed(pendingAddressSearch, 850);\n    }\n'''
repl(old_schedule, new_schedule, 'debounce da busca')

# Requisição velha que já entrou na rede não é interrompida no meio; ela apenas é ignorada pelo seq.
# Interromper HttpURLConnection repetidamente em alguns Androids pode provocar contenção e ANR.
repl('''        if (addressFuture != null) {\n            addressFuture.cancel(true);\n            addressFuture = null;\n        }\n''', '''        if (addressFuture != null) {\n            if (!addressFuture.isDone()) addressFuture.cancel(false);\n            addressFuture = null;\n        }\n''', 'cancelamento de busca')

# Descarta tarefa velha antes de abrir conexão.
repl('''        addressFuture = addressIo.submit(() -> {\n            try {\n                String url = BuildConfig.GEOCODE_URL''', '''        addressFuture = addressIo.submit(() -> {\n            try {\n                if (destroyed || seq != searchSeq) return;\n                String url = BuildConfig.GEOCODE_URL''', 'guarda da busca')

# Exibe primeiro a tela do mapa e só então desenha marcadores/rota.
repl('''        setContentView(root);\n        drawRoute();\n        loadOptions();\n''', '''        setContentView(root);\n        final MapView firstMap = map;\n        firstMap.post(() -> {\n            if (!destroyed && map == firstMap) drawRoute();\n        });\n        loadOptions();\n''', 'desenho inicial do mapa')

# O zoom passa a ocorrer após o MapView estar medido, evitando trabalho pesado durante a troca de tela.
old_zoom = '''        try { map.zoomToBoundingBox(BoundingBox.fromGeoPoints(routePoints), true, dp(70)); } catch (Exception ignored) {}\n        map.invalidate();\n    }\n'''
new_zoom = '''        final MapView routeMap = map;\n        final List<GeoPoint> safeRoute = new ArrayList<>(routePoints);\n        routeMap.post(() -> {\n            if (destroyed || map != routeMap) return;\n            try { routeMap.zoomToBoundingBox(BoundingBox.fromGeoPoints(safeRoute), true, dp(70)); } catch (Exception ignored) {}\n            routeMap.invalidate();\n        });\n    }\n'''
repl(old_zoom, new_zoom, 'zoom do mapa')

# Quando a foto chega, atualiza apenas o cabeçalho. Não dispara uma segunda rota/HTTP em paralelo.
repl('''        PassengerAvatar.preload(this, token, () -> {\n            avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));\n            if (map != null && origin != null && destination != null) drawRoute();\n        });\n''', '''        PassengerAvatar.preload(this, token, () -> {\n            if (!destroyed && avatar.isAttachedToWindow()) {\n                avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));\n            }\n        });\n''', 'callback de avatar')

# Marca a nova versão.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
build = build.replace('versionCode 10', 'versionCode 11', 1)
build = build.replace("versionName '1.0-native-beta'", "versionName '1.1-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

main_path.write_text(text, encoding='utf-8')

# Reduz a foto antes de mantê-la na memória. Fotos de câmera podem ter 10-30 MP e provocar GC/ANR.
avatar_path = Path('app/src/main/java/com/clickgo/passageiro/PassengerAvatar.java')
avatar = avatar_path.read_text(encoding='utf-8')
if 'import java.io.ByteArrayOutputStream;' not in avatar:
    avatar = avatar.replace('import java.io.InputStream;\n', 'import java.io.InputStream;\nimport java.io.ByteArrayOutputStream;\n', 1)

old_decode = '''            try (InputStream input = connection.getInputStream()) {\n                return BitmapFactory.decodeStream(input);\n            }\n'''
new_decode = '''            try (InputStream input = connection.getInputStream()) {\n                byte[] data = readLimited(input, 8 * 1024 * 1024);\n                if (data.length == 0) return null;\n\n                BitmapFactory.Options bounds = new BitmapFactory.Options();\n                bounds.inJustDecodeBounds = true;\n                BitmapFactory.decodeByteArray(data, 0, data.length, bounds);\n                int sample = 1;\n                int maxSide = Math.max(bounds.outWidth, bounds.outHeight);\n                while (maxSide / sample > 768) sample *= 2;\n\n                BitmapFactory.Options options = new BitmapFactory.Options();\n                options.inSampleSize = Math.max(1, sample);\n                options.inPreferredConfig = Bitmap.Config.ARGB_8888;\n                Bitmap decoded = BitmapFactory.decodeByteArray(data, 0, data.length, options);\n                if (decoded == null) return null;\n                int side = Math.max(decoded.getWidth(), decoded.getHeight());\n                if (side <= 768) return decoded;\n                float factor = 768f / side;\n                Bitmap scaled = Bitmap.createScaledBitmap(decoded,\n                        Math.max(1, Math.round(decoded.getWidth() * factor)),\n                        Math.max(1, Math.round(decoded.getHeight() * factor)), true);\n                if (scaled != decoded) decoded.recycle();\n                return scaled;\n            }\n'''
if old_decode not in avatar:
    raise SystemExit('Decodificação do avatar não encontrada')
avatar = avatar.replace(old_decode, new_decode, 1)

anchor = '''    private static Rect centerCrop(Bitmap bitmap) {\n'''
helper = '''    private static byte[] readLimited(InputStream input, int maxBytes) throws Exception {\n        ByteArrayOutputStream output = new ByteArrayOutputStream(Math.min(maxBytes, 256 * 1024));\n        byte[] buffer = new byte[16 * 1024];\n        int total = 0;\n        int read;\n        while ((read = input.read(buffer)) != -1) {\n            if (Thread.currentThread().isInterrupted()) throw new InterruptedException("Avatar cancelado");\n            int allowed = Math.min(read, maxBytes - total);\n            if (allowed <= 0) break;\n            output.write(buffer, 0, allowed);\n            total += allowed;\n            if (total >= maxBytes) break;\n        }\n        return output.toByteArray();\n    }\n\n    private static Rect centerCrop(Bitmap bitmap) {\n'''
if anchor not in avatar:
    raise SystemExit('Ponto para helper de avatar não encontrado')
avatar = avatar.replace(anchor, helper, 1)
avatar_path.write_text(avatar, encoding='utf-8')

print('Passageiro v1.1: ANR hardening aplicado.')
