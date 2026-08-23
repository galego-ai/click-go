from pathlib import Path
import re

root=Path('app')
main=root/'src/main/java/com/clickgo/motorista/MainActivity.java'
gradle=root/'build.gradle'
manifest=root/'src/main/AndroidManifest.xml'
text=main.read_text(encoding='utf-8')
build=gradle.read_text(encoding='utf-8')
man=manifest.read_text(encoding='utf-8')

if 'CLICKGO_FIREBASE_PROJECT_ID' not in build:
    build=build.replace("android {", "def firebaseProjectId = System.getenv('CLICKGO_FIREBASE_PROJECT_ID') ?: ''\ndef firebaseAppId = System.getenv('CLICKGO_FIREBASE_APP_ID') ?: ''\ndef firebaseApiKey = System.getenv('CLICKGO_FIREBASE_API_KEY') ?: ''\ndef firebaseSenderId = System.getenv('CLICKGO_FIREBASE_SENDER_ID') ?: ''\n\nandroid {",1)
    anchor="        buildConfigField 'String', 'SUPABASE_KEY', '\"sb_publishable_kvZR2g8wzx9MDIhgkRaMfw_wzujQvBt\"'\n"
    fields=anchor+"        buildConfigField 'String', 'FIREBASE_PROJECT_ID', '\"' + firebaseProjectId + '\"'\n        buildConfigField 'String', 'FIREBASE_APP_ID', '\"' + firebaseAppId + '\"'\n        buildConfigField 'String', 'FIREBASE_API_KEY', '\"' + firebaseApiKey + '\"'\n        buildConfigField 'String', 'FIREBASE_SENDER_ID', '\"' + firebaseSenderId + '\"'\n"
    if anchor not in build: raise SystemExit('SUPABASE_KEY anchor não encontrado')
    build=build.replace(anchor,fields,1)
if "firebase-messaging" not in build:
    build=build.replace("dependencies {", "dependencies {\n    implementation platform('com.google.firebase:firebase-bom:33.16.0')\n    implementation 'com.google.firebase:firebase-messaging'",1)

if 'POST_NOTIFICATIONS' not in man:
    man=man.replace('    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />','    <uses-permission android:name="android.permission.ACCESS_COARSE_LOCATION" />\n    <uses-permission android:name="android.permission.POST_NOTIFICATIONS" />',1)
if 'ClickGoMessagingService' not in man:
    svc='''        <service\n            android:name=".ClickGoMessagingService"\n            android:exported="false">\n            <intent-filter>\n                <action android:name="com.google.firebase.MESSAGING_EVENT" />\n            </intent-filter>\n        </service>\n'''
    man=man.replace('        <activity\n            android:name=".MainActivity"',svc+'        <activity\n            android:name=".MainActivity"',1)

if 'PushRegistration.register(this,token,"driver")' not in text:
    text=text.replace('    private void showHome() {\n','    private void showHome() {\n        PushRegistration.register(this,token,"driver");\n',1)

pkg=root/'src/main/java/com/clickgo/motorista'
pkg.mkdir(parents=True,exist_ok=True)
(pkg/'PushRegistration.java').write_text(r'''package com.clickgo.motorista;

import android.Manifest;
import android.app.Activity;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.os.Build;
import com.google.firebase.FirebaseApp;
import com.google.firebase.FirebaseOptions;
import com.google.firebase.messaging.FirebaseMessaging;
import org.json.JSONObject;

public final class PushRegistration {
    private static final String CHANNEL="clickgo_updates";
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
    static void ensureChannel(Context context){if(Build.VERSION.SDK_INT>=26){NotificationManager nm=(NotificationManager)context.getSystemService(Context.NOTIFICATION_SERVICE);if(nm!=null){NotificationChannel ch=new NotificationChannel(CHANNEL,"CLICK-GO",NotificationManager.IMPORTANCE_HIGH);ch.setDescription("Corridas, segurança e atualizações importantes");nm.createNotificationChannel(ch);}}}
    static String channel(){return CHANNEL;}
}
''',encoding='utf-8')
(pkg/'ClickGoMessagingService.java').write_text(r'''package com.clickgo.motorista;

import android.app.PendingIntent;
import android.content.Intent;
import androidx.core.app.NotificationCompat;
import androidx.core.app.NotificationManagerCompat;
import com.google.firebase.messaging.FirebaseMessagingService;
import com.google.firebase.messaging.RemoteMessage;

public class ClickGoMessagingService extends FirebaseMessagingService {
    @Override public void onNewToken(String token){super.onNewToken(token);getSharedPreferences("clickgo_push",MODE_PRIVATE).edit().putString("token",token).apply();String access=getSharedPreferences("MainActivity",MODE_PRIVATE).getString("access_token",null);if(access!=null)PushRegistration.sendToken(this,access,"driver",token);}
    @Override public void onMessageReceived(RemoteMessage msg){super.onMessageReceived(msg);PushRegistration.ensureChannel(this);String title="CLICK-GO";String body="Você recebeu uma atualização.";if(msg.getNotification()!=null){if(msg.getNotification().getTitle()!=null)title=msg.getNotification().getTitle();if(msg.getNotification().getBody()!=null)body=msg.getNotification().getBody();}else{if(msg.getData().get("title")!=null)title=msg.getData().get("title");if(msg.getData().get("body")!=null)body=msg.getData().get("body");}Intent i=new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_CLEAR_TOP|Intent.FLAG_ACTIVITY_SINGLE_TOP);PendingIntent pi=PendingIntent.getActivity(this,0,i,PendingIntent.FLAG_UPDATE_CURRENT|PendingIntent.FLAG_IMMUTABLE);NotificationCompat.Builder b=new NotificationCompat.Builder(this,PushRegistration.channel()).setSmallIcon(android.R.drawable.ic_dialog_info).setContentTitle(title).setContentText(body).setStyle(new NotificationCompat.BigTextStyle().bigText(body)).setPriority(NotificationCompat.PRIORITY_HIGH).setAutoCancel(true).setContentIntent(pi);try{NotificationManagerCompat.from(this).notify((int)(System.currentTimeMillis()%100000),b.build());}catch(SecurityException ignored){}}
}
''',encoding='utf-8')

m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.0-prime'",build,count=1)
gradle.write_text(build,encoding='utf-8');manifest.write_text(man,encoding='utf-8');main.write_text(text,encoding='utf-8')
print('Motorista v2.0 PRIME: infraestrutura FCM preparada; ativa quando variáveis Firebase estiverem configuradas.')
