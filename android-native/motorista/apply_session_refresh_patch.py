from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
api_path = Path('app/src/main/java/com/clickgo/motorista/ApiClient.java')
main = main_path.read_text(encoding='utf-8')
api = api_path.read_text(encoding='utf-8')

def repl(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f'Trecho não encontrado: {label}')
    return text.replace(old, new, count)

# ApiClient: centraliza renovação automática para REST/RPC/Auth e Storage.
api = repl(api,
'''public final class ApiClient {\n    private ApiClient() {}\n''',
'''public final class ApiClient {\n    public interface SessionRefresher {\n        String refresh(String failedAccessToken) throws Exception;\n    }\n\n    private static volatile SessionRefresher sessionRefresher;\n\n    private ApiClient() {}\n\n    public static void setSessionRefresher(SessionRefresher refresher) {\n        sessionRefresher = refresher;\n    }\n''',
'interface renovação')

request_sig = '''    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'''
request_new = '''    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n        try {\n            return requestOnce(urlString, method, body, auth, token, apiKey);\n        } catch (Exception first) {\n            SessionRefresher refresher = sessionRefresher;\n            if (!auth || refresher == null || !isExpiredJwt(first)) throw first;\n            String freshToken = refresher.refresh(token);\n            if (freshToken == null || freshToken.isBlank()) throw new Exception("Sessão expirada. Entre novamente.");\n            return requestOnce(urlString, method, body, true, freshToken, apiKey);\n        }\n    }\n\n    private static String requestOnce(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'''
api = repl(api, request_sig, request_new, 'request central')

storage_pattern = re.compile(r'''    public static void storageUpload\(String bucket, String objectPath, byte\[\] bytes, String contentType, String token\) throws Exception \{.*?\n    \}\n\n    private static String request''', re.S)
m = storage_pattern.search(api)
if not m:
    raise SystemExit('storageUpload não encontrado')
storage_new = '''    public static void storageUpload(String bucket, String objectPath, byte[] bytes, String contentType, String token) throws Exception {\n        try {\n            storageUploadOnce(bucket, objectPath, bytes, contentType, token);\n        } catch (Exception first) {\n            SessionRefresher refresher = sessionRefresher;\n            if (refresher == null || !isExpiredJwt(first)) throw first;\n            String freshToken = refresher.refresh(token);\n            if (freshToken == null || freshToken.isBlank()) throw new Exception("Sessão expirada. Entre novamente.");\n            storageUploadOnce(bucket, objectPath, bytes, contentType, freshToken);\n        }\n    }\n\n    private static void storageUploadOnce(String bucket, String objectPath, byte[] bytes, String contentType, String token) throws Exception {\n        HttpURLConnection connection = null;\n        try {\n            String encodedPath = objectPath.replace(" ", "%20");\n            connection = (HttpURLConnection) new URL(BuildConfig.SUPABASE_URL + "/storage/v1/object/" + bucket + "/" + encodedPath).openConnection();\n            connection.setRequestMethod("POST"); connection.setConnectTimeout(8000); connection.setReadTimeout(12000); connection.setUseCaches(false); connection.setDoOutput(true);\n            connection.setRequestProperty("apikey", BuildConfig.SUPABASE_KEY); connection.setRequestProperty("Authorization", "Bearer " + token); connection.setRequestProperty("Content-Type", contentType == null || contentType.isBlank() ? "image/jpeg" : contentType); connection.setRequestProperty("x-upsert", "true"); connection.setFixedLengthStreamingMode(bytes.length);\n            try (OutputStream os = connection.getOutputStream()) { os.write(bytes); }\n            int code = connection.getResponseCode(); InputStream stream = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream(); String text = readAll(stream); if (code < 200 || code >= 300) throw new Exception(extractMessage(text, "Erro no envio do arquivo"));\n        } finally { if (connection != null) connection.disconnect(); }\n    }\n\n    private static String request'''
api = api[:m.start()] + storage_new + api[m.end():]

read_anchor = '''    private static String readAll(InputStream is) throws Exception {\n'''
expired_helper = '''    private static boolean isExpiredJwt(Exception error) {\n        String message = error == null ? "" : String.valueOf(error.getMessage()).toLowerCase(java.util.Locale.ROOT);\n        return message.contains("jwt expired")\n                || message.contains("expired jwt")\n                || message.contains("token has expired")\n                || message.contains("access token expired");\n    }\n\n    private static String readAll(InputStream is) throws Exception {\n'''
api = repl(api, read_anchor, expired_helper, 'detecção JWT expirado')

# Estado de sessão do Motorista.
old_fields = '''    private String token, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";\n'''
new_fields = '''    private String token, refreshToken, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";\n    private final Object sessionLock = new Object();\n    private boolean sessionRedirectPending;\n'''
main = repl(main, old_fields, new_fields, 'campos sessão')

old_oncreate = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgomotorista".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            getPreferences(MODE_PRIVATE).edit().clear().apply();\n            token = null;\n            userId = null;\n        }\n        if (token == null || token.isBlank()) showLogin(); else loadSession();\n'''
new_oncreate = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        refreshToken = getPreferences(MODE_PRIVATE).getString("refresh_token", null);\n        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);\n        ApiClient.setSessionRefresher(this::refreshAccessTokenBlocking);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgomotorista".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            clearStoredSession();\n        }\n        if (token == null || token.isBlank()) {\n            showLogin();\n        } else if (refreshToken == null || refreshToken.isBlank()) {\n            clearStoredSession();\n            showLogin();\n            toast("Sua sessão precisa ser atualizada. Entre novamente uma vez.");\n        } else {\n            loadSession();\n        }\n'''
main = repl(main, old_oncreate, new_oncreate, 'inicialização sessão')

# Login passa a guardar refresh_token.
old_login = '''                token = response.optString("access_token","");\n                JSONObject user = response.optJSONObject("user"); userId = user == null ? "" : user.optString("id","");\n                if (token.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");\n                getPreferences(MODE_PRIVATE).edit().putString("access_token",token).putString("user_id",userId).apply();\n                loadSession();\n'''
new_login = '''                String accessToken = response.optString("access_token","");\n                String newRefreshToken = response.optString("refresh_token","");\n                JSONObject user = response.optJSONObject("user"); userId = user == null ? "" : user.optString("id","");\n                if (accessToken.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");\n                saveSession(accessToken, newRefreshToken);\n                loadSession();\n'''
main = repl(main, old_login, new_login, 'login salva refresh')

# Cadastro autenticado também guarda refresh_token, quando o Supabase já devolver sessão.
old_signup = '''JSONObject response=DriverRepository.signUp(request);String access=response.optString("access_token","");JSONObject u=response.optJSONObject("user");String id=u==null?"":u.optString("id","");if(!access.isBlank()){token=access;userId=id;getPreferences(MODE_PRIVATE).edit().putString("access_token",token).putString("user_id",userId).apply();uploadPendingRegistrationPhoto();ui.post(this::loadSession);}'''
new_signup = '''JSONObject response=DriverRepository.signUp(request);String access=response.optString("access_token","");String refresh=response.optString("refresh_token","");JSONObject u=response.optJSONObject("user");String id=u==null?"":u.optString("id","");if(!access.isBlank()){userId=id;saveSession(access,refresh);uploadPendingRegistrationPhoto();ui.post(this::loadSession);}'''
if old_signup in main:
    main = main.replace(old_signup, new_signup, 1)
else:
    # Alguns patches posteriores só alteram metadados do cadastro; valida que o refresh já não foi aplicado.
    if 'String refresh=response.optString("refresh_token","")' not in main:
        raise SystemExit('Cadastro autenticado não encontrado para refresh token')

# Insere métodos de sessão antes do releaseMap.
release_anchor = '''    private void releaseMap(){'''
session_methods = '''    private void saveSession(String accessToken, String newRefreshToken) {\n        token = accessToken;\n        if (newRefreshToken != null && !newRefreshToken.isBlank()) refreshToken = newRefreshToken;\n        android.content.SharedPreferences.Editor editor = getPreferences(MODE_PRIVATE).edit().putString("access_token", token);\n        if (refreshToken != null && !refreshToken.isBlank()) editor.putString("refresh_token", refreshToken);\n        if (userId != null && !userId.isBlank()) editor.putString("user_id", userId);\n        editor.apply();\n        sessionRedirectPending = false;\n    }\n\n    private void clearStoredSession() {\n        token = null;\n        refreshToken = null;\n        userId = null;\n        online = false;\n        getPreferences(MODE_PRIVATE).edit().clear().apply();\n    }\n\n    private String refreshAccessTokenBlocking(String failedAccessToken) throws Exception {\n        synchronized (sessionLock) {\n            if (token != null && !token.isBlank() && failedAccessToken != null && !token.equals(failedAccessToken)) return token;\n            if (refreshToken == null || refreshToken.isBlank()) {\n                postSessionExpired();\n                throw new Exception("Sessão expirada. Entre novamente.");\n            }\n            try {\n                JSONObject body = new JSONObject().put("refresh_token", refreshToken);\n                JSONObject response = new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=refresh_token", body));\n                String accessToken = response.optString("access_token", "");\n                String newRefreshToken = response.optString("refresh_token", "");\n                if (accessToken.isBlank()) throw new Exception("Não foi possível renovar a sessão.");\n                saveSession(accessToken, newRefreshToken);\n                return accessToken;\n            } catch (Exception error) {\n                postSessionExpired();\n                throw new Exception("Sessão expirada. Entre novamente.");\n            }\n        }\n    }\n\n    private void postSessionExpired() {\n        clearStoredSession();\n        if (sessionRedirectPending) return;\n        sessionRedirectPending = true;\n        ui.post(() -> {\n            if (destroyed || isFinishing()) return;\n            stopPolling();\n            stopLocationWatch();\n            toast("Sua sessão expirou. Entre novamente para continuar.");\n            showLogin();\n            sessionRedirectPending = false;\n        });\n    }\n\n    private void releaseMap(){'''
main = repl(main, release_anchor, session_methods, 'métodos de sessão')

# Logout usa o mesmo limpador central.
main = re.sub(
    r'''    private void logout\(\)\{token=null;userId=null;online=false;getPreferences\(MODE_PRIVATE\)\.edit\(\)\.clear\(\)\.apply\(\);stopPolling\(\);stopLocationWatch\(\);releaseMap\(\);showLogin\(\);\}''',
    '''    private void logout(){clearStoredSession();stopPolling();stopLocationWatch();releaseMap();showLogin();}''',
    main,
    count=1
)

# Marca a versão v1.3 PRIME.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '1.3-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

main_path.write_text(main, encoding='utf-8')
api_path.write_text(api, encoding='utf-8')
print('Motorista v1.3 PRIME: refresh token automático em API, chamadas, GPS e Storage.')
