from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
api_path = Path('app/src/main/java/com/clickgo/passageiro/ApiClient.java')
main = main_path.read_text(encoding='utf-8')
api = api_path.read_text(encoding='utf-8')

def repl(text, old, new, label, count=1):
    if old not in text:
        raise SystemExit(f'Trecho não encontrado: {label}')
    return text.replace(old, new, count)

# ApiClient: todas as chamadas autenticadas passam a tentar renovar a sessão
# automaticamente quando o Supabase responder que o JWT expirou.
api = repl(api,
'''public final class ApiClient {\n    private ApiClient() {}\n''',
'''public final class ApiClient {\n    public interface SessionRefresher {\n        String refresh(String failedAccessToken) throws Exception;\n    }\n\n    private static volatile SessionRefresher sessionRefresher;\n\n    private ApiClient() {}\n\n    public static void setSessionRefresher(SessionRefresher refresher) {\n        sessionRefresher = refresher;\n    }\n''',
'interface de renovação')

request_signature = '''    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'''
if request_signature not in api:
    raise SystemExit('Método request do ApiClient não encontrado')
request_wrapper = '''    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n        try {\n            return requestOnce(urlString, method, body, auth, token, apiKey);\n        } catch (Exception first) {\n            SessionRefresher refresher = sessionRefresher;\n            if (!auth || refresher == null || !isExpiredJwt(first)) throw first;\n            String freshToken = refresher.refresh(token);\n            if (freshToken == null || freshToken.isBlank()) {\n                throw new Exception("Sessão expirada. Entre novamente.");\n            }\n            return requestOnce(urlString, method, body, true, freshToken, apiKey);\n        }\n    }\n\n    private static String requestOnce(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'''
api = api.replace(request_signature, request_wrapper, 1)

read_anchor = '''    private static String readAll(InputStream is) throws Exception {\n'''
expired_helper = '''    private static boolean isExpiredJwt(Exception error) {\n        String message = error == null ? "" : String.valueOf(error.getMessage()).toLowerCase(java.util.Locale.ROOT);\n        return message.contains("jwt expired")\n                || message.contains("expired jwt")\n                || message.contains("token has expired")\n                || message.contains("access token expired");\n    }\n\n    private static String readAll(InputStream is) throws Exception {\n'''
api = repl(api, read_anchor, expired_helper, 'helper JWT expirado')

# MainActivity: guarda access_token + refresh_token e fornece a renovação ao ApiClient.
main = repl(main,
'''    private String token;\n''',
'''    private String token;\n    private String refreshToken;\n    private final Object sessionLock = new Object();\n    private boolean sessionRedirectPending = false;\n''',
'campos de sessão')

old_oncreate = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgopassageiro".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            getPreferences(MODE_PRIVATE).edit().clear().apply();\n            token = null;\n        }\n        if (token == null || token.isBlank()) showLogin(); else showHome();\n'''
new_oncreate = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        refreshToken = getPreferences(MODE_PRIVATE).getString("refresh_token", null);\n        ApiClient.setSessionRefresher(this::refreshAccessTokenBlocking);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgopassageiro".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            clearStoredSession();\n        }\n        if (token == null || token.isBlank()) {\n            showLogin();\n        } else if (refreshToken == null || refreshToken.isBlank()) {\n            clearStoredSession();\n            showLogin();\n            toast("Sua sessão precisa ser atualizada. Entre novamente uma vez.");\n        } else {\n            showHome();\n        }\n'''
main = repl(main, old_oncreate, new_oncreate, 'carregamento da sessão')

# Login e signup passam a capturar o refresh_token retornado pelo Supabase.
main, n = re.subn(
    r'(String accessToken = response\.optString\("access_token", ""\);)',
    r'\1\n                String newRefreshToken = response.optString("refresh_token", "");',
    main
)
if n < 2:
    raise SystemExit(f'Esperava pelo menos 2 respostas de autenticação; encontrei {n}')

save_pattern = r'''\s*token = accessToken;\n\s*getPreferences\(MODE_PRIVATE\)\.edit\(\)\.putString\("access_token", accessToken\)\.apply\(\);'''
main, n = re.subn(save_pattern, '\n                saveSession(accessToken, newRefreshToken);', main)
if n < 2:
    raise SystemExit(f'Esperava pelo menos 2 salvamentos de sessão; encontrei {n}')

# Logout antigo (quando existir) precisa remover também o refresh token.
main = main.replace(
    'getPreferences(MODE_PRIVATE).edit().remove("access_token").apply();',
    'clearStoredSession();'
)

recover_anchor = '''    private void recover(String email) {\n'''
session_methods = '''    private void saveSession(String accessToken, String newRefreshToken) {\n        token = accessToken;\n        if (newRefreshToken != null && !newRefreshToken.isBlank()) refreshToken = newRefreshToken;\n        android.content.SharedPreferences.Editor editor = getPreferences(MODE_PRIVATE).edit()\n                .putString("access_token", token);\n        if (refreshToken != null && !refreshToken.isBlank()) editor.putString("refresh_token", refreshToken);\n        editor.apply();\n        sessionRedirectPending = false;\n    }\n\n    private void clearStoredSession() {\n        token = null;\n        refreshToken = null;\n        currentUserId = null;\n        getPreferences(MODE_PRIVATE).edit()\n                .remove("access_token")\n                .remove("refresh_token")\n                .apply();\n    }\n\n    private String refreshAccessTokenBlocking(String failedAccessToken) throws Exception {\n        synchronized (sessionLock) {\n            if (token != null && !token.isBlank() && failedAccessToken != null && !token.equals(failedAccessToken)) {\n                return token;\n            }\n            if (refreshToken == null || refreshToken.isBlank()) {\n                postSessionExpired();\n                throw new Exception("Sessão expirada. Entre novamente.");\n            }\n            try {\n                JSONObject body = new JSONObject().put("refresh_token", refreshToken);\n                JSONObject response = new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=refresh_token", body));\n                String accessToken = response.optString("access_token", "");\n                String newRefreshToken = response.optString("refresh_token", "");\n                if (accessToken.isBlank()) throw new Exception("Não foi possível renovar a sessão.");\n                saveSession(accessToken, newRefreshToken);\n                return accessToken;\n            } catch (Exception error) {\n                postSessionExpired();\n                throw new Exception("Sessão expirada. Entre novamente.");\n            }\n        }\n    }\n\n    private void postSessionExpired() {\n        clearStoredSession();\n        if (sessionRedirectPending) return;\n        sessionRedirectPending = true;\n        ui.post(() -> {\n            if (destroyed || isFinishing()) return;\n            toast("Sua sessão expirou. Entre novamente para continuar.");\n            showLogin();\n            sessionRedirectPending = false;\n        });\n    }\n\n    private void recover(String email) {\n'''
main = repl(main, recover_anchor, session_methods, 'métodos de renovação')

# Versão da correção.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.2-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

main_path.write_text(main, encoding='utf-8')
api_path.write_text(api, encoding='utf-8')
print('Passageiro v2.2 PRIME: refresh token e renovação automática de JWT aplicados.')
