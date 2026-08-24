from pathlib import Path
p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=p.read_text(encoding='utf-8')
old='''new AlertDialog.Builder(this).setTitle("Seu motorista chegou!").setMessage("O motorista está no local de embarque.").setPositiveButton("OK",null).show();'''
new='''new AlertDialog.Builder(MainActivity.this).setTitle("Seu motorista chegou!").setMessage("O motorista está no local de embarque.").setPositiveButton("OK",null).show();'''
if old not in text: raise SystemExit('Alerta de chegada v2.14 não encontrado')
text=text.replace(old,new,1)
p.write_text(text,encoding='utf-8')
print('Passageiro v2.14: contexto do alerta de chegada corrigido.')
