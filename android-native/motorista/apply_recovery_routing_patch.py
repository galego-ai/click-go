from pathlib import Path

path = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text = path.read_text(encoding='utf-8')

old_recover = 'ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha",body);'
new_recover = 'ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha%3Fdestino%3Dmotorista-app",body);'
if old_recover not in text:
    raise SystemExit('URL de recuperação do Motorista não encontrada')
text = text.replace(old_recover, new_recover, 1)

old_session = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);\n        if (token == null || token.isBlank()) showLogin(); else loadSession();\n'''
new_session = '''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);\n        if (getIntent() != null && getIntent().getData() != null\n                && "clickgomotorista".equalsIgnoreCase(getIntent().getData().getScheme())) {\n            getPreferences(MODE_PRIVATE).edit().clear().apply();\n            token = null;\n            userId = null;\n        }\n        if (token == null || token.isBlank()) showLogin(); else loadSession();\n'''
if old_session not in text:
    raise SystemExit('Inicialização de sessão do Motorista não encontrada')
text = text.replace(old_session, new_session, 1)

build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
build = build.replace('versionCode 2', 'versionCode 3', 1)
build = build.replace("versionName '0.2-native-beta'", "versionName '0.3-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Motorista v0.3: recuperação retorna ao próprio app.')
