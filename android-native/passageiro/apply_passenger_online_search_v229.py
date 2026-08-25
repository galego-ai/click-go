from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.29 PRIME
# Restaura a busca online usando o cliente de rede estável que já funcionava
# antes da v2.28. Mantém as melhorias da v2.27 (debounce, workers e cancelamento)
# e deixa o helper rápido da v2.28 sem uso, evitando regressão no parser HTTP.

# A v2.28 trocou ApiClient.absoluteGet por fastAddressGet. Voltamos ao caminho
# comprovadamente funcional sem mexer nas demais APIs do aplicativo.
if 'fastAddressGet(url.toString())' in text:
    text=text.replace('fastAddressGet(url.toString())','ApiClient.absoluteGet(url.toString())',1)
elif 'ApiClient.absoluteGet(url.toString())' not in text:
    raise SystemExit('chamada online de geocode não encontrada')

# Adiciona diagnóstico apenas em DEBUG para provar se o corpo online chegou e
# foi convertido em resultados durante o smoke de CI.
old_root='JSONObject root=new JSONObject(ApiClient.absoluteGet(url.toString()));'
new_root='''String onlineBody=ApiClient.absoluteGet(url.toString());
                if(BuildConfig.DEBUG){
                    String prefix=onlineBody==null?"null":onlineBody.substring(0,Math.min(180,onlineBody.length()));
                    android.util.Log.i("CLICKGO_ADDRESS","online len="+(onlineBody==null?-1:onlineBody.length())+" prefix="+prefix);
                }
                JSONObject root=new JSONObject(onlineBody);'''
if old_root in text:
    text=text.replace(old_root,new_root,1)
elif 'String onlineBody=ApiClient.absoluteGet(url.toString());' not in text:
    raise SystemExit('ponto de diagnóstico do geocode não encontrado')

old_catch='''            }catch(Exception e){
                failure=message(e);
            }
'''
new_catch='''            }catch(Exception e){
                failure=message(e);
                if(BuildConfig.DEBUG)android.util.Log.e("CLICKGO_ADDRESS","online falhou: "+failure,e);
            }
'''
if old_catch in text:
    text=text.replace(old_catch,new_catch,1)
elif 'online falhou:' not in text:
    raise SystemExit('catch da busca online não encontrado')

# O smoke de rede exercita exatamente o caso real reportado: ponto de interesse.
old='''        }else if(networkSmoke){\n            destInput.setText("Avenida Tocantins");\n            destInput.setSelection(destInput.length());\n'''
new='''        }else if(networkSmoke){\n            destInput.setText("hospital");\n            destInput.setSelection(destInput.length());\n'''
if old in text:
    text=text.replace(old,new,1)
elif 'destInput.setText("hospital");' not in text:
    raise SystemExit('smoke online de endereço não encontrado')

if 'String onlineBody=ApiClient.absoluteGet(url.toString());' not in text:
    raise SystemExit('cliente estável não restaurado')
if 'destInput.setText("hospital")' not in text:
    raise SystemExit('smoke de hospital v2.29 não aplicado')

build=re.sub(r'versionCode\s+\d+','versionCode 229',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.29-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.29 PRIME: cliente de rede estável restaurado e smoke de hospital aplicado.')
