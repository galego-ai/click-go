from pathlib import Path

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')
old='private void showEndState(String status,double fare,String rideId){\\n        activeRideScreenVisible'
new='private void showEndState(String status,double fare,String rideId){\n        activeRideScreenVisible'
if old in text:
    text=text.replace(old,new,1)
path.write_text(text,encoding='utf-8')
print('Passageiro v2.16: quebra de linha normalizada.')
