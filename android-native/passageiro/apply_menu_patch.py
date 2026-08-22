from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

old = '''    private void showMenu() {
        String[] items = {"Histórico", "Pagamentos", "Cupons", "Favoritos", "Ajuda e suporte", "Sair"};
        new AlertDialog.Builder(this)
                .setTitle("CLICK-GO Passageiro")
                .setItems(items, (dialog, which) -> {
                    if (which == 5) {
                        token = null;
                        getPreferences(MODE_PRIVATE).edit().clear().apply();
                        showLogin();
                    } else {
                        toast("Essa área será conectada na próxima etapa do app nativo.");
                    }
                })
                .show();
    }
'''

new = '''    private void showMenu() {
        hideKeyboard();

        LinearLayout drawer = vertical(Color.WHITE);
        drawer.setPadding(dp(22), dp(28), dp(22), dp(22));

        LinearLayout header = horizontal();
        header.setGravity(Gravity.CENTER_VERTICAL);
        TextView avatar = text(PassengerAvatar.initials(), 18, YELLOW, true);
        avatar.setGravity(Gravity.CENTER);
        avatar.setBackground(round(BLACK, 30, BLACK));
        header.addView(avatar, new LinearLayout.LayoutParams(dp(60), dp(60)));
        LinearLayout headerText = vertical(Color.TRANSPARENT);
        headerText.setPadding(dp(14), 0, 0, 0);
        headerText.addView(text("CLICK-GO", 19, BLACK, true));
        headerText.addView(text("Passageiro", 13, GRAY, false));
        header.addView(headerText, new LinearLayout.LayoutParams(0, -2, 1));
        drawer.addView(header);
        drawer.addView(space(22));

        TextView home = drawerItem("⌂", "Início");
        TextView history = drawerItem("↻", "Histórico de corridas");
        TextView payments = drawerItem("▣", "Formas de pagamento");
        TextView coupons = drawerItem("%", "Cupons");
        TextView favorites = drawerItem("★", "Endereços favoritos");
        TextView support = drawerItem("?", "Ajuda e suporte");
        TextView profile = drawerItem("●", "Meu perfil");
        TextView logout = drawerItem("↪", "Sair");

        for (TextView item : Arrays.asList(home, history, payments, coupons, favorites, support, profile, logout)) {
            drawer.addView(item, lpMatch(dp(56)));
            drawer.addView(space(4));
        }

        AlertDialog dialog = new AlertDialog.Builder(this).setView(drawer).create();

        home.setOnClickListener(v -> { dialog.dismiss(); showHome(); });
        history.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Histórico de corridas", "Suas corridas concluídas e canceladas aparecerão aqui."); });
        payments.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Formas de pagamento", "Gerencie PIX, cartão, dinheiro e outras formas liberadas na sua cidade."); });
        coupons.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Cupons", "Consulte e aplique seus cupons CLICK-GO."); });
        favorites.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Endereços favoritos", "Casa, trabalho e outros locais salvos ficam aqui."); });
        support.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Ajuda e suporte", "Abra e acompanhe seus chamados de atendimento."); });
        profile.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Meu perfil", "Consulte e atualize seus dados de passageiro."); });
        logout.setOnClickListener(v -> {
            dialog.dismiss();
            token = null;
            getPreferences(MODE_PRIVATE).edit().clear().apply();
            showLogin();
        });

        dialog.setOnShowListener(d -> {
            Window window = dialog.getWindow();
            if (window != null) {
                int width = Math.min(dp(340), (int)(getResources().getDisplayMetrics().widthPixels * 0.88f));
                window.setLayout(width, -1);
                window.setGravity(Gravity.START);
            }
        });
        dialog.show();
    }

    private TextView drawerItem(String icon, String label) {
        TextView item = text(icon + "   " + label, 16, BLACK, true);
        item.setGravity(Gravity.CENTER_VERTICAL);
        item.setPadding(dp(14), 0, dp(14), 0);
        item.setBackground(round(Color.rgb(250, 250, 250), 14, Color.rgb(238, 238, 238)));
        item.setClickable(true);
        item.setFocusable(true);
        return item;
    }

    private void showPassengerSection(String title, String message) {
        LinearLayout root = vertical(LIGHT);
        root.setPadding(dp(18), dp(18), dp(18), dp(24));
        LinearLayout top = horizontal();
        top.setGravity(Gravity.CENTER_VERTICAL);
        Button back = circleButton("‹", 48);
        top.addView(back, new LinearLayout.LayoutParams(dp(50), dp(50)));
        TextView heading = text(title, 20, BLACK, true);
        heading.setPadding(dp(12), 0, 0, 0);
        top.addView(heading, new LinearLayout.LayoutParams(0, dp(50), 1));
        root.addView(top);
        root.addView(space(22));
        LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 18);
        card.addView(text(message, 15, GRAY, false));
        root.addView(card, lpMatchWrap());
        back.setOnClickListener(v -> showHome());
        setContentView(scroll(root, LIGHT));
    }
'''

if old not in text:
    raise SystemExit('Método showMenu antigo não encontrado')

text = text.replace(old, new, 1)
path.write_text(text, encoding='utf-8')
print('Menu lateral nativo aplicado e botão ☰ conectado.')
