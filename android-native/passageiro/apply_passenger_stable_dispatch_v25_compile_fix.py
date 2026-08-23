from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

old1 = 'TextView requestStatus = findViewWithTag("ride_request_status");'
new1 = 'TextView requestStatus = getWindow() == null ? null : getWindow().getDecorView().findViewWithTag("ride_request_status");'
old2 = 'TextView status = findViewWithTag("ride_request_status");'
new2 = 'TextView status = getWindow() == null ? null : getWindow().getDecorView().findViewWithTag("ride_request_status");'

if old1 not in text:
    raise SystemExit('requestStatus lookup não encontrado')
if old2 not in text:
    raise SystemExit('status lookup não encontrado')

text = text.replace(old1, new1, 1)
text = text.replace(old2, new2, 1)
path.write_text(text, encoding='utf-8')
print('Passageiro v2.5 PRIME: lookup do status de solicitação corrigido para Android View.')
