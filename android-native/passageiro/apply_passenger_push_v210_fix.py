from pathlib import Path
import re

root=Path('app')
gradle=root/'build.gradle'
push_reg=root/'src/main/java/com/clickgo/passageiro/PushRegistration.java'
push_service=root/'src/main/java/com/clickgo/passageiro/ClickGoMessagingService.java'

build=gradle.read_text(encoding='utf-8')
build=build.replace("com.google.firebase:firebase-bom:33.16.0","com.google.firebase:firebase-bom:34.17.0")

if push_reg.exists():
    pr=push_reg.read_text(encoding='utf-8')
    anchor='''        ensureChannel(activity);\n'''
    extra='''        ensureChannel(activity);\n        activity.getSharedPreferences("clickgo_push",Context.MODE_PRIVATE).edit().putString("access_token",accessToken==null?"":accessToken).apply();\n'''
    if 'putString("access_token"' not in pr and anchor in pr:
        pr=pr.replace(anchor,extra,1)
    push_reg.write_text(pr,encoding='utf-8')

if push_service.exists():
    ps=push_service.read_text(encoding='utf-8')
    ps=ps.replace('getSharedPreferences("MainActivity",MODE_PRIVATE).getString("access_token",null)','getSharedPreferences("clickgo_push",MODE_PRIVATE).getString("access_token",null)')
    push_service.write_text(ps,encoding='utf-8')

m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.10-prime'",build,count=1)
gradle.write_text(build,encoding='utf-8')
print('Passageiro v2.10 PRIME: Firebase BoM 34.17.0 e refresh do token FCM robusto.')
