from pathlib import Path

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

# Normaliza uma quebra de linha que pode ter sido escrita literalmente pelo patch principal.
old='private void showEndState(String status,double fare,String rideId){\\n        activeRideScreenVisible'
new='private void showEndState(String status,double fare,String rideId){\n        activeRideScreenVisible'
if old in text:
    text=text.replace(old,new,1)

# Dentro do Runnable do polling, `this` aponta para o Runnable. O AlertDialog precisa da Activity.
text=text.replace('new AlertDialog.Builder(this).setTitle("Seu motorista chegou!")','new AlertDialog.Builder(MainActivity.this).setTitle("Seu motorista chegou!")',1)

# Se o Android encerrar o processo em segundo plano, a corrida salva é validada no banco
# antes de liberar a home. Isso impede uma segunda solicitação durante uma corrida ativa.
home='''    private void showHome() {\n        cancelAddressSearch();'''
home_new='''    private void showHome() {\n        String savedRide=getPreferences(MODE_PRIVATE).getString("active_ride_id","");\n        if((activeRideId==null||activeRideId.isBlank())&&!savedRide.isBlank()&&!restoringActiveRide){restoreActiveRideIfNeeded(true);return;}\n        cancelAddressSearch();'''
if home in text:
    text=text.replace(home,home_new,1)

path.write_text(text,encoding='utf-8')
print('Passageiro v2.16: alerta de chegada e retomada persistente corrigidos.')
