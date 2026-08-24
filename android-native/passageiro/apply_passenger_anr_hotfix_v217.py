from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.17 PRIME - hotfix ANR
# A v2.16 podia repetir restore -> showHome -> restore em caso de falha de rede/token,
# mantendo a Activity em um ciclo de trabalho. A retomada agora é assíncrona,
# limitada e nunca bloqueia/recursa a tela principal.

# 1) A home deve SEMPRE renderizar imediatamente. A corrida salva será validada
# em background pelo onResume, sem impedir a primeira pintura da Activity.
old_home = '''    private void showHome() {\n        String savedRide=getPreferences(MODE_PRIVATE).getString("active_ride_id","");\n        if((activeRideId==null||activeRideId.isBlank())&&!savedRide.isBlank()&&!restoringActiveRide){restoreActiveRideIfNeeded(true);return;}\n        cancelAddressSearch();'''
new_home = '''    private void showHome() {\n        String savedRide=getPreferences(MODE_PRIVATE).getString("active_ride_id","");\n        cancelAddressSearch();'''
if old_home in text:
    text = text.replace(old_home, new_home, 1)
elif 'if((activeRideId==null||activeRideId.isBlank())&&!savedRide.isBlank()&&!restoringActiveRide){restoreActiveRideIfNeeded(true);return;}' in text:
    text = text.replace('        if((activeRideId==null||activeRideId.isBlank())&&!savedRide.isBlank()&&!restoringActiveRide){restoreActiveRideIfNeeded(true);return;}\n', '', 1)
else:
    raise SystemExit('Hotfix v2.17: preâmbulo de showHome v2.16 não encontrado')

# 2) Adiciona throttle para não repetir consulta de retomada em sequência.
field = '''    private boolean restoringActiveRide;\n'''
field_new = '''    private boolean restoringActiveRide;\n    private long lastActiveRideRestoreAt;\n'''
if 'private long lastActiveRideRestoreAt;' not in text:
    if field not in text:
        raise SystemExit('Hotfix v2.17: campo restoringActiveRide não encontrado')
    text = text.replace(field, field_new, 1)

restore_start = '''    private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing){\n        if(restoringActiveRide||token==null||token.isBlank())return;\n        restoringActiveRide=true;'''
restore_start_new = '''    private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing){\n        if(restoringActiveRide||token==null||token.isBlank()||destroyed||isFinishing())return;\n        long now=android.os.SystemClock.elapsedRealtime();\n        if(!goHomeWhenMissing&&lastActiveRideRestoreAt>0&&now-lastActiveRideRestoreAt<3500)return;\n        lastActiveRideRestoreAt=now;\n        restoringActiveRide=true;'''
if restore_start in text:
    text = text.replace(restore_start, restore_start_new, 1)
elif 'lastActiveRideRestoreAt' not in text:
    raise SystemExit('Hotfix v2.17: início do restore não encontrado')

# 3) Em erro de rede/token não chama showHome() de novo. Isso elimina a recursão.
old_catch = '''            }catch(Exception e){ui.post(()->{restoringActiveRide=false;if(goHomeWhenMissing)showHome();});}\n        });\n    }'''
new_catch = '''            }catch(Exception e){\n                ui.post(()->{\n                    restoringActiveRide=false;\n                    if(destroyed||isFinishing())return;\n                    if(goHomeWhenMissing)toast("Não foi possível verificar sua corrida agora. Tente novamente em instantes.");\n                });\n            }\n        });\n    }'''
if old_catch in text:
    text = text.replace(old_catch, new_catch, 1)
else:
    raise SystemExit('Hotfix v2.17: catch recursivo do restore não encontrado')

# 4) Antes de solicitar uma nova corrida, se existir um id salvo ainda não validado,
# inicia uma verificação em background e impede duplicidade até o resultado.
old_request = '''    private void requestRide() {\n        if (destroyed || isFinishing()) return;\n        if(activeRideId!=null&&!activeRideId.isBlank()){toast("Você já possui uma corrida em andamento.");showActiveRide();return;}'''
new_request = '''    private void requestRide() {\n        if (destroyed || isFinishing()) return;\n        if(activeRideId!=null&&!activeRideId.isBlank()){toast("Você já possui uma corrida em andamento.");showActiveRide();return;}\n        String savedActiveRide=getPreferences(MODE_PRIVATE).getString("active_ride_id","");\n        if(!savedActiveRide.isBlank()){restoreActiveRideIfNeeded(false);toast("Verificando sua corrida em andamento…");return;}\n        if(restoringActiveRide){toast("Aguarde um instante enquanto verificamos sua corrida.");return;}'''
if old_request in text:
    text = text.replace(old_request, new_request, 1)
else:
    raise SystemExit('Hotfix v2.17: requestRide v2.16 não encontrado')

# 5) Se não houver corrida ativa, a preferência é removida antes da home; isso já existia,
# mas garantimos também que o throttle seja liberado para futuras verificações legítimas.
old_empty = '''restoringActiveRide=false;activeRideId=null;trackingUiActive=false;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();if(goHomeWhenMissing)showHome();'''
new_empty = '''restoringActiveRide=false;lastActiveRideRestoreAt=0;activeRideId=null;trackingUiActive=false;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();if(goHomeWhenMissing)showHome();'''
if old_empty in text:
    text = text.replace(old_empty, new_empty, 1)

# Marca versão final do APK independentemente das versões intermediárias dos patches.
build = re.sub(r'versionCode\s+\d+', 'versionCode 217', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.17-prime'", build, count=1)

main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.17 PRIME: hotfix ANR e retomada não bloqueante aplicados.')
