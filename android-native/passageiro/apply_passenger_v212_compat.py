from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

# Normaliza apenas a declaração local de pagamento para o formato esperado pelo
# patch comercial v2.12. A variável continua efetivamente final e pode ser
# capturada pelas lambdas Java sem alteração de comportamento.
pattern=r'\s*final\s+String\s+payment\s*=\s*paymentValues\.get\([^;]+\);'
match=re.search(pattern,text)
if match:
    line='\n        String payment = paymentValues.get(Math.min(index, paymentValues.size() - 1));'
    text=text[:match.start()]+line+text[match.end():]
elif 'String payment = paymentValues.get(Math.min(index, paymentValues.size() - 1));' not in text:
    raise SystemExit('Declaração de pagamento atual não encontrada')

path.write_text(text,encoding='utf-8')
print('Compatibilidade v2.12: declaração de pagamento normalizada.')
