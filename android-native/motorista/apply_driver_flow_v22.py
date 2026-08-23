from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=main.read_text(encoding='utf-8')

# Validação final do novo fluxo: início direto e rota viária permanecem ativos.
if 'Button start=primary("▶ Iniciar corrida")' not in text:
    raise SystemExit('Botão de início direto da corrida não encontrado')
if 'drawDriverRoadRoute(r);' not in text:
    raise SystemExit('Rota viária da corrida não está ligada ao mapa do motorista')
if 'Validar PIN' in text or 'Peça ao passageiro o PIN' in text or '🆘 SOS' in text:
    raise SystemExit('PIN/SOS ainda presente no fluxo do motorista')

build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.2-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
print('Motorista v2.2 PRIME: início sem PIN/SOS e rota viária validados.')
