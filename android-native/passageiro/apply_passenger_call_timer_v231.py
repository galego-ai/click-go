from pathlib import Path
import re
import runpy

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.31 PRIME
# Mostra há quanto tempo o passageiro está chamando/procurando um motorista.

field_anchor='    private TextView activeStatus;\n'
if 'private TextView callTimerText;' not in text:
    if field_anchor not in text:
        raise SystemExit('Campo activeStatus não encontrado para contador de chamada')
    text=text.replace(field_anchor,field_anchor+'''    private TextView callTimerText;\n    private long callStartedAtMs=0L;\n    private Runnable callTimerRunnable;\n''',1)

request_anchor='''        final RideOption option = selectedOption;\n        final Button targetButton = requestRideButton;\n'''
if 'callStartedAtMs=System.currentTimeMillis();' not in text:
    if request_anchor not in text:
        raise SystemExit('Ponto de início da solicitação não encontrado')
    text=text.replace(request_anchor,'''        final RideOption option = selectedOption;\n        final Button targetButton = requestRideButton;\n        callStartedAtMs=System.currentTimeMillis();\n''',1)

active_anchor='''        activeStatus=text(trackingUiActive?"Motorista a caminho":"Procurando motorista mais próximo…",25,BLACK,true);body.addView(activeStatus,lpMatchWrap());activeFare=text(selectedOption==null?"":money(selectedOption.fare),20,BLACK,true);body.addView(activeFare,lpMatchWrap());body.addView(space(12));\n'''
active_replacement='''        stopCallTimer();\n        activeStatus=text(trackingUiActive?"Motorista a caminho":"Procurando motorista mais próximo…",25,BLACK,true);body.addView(activeStatus,lpMatchWrap());\n        if(!trackingUiActive){\n            callTimerText=text("Chamando motorista há 00:00",15,Color.rgb(155,105,0),true);\n            callTimerText.setGravity(Gravity.LEFT);\n            callTimerText.setPadding(0,dp(5),0,dp(3));\n            body.addView(callTimerText,lpMatchWrap());\n            if(callStartedAtMs<=0L)callStartedAtMs=System.currentTimeMillis();\n            startCallTimer();\n        }\n        activeFare=text(selectedOption==null?"":money(selectedOption.fare),20,BLACK,true);body.addView(activeFare,lpMatchWrap());body.addView(space(12));\n'''
if 'Chamando motorista há 00:00' not in text:
    if active_anchor not in text:
        raise SystemExit('Tela de busca do motorista não encontrada para inserir contador')
    text=text.replace(active_anchor,active_replacement,1)

poll_anchor='    private void startRidePolling() {\n'
helpers=r'''    private void startCallTimer(){
        stopCallTimer();
        if(callStartedAtMs<=0L)callStartedAtMs=System.currentTimeMillis();
        callTimerRunnable=new Runnable(){
            @Override public void run(){
                if(destroyed||isFinishing()||trackingUiActive||activeRideId==null||callTimerText==null||!callTimerText.isAttachedToWindow())return;
                long elapsed=Math.max(0L,System.currentTimeMillis()-callStartedAtMs);
                callTimerText.setText("Chamando motorista há "+formatCallElapsed(elapsed));
                ui.postDelayed(this,1000L);
            }
        };
        ui.post(callTimerRunnable);
    }

    private void stopCallTimer(){
        if(callTimerRunnable!=null)ui.removeCallbacks(callTimerRunnable);
        callTimerRunnable=null;
        callTimerText=null;
    }

    private String formatCallElapsed(long elapsedMs){
        long total=Math.max(0L,elapsedMs/1000L);
        long minutes=total/60L;
        long seconds=total%60L;
        return String.format(Locale.getDefault(),"%02d:%02d",minutes,seconds);
    }

'''
if 'private void startCallTimer()' not in text:
    if poll_anchor not in text:
        raise SystemExit('startRidePolling não encontrado para inserir helpers do contador')
    text=text.replace(poll_anchor,helpers+poll_anchor,1)

# Finalização/cancelamento encerra o contador e zera a referência para a próxima chamada.
end_pat=r'(    private void showEndState\(String status, double fare\)\s*\{\n)'
if 'callStartedAtMs=0L;' not in text:
    text,n=re.subn(end_pat,r'\1        stopCallTimer();\n        callStartedAtMs=0L;\n',text,count=1)
    if n!=1:
        raise SystemExit('showEndState não encontrado para finalizar contador')

for required in ['Chamando motorista há 00:00','startCallTimer()','formatCallElapsed','callStartedAtMs=System.currentTimeMillis()']:
    if required not in text:
        raise SystemExit('Contador de chamada incompleto: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 231',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.31-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.31 PRIME: tempo de chamada do motorista visível durante a busca.')

runpy.run_path('apply_passenger_efi_card_registration_v232.py',run_name='__main__')
