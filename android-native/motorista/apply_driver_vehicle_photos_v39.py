from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Motorista v3.9 PRIME
# Reaproveita o fluxo seguro de documentos já existente (câmera + storage + RPC)
# para registrar fotos de inspeção do veículo.

if 'vehicle_front' not in text:
    old='''{"comprovante_residencia","🏠 Comprovante de residência"}};'''
    new='''{"comprovante_residencia","🏠 Comprovante de residência"},{"vehicle_front","🚘 Veículo - frente"},{"vehicle_left","🚘 Veículo - lateral esquerda"},{"vehicle_right","🚘 Veículo - lateral direita"},{"vehicle_rear","🚘 Veículo - traseira"}};'''
    if old not in text:
        raise SystemExit('Lista de documentos obrigatórios não encontrada para inserir fotos do veículo')
    text=text.replace(old,new,1)

# Mantém as fotos do veículo na mesma central de documentos, com botão de câmera
# e possibilidade de reenvio caso o franqueado reprove a imagem.
for required in ['vehicle_front','vehicle_left','vehicle_right','vehicle_rear','openDocumentCamera(type)','driverDocumentCard(']:
    if required not in text:
        raise SystemExit('Fluxo de fotos do veículo incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m:
    build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.9-prime'",build,count=1)

main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.9 PRIME: fotos do veículo (frente, laterais e traseira) habilitadas.')
