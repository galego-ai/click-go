from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.33 PRIME
# PIX deixa de ser oferecido ao passageiro. Mantemos o backend e outros módulos intactos.

# Mesmo que a cidade tenha PIX habilitado na configuração financeira, o app Passageiro
# remove essa opção antes de montar o seletor de pagamento.
anchor='''                    paymentValues.clear();\n                    paymentValues.addAll(payments);\n'''
replacement='''                    paymentValues.clear();\n                    paymentValues.addAll(payments);\n                    paymentValues.remove("pix");\n'''
if 'paymentValues.remove("pix");' not in text:
    if anchor not in text:
        raise SystemExit('lista final de pagamentos nao encontrada')
    text=text.replace(anchor,replacement,1)

# Formas de pagamento: não exibir PIX como disponibilidade para o passageiro.
text=text.replace(
    'PIX, dinheiro e cartão são liberados por cidade. A disponibilidade exata também aparece antes de solicitar a corrida.',
    'Dinheiro e cartão são liberados por cidade. A disponibilidade exata também aparece antes de solicitar a corrida.'
)
text=text.replace('            availability.addView(paymentStatus("PIX", settings.optBoolean("pix_enabled")));\n','')

# Defesa adicional: um estado antigo ou valor residual nunca pode criar corrida com PIX.
payment_anchor='''        final String payment = paymentValues.get(index);\n'''
payment_replacement='''        final String payment = paymentValues.get(index);\n        if ("pix".equals(payment)) {\n            toast("PIX não está disponível no app Passageiro.");\n            return;\n        }\n'''
if 'PIX não está disponível no app Passageiro.' not in text:
    if payment_anchor not in text:
        raise SystemExit('selecao de pagamento da corrida nao encontrada')
    text=text.replace(payment_anchor,payment_replacement,1)

# Garante que a tela de cadastro continue orientada ao cartão Efí.
text=text.replace('Cartões Efí salvos','Cartões Efí salvos')

for required in ['paymentValues.remove("pix")','PIX não está disponível no app Passageiro.','clickgo_add_efi_card','p_payment_method_id']:
    if required not in text:
        raise SystemExit('Passageiro v2.33 incompleto: '+required)

# Não exigimos remover a palavra PIX de histórico/labels: corridas antigas pagas por PIX
# devem continuar aparecendo corretamente no histórico. A restrição vale para novas corridas.

build=re.sub(r'versionCode\s+\d+','versionCode 233',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.33-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.33 PRIME: novas corridas sem PIX; dinheiro/cartao permanecem.')
