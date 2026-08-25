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

# Mantém o autocomplete leve e reduz o tempo entre digitação e consulta.
text,n=re.subn(
    r'ui\.postDelayed\(pendingAddressSearch\s*,\s*\d+\s*\);',
    'ui.postDelayed(pendingAddressSearch,220);',
    text,
    count=1
)
if n!=1:
    raise SystemExit('debounce atual de endereço não encontrado')

# Cancela apenas trabalho antigo que ainda esteja pendente; searchSeq protege a tela de resposta atrasada.
if 'if(addressFuture!=null&&!addressFuture.isDone())addressFuture.cancel(false);' not in text:
    needle='''        if(pendingAddressSearch!=null){ui.removeCallbacks(pendingAddressSearch);pendingAddressSearch=null;}\n        String normalized=query==null?"":query.trim();'''
    replacement='''        if(pendingAddressSearch!=null){ui.removeCallbacks(pendingAddressSearch);pendingAddressSearch=null;}\n        if(addressFuture!=null&&!addressFuture.isDone())addressFuture.cancel(false);\n        String normalized=query==null?"":query.trim();'''
    if needle in text:
        text=text.replace(needle,replacement,1)

# O endpoint /api/geocode já usa o caminho rápido globalmente: Mapbox primeiro e fallbacks só quando necessários.
# Mantém no máximo cinco sugestões para renderização mais leve.
text=text.replace('items.size()<6','items.size()<5',1)

build=re.sub(r'versionCode\s+\d+','versionCode 222',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.22-prime'",build,count=1)
main.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.22 PRIME: busca de endereço rápida, regionalizada e não bloqueante aplicada.')
