from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.28 PRIME
# A consulta de autocomplete não pode prender a tela esperando o servidor.
# Se o endpoint demorar, o fluxo existente cai rapidamente no Geocoder nativo.

method='''    private String fastAddressGet(String urlString) throws Exception {\n        java.net.HttpURLConnection connection = null;\n        try {\n            connection = (java.net.HttpURLConnection) new java.net.URL(urlString).openConnection();\n            connection.setRequestMethod("GET");\n            connection.setConnectTimeout(1600);\n            connection.setReadTimeout(2200);\n            connection.setUseCaches(false);\n            connection.setRequestProperty("Accept", "application/json");\n            connection.setRequestProperty("User-Agent", "CLICK-GO-Passageiro/2.28");\n            int code = connection.getResponseCode();\n            java.io.InputStream stream = code >= 200 && code < 300\n                    ? connection.getInputStream()\n                    : connection.getErrorStream();\n            java.io.BufferedReader reader = new java.io.BufferedReader(\n                    new java.io.InputStreamReader(stream == null ? new java.io.ByteArrayInputStream(new byte[0]) : stream, java.nio.charset.StandardCharsets.UTF_8));\n            StringBuilder out = new StringBuilder();\n            String line;\n            while ((line = reader.readLine()) != null) out.append(line);\n            reader.close();\n            if (code < 200 || code >= 300) throw new java.io.IOException("HTTP " + code);\n            return out.toString();\n        } finally {\n            if (connection != null) connection.disconnect();\n        }\n    }\n\n'''

if 'private String fastAddressGet(String urlString)' not in text:
    anchor='    private void startAddressSearch(String raw, LinearLayout target, int seq) {'
    if anchor not in text:
        raise SystemExit('startAddressSearch não encontrado')
    text=text.replace(anchor, method+anchor, 1)

if 'ApiClient.absoluteGet(url.toString())' in text:
    text=text.replace('ApiClient.absoluteGet(url.toString())','fastAddressGet(url.toString())',1)
elif 'fastAddressGet(url.toString())' not in text:
    raise SystemExit('chamada de geocode não encontrada')

if 'fastAddressGet(url.toString())' not in text or 'setReadTimeout(2200)' not in text:
    raise SystemExit('timeout rápido de endereço não aplicado')

build=re.sub(r'versionCode\s+\d+','versionCode 228',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.28-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.28 PRIME: timeout rápido de geocodificação aplicado.')
