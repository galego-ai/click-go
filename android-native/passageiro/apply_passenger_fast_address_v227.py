from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.27 PRIME
# - reduz o debounce do autocomplete;
# - aumenta a concorrência para uma busca antiga/lenta não bloquear a nova;
# - interrompe trabalhos antigos quando possível;
# - mantém o fallback nativo e Buscar no mapa sem alterar a camada geral de rede.

if 'private final ExecutorService addressIo = Executors.newFixedThreadPool(2);' in text:
    text=text.replace(
        'private final ExecutorService addressIo = Executors.newFixedThreadPool(2);',
        'private final ExecutorService addressIo = Executors.newFixedThreadPool(4);',
        1
    )
elif 'private final ExecutorService addressIo = Executors.newFixedThreadPool(4);' not in text:
    raise SystemExit('executor de endereço não encontrado')

if 'ui.postDelayed(pendingAddressSearch,220);' in text:
    text=text.replace('ui.postDelayed(pendingAddressSearch,220);','ui.postDelayed(pendingAddressSearch,140);',1)
elif 'ui.postDelayed(pendingAddressSearch,140);' not in text:
    raise SystemExit('debounce de endereço não encontrado')

text=text.replace(
    'if(addressFuture!=null&&!addressFuture.isDone())addressFuture.cancel(false);',
    'if(addressFuture!=null&&!addressFuture.isDone())addressFuture.cancel(true);'
)

if 'newFixedThreadPool(4)' not in text or 'pendingAddressSearch,140' not in text:
    raise SystemExit('marcadores v2.27 não aplicados')

build=re.sub(r'versionCode\s+\d+','versionCode 227',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.27-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.27 PRIME: autocomplete de endereço acelerado.')

next_patch=Path('apply_passenger_geocode_timeout_v228.py')
if next_patch.exists():
    exec(compile(next_patch.read_text(encoding='utf-8'),str(next_patch),'exec'),{'__name__':'__main__'})
