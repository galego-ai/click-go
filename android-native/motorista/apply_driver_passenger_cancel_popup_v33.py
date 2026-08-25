from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Motorista v3.3 PRIME
# - quando uma corrida ativa desaparece porque o passageiro cancelou, o motorista
#   recebe um popup central "Corrida cancelada pelo passageiro";
# - a corrida cancelada deixa de permanecer como operação ativa;
# - o aviso não se repete e sobrevive a uma breve ida do app ao segundo plano.

field_anchor='''    private String driverFranchiseId="",driverCityId="";\n'''
fields='''    private String driverFranchiseId="",driverCityId="";\n    private volatile String watchedRideId="";\n    private boolean passengerCancelNoticePending;\n    private boolean activityResumed;\n    private android.app.AlertDialog passengerCancelDialog;\n'''
if 'private volatile String watchedRideId=' not in text:
    if field_anchor not in text: raise SystemExit('campo driverFranchiseId não encontrado')
    text=text.replace(field_anchor,fields,1)

# Consulta pontual do último ride aceito para distinguir cancelamento de conclusão.
if 'public static JSONObject rideState(' not in repo:
    anchor='''    public static JSONObject activeRide(String token, String userId) throws Exception {\n'''
    method='''    public static JSONObject rideState(String token, String userId, String rideId) throws Exception {\n        if (rideId == null || rideId.isBlank() || userId == null || userId.isBlank()) return null;\n        JSONArray rows = new JSONArray(ApiClient.restGet("rides?id=eq." + rideId + "&driver_id=eq." + userId + "&select=id,status,cancelled_at,completed_at&limit=1", token));\n        return rows.length() > 0 ? rows.getJSONObject(0) : null;\n    }\n\n'''
    if anchor not in repo: raise SystemExit('activeRide não encontrado no DriverRepository')
    repo=repo.replace(anchor,method+anchor,1)

# Helpers do estado e popup.
helper_anchor='''    private void startPolling(){'''
helpers=r'''    private void rememberWatchedRide(String rideId){
        if(rideId==null||rideId.isBlank())return;
        watchedRideId=rideId;
        getPreferences(MODE_PRIVATE).edit().putString("watched_ride_id",rideId).apply();
    }

    private void clearWatchedRide(){
        watchedRideId="";
        getPreferences(MODE_PRIVATE).edit().remove("watched_ride_id").apply();
    }

    private void queuePassengerCancelledPopup(){
        passengerCancelNoticePending=true;
        maybeShowPassengerCancelledPopup();
    }

    private void maybeShowPassengerCancelledPopup(){
        if(!passengerCancelNoticePending||destroyed||isFinishing()||!activityResumed)return;
        if(passengerCancelDialog!=null&&passengerCancelDialog.isShowing())return;
        try{stopRideCallSound(true);}catch(Exception ignored){}
        try{dismissOfferDialog();}catch(Exception ignored){}
        if(operationBox!=null)operationBox.removeAllViews();
        if(operationTitle!=null)operationTitle.setText("Corrida cancelada");
        try{DriverMapRenderer.render(map,currentLocation,null,dp(5));}catch(Exception ignored){}
        try{
            android.os.Vibrator vib=(android.os.Vibrator)getSystemService(VIBRATOR_SERVICE);
            if(vib!=null){if(android.os.Build.VERSION.SDK_INT>=26)vib.vibrate(android.os.VibrationEffect.createOneShot(450,android.os.VibrationEffect.DEFAULT_AMPLITUDE));else vib.vibrate(450);}
        }catch(Exception ignored){}
        android.app.AlertDialog dialog=new android.app.AlertDialog.Builder(this)
                .setTitle("Corrida cancelada")
                .setMessage("Corrida cancelada pelo passageiro.")
                .setPositiveButton("OK",(d,w)->{
                    passengerCancelNoticePending=false;
                    passengerCancelDialog=null;
                    if(operationTitle!=null)operationTitle.setText("Aguardando chamadas");
                    refreshOperation();
                }).create();
        dialog.setCancelable(false);
        dialog.setCanceledOnTouchOutside(false);
        passengerCancelDialog=dialog;
        dialog.setOnDismissListener(d->{if(passengerCancelDialog==dialog)passengerCancelDialog=null;});
        dialog.show();
    }

'''
if 'private void queuePassengerCancelledPopup()' not in text:
    if helper_anchor not in text: raise SystemExit('startPolling não encontrado')
    text=text.replace(helper_anchor,helpers+helper_anchor,1)

# Polling: memoriza o ride ativo; se ele some, consulta o status final e avisa se cancelled.
pat=re.compile(r'''    private void refreshOperation\(\)\{\n        if\(!refreshingOperation\.compareAndSet\(false,true\)\) return;\n        io\.execute\(\(\) -> \{\n            try \{\n                JSONObject ride=DriverRepository\.activeRide\(token,userId\);\n                if\(ride!=null\)\{ui\.post\(\(\)->renderRide\(ride\)\);return;\}\n                JSONObject offer=DriverRepository\.firstOffer\(token\);\n                ui\.post\(\(\)->renderOffer\(offer\)\);\n            \} catch\(Exception e\)\{\n                ui\.post\(\(\)->\{if\(operationTitle!=null\)operationTitle\.setText\("Falha ao atualizar chamadas\."\);\}\);\n            \} finally \{\n                refreshingOperation\.set\(false\);\n            \}\n        \}\);\n    \}''')
replacement='''    private void refreshOperation(){\n        if(passengerCancelNoticePending||(passengerCancelDialog!=null&&passengerCancelDialog.isShowing()))return;\n        if(!refreshingOperation.compareAndSet(false,true)) return;\n        io.execute(() -> {\n            try {\n                JSONObject ride=DriverRepository.activeRide(token,userId);\n                if(ride!=null){\n                    rememberWatchedRide(ride.optString("id",""));\n                    ui.post(()->renderRide(ride));\n                    return;\n                }\n                String watched=watchedRideId;\n                if(watched==null||watched.isBlank()){\n                    watched=getPreferences(MODE_PRIVATE).getString("watched_ride_id","");\n                    watchedRideId=watched==null?"":watched;\n                }\n                if(watched!=null&&!watched.isBlank()){\n                    JSONObject ended=DriverRepository.rideState(token,userId,watched);\n                    String endedStatus=ended==null?"":ended.optString("status","");\n                    if("cancelled".equals(endedStatus)){\n                        clearWatchedRide();\n                        ui.post(this::queuePassengerCancelledPopup);\n                        return;\n                    }\n                    if(!endedStatus.isBlank()&&!"accepted".equals(endedStatus)&&!"driver_arriving".equals(endedStatus)&&!"in_progress".equals(endedStatus))clearWatchedRide();\n                }\n                JSONObject offer=DriverRepository.firstOffer(token);\n                ui.post(()->renderOffer(offer));\n            } catch(Exception e){\n                ui.post(()->{if(operationTitle!=null)operationTitle.setText("Falha ao atualizar chamadas.");});\n            } finally {\n                refreshingOperation.set(false);\n            }\n        });\n    }'''
text,n=pat.subn(replacement,text,count=1)
if n!=1: raise SystemExit('refreshOperation final não encontrado')

# Lifecycle: se o cancelamento chegar com o app atrás, exibe ao voltar.
resume_pat=re.compile(r'''    @Override protected void onResume\(\) \{ super\.onResume\(\); if\(map!=null\) try\{map\.onResume\(\);\}catch\(Exception ignored\)\{\} if\(online\)syncFloatingBubble\(\); \}''')
text,n=resume_pat.subn('    @Override protected void onResume() { super.onResume(); activityResumed=true; if(map!=null) try{map.onResume();}catch(Exception ignored){} if(online)syncFloatingBubble(); maybeShowPassengerCancelledPopup(); }',text,count=1)
if n!=1: raise SystemExit('onResume final não encontrado')

pause_pat=re.compile(r'''    @Override protected void onPause\(\) \{ if\(map!=null\) try\{map\.onPause\(\);\}catch\(Exception ignored\)\{\} super\.onPause\(\); \}''')
text,n=pause_pat.subn('    @Override protected void onPause() { activityResumed=false; if(map!=null) try{map.onPause();}catch(Exception ignored){} super.onPause(); }',text,count=1)
if n!=1: raise SystemExit('onPause final não encontrado')

# Logout limpa qualquer referência antiga para não avisar outra conta.
text=text.replace('''    private void logout(){stopRideCallSound(true);stopFloatingBubble();clearStoredSession();stopPolling();stopLocationWatch();releaseMap();showLogin();}''','''    private void logout(){clearWatchedRide();passengerCancelNoticePending=false;stopRideCallSound(true);stopFloatingBubble();clearStoredSession();stopPolling();stopLocationWatch();releaseMap();showLogin();}''',1)

build=re.sub(r'versionCode\s+\d+','versionCode 33',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '3.3-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
repo_path.write_text(repo,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.3 PRIME: popup de cancelamento pelo passageiro aplicado.')
