from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

old_recover = 'ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha", body);'
new_recover = 'ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha%3Fdestino%3Dpassageiro-app", body);'
if old_recover not in text:
    raise SystemExit('URL de recuperação do Passageiro não encontrada')
text = text.replace(old_recover, new_recover, 1)

old_session = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if (token == null || token.isBlank()) showLogin(); else showHome();\n'''
new_session = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgopassageiro".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            getPreferences(MODE_PRIVATE).edit().clear().apply();\n            token = null;\n        }\n        if (token == null || token.isBlank()) showLogin(); else showHome();\n'''
if old_session not in text:
    raise SystemExit('Inicialização de sessão do Passageiro não encontrada')
text = text.replace(old_session, new_session, 1)

build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
build = build.replace('versionCode 9', 'versionCode 10', 1)
build = build.replace("versionName '0.9-native-beta'", "versionName '1.0-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Passageiro v1.0: recuperação retorna ao próprio app.')
