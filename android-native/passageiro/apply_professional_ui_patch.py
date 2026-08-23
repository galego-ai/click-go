from pathlib import Path

java = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
gradle = Path('app/build.gradle')
s = java.read_text(encoding='utf-8')

# Acabamento visual/copy aplicado por último, sem alterar regras de corrida.
replacements = {
    'Configuration.getInstance().setUserAgentValue("CLICK-GO-Passageiro-Android/0.2");': 'Configuration.getInstance().setUserAgentValue("CLICK-GO-Passageiro-Android/1.8");',
    'TextView title = text("Passageiro", 34, Color.WHITE, true);': 'TextView title = text("Entre e vá.", 34, Color.WHITE, true);',
    'TextView sub = text("Entre para pedir sua corrida", 16, Color.rgb(180, 180, 180), false);': 'TextView sub = text("Mobilidade simples, segura e sem complicação.", 15, Color.rgb(190, 190, 190), false);',
    'Button enter = primary("Entrar");': 'Button enter = primary("Entrar no CLICK-GO");',
    'Button create = secondary("Criar conta");': 'Button create = secondary("Criar minha conta");',
    'body.addView(text("Cadastro de passageiro", 16, Color.LTGRAY, false));': 'body.addView(text("Cadastro livre — você não precisa escolher uma cidade.", 15, Color.LTGRAY, false));',
    'root.addView(text("Para onde vamos?", 30, BLACK, true));': 'root.addView(text("Para onde vamos?", 32, BLACK, true));',
    'EditText destInput = editLight("Para onde vamos?");': 'EditText destInput = editLight("Informe seu destino");',
    'root.addView(text("Digite ao menos 3 letras do destino. A localização atual é usada como origem, mas você pode alterá-la.", 13, GRAY, false));': 'root.addView(text("Digite seu destino. A origem usa sua localização atual e pode ser alterada a qualquer momento.", 13, GRAY, false));',
    'quick.addView(quickButton("⌂", "Casa"), new LinearLayout.LayoutParams(0, dp(84), 1));': 'quick.addView(quickButton("⌂", "Casa"), new LinearLayout.LayoutParams(0, dp(78), 1));',
    'quick.addView(quickButton("▣", "Trabalho"), new LinearLayout.LayoutParams(0, dp(84), 1));': 'quick.addView(quickButton("▣", "Trabalho"), new LinearLayout.LayoutParams(0, dp(78), 1));',
    'quick.addView(quickButton("★", "Favoritos"), new LinearLayout.LayoutParams(0, dp(84), 1));': 'quick.addView(quickButton("★", "Favoritos"), new LinearLayout.LayoutParams(0, dp(78), 1));',
}
for old, new in replacements.items():
    s = s.replace(old, new)
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
g = g.replace('versionCode 6', 'versionCode 7')
g = g.replace("versionName '0.6-native-beta'", "versionName '1.8-native-review'")
gradle.write_text(g, encoding='utf-8')
print('Passenger professional UI patch applied')
