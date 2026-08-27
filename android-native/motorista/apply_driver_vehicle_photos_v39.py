from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Motorista v3.9 PRIME
# Reaproveita o fluxo seguro de documentos já existente (câmera + storage + RPC)
# para registrar fotos de inspeção do veículo, sem confundi-las com documentos pessoais obrigatórios.

if 'vehicle_front' not in text:
    old='''            for(String[] item:required){body.addView(driverDocumentCard(item[0],item[1],latest.get(item[0])));body.addView(space(9));}\n'''
    new='''            for(String[] item:required){body.addView(driverDocumentCard(item[0],item[1],latest.get(item[0])));body.addView(space(9));}\n            body.addView(space(8));\n            body.addView(text("Fotos de vistoria do veículo",19,Color.WHITE,true));\n            body.addView(text("Tire fotos atuais mostrando o veículo inteiro. O franqueado poderá visualizar e validar cada ângulo.",13,GRAY,false));\n            body.addView(space(10));\n            String[][] vehiclePhotos={{"vehicle_front","🚘 Veículo - frente"},{"vehicle_left","🚘 Veículo - lateral esquerda"},{"vehicle_right","🚘 Veículo - lateral direita"},{"vehicle_rear","🚘 Veículo - traseira"}};\n            for(String[] item:vehiclePhotos){body.addView(driverDocumentCard(item[0],item[1],latest.get(item[0])));body.addView(space(9));}\n'''
    if old not in text:
        raise SystemExit('Lista renderizada de documentos não encontrada para inserir fotos do veículo')
    text=text.replace(old,new,1)

# Mantém as fotos do veículo na mesma central de documentos, com botão de câmera
# e possibilidade de reenvio caso o franqueado reprove a imagem.
for required in ['vehicle_front','vehicle_left','vehicle_right','vehicle_rear','openDocumentCamera(type)','driverDocumentCard(','Fotos de vistoria do veículo']:
    if required not in text:
        raise SystemExit('Fluxo de fotos do veículo incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m:
    build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.9-prime'",build,count=1)

main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.9 PRIME: fotos do veículo (frente, laterais e traseira) habilitadas como vistoria separada.')
