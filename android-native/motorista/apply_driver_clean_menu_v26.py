from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Menu operacional enxuto. Documentos deixam de ocupar espaço depois da aprovação.
pattern=r'''    private void showDriverMenu\(\)\{.*?\n    \}\n\n    private View menuCard'''
replacement=r'''    private void showDriverMenu(){
        stopPolling(); releaseMap();
        LinearLayout body=vertical(BLACK); body.setPadding(dp(18),dp(24),dp(18),dp(26));
        LinearLayout top=horizontal(); top.setGravity(Gravity.CENTER_VERTICAL);
        Button back=darkButton("← Início"); top.addView(back,new LinearLayout.LayoutParams(dp(110),dp(50)));
        LinearLayout heading=vertical(Color.TRANSPARENT); heading.setPadding(dp(14),0,0,0);
        heading.addView(text("Menu",24,Color.WHITE,true));
        heading.addView(text("Só o essencial para dirigir",12,GRAY,false));
        top.addView(heading,new LinearLayout.LayoutParams(0,dp(54),1));
        body.addView(top); body.addView(space(16));

        body.addView(menuCard("🚘", "Corridas", "Voltar ao mapa e à operação", () -> showHome())); body.addView(space(9));
        body.addView(menuCard("🕘", "Histórico", "Corridas concluídas e canceladas", () -> showRideHistory())); body.addView(space(9));
        body.addView(menuCard("💰", "Ganhos e carteira", "Saldo, ganhos e regras de cobrança", () -> showEarnings())); body.addView(space(9));
        body.addView(menuCard("👤", "Perfil", "Dados, veículo e avaliação", () -> showDriverProfile())); body.addView(space(9));

        // Depois de aprovado, Documentos some do menu principal. Se houver nova pendência,
        // o status do motorista volta a exigir atenção e o item reaparece automaticamente.
        if(!"approved".equalsIgnoreCase(driverStatus)){
            body.addView(menuCard("📄", "Documentos", "Enviar ou corrigir documentos pendentes", () -> showDocuments()));
            body.addView(space(9));
        }

        body.addView(menuCard("🛟", "Suporte", "Ajuda e contato com a operação", () -> showSupport())); body.addView(space(9));
        body.addView(menuCard("⚙", "Configurações", "Senha, conta e segurança", () -> showDriverSettings())); body.addView(space(16));

        Button exit=darkButton("Sair da conta"); exit.setTextColor(Color.rgb(248,113,113)); body.addView(exit,match(dp(56)));
        back.setOnClickListener(v->showHome()); exit.setOnClickListener(v->logout());
        setContentView(scroll(body,BLACK));
    }

    private View menuCard'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1:
    raise SystemExit('showDriverMenu não encontrado')

m=re.search(r'versionCode\s+(\d+)',build)
if m:
    build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.6-prime'",build,count=1)

path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v2.6 PRIME: menu limpo e documentos condicionais aplicados.')
