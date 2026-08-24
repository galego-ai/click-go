from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.17 PRIME - hotfix ANR
# A retomada de corrida deve ser totalmente assíncrona e nunca impedir a primeira
# renderização da home, nem disparar showHome -> restore -> showHome em caso de erro.

# 1) Se a correção v2.16 tiver inserido uma trava síncrona no começo de showHome,
# remove somente essa condicional. O regex tolera qualquer espaçamento/formatação.
home_guard = re.compile(
    r'\s*if\s*\(\s*\(\s*activeRideId\s*==\s*null\s*\|\|\s*activeRideId\.isBlank\(\)\s*\)\s*'
    r'&&\s*!\s*savedRide\.isBlank\(\)\s*&&\s*!\s*restoringActiveRide\s*\)\s*\{\s*'
    r'restoreActiveRideIfNeeded\s*\(\s*true\s*\)\s*;\s*return\s*;\s*\}',
    re.S,
)
text, _ = home_guard.subn('', text, count=1)

# 2) Throttle das verificações para evitar tempestade de chamadas ao voltar do background.
if 'private long lastActiveRideRestoreAt;' not in text:
    text, n = re.subn(
        r'(\s*private\s+boolean\s+restoringActiveRide\s*;)',
        r'\1\n    private long lastActiveRideRestoreAt;',
        text,
        count=1,
    )
    if n != 1:
        raise SystemExit('Hotfix v2.17: campo restoringActiveRide não encontrado')

# 3) Localiza somente o método de restore, para não alterar catches de outras rotinas.
restore_pos = text.find('private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing)')
if restore_pos < 0:
    raise SystemExit('Hotfix v2.17: método restoreActiveRideIfNeeded não encontrado')
show_home_pos = text.find('private void showHome()', restore_pos)
if show_home_pos < 0:
    raise SystemExit('Hotfix v2.17: limite do método restore não encontrado')
restore = text[restore_pos:show_home_pos]

# Guarda + throttle no início do restore.
restore, n = re.subn(
    r'if\s*\(\s*restoringActiveRide\s*\|\|\s*token\s*==\s*null\s*\|\|\s*token\.isBlank\(\)\s*\)\s*return\s*;\s*'
    r'restoringActiveRide\s*=\s*true\s*;',
    'if(restoringActiveRide||token==null||token.isBlank()||destroyed||isFinishing())return;\n'
    '        long now=android.os.SystemClock.elapsedRealtime();\n'
    '        if(lastActiveRideRestoreAt>0&&now-lastActiveRideRestoreAt<3500)return;\n'
    '        lastActiveRideRestoreAt=now;\n'
    '        restoringActiveRide=true;',
    restore,
    count=1,
)
if n != 1 and 'android.os.SystemClock.elapsedRealtime()' not in restore:
    raise SystemExit('Hotfix v2.17: guarda inicial do restore não encontrada')

# Quando não há corrida, limpa o id local e libera o throttle.
restore = restore.replace(
    'restoringActiveRide=false;activeRideId=null;trackingUiActive=false;',
    'restoringActiveRide=false;lastActiveRideRestoreAt=0;activeRideId=null;trackingUiActive=false;',
    1,
)

# O último showHome condicionado dentro do método é o catch de erro. Em erro de
# rede/token apenas libera a flag; NÃO chama showHome novamente.
needle = 'if(goHomeWhenMissing)showHome();'
last = restore.rfind(needle)
if last >= 0:
    restore = restore[:last] + 'if(goHomeWhenMissing&&!destroyed&&!isFinishing())toast("Não foi possível verificar sua corrida agora. Tente novamente em instantes.");' + restore[last + len(needle):]
else:
    # Aceita também versões já corrigidas; não falha se não houver recursão.
    if 'Não foi possível verificar sua corrida agora' not in restore:
        raise SystemExit('Hotfix v2.17: catch de restore não identificado')

text = text[:restore_pos] + restore + text[show_home_pos:]

# 4) A retomada ao voltar ao app é atrasada alguns milissegundos para a Activity
# concluir layout/mapa primeiro. A consulta continua no executor de I/O.
immediate_resume = 'if(token!=null&&!token.isBlank()&&activeRideId==null&&!restoringActiveRide) restoreActiveRideIfNeeded(false);'
delayed_resume = 'if(token!=null&&!token.isBlank()&&activeRideId==null&&!restoringActiveRide) ui.postDelayed(()->{if(!destroyed&&!isFinishing()&&activeRideId==null)restoreActiveRideIfNeeded(false);},700);'
if immediate_resume in text:
    text = text.replace(immediate_resume, delayed_resume, 1)

# 5) Antes de criar outra corrida, valida um id salvo em background. Isso preserva
# a regra de não permitir duas corridas simultâneas sem bloquear a interface.
request_pos = text.find('private void requestRide()')
if request_pos < 0:
    raise SystemExit('Hotfix v2.17: requestRide não encontrado')
request_end = text.find('\n    private void ', request_pos + 10)
if request_end < 0:
    request_end = min(len(text), request_pos + 5000)
request = text[request_pos:request_end]
if 'String savedActiveRide=' not in request:
    anchor = 'if(activeRideId!=null&&!activeRideId.isBlank()){toast("Você já possui uma corrida em andamento.");showActiveRide();return;}'
    if anchor in request:
        request = request.replace(
            anchor,
            anchor + '\n        String savedActiveRide=getPreferences(MODE_PRIVATE).getString("active_ride_id","");\n'
            '        if(!savedActiveRide.isBlank()){restoreActiveRideIfNeeded(false);toast("Verificando sua corrida em andamento…");return;}\n'
            '        if(restoringActiveRide){toast("Aguarde um instante enquanto verificamos sua corrida.");return;}',
            1,
        )
    else:
        # Formatação variável: insere após o guard de Activity.
        request, n = re.subn(
            r'(if\s*\(\s*destroyed\s*\|\|\s*isFinishing\(\)\s*\)\s*return\s*;)',
            r'\1\n        String savedActiveRide=getPreferences(MODE_PRIVATE).getString("active_ride_id","");\n'
            r'        if(!savedActiveRide.isBlank()){restoreActiveRideIfNeeded(false);toast("Verificando sua corrida em andamento…");return;}\n'
            r'        if(restoringActiveRide){toast("Aguarde um instante enquanto verificamos sua corrida.");return;}',
            request,
            count=1,
        )
        if n != 1:
            raise SystemExit('Hotfix v2.17: ponto de proteção em requestRide não encontrado')
    text = text[:request_pos] + request + text[request_end:]

# Versão final do APK.
build = re.sub(r'versionCode\s+\d+', 'versionCode 217', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.17-prime'", build, count=1)

main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.17 PRIME: hotfix ANR não bloqueante aplicado.')
