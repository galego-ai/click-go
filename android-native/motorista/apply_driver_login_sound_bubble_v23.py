from pathlib import Path
import re

root = Path('app')
main_path = root / 'src/main/java/com/clickgo/motorista/MainActivity.java'
repo_path = root / 'src/main/java/com/clickgo/motorista/DriverRepository.java'
manifest_path = root / 'src/main/AndroidManifest.xml'
build_path = root / 'build.gradle'

text = main_path.read_text(encoding='utf-8')
repo = repo_path.read_text(encoding='utf-8')
manifest = manifest_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# 1) Conta de motorista existente: usa RPC público mínimo, sem expor dados.
# -----------------------------------------------------------------------------
if 'driverAccountExists(String email)' not in repo:
    anchor = '''    public static JSONObject signUp(JSONObject body) throws Exception {\n'''
    method = '''    public static boolean driverAccountExists(String email) throws Exception {\n        Object result = ApiClient.publicRpc("driver_account_exists", new JSONObject().put("p_email", email == null ? "" : email.trim()));\n        String raw = String.valueOf(result).trim();\n        if (raw.equalsIgnoreCase("true")) return true;\n        if (raw.equalsIgnoreCase("false")) return false;\n        if (raw.startsWith("[") && raw.endsWith("]")) {\n            org.json.JSONArray a = new org.json.JSONArray(raw);\n            if (a.length() > 0) return a.optBoolean(0, false);\n        }\n        return new org.json.JSONObject("{\\\"value\\\":" + raw + "}").optBoolean("value", false);\n    }\n\n'''
    if anchor not in repo:
        raise SystemExit('Anchor signUp não encontrado no DriverRepository')
    repo = repo.replace(anchor, method + anchor, 1)

# -----------------------------------------------------------------------------
# 2) Login: diferencia motorista inexistente de senha incorreta.
# -----------------------------------------------------------------------------
login_pattern = re.compile(r'''    private void login\(String email, String password\) \{.*?\n    \}\n\n(?=    private void loadSession\(\))''', re.S)
login_replacement = '''    private void login(String email, String password) {\n        if (email.isBlank() || password.isBlank()) { toast("Informe e-mail e senha."); return; }\n        io.execute(() -> {\n            try {\n                JSONObject response = DriverRepository.signIn(email,password);\n                String accessToken=response.optString("access_token","");\n                String newRefreshToken=response.optString("refresh_token","");\n                JSONObject user=response.optJSONObject("user"); userId=user==null?"":user.optString("id","");\n                if(accessToken.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");\n                saveSession(accessToken,newRefreshToken);\n                loadSession();\n            } catch (Exception e) {\n                String shown = msg(e);\n                if (isInvalidLoginError(e)) {\n                    try {\n                        shown = DriverRepository.driverAccountExists(email) ? "Senha incorreta." : "Esse usuário não existe.";\n                    } catch (Exception ignored) {\n                        shown = "E-mail ou senha incorretos.";\n                    }\n                }\n                String finalShown = shown;\n                ui.post(() -> toast(finalShown));\n            }\n        });\n    }\n\n    private boolean isInvalidLoginError(Exception e) {\n        String m = e == null || e.getMessage() == null ? "" : e.getMessage().toLowerCase(java.util.Locale.ROOT);\n        return m.contains("invalid login credentials") || m.contains("invalid credentials") || m.contains("email or password");\n    }\n\n'''
text, n = login_pattern.subn(login_replacement, text, count=1)
if n != 1:
    raise SystemExit('Método login final não encontrado')

# -----------------------------------------------------------------------------
# 3) Recuperação: primeiro verifica se é uma conta de motorista existente.
# -----------------------------------------------------------------------------
recover_pattern = re.compile(r'''    private void recover\(String email\) \{.*?\n    \}\n\n(?=    private void login\()''', re.S)
recover_replacement = '''    private void recover(String email) {\n        if(email.isBlank()){toast("Informe seu e-mail.");return;}\n        io.execute(() -> {\n            try {\n                if (!DriverRepository.driverAccountExists(email)) {\n                    ui.post(() -> new android.app.AlertDialog.Builder(this)\n                            .setTitle("Usuário não encontrado")\n                            .setMessage("Esse usuário não existe no CLICK-GO Motorista. Confira o e-mail ou faça seu cadastro.")\n                            .setPositiveButton("OK", null)\n                            .show());\n                    return;\n                }\n                JSONObject body = new JSONObject().put("email",email);\n                ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha%3Fdestino%3Dmotorista-app",body);\n                ui.post(() -> new android.app.AlertDialog.Builder(this)\n                        .setTitle("Link enviado")\n                        .setMessage("Confira seu e-mail. Abra o link para criar uma nova senha e depois volte ao aplicativo.")\n                        .setPositiveButton("Voltar ao login",(d,w)->showLogin())\n                        .show());\n            } catch(Exception e){ui.post(()->toast(msg(e)));}\n        });\n    }\n\n'''
text, n = recover_pattern.subn(recover_replacement, text, count=1)
if n != 1:
    raise SystemExit('Método recover final não encontrado')

# -----------------------------------------------------------------------------
# 4) Som contínuo da chamada enquanto uma oferta estiver na tela.
# -----------------------------------------------------------------------------
if 'private android.media.MediaPlayer rideCallPlayer;' not in text:
    field_anchor = '    private boolean destroyed;\n'
    fields = '''    private boolean destroyed;\n    private android.media.MediaPlayer rideCallPlayer;\n    private String alertedOfferId = "";\n    private boolean overlayPrompted;\n'''
    if field_anchor not in text:
        raise SystemExit('Campo destroyed não encontrado')
    text = text.replace(field_anchor, fields, 1)

sound_anchor = '    private void startPolling(){'
if 'private void startRideCallSound(String offerId)' not in text:
    sound_methods = '''    private void startRideCallSound(String offerId) {\n        if (offerId == null || offerId.isBlank()) return;\n        try {\n            if (offerId.equals(alertedOfferId) && rideCallPlayer != null && rideCallPlayer.isPlaying()) return;\n        } catch (Exception ignored) {}\n        stopRideCallSound(false);\n        alertedOfferId = offerId;\n        try {\n            android.net.Uri uri = android.media.RingtoneManager.getDefaultUri(android.media.RingtoneManager.TYPE_RINGTONE);\n            rideCallPlayer = android.media.MediaPlayer.create(this, uri);\n            if (rideCallPlayer != null) {\n                rideCallPlayer.setLooping(true);\n                rideCallPlayer.start();\n            }\n        } catch (Exception ignored) {}\n    }\n\n    private void stopRideCallSound(boolean clearOffer) {\n        android.media.MediaPlayer player = rideCallPlayer;\n        rideCallPlayer = null;\n        if (player != null) {\n            try { if (player.isPlaying()) player.stop(); } catch (Exception ignored) {}\n            try { player.release(); } catch (Exception ignored) {}\n        }\n        if (clearOffer) alertedOfferId = "";\n    }\n\n'''
    if sound_anchor not in text:
        raise SystemExit('startPolling não encontrado para inserir som')
    text = text.replace(sound_anchor, sound_methods + sound_anchor, 1)

render_offer_pattern = re.compile(r'''    private void renderOffer\(JSONObject o\)\{.*?\}\n(?=    private void respond\(String id,boolean accept\))''', re.S)
render_offer = '''    private void renderOffer(JSONObject o){\n        if(operationBox==null)return;\n        operationBox.removeAllViews();\n        if(o==null){\n            stopRideCallSound(true);\n            operationTitle.setText("Aguardando chamadas…");\n            DriverMapRenderer.render(map,currentLocation,null,dp(5));\n            return;\n        }\n        startRideCallSound(o.optString("offer_id",""));\n        operationTitle.setText("🔔 Nova corrida");\n        LinearLayout c=card(DARK,YELLOW);\n        c.addView(text(o.optString("category_name","Corrida CLICK-GO"),20,Color.WHITE,true));\n        c.addView(text("Embarque: "+o.optString("origin_label",""),14,Color.WHITE,false));\n        c.addView(text("Destino: "+o.optString("destination_label",""),14,GRAY,false));\n        if(o.has("distance_to_pickup_km"))c.addView(text(String.format(Locale.getDefault(),"Até o passageiro: %.1f km",o.optDouble("distance_to_pickup_km",0)),13,GRAY,false));\n        if(o.has("eta_to_pickup_min"))c.addView(text("Previsão: "+o.optInt("eta_to_pickup_min",0)+" min",13,GRAY,false));\n        c.addView(text("Ganho estimado "+privateMoney(o.optDouble("estimated_driver_earning",0)),18,YELLOW,true));\n        LinearLayout a=horizontal();\n        Button yes=primary("Aceitar"),no=darkButton("Recusar");\n        a.addView(yes,new LinearLayout.LayoutParams(0,dp(54),1));\n        a.addView(spaceH(8));\n        a.addView(no,new LinearLayout.LayoutParams(0,dp(54),1));\n        c.addView(a);\n        operationBox.addView(c,wrap());\n        yes.setOnClickListener(v->respond(o.optString("offer_id"),true));\n        no.setOnClickListener(v->respond(o.optString("offer_id"),false));\n        DriverMapRenderer.render(map,currentLocation,o,dp(5));\n    }\n'''
text, n = render_offer_pattern.subn(render_offer, text, count=1)
if n != 1:
    raise SystemExit('renderOffer final não encontrado')

respond_pattern = re.compile(r'''    private void respond\(String id,boolean accept\)\{.*?\}\n(?=    private void renderRide\(JSONObject r\))''', re.S)
respond_replacement = '''    private void respond(String id,boolean accept){\n        stopRideCallSound(true);\n        io.execute(()->{try{DriverRepository.respondOffer(token,id,accept);ui.post(()->toast(accept?"Corrida aceita.":"Chamada recusada."));refreshOperation();}catch(Exception e){ui.post(()->toast(msg(e)));}});\n    }\n'''
text, n = respond_pattern.subn(respond_replacement, text, count=1)
if n != 1:
    raise SystemExit('respond final não encontrado')

text = text.replace('    private void renderRide(JSONObject r) {\n', '    private void renderRide(JSONObject r) {\n        stopRideCallSound(true);\n', 1)

# -----------------------------------------------------------------------------
# 5) Bolinha flutuante: ativa enquanto o motorista estiver online.
# -----------------------------------------------------------------------------
if 'private void syncFloatingBubble()' not in text:
    bubble_anchor = '    private void releaseMap(){'
    bubble_methods = '''    private void syncFloatingBubble(){\n        if(!online){ stopFloatingBubble(); return; }\n        if(android.os.Build.VERSION.SDK_INT < android.os.Build.VERSION_CODES.M || android.provider.Settings.canDrawOverlays(this)){\n            try{\n                android.content.Intent service=new android.content.Intent(this,DriverFloatingBubbleService.class);\n                if(android.os.Build.VERSION.SDK_INT>=android.os.Build.VERSION_CODES.O)startForegroundService(service);else startService(service);\n            }catch(Exception ignored){}\n            return;\n        }\n        if(overlayPrompted)return;\n        overlayPrompted=true;\n        new android.app.AlertDialog.Builder(this)\n                .setTitle("Ativar bolinha do CLICK-GO")\n                .setMessage("Permita que o CLICK-GO Motorista apareça sobre outros aplicativos. A bolinha ficará na tela enquanto você estiver online e permite voltar rapidamente ao app.")\n                .setNegativeButton("Agora não",null)\n                .setPositiveButton("Ativar",(d,w)->{\n                    try{startActivity(new android.content.Intent(android.provider.Settings.ACTION_MANAGE_OVERLAY_PERMISSION,android.net.Uri.parse("package:"+getPackageName())));}catch(Exception e){toast("Abra as configurações e permita 'Exibir sobre outros apps'.");}\n                }).show();\n    }\n\n    private void stopFloatingBubble(){\n        try{stopService(new android.content.Intent(this,DriverFloatingBubbleService.class));}catch(Exception ignored){}\n    }\n\n'''
    if bubble_anchor not in text:
        raise SystemExit('releaseMap não encontrado para inserir bolha')
    text = text.replace(bubble_anchor, bubble_methods + bubble_anchor, 1)

# Solicita/ativa a bolha quando a home online é reconstruída.
if 'PushRegistration.register(this,token,"driver");\n        syncFloatingBubble();' not in text:
    push_line = '        PushRegistration.register(this,token,"driver");\n'
    if push_line not in text:
        raise SystemExit('Registro push na home não encontrado')
    text = text.replace(push_line, push_line + '        syncFloatingBubble();\n', 1)

# Volta das configurações de overlay: ativa automaticamente se já houver permissão.
resume_pattern = re.compile(r'''    @Override protected void onResume\(\) \{ super\.onResume\(\); if\(map!=null\) try\{map\.onResume\(\);\}catch\(Exception ignored\)\{\} \}''')
text, n = resume_pattern.subn('    @Override protected void onResume() { super.onResume(); if(map!=null) try{map.onResume();}catch(Exception ignored){} if(online)syncFloatingBubble(); }', text, count=1)
if n != 1:
    raise SystemExit('onResume final não encontrado')

# Login/logout/offline nunca deixam som ou bolha presos.
text = text.replace('    private void showLogin() {\n', '    private void showLogin() {\n        stopRideCallSound(true);\n        stopFloatingBubble();\n', 1)
text = text.replace('    private void logout(){clearStoredSession();stopPolling();stopLocationWatch();releaseMap();showLogin();}', '    private void logout(){stopRideCallSound(true);stopFloatingBubble();clearStoredSession();stopPolling();stopLocationWatch();releaseMap();showLogin();}', 1)
text = text.replace('        destroyed = true; stopPolling(); stopLocationWatch(); releaseMap(); io.shutdownNow();', '        destroyed = true; stopRideCallSound(true); stopPolling(); stopLocationWatch(); releaseMap(); io.shutdownNow();', 1)

# -----------------------------------------------------------------------------
# 6) Manifest: overlay + foreground service para manter a bolha fora do app.
# -----------------------------------------------------------------------------
for permission in [
    'android.permission.SYSTEM_ALERT_WINDOW',
    'android.permission.FOREGROUND_SERVICE',
    'android.permission.FOREGROUND_SERVICE_SPECIAL_USE',
]:
    line = f'    <uses-permission android:name="{permission}" />\n'
    if permission not in manifest:
        manifest = manifest.replace('    <application\n', line + '\n    <application\n', 1)

if 'DriverFloatingBubbleService' not in manifest:
    service = '''        <service\n            android:name=".DriverFloatingBubbleService"\n            android:exported="false"\n            android:stopWithTask="false"\n            android:foregroundServiceType="specialUse">\n            <property\n                android:name="android.app.PROPERTY_SPECIAL_USE_FGS_SUBTYPE"\n                android:value="Bolha flutuante do motorista online para retorno rápido ao CLICK-GO e recebimento de chamadas." />\n        </service>\n'''
    manifest = manifest.replace('        <activity\n            android:name=".MainActivity"', service + '        <activity\n            android:name=".MainActivity"', 1)

# -----------------------------------------------------------------------------
# 7) Canais FCM: canal normal + canal de CHAMADA com ringtone e vibração.
# -----------------------------------------------------------------------------
pkg = root / 'src/main/java/com/clickgo/motorista'
pkg.mkdir(parents=True, exist_ok=True)

(pkg / 'PushRegistration.java').write_text(r'''package com.clickgo.motorista;

import android.Manifest;
import android.app.Activity;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.media.AudioAttributes;
import android.media.RingtoneManager;
import android.net.Uri;
import android.os.Build;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.messaging.FirebaseMessaging;
import org.json.JSONObject;

public final class PushRegistration {
    private static final String CHANNEL="clickgo_updates";
    private static final String RIDE_CALL_CHANNEL="clickgo_ride_calls";
    private PushRegistration(){}
    public static boolean configured(){return !BuildConfig.FIREBASE_PROJECT_ID.isBlank()&&!BuildConfig.FIREBASE_APP_ID.isBlank()&&!BuildConfig.FIREBASE_API_KEY.isBlank()&&!BuildConfig.FIREBASE_SENDER_ID.isBlank();}
    public static void register(Activity activity,String accessToken,String appKind){
        ensureChannel(activity);
        if(Build.VERSION.SDK_INT>=33&&activity.checkSelfPermission(Manifest.permission.POST_NOTIFICATIONS)!=PackageManager.PERMISSION_GRANTED){try{activity.requestPermissions(new String[]{Manifest.permission.POST_NOTIFICATIONS},730);}catch(Exception ignored){}}
        if(accessToken==null||accessToken.isBlank()||!configured())return;
        try{
            if(FirebaseApp.getApps(activity).isEmpty()){
                FirebaseOptions opts=new FirebaseOptions.Builder().setProjectId(BuildConfig.FIREBASE_PROJECT_ID).setApplicationId(BuildConfig.FIREBASE_APP_ID).setApiKey(BuildConfig.FIREBASE_API_KEY).setGcmSenderId(BuildConfig.FIREBASE_SENDER_ID).build();
                FirebaseApp.initializeApp(activity,opts);
            }
            FirebaseMessaging.getInstance().getToken().addOnCompleteListener(task->{if(task.isSuccessful()&&task.getResult()!=null){String push=task.getResult();activity.getSharedPreferences("clickgo_push",Context.MODE_PRIVATE).edit().putString("token",push).apply();sendToken(activity,accessToken,appKind,push);}});
        }catch(Exception ignored){}
    }
    static void sendToken(Context context,String accessToken,String appKind,String pushToken){
        if(accessToken==null||accessToken.isBlank()||pushToken==null||pushToken.isBlank())return;
        new Thread(()->{try{ApiClient.rpc("register_device_push_token",new JSONObject().put("p_token",pushToken).put("p_app_kind",appKind).put("p_platform","android"),accessToken);}catch(Exception ignored){}}).start();
    }
    static void ensureChannel(Context context){
        if(Build.VERSION.SDK_INT<26)return;
        NotificationManager nm=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);
        if(nm==null)return;
        NotificationChannel updates=new NotificationChannel(CHANNEL,"CLICK-GO",NotificationManager.IMPORTANCE_HIGH);
        updates.setDescription("Atualizações de corridas e da conta");
        nm.createNotificationChannel(updates);

        NotificationChannel calls=new NotificationChannel(RIDE_CALL_CHANNEL,"Chamadas de corrida",NotificationManager.IMPORTANCE_HIGH);
        calls.setDescription("Toca quando uma nova corrida é oferecida ao motorista");
        calls.enableVibration(true);
        calls.setVibrationPattern(new long[]{0,500,250,500,250,900});
        calls.setLockscreenVisibility(Notification.VISIBILITY_PUBLIC);
        Uri ringtone=RingtoneManager.getDefaultUri(RingtoneManager.TYPE_RINGTONE);
        AudioAttributes attrs=new AudioAttributes.Builder().setUsage(AudioAttributes.USAGE_NOTIFICATION_RINGTONE).setContentType(AudioAttributes.CONTENT_TYPE_SONIFICATION).build();
        calls.setSound(ringtone,attrs);
        nm.createNotificationChannel(calls);
    }
    static String channel(){return CHANNEL;}
    static String rideCallChannel(){return RIDE_CALL_CHANNEL;}
}
''', encoding='utf-8')

(pkg / 'ClickGoMessagingService.java').write_text(r'''package com.clickgo.motorista;

import android.app.PendingIntent;
import android.content.Intent;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class ClickGoMessagingService extends FirebaseMessagingService {
    @Override public void onNewToken(String token){super.onNewToken(token);getSharedPreferences("clickgo_push",MODE_PRIVATE).edit().putString("token",token).apply();String access=getSharedPreferences("MainActivity",MODE_PRIVATE).getString("access_token",null);if(access!=null)PushRegistration.sendToken(this,access,"driver",token);}
    @Override public void onMessageReceived(RemoteMessage msg){
        super.onMessageReceived(msg);
        PushRegistration.ensureChannel(this);
        String title="CLICK-GO";String body="Você recebeu uma atualização.";
        if(msg.getNotification()!=null){if(msg.getNotification().getTitle()!=null)title=msg.getNotification().getTitle();if(msg.getNotification().getBody()!=null)body=msg.getNotification().getBody();}
        else{if(msg.getData().get("title")!=null)title=msg.getData().get("title");if(msg.getData().get("body")!=null)body=msg.getData().get("body");}
        String type=msg.getData().get("type");
        boolean rideCall="ride_offer".equals(type);
        String channel=rideCall?PushRegistration.rideCallChannel():PushRegistration.channel();
        Intent i=new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi=PendingIntent.getActivity(this,0,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        NotificationCompat.Builder b=new NotificationCompat.Builder(this,channel)
                .setSmallIcon(android.R.drawable.ic_dialog_info)
                .setContentTitle(title).setContentText(body)
                .setStyle(new NotificationCompat.BigTextStyle().bigText(body))
                .setPriority(NotificationCompat.PRIORITY_MAX)
                .setCategory(rideCall?NotificationCompat.CATEGORY_CALL:NotificationCompat.CATEGORY_STATUS)
                .setAutoCancel(true).setContentIntent(pi);
        try{NotificationManagerCompat.from(this).notify((int)(System.currentTimeMillis()%100000),b.build());}catch(SecurityException ignored){}
    }
}
''', encoding='utf-8')

# -----------------------------------------------------------------------------
# 8) Serviço da bolha flutuante (GO), arrastável e clicável.
# -----------------------------------------------------------------------------
(pkg / 'DriverFloatingBubbleService.java').write_text(r'''package com.clickgo.motorista;

import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.app.Service;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.os.Build;
import android.os.IBinder;
import android.provider.Settings;
import android.view.Gravity;
import android.view.MotionEvent;
import android.view.View;
import android.view.WindowManager;
import android.widget.TextView;
import androidx.core.app.NotificationCompat;

public class DriverFloatingBubbleService extends Service {
    private static final String CHANNEL="clickgo_driver_online";
    private static final int NOTIFICATION_ID=7731;
    private WindowManager wm;
    private View bubble;
    private WindowManager.LayoutParams params;

    @Override public void onCreate(){
        super.onCreate();
        createNotificationChannel();
        Intent open=new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP);
        PendingIntent pi=PendingIntent.getActivity(this,91,open,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);
        startForeground(NOTIFICATION_ID,new NotificationCompat.Builder(this,CHANNEL)
                .setSmallIcon(android.R.drawable.ic_menu_mylocation)
                .setContentTitle("CLICK-GO Motorista online")
                .setContentText("Toque para voltar ao app. A bolinha CLICK-GO está ativa.")
                .setPriority(NotificationCompat.PRIORITY_LOW)
                .setOngoing(true).setContentIntent(pi).build());
        showBubble();
    }

    private void createNotificationChannel(){
        if(Build.VERSION.SDK_INT>=26){
            NotificationManager nm=(NotificationManager)getSystemService(NOTIFICATION_SERVICE);
            if(nm!=null){NotificationChannel c=new NotificationChannel(CHANNEL,"Motorista online",NotificationManager.IMPORTANCE_LOW);c.setDescription("Mantém a bolinha flutuante do CLICK-GO ativa");nm.createNotificationChannel(c);}
        }
    }

    private void showBubble(){
        if(Build.VERSION.SDK_INT>=23&&!Settings.canDrawOverlays(this)){stopSelf();return;}
        if(bubble!=null)return;
        wm=(WindowManager)getSystemService(WINDOW_SERVICE);
        if(wm==null){stopSelf();return;}
        TextView v=new TextView(this);
        v.setText("GO");v.setTextColor(Color.BLACK);v.setTextSize(17);v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);v.setGravity(Gravity.CENTER);
        int size=dp(58);
        GradientDrawable bg=new GradientDrawable();bg.setShape(GradientDrawable.OVAL);bg.setColor(Color.rgb(255,212,0));bg.setStroke(dp(3),Color.BLACK);v.setBackground(bg);v.setElevation(dp(8));
        int type=Build.VERSION.SDK_INT>=26?WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY:WindowManager.LayoutParams.TYPE_PHONE;
        params=new WindowManager.LayoutParams(size,size,type,WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE|WindowManager.LayoutParams.FLAG_LAYOUT_NO_LIMITS,PixelFormat.TRANSLUCENT);
        params.gravity=Gravity.TOP|Gravity.START;params.x=dp(12);params.y=dp(180);
        final float[] down={0,0};final int[] origin={0,0};final boolean[] moved={false};
        v.setOnTouchListener((view,event)->{
            switch(event.getAction()){
                case MotionEvent.ACTION_DOWN: down[0]=event.getRawX();down[1]=event.getRawY();origin[0]=params.x;origin[1]=params.y;moved[0]=false;return true;
                case MotionEvent.ACTION_MOVE:
                    int dx=(int)(event.getRawX()-down[0]),dy=(int)(event.getRawY()-down[1]);
                    if(Math.abs(dx)>8||Math.abs(dy)>8)moved[0]=true;
                    params.x=origin[0]+dx;params.y=origin[1]+dy;try{wm.updateViewLayout(v,params);}catch(Exception ignored){}return true;
                case MotionEvent.ACTION_UP:
                    if(!moved[0])openApp();return true;
            }
            return false;
        });
        bubble=v;
        try{wm.addView(bubble,params);}catch(Exception e){bubble=null;stopSelf();}
    }

    private void openApp(){try{startActivity(new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP));}catch(Exception ignored){}}
    private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}
    @Override public int onStartCommand(Intent intent,int flags,int startId){if(bubble==null)showBubble();return START_STICKY;}
    @Override public void onDestroy(){if(wm!=null&&bubble!=null)try{wm.removeView(bubble);}catch(Exception ignored){}bubble=null;super.onDestroy();}
    @Override public IBinder onBind(Intent intent){return null;}
}
''', encoding='utf-8')

# -----------------------------------------------------------------------------
# 9) Versão 2.3 PRIME.
# -----------------------------------------------------------------------------
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.3-prime'", build, count=1)

repo_path.write_text(repo, encoding='utf-8')
main_path.write_text(text, encoding='utf-8')
manifest_path.write_text(manifest, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Motorista v2.3 PRIME: usuário inexistente, recuperação validada, som de chamada e bolha flutuante aplicados.')
