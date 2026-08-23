from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
api_path=Path('app/src/main/java/com/clickgo/motorista/ApiClient.java')
main=main_path.read_text(encoding='utf-8')
api=api_path.read_text(encoding='utf-8')

def replace_once(text, old, new, label):
    if old not in text:
        raise SystemExit('Trecho não encontrado: '+label)
    return text.replace(old,new,1)

# ----- ApiClient -----
api=replace_once(api,
'public final class ApiClient {\n    private ApiClient() {}\n',
'''public final class ApiClient {\n    public interface SessionRefresher { String refresh(String failedAccessToken) throws Exception; }\n    private static volatile SessionRefresher sessionRefresher;\n    private ApiClient() {}\n    public static void setSessionRefresher(SessionRefresher refresher) { sessionRefresher = refresher; }\n''',
'ApiClient session refresher')

sig='    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'
wrapped='''    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n        try { return requestOnce(urlString,method,body,auth,token,apiKey); }\n        catch(Exception first) {\n            SessionRefresher refresher=sessionRefresher;\n            if(!auth||refresher==null||!isExpiredJwt(first)) throw first;\n            String fresh=refresher.refresh(token);\n            if(fresh==null||fresh.isBlank()) throw new Exception("Sessão expirada. Entre novamente.");\n            return requestOnce(urlString,method,body,true,fresh,apiKey);\n        }\n    }\n\n    private static String requestOnce(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'''
api=replace_once(api,sig,wrapped,'request central')

storage=re.compile(r'''    public static void storageUpload\(String bucket, String objectPath, byte\[\] bytes, String contentType, String token\) throws Exception \{.*?\n    \}\n\n    private static String request''',re.S)
m=storage.search(api)
if not m: raise SystemExit('storageUpload não encontrado')
replacement='''    public static void storageUpload(String bucket, String objectPath, byte[] bytes, String contentType, String token) throws Exception {\n        try { storageUploadOnce(bucket,objectPath,bytes,contentType,token); }\n        catch(Exception first) {\n            SessionRefresher refresher=sessionRefresher;\n            if(refresher==null||!isExpiredJwt(first)) throw first;\n            String fresh=refresher.refresh(token);\n            if(fresh==null||fresh.isBlank()) throw new Exception("Sessão expirada. Entre novamente.");\n            storageUploadOnce(bucket,objectPath,bytes,contentType,fresh);\n        }\n    }\n\n    private static void storageUploadOnce(String bucket, String objectPath, byte[] bytes, String contentType, String token) throws Exception {\n        HttpURLConnection connection=null;\n        try {\n            String encodedPath=objectPath.replace(" ","%20");\n            connection=(HttpURLConnection)new URL(BuildConfig.SUPABASE_URL+"/storage/v1/object/"+bucket+"/"+encodedPath).openConnection();\n            connection.setRequestMethod("POST"); connection.setConnectTimeout(8000); connection.setReadTimeout(12000); connection.setUseCaches(false); connection.setDoOutput(true);\n            connection.setRequestProperty("apikey",BuildConfig.SUPABASE_KEY); connection.setRequestProperty("Authorization","Bearer "+token); connection.setRequestProperty("Content-Type",contentType==null||contentType.isBlank()?"image/jpeg":contentType); connection.setRequestProperty("x-upsert","true"); connection.setFixedLengthStreamingMode(bytes.length);\n            try(OutputStream os=connection.getOutputStream()){os.write(bytes);}\n            int code=connection.getResponseCode(); InputStream stream=code>=200&&code<300?connection.getInputStream():connection.getErrorStream(); String text=readAll(stream);\n            if(code<200||code>=300) throw new Exception(extractMessage(text,"Erro no envio do arquivo"));\n        } finally { if(connection!=null) connection.disconnect(); }\n    }\n\n    private static String request'''
api=api[:m.start()]+replacement+api[m.end():]

if 'private static boolean isExpiredJwt(' not in api:
    helper='''\n    private static boolean isExpiredJwt(Exception error) {\n        String message=error==null?"":String.valueOf(error.getMessage()).toLowerCase(java.util.Locale.ROOT);\n        return message.contains("jwt expired")||message.contains("expired jwt")||message.contains("token has expired")||message.contains("access token expired");\n    }\n'''
    pos=api.rfind('\n}')
    if pos<0: raise SystemExit('Fim de ApiClient não encontrado')
    api=api[:pos]+helper+api[pos:]

# ----- MainActivity -----
main=replace_once(main,
'    private String token, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";\n',
'''    private String token, refreshToken, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";\n    private final Object sessionLock = new Object();\n    private boolean sessionRedirectPending;\n''',
'campos sessão')

old='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgomotorista".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            getPreferences(MODE_PRIVATE).edit().clear().apply();\n            token = null;\n            userId = null;\n        }\n        if (token == null || token.isBlank()) showLogin(); else loadSession();\n'''
new='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        refreshToken = getPreferences(MODE_PRIVATE).getString("refresh_token", null);\n        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);\n        ApiClient.setSessionRefresher(this::refreshAccessTokenBlocking);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgomotorista".equalsIgnoreCase(getIntent().getData().getScheme())) clearStoredSession();\n        if(token==null||token.isBlank()) showLogin();\n        else if(refreshToken==null||refreshToken.isBlank()){clearStoredSession();showLogin();toast("Sua sessão precisa ser atualizada. Entre novamente uma vez.");}\n        else loadSession();\n'''
main=replace_once(main,old,new,'onCreate sessão')

old='''                token = response.optString("access_token","");\n                JSONObject user = response.optJSONObject("user"); userId = user == null ? "" : user.optString("id","");\n                if (token.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");\n                getPreferences(MODE_PRIVATE).edit().putString("access_token",token).putString("user_id",userId).apply();\n                loadSession();\n'''
new='''                String accessToken=response.optString("access_token","");\n                String newRefreshToken=response.optString("refresh_token","");\n                JSONObject user=response.optJSONObject("user"); userId=user==null?"":user.optString("id","");\n                if(accessToken.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");\n                saveSession(accessToken,newRefreshToken);\n                loadSession();\n'''
main=replace_once(main,old,new,'login refresh')

signup_old='JSONObject response=DriverRepository.signUp(request);String access=response.optString("access_token","");JSONObject u=response.optJSONObject("user");String id=u==null?"":u.optString("id","");if(!access.isBlank()){token=access;userId=id;getPreferences(MODE_PRIVATE).edit().putString("access_token",token).putString("user_id",userId).apply();uploadPendingRegistrationPhoto();ui.post(this::loadSession);}'
signup_new='JSONObject response=DriverRepository.signUp(request);String access=response.optString("access_token","");String refresh=response.optString("refresh_token","");JSONObject u=response.optJSONObject("user");String id=u==null?"":u.optString("id","");if(!access.isBlank()){userId=id;saveSession(access,refresh);uploadPendingRegistrationPhoto();ui.post(this::loadSession);}'
if signup_old in main: main=main.replace(signup_old,signup_new,1)
elif 'String refresh=response.optString("refresh_token","")' not in main: raise SystemExit('signup refresh não encontrado')

anchor='    private void releaseMap(){'
methods='''    private void saveSession(String accessToken,String newRefreshToken){\n        token=accessToken; if(newRefreshToken!=null&&!newRefreshToken.isBlank())refreshToken=newRefreshToken;\n        android.content.SharedPreferences.Editor e=getPreferences(MODE_PRIVATE).edit().putString("access_token",token);\n        if(refreshToken!=null&&!refreshToken.isBlank())e.putString("refresh_token",refreshToken); if(userId!=null&&!userId.isBlank())e.putString("user_id",userId); e.apply(); sessionRedirectPending=false;\n    }\n    private void clearStoredSession(){token=null;refreshToken=null;userId=null;online=false;getPreferences(MODE_PRIVATE).edit().clear().apply();}\n    private String refreshAccessTokenBlocking(String failedAccessToken)throws Exception{\n        synchronized(sessionLock){\n            if(token!=null&&!token.isBlank()&&failedAccessToken!=null&&!token.equals(failedAccessToken))return token;\n            if(refreshToken==null||refreshToken.isBlank()){postSessionExpired();throw new Exception("Sessão expirada. Entre novamente.");}\n            try{JSONObject response=new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=refresh_token",new JSONObject().put("refresh_token",refreshToken)));String access=response.optString("access_token","");String refresh=response.optString("refresh_token","");if(access.isBlank())throw new Exception("Falha ao renovar sessão");saveSession(access,refresh);return access;}\n            catch(Exception ex){postSessionExpired();throw new Exception("Sessão expirada. Entre novamente.");}\n        }\n    }\n    private void postSessionExpired(){\n        clearStoredSession(); if(sessionRedirectPending)return; sessionRedirectPending=true;\n        ui.post(()->{if(destroyed||isFinishing())return;stopPolling();stopLocationWatch();toast("Sua sessão expirou. Entre novamente para continuar.");showLogin();sessionRedirectPending=false;});\n    }\n\n    private void releaseMap(){'''
main=replace_once(main,anchor,methods,'métodos sessão')

main=re.sub(r'    private void logout\(\)\{token=null;userId=null;online=false;getPreferences\(MODE_PRIVATE\)\.edit\(\)\.clear\(\)\.apply\(\);stopPolling\(\);stopLocationWatch\(\);releaseMap\(\);showLogin\(\);\}',
            '    private void logout(){clearStoredSession();stopPolling();stopLocationWatch();releaseMap();showLogin();}',main,count=1)

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8');m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.3-prime'",build,count=1);build_path.write_text(build,encoding='utf-8')
main_path.write_text(main,encoding='utf-8');api_path.write_text(api,encoding='utf-8')
print('Motorista v1.3 PRIME: refresh JWT automático aplicado.')
