from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.29 PRIME
# Restaura a busca online de endereços/POIs em rede móvel.
# A chamada de geocode pede resposta sem compressão para evitar Brotli em
# HttpURLConnection e mantém tempo suficiente para cold start da Vercel.

if 'connection.setConnectTimeout(1600);' in text:
    text=text.replace('connection.setConnectTimeout(1600);','connection.setConnectTimeout(3000);',1)
elif 'connection.setConnectTimeout(3000);' not in text:
    raise SystemExit('timeout de conexão v2.28 não encontrado')

if 'connection.setReadTimeout(2200);' in text:
    text=text.replace('connection.setReadTimeout(2200);','connection.setReadTimeout(5000);',1)
elif 'connection.setReadTimeout(5000);' not in text:
    raise SystemExit('timeout de leitura v2.28 não encontrado')

text=text.replace('CLICK-GO-Passageiro/2.28','CLICK-GO-Passageiro/2.29',1)

accept_anchor='connection.setRequestProperty("Accept", "application/json");'
identity_line='connection.setRequestProperty("Accept-Encoding", "identity");'
if identity_line not in text:
    if accept_anchor not in text:
        raise SystemExit('header Accept do geocode não encontrado')
    text=text.replace(accept_anchor,accept_anchor+'\n            '+identity_line,1)

# O smoke de rede exercita ponto de interesse genérico, exatamente o caso real
# reportado pelo usuário ("hospital").
old='''        }else if(networkSmoke){\n            destInput.setText("Avenida Tocantins");\n            destInput.setSelection(destInput.length());\n'''
new='''        }else if(networkSmoke){\n            destInput.setText("hospital");\n            destInput.setSelection(destInput.length());\n'''
if old in text:
    text=text.replace(old,new,1)
elif 'destInput.setText("hospital");' not in text:
    raise SystemExit('smoke online de endereço não encontrado')

if 'setConnectTimeout(3000)' not in text or 'setReadTimeout(5000)' not in text:
    raise SystemExit('timeouts v2.29 não aplicados')
if identity_line not in text:
    raise SystemExit('Accept-Encoding identity não aplicado')
if 'destInput.setText("hospital")' not in text:
    raise SystemExit('smoke de hospital v2.29 não aplicado')

build=re.sub(r'versionCode\s+\d+','versionCode 229',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.29-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.29 PRIME: busca online restaurada com resposta HTTP sem Brotli e teste de hospital.')
