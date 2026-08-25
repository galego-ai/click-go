from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# A busca roda fora da UI. Dois workers evitam que uma consulta lenta antiga bloqueie a mais nova;
# searchSeq continua descartando qualquer resposta ultrapassada.
text=text.replace(
    'private final ExecutorService addressIo = Executors.newSingleThreadExecutor();',
    'private final ExecutorService addressIo = Executors.newFixedThreadPool(2);',
    1
)

# Mantém o mínimo de 3 caracteres para não bombardear o serviço e reduz o debounce,
# independentemente do valor deixado pelos patches anteriores.
text,n=re.subn(
    r'ui\.postDelayed\(pendingAddressSearch\s*,\s*\d+\s*\);',
    'ui.postDelayed(pendingAddressSearch,220);',
    text,
    count=1
)
if n!=1:
    raise SystemExit('debounce atual de endereço não encontrado')

# Cancela trabalho que ainda esteja na fila antes de enfileirar a nova consulta.
needle='''        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);\n        if (safeQuery.length() < 3) {'''
replacement='''        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);\n        if (addressFuture != null && !addressFuture.isDone()) addressFuture.cancel(false);\n        if (safeQuery.length() < 3) {'''
if needle in text:
    text=text.replace(needle,replacement,1)
else:
    needle='''        if(pendingAddressSearch!=null){ui.removeCallbacks(pendingAddressSearch);pendingAddressSearch=null;}\n        if(normalized.length()<3){'''
    replacement='''        if(pendingAddressSearch!=null){ui.removeCallbacks(pendingAddressSearch);pendingAddressSearch=null;}\n        if(addressFuture!=null&&!addressFuture.isDone())addressFuture.cancel(false);\n        if(normalized.length()<3){'''
    if needle in text:
        text=text.replace(needle,replacement,1)

# Pede ao backend o caminho rápido, sem pesquisas pesadas de POI quando o usuário só está digitando endereço.
old='''.append("?q=").append(URLEncoder.encode(query,StandardCharsets.UTF_8.toString()));'''
new='''.append("?q=").append(URLEncoder.encode(query,StandardCharsets.UTF_8.toString())).append("&fast=1");'''
if old not in text:
    raise SystemExit('construção da URL de geocode não encontrada')
text=text.replace(old,new,1)

# Cinco sugestões são suficientes para a tela e deixam renderização/rolagem mais leves.
text=text.replace('items.size()<6','items.size()<5',1)

build=re.sub(r'versionCode\s+\d+','versionCode 222',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.22-prime'",build,count=1)
main.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.22 PRIME: busca de endereço rápida, regionalizada e não bloqueante aplicada.')
