from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.34 PRIME
# - encerra a busca após 5 minutos somente se o servidor confirmar que nenhum motorista aceitou;
# - não gera taxa de cancelamento por timeout;
# - oferece "Tentar de novo" com a mesma origem/destino/categoria/pagamento ou "Voltar";
# - ao reabrir o app, preserva o tempo real da busca usando requested_at do banco.

field_anchor='    private AlertDialog efiCardDialog;\n'
fields='''    private AlertDialog efiCardDialog;\n    private static final long DRIVER_SEARCH_TIMEOUT_MS=5L*60L*1000L;\n    private boolean driverSearchTimeoutInProgress=false;\n    private AlertDialog driverSearchTimeoutDialog;\n'''
if 'DRIVER_SEARCH_TIMEOUT_MS' not in text:
    if field_anchor not in text: raise SystemExit('campo efiCardDialog não encontrado')
    text=text.replace(field_anchor,fields,1)

# A restauração precisa trazer requested_at para não reiniciar a contagem ao fechar/reabrir o app.
restore_start=text.find('private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing)')
restore_end=text.find('\n    private void showHome()',restore_start)
if restore_start<0 or restore_end<0: raise SystemExit('restoreActiveRideIfNeeded não encontrado')
restore=text[restore_start:restore_end]
if 'requested_at' not in restore:
    restore=restore.replace('payment_method_preference,driver_id&order=', 'payment_method_preference,driver_id,requested_at&order=',1)
    if 'requested_at' not in restore: raise SystemExit('select da restauração não encontrado')

status_anchor='activeRideId=id;activeRideStatus=status;trackingUiActive=(status.equals("accepted")||status.equals("driver_arriving")||status.equals("in_progress"));'
status_repl=status_anchor+'''\n                    if(status.equals("requested")||status.equals("searching")){long restoredStart=parseSupabaseTimestampMs(r.optString("requested_at",""));callStartedAtMs=restoredStart>0L?restoredStart:System.currentTimeMillis();}'''
if 'parseSupabaseTimestampMs(r.optString("requested_at"' not in restore:
    if status_anchor not in restore: raise SystemExit('estado restaurado não encontrado')
    restore=restore.replace(status_anchor,status_repl,1)
text=text[:restore_start]+restore+text[restore_end:]

# Helpers de timestamp + timeout/retry. Usa SimpleDateFormat para manter compatibilidade com minSdk 24.
insert_anchor='    private final class SearchTimerRing extends View {'
helpers=r'''    private long parseSupabaseTimestampMs(String raw){
        if(raw==null||raw.isBlank())return 0L;
        try{
            String value=raw.trim();int t=value.indexOf('T');int z=value.endsWith("Z")?value.length()-1:-1;int plus=value.lastIndexOf('+');int minus=value.lastIndexOf('-');int tz=z>=0?z:Math.max(plus,(minus>t?minus:-1));
            if(tz<0)return 0L;int dot=value.indexOf('.',t);
            if(dot<0)value=value.substring(0,tz)+".000"+value.substring(tz);
            else{String frac=value.substring(dot+1,tz);String ms=(frac+"000").substring(0,3);value=value.substring(0,dot+1)+ms+value.substring(tz);}
            java.text.SimpleDateFormat f=new java.text.SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSSXXX",Locale.US);f.setLenient(false);java.util.Date d=f.parse(value);return d==null?0L:d.getTime();
        }catch(Exception ignored){return 0L;}
    }

    private void handleDriverSearchTimeout(){
        if(driverSearchTimeoutInProgress||destroyed||isFinishing()||trackingUiActive||activeRideId==null||activeRideId.isBlank())return;
        driverSearchTimeoutInProgress=true;final String rideId=activeRideId;stopCallTimer();
        runIo(()->{try{
            JSONObject result=new JSONObject(ApiClient.rpc("timeout_passenger_ride_search",new JSONObject().put("p_ride_id",rideId),token));
            ui.post(()->{
                driverSearchTimeoutInProgress=false;if(destroyed||isFinishing()||activeRideId==null||!rideId.equals(activeRideId))return;
                String reason=result.optString("reason","");
                if(result.optBoolean("timed_out",false)){
                    stopRidePolling();activeRideId=null;activeRideStatus="cancelled";trackingUiActive=false;callStartedAtMs=0L;driverFoundElapsedMs=0L;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();showDriverSearchTimeoutDialog(result);return;
                }
                if("too_early".equals(reason)){
                    long remaining=Math.max(1L,result.optLong("remaining_seconds",1L));callStartedAtMs=System.currentTimeMillis()-Math.max(0L,DRIVER_SEARCH_TIMEOUT_MS-(remaining*1000L));startCallTimer();return;
                }
                if("driver_found".equals(reason)){
                    // O servidor viu um aceite concorrente; o polling normal assume a transição para acompanhamento.
                    if(ridePoll==null)startRidePolling();return;
                }
                if("terminal".equals(reason)){
                    stopRidePolling();activeRideId=null;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();showHome();return;
                }
                startCallTimer();
            });
        }catch(Exception e){ui.post(()->{driverSearchTimeoutInProgress=false;if(!destroyed&&!isFinishing()&&activeRideId!=null){callStartedAtMs=System.currentTimeMillis()-295000L;startCallTimer();}});}});
    }

    private void showDriverSearchTimeoutDialog(JSONObject snapshot){
        if(destroyed||isFinishing())return;
        AlertDialog old=driverSearchTimeoutDialog;driverSearchTimeoutDialog=null;if(old!=null&&old.isShowing())try{old.dismiss();}catch(Exception ignored){}
        LinearLayout box=vertical(Color.WHITE);box.setPadding(dp(24),dp(24),dp(24),dp(20));
        TextView icon=text("⌖",46,YELLOW,true);icon.setGravity(Gravity.CENTER);box.addView(icon,lpMatchWrap());
        TextView title=text("Infelizmente não encontramos um motorista",22,BLACK,true);title.setGravity(Gravity.CENTER);title.setPadding(0,dp(8),0,dp(8));box.addView(title,lpMatchWrap());
        TextView copy=text("A busca chegou a 5 minutos. Você pode tentar novamente com o mesmo endereço ou voltar.",14,GRAY,false);copy.setGravity(Gravity.CENTER);copy.setPadding(0,0,0,dp(18));box.addView(copy,lpMatchWrap());
        Button retry=primary("Tentar de novo");retry.setContentDescription("clickgo_retry_same_ride");box.addView(retry,lpMatch(dp(56)));box.addView(space(9));
        Button back=secondaryLight("Voltar");back.setContentDescription("clickgo_search_timeout_back");box.addView(back,lpMatch(dp(54)));
        driverSearchTimeoutDialog=new AlertDialog.Builder(this).setView(box).create();driverSearchTimeoutDialog.setCancelable(false);driverSearchTimeoutDialog.setCanceledOnTouchOutside(false);
        retry.setOnClickListener(v->retryTimedOutRide(snapshot));back.setOnClickListener(v->{AlertDialog d=driverSearchTimeoutDialog;driverSearchTimeoutDialog=null;if(d!=null&&d.isShowing())d.dismiss();showHome();});
        driverSearchTimeoutDialog.show();if(driverSearchTimeoutDialog.getWindow()!=null)driverSearchTimeoutDialog.getWindow().setBackgroundDrawable(round(Color.WHITE,24,Color.TRANSPARENT));
    }

    private void retryTimedOutRide(JSONObject snapshot){
        if(snapshot==null||destroyed||isFinishing()||activeRideId!=null)return;
        refreshManagementConfiguration();if(!canRequestRideByManagement())return;
        final String categoryId=snapshot.optString("category_id","");final String payment=snapshot.optString("payment_method","cash");final String paymentId=snapshot.optString("payment_method_id","");
        final String from=snapshot.optString("origin_label","");final String to=snapshot.optString("destination_label","");final double olat=snapshot.optDouble("origin_lat",Double.NaN),olng=snapshot.optDouble("origin_lng",Double.NaN),dlat=snapshot.optDouble("destination_lat",Double.NaN),dlng=snapshot.optDouble("destination_lng",Double.NaN);
        if(categoryId.isBlank()||from.isBlank()||to.isBlank()||!Double.isFinite(olat)||!Double.isFinite(olng)||!Double.isFinite(dlat)||!Double.isFinite(dlng)){toast("Não foi possível repetir esta corrida. Escolha o destino novamente.");return;}
        runIo(()->{try{
            JSONObject body=new JSONObject().put("p_origin_label",from).put("p_origin_lat",olat).put("p_origin_lng",olng).put("p_destination_label",to).put("p_destination_lat",dlat).put("p_destination_lng",dlng).put("p_category_id",categoryId).put("p_payment_method",payment);
            if(!paymentId.isBlank()&&!"null".equalsIgnoreCase(paymentId))body.put("p_payment_method_id",paymentId);
            String raw=ApiClient.rpc("create_passenger_ride",body,token);String newRideId=raw==null?"":raw.trim();if(newRideId.startsWith("\"")&&newRideId.endsWith("\"")&&newRideId.length()>1)newRideId=newRideId.substring(1,newRideId.length()-1);java.util.UUID.fromString(newRideId);final String id=newRideId;
            ui.post(()->{if(destroyed||isFinishing())return;AlertDialog d=driverSearchTimeoutDialog;driverSearchTimeoutDialog=null;if(d!=null&&d.isShowing())d.dismiss();origin=new GeoPoint(olat,olng);destination=new GeoPoint(dlat,dlng);originLabel=from;destinationLabel=to;activeRideId=id;activeRideStatus="requested";trackingUiActive=false;callStartedAtMs=System.currentTimeMillis();driverFoundElapsedMs=0L;liveRoutePhase="";liveRouteUpdatedAtMs=0L;getPreferences(MODE_PRIVATE).edit().putString("active_ride_id",id).apply();showActiveRide();});
        }catch(Exception e){String m=message(e);ui.post(()->{if(!destroyed&&!isFinishing()){toast(m);showDriverSearchTimeoutDialog(snapshot);}});}});
    }

'''
if 'private void handleDriverSearchTimeout()' not in text:
    if insert_anchor not in text: raise SystemExit('SearchTimerRing não encontrado')
    text=text.replace(insert_anchor,helpers+insert_anchor,1)

# Aos 5 minutos chama o servidor. O servidor é a autoridade final para evitar corrida com aceite concorrente.
timer_old='''            long elapsed=Math.max(0L,System.currentTimeMillis()-callStartedAtMs);\n            if(driverSearchRing!=null)driverSearchRing.setElapsed(elapsed);\n            ui.postDelayed(this,250L);'''
timer_new='''            long elapsed=Math.max(0L,System.currentTimeMillis()-callStartedAtMs);\n            if(driverSearchRing!=null)driverSearchRing.setElapsed(Math.min(elapsed,DRIVER_SEARCH_TIMEOUT_MS));\n            if(elapsed>=DRIVER_SEARCH_TIMEOUT_MS){handleDriverSearchTimeout();return;}\n            ui.postDelayed(this,250L);'''
if 'elapsed>=DRIVER_SEARCH_TIMEOUT_MS' not in text:
    if timer_old not in text: raise SystemExit('loop do cronômetro não encontrado')
    text=text.replace(timer_old,timer_new,1)

# Ao sair/destruir a Activity, fecha também o diálogo de timeout.
destroy_anchor='''        try{stopRidePolling();}catch(Exception ignored){}\n'''
if 'driverSearchTimeoutDialog' in text and 'try{if(driverSearchTimeoutDialog!=null' not in text:
    if destroy_anchor not in text: raise SystemExit('onDestroy não encontrado')
    text=text.replace(destroy_anchor,destroy_anchor+'''        try{if(driverSearchTimeoutDialog!=null&&driverSearchTimeoutDialog.isShowing())driverSearchTimeoutDialog.dismiss();}catch(Exception ignored){}\n        driverSearchTimeoutDialog=null;driverSearchTimeoutInProgress=false;\n''',1)

for required in ['DRIVER_SEARCH_TIMEOUT_MS','timeout_passenger_ride_search','Infelizmente não encontramos um motorista','Tentar de novo','clickgo_retry_same_ride','parseSupabaseTimestampMs(r.optString("requested_at"','elapsed>=DRIVER_SEARCH_TIMEOUT_MS']:
    if required not in text: raise SystemExit('timeout de busca incompleto: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 234',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.34-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.34 PRIME: timeout de 5 minutos com tentar de novo no mesmo endereço ou voltar.')
