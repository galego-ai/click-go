from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.35 PRIME
# Deixa a exclusao de cartao clara para o passageiro sem alterar a regra segura
# de exclusao existente no backend/Efi.

# Botao exibido no cartao salvo.
text, button_count = re.subn(
    r'smallButton\(\s*"Remover"\s*\)',
    'smallButton("Excluir cartão")',
    text,
    count=1,
)
if button_count == 0 and 'smallButton("Excluir cartão")' not in text:
    raise SystemExit('Botao de remover cartao nao encontrado')

# Dialogo de confirmacao. Aceita tanto a formatacao antiga quanto a compactada
# pelos patches mais novos.
text = text.replace('"Remover cartão"', '"Excluir cartão"', 1)
text = text.replace('"Deseja remover esta forma de pagamento salva?"', '"Deseja excluir este cartão salvo?"', 1)
text, positive_count = re.subn(
    r'\.setPositiveButton\(\s*"Remover"\s*,',
    '.setPositiveButton("Excluir",',
    text,
    count=1,
)
if positive_count == 0 and '.setPositiveButton("Excluir",' not in text:
    raise SystemExit('Acao positiva do dialogo de cartao nao encontrada')

# Mensagem de sucesso: se a versao anterior estiver presente, melhora o texto;
# caso outro patch ja tenha alterado a mensagem, nao bloqueia o build.
text = text.replace('toast("Forma de pagamento removida.");', 'toast("Cartão excluído com sucesso.");', 1)

# A exclusao deve continuar usando a Edge Function delete_method; nunca volta para
# exclusao direta da tabela pelo cliente.
if 'delete_method' not in text or 'efi-card' not in text:
    raise SystemExit('Fluxo seguro delete_method da Efi nao encontrado')

for required in ['Excluir cartão', 'Deseja excluir este cartão salvo?', '.setPositiveButton("Excluir",', 'delete_method']:
    if required not in text:
        raise SystemExit('Alteracao incompleta: ' + required)

build = re.sub(r'versionCode\s+\d+', 'versionCode 235', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.35-prime'", build, count=1)

main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.35 PRIME: botao Excluir cartao aplicado; delete_method seguro preservado.')
