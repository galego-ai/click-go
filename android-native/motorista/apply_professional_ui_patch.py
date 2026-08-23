from pathlib import Path

java = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
gradle = Path('app/build.gradle')
s = java.read_text(encoding='utf-8')

# Última camada de UX: linguagem direta e hierarquia parecida com apps modernos de mobilidade.
replacements = {
    'body.addView(text("App Motorista",32,Color.WHITE,true));': 'body.addView(text("Pronto para rodar?",32,Color.WHITE,true));',
    'body.addView(text("Entre para ficar online e receber corridas.",15,GRAY,false));': 'body.addView(text("Entre, fique online e receba chamadas na sua cidade.",15,GRAY,false));',
    'Button enter = primary("Entrar");': 'Button enter = primary("Entrar como motorista");',
    'body.addView(text("O franqueado da cidade precisa aprovar seu cadastro antes de você ficar online.",13,GRAY,false));': 'body.addView(text("Seu cadastro e documentos são conferidos pelo franqueado da cidade escolhida.",13,GRAY,false));',
    'id.addView(text("Avaliação "+String.format(Locale.getDefault(),"%.1f",rating),13,GRAY,false));': 'id.addView(text("★ "+String.format(Locale.getDefault(),"%.1f",rating)+" · CLICK-GO Motorista",13,GRAY,false));',
    'Button onlineBtn = primary(online?"● ONLINE — ficar offline":"○ OFFLINE — ficar online");': 'Button onlineBtn = primary(online?"Você está online · Ficar offline":"Ficar online e receber chamadas");',
    'operationTitle = text(online?"Aguardando chamadas…":"Fique online para receber corridas.",16,Color.WHITE,true);': 'operationTitle = text(online?"Procurando corridas próximas…":"Fique online para começar.",17,Color.WHITE,true);',
    'operationTitle.setText("Aguardando chamadas…");': 'operationTitle.setText("Procurando corridas próximas…");',
    'operationTitle.setText("Nova corrida");': 'operationTitle.setText("Nova chamada");',
    'Button yes=primary("Aceitar"),no=darkButton("Recusar");': 'Button yes=primary("Aceitar corrida"),no=darkButton("Recusar");',
    'if(s.equals("accepted")){b=primary("Estou a caminho");action="arrived";}else if(s.equals("driver_arriving")){b=primary("Iniciar corrida");action="start";}else{b=primary("Finalizar corrida");action="complete";}': 'if(s.equals("accepted")){b=primary("Estou indo buscar");action="arrived";}else if(s.equals("driver_arriving")){b=primary("Passageiro embarcou");action="start";}else{b=primary("Concluir corrida");action="complete";}',
}
for old, new in replacements.items():
    s = s.replace(old, new)
java.write_text(s, encoding='utf-8')

g = gradle.read_text(encoding='utf-8')
# O patch de seleção de franquia leva a versão funcional para 0.6; esta camada vira a revisão 0.7.
g = g.replace('versionCode 6', 'versionCode 7')
g = g.replace("versionName '0.6-native-beta'", "versionName '0.7-native-review'")
gradle.write_text(g, encoding='utf-8')
print('Driver professional UI patch applied')
