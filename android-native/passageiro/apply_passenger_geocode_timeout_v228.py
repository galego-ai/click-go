from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.28 PRIME
# A consulta de autocomplete não pode prender a tela esperando o servidor.
# Se o endpoint demorar, o fluxo existente cai rapidamente no Geocoder nativo.

method='''
    private String fastAddressGet(String urlString) throws Exception {
        java.net.HttpURLConnection connection = null;
        try {
            connection = (java.net.HttpURLConnection) new java.net.URL(urlString).openConnection();
            connection.setRequestMethod("GET");
            connection.setConnectTimeout(1600);
            connection.setReadTimeout(2200);
            connection.setUseCaches(false);
            connection.setInstanceFollowRedirects(true);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("User-Agent", "CLICK-GO-Passageiro/2.28");
            int code = connection.getResponseCode();
            java.io.InputStream stream = code >= 200 && code < 300
                    ? connection.getInputStream()
                    : connection.getErrorStream();
            if (stream == null) throw new java.io.IOException("HTTP " + code + " sem resposta");
            java.io.BufferedReader reader = new java.io.BufferedReader(
                    new java.io.InputStreamReader(stream, java.nio.charset.StandardCharsets.UTF_8));
            StringBuilder out = new StringBuilder();
            String line;
            while ((line = reader.readLine()) != null) out.append(line);
            reader.close();
            if (code < 200 || code >= 300) throw new java.io.IOException("HTTP " + code);
            return out.toString();
        } finally {
            if (connection != null) connection.disconnect();
        }
    }
'''

# Insere antes do último fechamento da classe MainActivity. Isso é mais robusto do que
# depender da assinatura/posição de um método que outros patches anteriores podem alterar.
if 'private String fastAddressGet(String urlString)' not in text:
    close_idx=text.rfind('\n}')
    if close_idx < 0:
        raise SystemExit('fechamento da MainActivity não encontrado')
    text=text[:close_idx] + method + text[close_idx:]

before=text
if 'ApiClient.absoluteGet(url.toString())' in text:
    text=text.replace('ApiClient.absoluteGet(url.toString())','fastAddressGet(url.toString())',1)
elif 'fastAddressGet(url.toString())' not in text:
    text,n=re.subn(r'ApiClient\.absoluteGet\(\s*url\.toString\(\)\s*\)', 'fastAddressGet(url.toString())', text, count=1)
    if n == 0:
        raise SystemExit('chamada de geocode não encontrada')

if 'fastAddressGet(url.toString())' not in text or 'setReadTimeout(2200)' not in text:
    raise SystemExit('timeout rápido de endereço não aplicado')

build=re.sub(r'versionCode\s+\d+','versionCode 228',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.28-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.28 PRIME: timeout rápido de geocodificação aplicado.')

next_patch=Path('apply_passenger_online_search_v229.py')
if next_patch.exists():
    exec(compile(next_patch.read_text(encoding='utf-8'),str(next_patch),'exec'),{'__name__':'__main__'})
