from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.35 PRIME
# Torna a acao de exclusao de cartao mais clara para o passageiro,
# sem alterar a operacao segura delete_method da Edge Function Efi.

replacements = [
    ('Button remove = smallButton("Remover");', 'Button remove = smallButton("Excluir cartão");'),
    ('.setTitle("Remover cartão")', '.setTitle("Excluir cartão")'),
    ('.setMessage("Deseja remover esta forma de pagamento salva?")', '.setMessage("Deseja excluir este cartão salvo?")'),
    ('.setPositiveButton("Remover", (d, w) -> io.execute(() -> {', '.setPositiveButton("Excluir", (d, w) -> io.execute(() -> {'),
    ('toast("Forma de pagamento removida.");', 'toast("Cartão excluído com sucesso.");'),
]

for old, new in replacements:
    if old not in text:
        raise SystemExit('Texto de exclusao de cartao nao encontrado: ' + old)
    text = text.replace(old, new, 1)

# Confirma que a exclusao continua passando pela Edge Function segura da Efi.
if 'ApiClient.functionPost("efi-card",new JSONObject().put("action","delete_method").put("method_id",id),token);' not in text:
    raise SystemExit('delete_method seguro da Efi nao encontrado')

for required in ['Excluir cartão', 'Deseja excluir este cartão salvo?', 'Cartão excluído com sucesso.', 'delete_method']:
    if required not in text:
        raise SystemExit('Alteracao incompleta: ' + required)

build = re.sub(r'versionCode\s+\d+', 'versionCode 235', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.35-prime'", build, count=1)

main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.35 PRIME: botao Excluir cartao com confirmacao clara e delete_method seguro preservado.')
