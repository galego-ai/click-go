from pathlib import Path

p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=p.read_text(encoding='utf-8')

broken='String route=ride.optString("_origin_address","Endereço não informado")+"\n→ "+ride.optString("_destination_address","Endereço não informado");'
fixed='String route=ride.optString("_origin_address","Endereço não informado")+" → "+ride.optString("_destination_address","Endereço não informado");'

if broken not in text:
    raise SystemExit('Rótulo de rota quebrado da v2.20 não encontrado')
text=text.replace(broken,fixed,1)
p.write_text(text,encoding='utf-8')
print('Passageiro v2.20: rótulo do histórico normalizado para Java válido.')
