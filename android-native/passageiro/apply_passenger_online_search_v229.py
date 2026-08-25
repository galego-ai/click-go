from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
api_path=Path('app/src/main/java/com/clickgo/passageiro/ApiClient.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
api=api_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.29 PRIME
# Restaura a busca online e dá ao geocode um timeout próprio. O restante do app
# continua com os timeouts normais; somente a busca de endereço pode aguardar
# um pouco mais em cold start/rede móvel.

# 1) Método de rede exclusivo para geocodificação. O ApiClient geral permanece
# inalterado para não deixar login, Supabase, corridas e demais ações lentas.
address_method='''    public static String absoluteGetAddress(String url) throws Exception {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(url).openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(10000);
            connection.setReadTimeout(20000);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("User-Agent", "CLICK-GO-Passageiro-Android/2.29");
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream();
            String body = readAll(stream);
            if (code < 200 || code >= 300) throw new Exception(extractMessage(body, "Erro HTTP " + code));
            return body == null ? "" : body;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

'''
if 'public static String absoluteGetAddress(String url)' not in api:
    anchor='''    public static String absoluteGet(String url) throws Exception {
        return request(url, "GET", null, false, null, false);
    }

'''
    if anchor not in api:
        raise SystemExit('absoluteGet do ApiClient não encontrado')
    api=api.replace(anchor,anchor+address_method,1)

# 2) A v2.28 criou fastAddressGet. A v2.29 usa o método dedicado do ApiClient.
if 'fastAddressGet(url.toString())' in text:
    text=text.replace('fastAddressGet(url.toString())','ApiClient.absoluteGetAddress(url.toString())',1)
elif 'ApiClient.absoluteGet(url.toString())' in text:
    text=text.replace('ApiClient.absoluteGet(url.toString())','ApiClient.absoluteGetAddress(url.toString())',1)
elif 'ApiClient.absoluteGetAddress(url.toString())' not in text:
    raise SystemExit('chamada online de geocode não encontrada')

# 3) Diagnóstico DEBUG: confirma corpo HTTP ou causa da falha durante o smoke.
old_root='JSONObject root=new JSONObject(ApiClient.absoluteGetAddress(url.toString()));'
new_root='''String onlineBody=ApiClient.absoluteGetAddress(url.toString());
                if(BuildConfig.DEBUG){
                    String prefix=onlineBody==null?"null":onlineBody.substring(0,Math.min(180,onlineBody.length()));
                    android.util.Log.i("CLICKGO_ADDRESS","online len="+(onlineBody==null?-1:onlineBody.length())+" prefix="+prefix);
                }
                JSONObject root=new JSONObject(onlineBody);'''
if old_root in text:
    text=text.replace(old_root,new_root,1)
elif 'String onlineBody=ApiClient.absoluteGetAddress(url.toString());' not in text:
    # Compatibilidade com uma rodada anterior do patch.
    old_diag='String onlineBody=ApiClient.absoluteGet(url.toString());'
    if old_diag in text:
        text=text.replace(old_diag,'String onlineBody=ApiClient.absoluteGetAddress(url.toString());',1)
    else:
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

# 4) Smoke de rede exercita exatamente o caso real reportado: "hospital".
old='''        }else if(networkSmoke){\n            destInput.setText("Avenida Tocantins");\n            destInput.setSelection(destInput.length());\n'''
new='''        }else if(networkSmoke){\n            destInput.setText("hospital");\n            destInput.setSelection(destInput.length());\n'''
if old in text:
    text=text.replace(old,new,1)
elif 'destInput.setText("hospital");' not in text:
    raise SystemExit('smoke online de endereço não encontrado')

if 'String onlineBody=ApiClient.absoluteGetAddress(url.toString());' not in text:
    raise SystemExit('cliente dedicado de endereço não aplicado')
if 'public static String absoluteGetAddress(String url)' not in api:
    raise SystemExit('método dedicado do ApiClient não aplicado')
if 'connection.setReadTimeout(20000);' not in api:
    raise SystemExit('timeout dedicado de endereço não aplicado')
if 'destInput.setText("hospital")' not in text:
    raise SystemExit('smoke de hospital v2.29 não aplicado')

build=re.sub(r'versionCode\s+\d+','versionCode 229',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.29-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
api_path.write_text(api,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.29 PRIME: busca online com timeout dedicado de endereço aplicada.')
