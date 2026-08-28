from pathlib import Path

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = main_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro - active ride resume regression fix
# The database (under the authenticated passenger token/RLS) is the source of truth.
# Any ride that is not completed/cancelled must be restored after relaunch/resume.

restore_start = text.find('private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing)')
if restore_start < 0:
    raise SystemExit('active ride restore method not found')
restore_end = text.find('\n    private void showHome()', restore_start)
if restore_end < 0:
    raise SystemExit('active ride restore method boundary not found')

restore = text[restore_start:restore_end]
old_filter = 'rides?status=in.(searching,accepted,driver_arriving,in_progress)&select='
new_filter = 'rides?status=not.in.(completed,cancelled)&select='
if old_filter in restore:
    restore = restore.replace(old_filter, new_filter, 1)
elif new_filter not in restore:
    raise SystemExit('active ride status query not found')

text = text[:restore_start] + restore + text[restore_end:]

# v2.20 rebuilt showHome and could remove its delayed restore check. Keep a second,
# asynchronous recovery point on the home screen in addition to onResume().
home_start = text.find('private void showHome()')
if home_start < 0:
    raise SystemExit('showHome not found')
home_end = text.find('\n    private void ', home_start + len('private void showHome()'))
if home_end < 0:
    raise SystemExit('showHome boundary not found')
home = text[home_start:home_end]

if 'restoreActiveRideIfNeeded(false)' not in home:
    close_at = home.rfind('\n    }')
    if close_at < 0:
        raise SystemExit('showHome closing brace not found')
    resume_check = '''\n        // Re-check the authenticated passenger's active ride after home is rendered.\n        if(!homeSmokeMode && token!=null && !token.isBlank() && activeRideId==null && !restoringActiveRide) {\n            ui.postDelayed(() -> {\n                if(!destroyed && !isFinishing() && activeRideId==null && !restoringActiveRide) {\n                    restoreActiveRideIfNeeded(false);\n                }\n            }, 450);\n        }\n'''
    home = home[:close_at] + resume_check + home[close_at:]
    text = text[:home_start] + home + text[home_end:]

# Static regression guards: the generated Java must keep the exact business rule.
restore_start = text.find('private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing)')
restore_end = text.find('\n    private void showHome()', restore_start)
restore = text[restore_start:restore_end]
if 'status=not.in.(completed,cancelled)' not in restore:
    raise SystemExit('non-terminal active ride filter missing')
if 'status=in.(searching,accepted,driver_arriving,in_progress)' in restore:
    raise SystemExit('legacy restrictive active ride filter still present')

home_start = text.find('private void showHome()')
home_end = text.find('\n    private void ', home_start + len('private void showHome()'))
home = text[home_start:home_end]
if 'restoreActiveRideIfNeeded(false)' not in home:
    raise SystemExit('home active ride restore trigger missing')

text_path = main_path
text_path.write_text(text, encoding='utf-8')
print('Passageiro: corrida ativa agora retorna após fechar/reabrir o app enquanto não estiver completed/cancelled.')
