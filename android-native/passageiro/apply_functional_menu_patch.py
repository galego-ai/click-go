from pathlib import Path

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = main_path.read_text(encoding='utf-8')

# Guarda o id do passageiro autenticado para inserts/updates próprios.
if 'private String currentUserId;' not in text:
    text = text.replace('    private String token;\n', '    private String token;\n    private String currentUserId;\n', 1)

# Menu: troca os placeholders pelas telas funcionais.
replacements = {
'''        history.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Histórico de corridas", "Suas corridas concluídas e canceladas aparecerão aqui."); });\n''': '''        history.setOnClickListener(v -> { dialog.dismiss(); showHistory(); });\n''',
'''        payments.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Formas de pagamento", "Gerencie PIX, cartão, dinheiro e outras formas liberadas na sua cidade."); });\n''': '''        payments.setOnClickListener(v -> { dialog.dismiss(); showPayments(); });\n''',
'''        coupons.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Cupons", "Consulte e aplique seus cupons CLICK-GO."); });\n''': '''        coupons.setOnClickListener(v -> { dialog.dismiss(); showCoupons(); });\n''',
'''        favorites.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Endereços favoritos", "Casa, trabalho e outros locais salvos ficam aqui."); });\n''': '''        favorites.setOnClickListener(v -> { dialog.dismiss(); showFavorites(); });\n''',
'''        support.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Ajuda e suporte", "Abra e acompanhe seus chamados de atendimento."); });\n''': '''        support.setOnClickListener(v -> { dialog.dismiss(); showSupport(); });\n''',
'''        profile.setOnClickListener(v -> { dialog.dismiss(); showPassengerSection("Meu perfil", "Consulte e atualize seus dados de passageiro."); });\n''': '''        profile.setOnClickListener(v -> { dialog.dismiss(); showProfile(); });\n'''
}
for old, new in replacements.items():
    if old not in text:
        raise SystemExit('Trecho de menu não encontrado: ' + old[:50])
    text = text.replace(old, new, 1)

# Menu mostra a foto real, não apenas iniciais.
old_header_avatar = '''        TextView avatar = text(PassengerAvatar.initials(), 18, YELLOW, true);\n        avatar.setGravity(Gravity.CENTER);\n        avatar.setBackground(round(BLACK, 30, BLACK));\n        header.addView(avatar, new LinearLayout.LayoutParams(dp(60), dp(60)));\n'''
new_header_avatar = '''        ImageView avatar = new ImageView(this);\n        avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));\n        avatar.setScaleType(ImageView.ScaleType.CENTER_CROP);\n        header.addView(avatar, new LinearLayout.LayoutParams(dp(60), dp(60)));\n        PassengerAvatar.preload(this, token, () -> {\n            if (!destroyed && avatar.isAttachedToWindow()) avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));\n        });\n'''
if old_header_avatar in text:
    text = text.replace(old_header_avatar, new_header_avatar, 1)

# Atalhos da tela inicial passam a funcionar com os favoritos salvos.
anchor = '''        root.addView(quick);\n        root.addView(space(12));\n'''
insert = '''        root.addView(quick);\n        quick.getChildAt(0).setOnClickListener(v -> useFavoriteByLabel("Casa"));\n        quick.getChildAt(2).setOnClickListener(v -> useFavoriteByLabel("Trabalho"));\n        quick.getChildAt(4).setOnClickListener(v -> showFavorites());\n        root.addView(space(12));\n'''
if anchor not in text:
    raise SystemExit('Atalho Casa/Trabalho não encontrado')
text = text.replace(anchor, insert, 1)

# Insere telas funcionais antes do helper drawerItem.
marker = '''    private TextView drawerItem(String icon, String label) {\n'''
if marker not in text:
    raise SystemExit('Ponto de inserção das telas do menu não encontrado')

methods = r'''    private LinearLayout showSectionShell(String title) {
        cancelAddressSearch();
        stopRidePolling();
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
        root.addView(space(18));
        LinearLayout content = vertical(Color.TRANSPARENT);
        root.addView(content, lpMatchWrap());
        back.setOnClickListener(v -> showHome());
        setContentView(scroll(root, LIGHT));
        return content;
    }

    private TextView loadingText(String value) {
        TextView loading = text(value, 14, GRAY, false);
        loading.setPadding(dp(10), dp(16), dp(10), dp(16));
        return loading;
    }

    private String ensureUserId() throws Exception {
        if (currentUserId != null && !currentUserId.isBlank()) return currentUserId;
        JSONArray rows = new JSONArray(ApiClient.restGet("profiles?select=id&limit=1", token));
        if (rows.length() == 0) throw new Exception("Perfil do passageiro não encontrado.");
        currentUserId = rows.getJSONObject(0).optString("id", "");
        if (currentUserId.isBlank()) throw new Exception("Perfil do passageiro não encontrado.");
        return currentUserId;
    }

    private void showHistory() {
        LinearLayout content = showSectionShell("Histórico de corridas");
        content.addView(loadingText("Carregando suas corridas…"));
        io.execute(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet(
                        "rides?select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,payment_method_preference&order=requested_at.desc&limit=50",
                        token));
                ui.post(() -> {
                    if (destroyed || !content.isAttachedToWindow()) return;
                    content.removeAllViews();
                    if (rows.length() == 0) {
                        content.addView(unavailable("Nenhuma corrida ainda", "Quando você fizer uma corrida, ela aparecerá aqui."));
                        return;
                    }
                    for (int i = 0; i < rows.length(); i++) {
                        JSONObject ride = rows.optJSONObject(i);
                        if (ride == null) continue;
                        LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 15);
                        LinearLayout top = horizontal();
                        TextView status = text(statusLabel(ride.optString("status", "")), 15, BLACK, true);
                        top.addView(status, new LinearLayout.LayoutParams(0, -2, 1));
                        double fare = ride.isNull("final_fare") ? ride.optDouble("estimated_fare", 0) : ride.optDouble("final_fare", 0);
                        top.addView(text(money(fare), 15, BLACK, true));
                        card.addView(top);
                        String route = cleanLabel(ride.optString("origin_label", "")) + "\n→ " + cleanLabel(ride.optString("destination_label", ""));
                        TextView routeView = text(route, 13, GRAY, false);
                        routeView.setPadding(0, dp(7), 0, dp(5));
                        card.addView(routeView);
                        String when = ride.optString("requested_at", "");
                        if (when.length() >= 16) when = when.substring(0, 16).replace('T', ' ');
                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));
                        content.addView(card, lpMatchWrap());
                        content.addView(space(9));
                    }
                });
            } catch (Exception e) {
                ui.post(() -> {
                    if (!content.isAttachedToWindow()) return;
                    content.removeAllViews();
                    content.addView(unavailable("Não foi possível carregar", message(e)));
                });
            }
        });
    }

    private void showPayments() {
        LinearLayout content = showSectionShell("Formas de pagamento");
        content.addView(loadingText("Carregando formas de pagamento…"));
        io.execute(() -> {
            try {
                JSONArray methods = new JSONArray(ApiClient.restGet(
                        "passenger_payment_methods?select=id,method_type,provider,brand,last4,is_default,active&active=eq.true&order=created_at.desc",
                        token));
                JSONObject settings = null;
                JSONArray lastRide = new JSONArray(ApiClient.restGet("rides?select=city_id&order=requested_at.desc&limit=1", token));
                if (lastRide.length() > 0) {
                    String cityId = lastRide.getJSONObject(0).optString("city_id", "");
                    if (!cityId.isBlank()) {
                        JSONArray rows = new JSONArray(ApiClient.rpc("get_effective_payment_settings", new JSONObject().put("p_city_id", cityId), token));
                        if (rows.length() > 0) settings = rows.getJSONObject(0);
                    }
                }
                JSONObject finalSettings = settings;
                ui.post(() -> renderPayments(content, methods, finalSettings));
            } catch (Exception e) {
                ui.post(() -> {
                    if (!content.isAttachedToWindow()) return;
                    content.removeAllViews();
                    content.addView(unavailable("Não foi possível carregar", message(e)));
                });
            }
        });
    }

    private void renderPayments(LinearLayout content, JSONArray methods, JSONObject settings) {
        if (destroyed || !content.isAttachedToWindow()) return;
        content.removeAllViews();
        LinearLayout availability = card(Color.WHITE, Color.rgb(232,232,232), 18, 16);
        availability.addView(text("Disponibilidade na operação", 17, BLACK, true));
        if (settings == null) {
            TextView t = text("PIX, dinheiro e cartão são liberados por cidade. A disponibilidade exata também aparece antes de solicitar a corrida.", 13, GRAY, false);
            t.setPadding(0, dp(8), 0, 0);
            availability.addView(t);
        } else {
            availability.addView(paymentStatus("PIX", settings.optBoolean("pix_enabled")));
            availability.addView(paymentStatus("Dinheiro", settings.optBoolean("cash_enabled")));
            availability.addView(paymentStatus("Cartão no app", settings.optBoolean("card_app_enabled")));
            availability.addView(paymentStatus("Cartão com motorista", settings.optBoolean("card_machine_enabled")));
        }
        content.addView(availability, lpMatchWrap());
        content.addView(space(14));
        content.addView(text("Cartões salvos", 18, BLACK, true));
        content.addView(space(8));
        if (methods.length() == 0) {
            LinearLayout empty = card(Color.WHITE, Color.rgb(232,232,232), 18, 16);
            empty.addView(text("Nenhum cartão salvo nesta conta.", 14, GRAY, false));
            content.addView(empty, lpMatchWrap());
            return;
        }
        for (int i = 0; i < methods.length(); i++) {
            JSONObject method = methods.optJSONObject(i);
            if (method == null) continue;
            String id = method.optString("id", "");
            String brand = method.optString("brand", "Cartão");
            String last4 = method.optString("last4", "");
            boolean isDefault = method.optBoolean("is_default", false);
            LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 14);
            card.addView(text(brand + (last4.isBlank() ? "" : " •••• " + last4), 16, BLACK, true));
            card.addView(text(isDefault ? "Forma padrão" : "Cartão salvo", 12, isDefault ? Color.rgb(30,140,80) : GRAY, false));
            LinearLayout actions = horizontal();
            if (!isDefault) {
                Button def = smallButton("Tornar padrão");
                def.setOnClickListener(v -> setDefaultPayment(id));
                actions.addView(def, new LinearLayout.LayoutParams(0, dp(44), 1));
                actions.addView(spaceH(7));
            }
            Button remove = smallButton("Remover");
            remove.setOnClickListener(v -> confirmDeletePayment(id));
            actions.addView(remove, new LinearLayout.LayoutParams(0, dp(44), 1));
            card.addView(space(9));
            card.addView(actions);
            content.addView(card, lpMatchWrap());
            content.addView(space(8));
        }
    }

    private TextView paymentStatus(String label, boolean enabled) {
        TextView row = text((enabled ? "✓  " : "—  ") + label, 14, enabled ? BLACK : GRAY, enabled);
        row.setPadding(0, dp(8), 0, 0);
        return row;
    }

    private void setDefaultPayment(String id) {
        io.execute(() -> {
            try {
                String uid = ensureUserId();
                ApiClient.restPatch("passenger_payment_methods?passenger_id=eq." + uid, new JSONObject().put("is_default", false), token);
                ApiClient.restPatch("passenger_payment_methods?id=eq." + id, new JSONObject().put("is_default", true), token);
                ui.post(() -> { toast("Forma de pagamento padrão atualizada."); showPayments(); });
            } catch (Exception e) { ui.post(() -> toast(message(e))); }
        });
    }

    private void confirmDeletePayment(String id) {
        new AlertDialog.Builder(this)
                .setTitle("Remover cartão")
                .setMessage("Deseja remover esta forma de pagamento salva?")
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Remover", (d, w) -> io.execute(() -> {
                    try {
                        ApiClient.restDelete("passenger_payment_methods?id=eq." + id, token);
                        ui.post(() -> { toast("Forma de pagamento removida."); showPayments(); });
                    } catch (Exception e) { ui.post(() -> toast(message(e))); }
                }))
                .show();
    }

    private void showFavorites() {
        LinearLayout content = showSectionShell("Endereços favoritos");
        Button add = primary("+ Adicionar endereço");
        content.addView(add, lpMatch(dp(54)));
        content.addView(space(12));
        LinearLayout list = vertical(Color.TRANSPARENT);
        content.addView(list, lpMatchWrap());
        list.addView(loadingText("Carregando favoritos…"));
        add.setOnClickListener(v -> showAddFavorite());
        io.execute(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet(
                        "passenger_favorites?select=id,label,address,lat,lng,created_at&order=created_at.desc",
                        token));
                ui.post(() -> renderFavorites(list, rows));
            } catch (Exception e) {
                ui.post(() -> {
                    if (!list.isAttachedToWindow()) return;
                    list.removeAllViews();
                    list.addView(unavailable("Não foi possível carregar", message(e)));
                });
            }
        });
    }

    private void renderFavorites(LinearLayout list, JSONArray rows) {
        if (destroyed || !list.isAttachedToWindow()) return;
        list.removeAllViews();
        if (rows.length() == 0) {
            list.addView(unavailable("Nenhum favorito", "Salve Casa, Trabalho ou qualquer outro endereço para usar com um toque."));
            return;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject item = rows.optJSONObject(i);
            if (item == null) continue;
            String id = item.optString("id", "");
            String label = item.optString("label", "Favorito");
            String address = item.optString("address", "");
            double lat = item.optDouble("lat", Double.NaN);
            double lng = item.optDouble("lng", Double.NaN);
            LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 14);
            card.addView(text("★  " + label, 16, BLACK, true));
            TextView addr = text(address, 13, GRAY, false);
            addr.setPadding(0, dp(5), 0, dp(8));
            card.addView(addr);
            LinearLayout actions = horizontal();
            Button use = smallButton("Usar destino");
            use.setOnClickListener(v -> {
                if (!Double.isFinite(lat) || !Double.isFinite(lng)) { toast("Esse favorito não possui coordenadas válidas."); return; }
                destination = new GeoPoint(lat, lng);
                destinationLabel = address.isBlank() ? label : address;
                showOptions();
            });
            Button del = smallButton("Excluir");
            del.setOnClickListener(v -> confirmDeleteFavorite(id));
            actions.addView(use, new LinearLayout.LayoutParams(0, dp(44), 2));
            actions.addView(spaceH(7));
            actions.addView(del, new LinearLayout.LayoutParams(0, dp(44), 1));
            card.addView(actions);
            list.addView(card, lpMatchWrap());
            list.addView(space(8));
        }
    }

    private void showAddFavorite() {
        LinearLayout content = showSectionShell("Adicionar favorito");
        EditText label = editLight("Nome: Casa, Trabalho...");
        EditText address = editLight("Endereço completo");
        Button save = primary("Salvar favorito");
        content.addView(label, lpMatch(dp(56)));
        content.addView(space(9));
        content.addView(address, lpMatch(dp(56)));
        content.addView(space(14));
        content.addView(save, lpMatch(dp(56)));
        save.setOnClickListener(v -> {
            String name = label.getText().toString().trim();
            String addr = address.getText().toString().trim();
            if (name.isBlank() || addr.length() < 3) { toast("Informe um nome e o endereço."); return; }
            save.setEnabled(false);
            save.setText("Localizando endereço…");
            io.execute(() -> {
                try {
                    String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(addr, StandardCharsets.UTF_8.toString());
                    if (origin != null) url += "&lat=" + origin.getLatitude() + "&lng=" + origin.getLongitude();
                    if (originSearchContext != null && !originSearchContext.isBlank())
                        url += "&context=" + URLEncoder.encode(originSearchContext, StandardCharsets.UTF_8.toString());
                    JSONObject result = new JSONObject(ApiClient.absoluteGet(url));
                    JSONArray matches = result.optJSONArray("results");
                    if (matches == null || matches.length() == 0) throw new Exception("Endereço não encontrado.");
                    JSONObject first = matches.getJSONObject(0);
                    double lat = first.optDouble("lat", Double.NaN);
                    double lng = first.optDouble("lng", Double.NaN);
                    if (!Double.isFinite(lat) || !Double.isFinite(lng)) throw new Exception("Endereço sem coordenadas válidas.");
                    String uid = ensureUserId();
                    String resolved = cleanLabel(first.optString("label", addr));
                    JSONObject body = new JSONObject()
                            .put("passenger_id", uid)
                            .put("label", name)
                            .put("address", resolved)
                            .put("lat", lat)
                            .put("lng", lng);
                    ApiClient.restPost("passenger_favorites", body, token);
                    ui.post(() -> { toast("Favorito salvo."); showFavorites(); });
                } catch (Exception e) {
                    ui.post(() -> { save.setEnabled(true); save.setText("Salvar favorito"); toast(message(e)); });
                }
            });
        });
    }

    private void confirmDeleteFavorite(String id) {
        new AlertDialog.Builder(this)
                .setTitle("Excluir favorito")
                .setMessage("Deseja remover este endereço salvo?")
                .setNegativeButton("Cancelar", null)
                .setPositiveButton("Excluir", (d, w) -> io.execute(() -> {
                    try {
                        ApiClient.restDelete("passenger_favorites?id=eq." + id, token);
                        ui.post(() -> { toast("Favorito removido."); showFavorites(); });
                    } catch (Exception e) { ui.post(() -> toast(message(e))); }
                }))
                .show();
    }

    private void useFavoriteByLabel(String wanted) {
        io.execute(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet("passenger_favorites?select=label,address,lat,lng&order=created_at.desc", token));
                JSONObject found = null;
                for (int i = 0; i < rows.length(); i++) {
                    JSONObject item = rows.optJSONObject(i);
                    if (item != null && wanted.equalsIgnoreCase(item.optString("label", "").trim())) { found = item; break; }
                }
                if (found == null) { ui.post(() -> { toast("Você ainda não salvou “" + wanted + "”."); showFavorites(); }); return; }
                double lat = found.optDouble("lat", Double.NaN);
                double lng = found.optDouble("lng", Double.NaN);
                String label = found.optString("address", wanted);
                if (!Double.isFinite(lat) || !Double.isFinite(lng)) throw new Exception("Favorito sem coordenadas válidas.");
                GeoPoint point = new GeoPoint(lat, lng);
                ui.post(() -> { destination = point; destinationLabel = label; showOptions(); });
            } catch (Exception e) { ui.post(() -> toast(message(e))); }
        });
    }

    private void showProfile() {
        LinearLayout content = showSectionShell("Meu perfil");
        content.addView(loadingText("Carregando seu perfil…"));
        io.execute(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet("profiles?select=id,full_name,email,phone,cpf,avatar_url&limit=1", token));
                if (rows.length() == 0) throw new Exception("Perfil não encontrado.");
                JSONObject profile = rows.getJSONObject(0);
                currentUserId = profile.optString("id", currentUserId);
                ui.post(() -> renderProfile(content, profile));
            } catch (Exception e) {
                ui.post(() -> {
                    if (!content.isAttachedToWindow()) return;
                    content.removeAllViews();
                    content.addView(unavailable("Não foi possível carregar", message(e)));
                });
            }
        });
    }

    private void renderProfile(LinearLayout content, JSONObject profile) {
        if (destroyed || !content.isAttachedToWindow()) return;
        content.removeAllViews();
        ImageView avatar = new ImageView(this);
        avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));
        avatar.setScaleType(ImageView.ScaleType.CENTER_CROP);
        LinearLayout avatarRow = horizontal();
        avatarRow.setGravity(Gravity.CENTER);
        avatarRow.addView(avatar, new LinearLayout.LayoutParams(dp(88), dp(88)));
        content.addView(avatarRow, lpMatch(dp(100)));
        PassengerAvatar.preload(this, token, () -> {
            if (!destroyed && avatar.isAttachedToWindow()) avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));
        });
        content.addView(space(8));
        EditText name = editLight("Nome completo"); name.setText(profile.optString("full_name", ""));
        EditText email = editLight("E-mail"); email.setText(profile.optString("email", "")); email.setEnabled(false);
        EditText phone = editLight("Telefone"); phone.setText(profile.optString("phone", "")); phone.setInputType(InputType.TYPE_CLASS_PHONE);
        EditText cpf = editLight("CPF"); cpf.setText(profile.optString("cpf", "")); cpf.setInputType(InputType.TYPE_CLASS_NUMBER);
        Button save = primary("Salvar alterações");
        content.addView(name, lpMatch(dp(56))); content.addView(space(8));
        content.addView(email, lpMatch(dp(56))); content.addView(space(8));
        content.addView(phone, lpMatch(dp(56))); content.addView(space(8));
        content.addView(cpf, lpMatch(dp(56))); content.addView(space(14));
        content.addView(save, lpMatch(dp(56)));
        save.setOnClickListener(v -> {
            String fullName = name.getText().toString().trim();
            if (fullName.length() < 2) { toast("Informe seu nome."); return; }
            save.setEnabled(false); save.setText("Salvando…");
            io.execute(() -> {
                try {
                    String uid = ensureUserId();
                    JSONObject body = new JSONObject()
                            .put("full_name", fullName)
                            .put("phone", phone.getText().toString().trim())
                            .put("cpf", cpf.getText().toString().trim());
                    ApiClient.restPatch("profiles?id=eq." + uid, body, token);
                    PassengerAvatar.reset();
                    PassengerAvatar.preload(this, token, () -> {});
                    ui.post(() -> { toast("Perfil atualizado."); showProfile(); });
                } catch (Exception e) {
                    ui.post(() -> { save.setEnabled(true); save.setText("Salvar alterações"); toast(message(e)); });
                }
            });
        });
    }

    private void showCoupons() {
        LinearLayout content = showSectionShell("Cupons");
        content.addView(loadingText("Buscando cupons disponíveis…"));
        io.execute(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet(
                        "coupons?select=code,description,discount_type,discount_value,max_discount,min_ride_value,ends_at&order=created_at.desc&limit=50",
                        token));
                ui.post(() -> renderCoupons(content, rows));
            } catch (Exception e) {
                ui.post(() -> {
                    if (!content.isAttachedToWindow()) return;
                    content.removeAllViews();
                    content.addView(unavailable("Não foi possível carregar", message(e)));
                });
            }
        });
    }

    private void renderCoupons(LinearLayout content, JSONArray rows) {
        if (destroyed || !content.isAttachedToWindow()) return;
        content.removeAllViews();
        if (rows.length() == 0) {
            content.addView(unavailable("Nenhum cupom disponível", "Quando houver uma promoção válida para sua operação, ela aparecerá aqui."));
            return;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject coupon = rows.optJSONObject(i);
            if (coupon == null) continue;
            String code = coupon.optString("code", "");
            String type = coupon.optString("discount_type", "");
            double value = coupon.optDouble("discount_value", 0);
            String discount = type.toLowerCase(Locale.ROOT).contains("percent") ? String.format(Locale.getDefault(), "%.0f%% de desconto", value) : money(value) + " de desconto";
            LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 15);
            card.addView(text(code, 19, BLACK, true));
            card.addView(text(discount, 14, Color.rgb(30,140,80), true));
            String description = coupon.optString("description", "");
            if (!description.isBlank()) { TextView d = text(description, 13, GRAY, false); d.setPadding(0, dp(5), 0, 0); card.addView(d); }
            double min = coupon.optDouble("min_ride_value", 0);
            if (min > 0) card.addView(text("Valor mínimo da corrida: " + money(min), 12, GRAY, false));
            Button copy = smallButton("Copiar código");
            copy.setOnClickListener(v -> {
                android.content.ClipboardManager clipboard = (android.content.ClipboardManager) getSystemService(CLIPBOARD_SERVICE);
                if (clipboard != null) clipboard.setPrimaryClip(android.content.ClipData.newPlainText("Cupom CLICK-GO", code));
                toast("Cupom " + code + " copiado.");
            });
            card.addView(space(8)); card.addView(copy, lpMatch(dp(44)));
            content.addView(card, lpMatchWrap()); content.addView(space(8));
        }
    }

    private void showSupport() {
        LinearLayout content = showSectionShell("Ajuda e suporte");
        Button newTicket = primary("+ Novo chamado");
        content.addView(newTicket, lpMatch(dp(54)));
        content.addView(space(12));
        LinearLayout list = vertical(Color.TRANSPARENT);
        content.addView(list, lpMatchWrap());
        list.addView(loadingText("Carregando seus chamados…"));
        newTicket.setOnClickListener(v -> showNewSupportTicket());
        io.execute(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet(
                        "support_tickets?select=id,subject,category,priority,status,description,created_at,updated_at&order=created_at.desc&limit=30",
                        token));
                ui.post(() -> renderSupportTickets(list, rows));
            } catch (Exception e) {
                ui.post(() -> {
                    if (!list.isAttachedToWindow()) return;
                    list.removeAllViews();
                    list.addView(unavailable("Não foi possível carregar", message(e)));
                });
            }
        });
    }

    private void renderSupportTickets(LinearLayout list, JSONArray rows) {
        if (destroyed || !list.isAttachedToWindow()) return;
        list.removeAllViews();
        if (rows.length() == 0) {
            list.addView(unavailable("Nenhum chamado", "Use “Novo chamado” sempre que precisar falar com o suporte."));
            return;
        }
        for (int i = 0; i < rows.length(); i++) {
            JSONObject ticket = rows.optJSONObject(i);
            if (ticket == null) continue;
            LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 15);
            LinearLayout top = horizontal();
            top.addView(text(ticket.optString("subject", "Chamado"), 16, BLACK, true), new LinearLayout.LayoutParams(0, -2, 1));
            top.addView(text(ticketStatusLabel(ticket.optString("status", "open")), 12, GRAY, true));
            card.addView(top);
            String desc = ticket.optString("description", "");
            if (desc.length() > 120) desc = desc.substring(0, 117) + "…";
            TextView d = text(desc, 13, GRAY, false); d.setPadding(0, dp(6), 0, 0); card.addView(d);
            card.setClickable(true);
            card.setOnClickListener(v -> showTicketDetails(ticket));
            list.addView(card, lpMatchWrap()); list.addView(space(8));
        }
    }

    private String ticketStatusLabel(String status) {
        switch (status == null ? "" : status.toLowerCase(Locale.ROOT)) {
            case "open": return "Aberto";
            case "in_progress": return "Em atendimento";
            case "resolved": return "Resolvido";
            case "closed": return "Fechado";
            default: return status;
        }
    }

    private void showTicketDetails(JSONObject ticket) {
        LinearLayout content = showSectionShell("Detalhes do chamado");
        LinearLayout card = card(Color.WHITE, Color.rgb(232,232,232), 18, 17);
        card.addView(text(ticket.optString("subject", "Chamado"), 19, BLACK, true));
        card.addView(text(ticketStatusLabel(ticket.optString("status", "open")), 13, Color.rgb(30,140,80), true));
        TextView desc = text(ticket.optString("description", ""), 14, GRAY, false);
        desc.setPadding(0, dp(12), 0, dp(8)); card.addView(desc);
        String created = ticket.optString("created_at", "");
        if (created.length() >= 16) created = created.substring(0, 16).replace('T', ' ');
        card.addView(text("Criado em " + created, 12, GRAY, false));
        content.addView(card, lpMatchWrap());
        content.addView(space(12));
        Button back = secondaryLight("Voltar aos chamados");
        back.setOnClickListener(v -> showSupport());
        content.addView(back, lpMatch(dp(52)));
    }

    private void showNewSupportTicket() {
        LinearLayout content = showSectionShell("Novo chamado");
        EditText subject = editLight("Assunto");
        EditText category = editLight("Categoria (ex.: Corrida, Pagamento)");
        EditText description = editLight("Descreva o que aconteceu");
        description.setSingleLine(false); description.setMinLines(4); description.setGravity(Gravity.TOP | Gravity.START);
        description.setPadding(dp(12), dp(12), dp(12), dp(12));
        Button send = primary("Enviar chamado");
        content.addView(subject, lpMatch(dp(56))); content.addView(space(8));
        content.addView(category, lpMatch(dp(56))); content.addView(space(8));
        content.addView(description, lpMatch(dp(120))); content.addView(space(14));
        content.addView(send, lpMatch(dp(56)));
        send.setOnClickListener(v -> {
            String sub = subject.getText().toString().trim();
            String cat = category.getText().toString().trim();
            String desc = description.getText().toString().trim();
            if (sub.length() < 3 || desc.length() < 5) { toast("Informe o assunto e descreva o problema."); return; }
            send.setEnabled(false); send.setText("Enviando…");
            io.execute(() -> {
                try {
                    String uid = ensureUserId();
                    JSONObject body = new JSONObject()
                            .put("requester_id", uid)
                            .put("subject", sub)
                            .put("category", cat.isBlank() ? "Geral" : cat)
                            .put("description", desc);
                    JSONArray last = new JSONArray(ApiClient.restGet("rides?select=franchise_id,city_id&order=requested_at.desc&limit=1", token));
                    if (last.length() > 0) {
                        JSONObject ride = last.getJSONObject(0);
                        String franchise = ride.optString("franchise_id", "");
                        String city = ride.optString("city_id", "");
                        if (!franchise.isBlank()) body.put("franchise_id", franchise);
                        if (!city.isBlank()) body.put("city_id", city);
                    }
                    ApiClient.restPost("support_tickets", body, token);
                    ui.post(() -> { toast("Chamado enviado."); showSupport(); });
                } catch (Exception e) {
                    ui.post(() -> { send.setEnabled(true); send.setText("Enviar chamado"); toast(message(e)); });
                }
            });
        });
    }

'''

text = text.replace(marker, methods + marker, 1)
main_path.write_text(text, encoding='utf-8')

# Adiciona POST/PATCH/DELETE REST ao cliente Supabase.
api_path = Path('app/src/main/java/com/clickgo/passageiro/ApiClient.java')
api = api_path.read_text(encoding='utf-8')
needle = '''    public static String restGet(String pathAndQuery, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "GET", null, true, token, true);\n    }\n'''
addition = needle + '''\n    public static String restPost(String pathAndQuery, JSONObject body, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "POST", body.toString(), true, token, true);\n    }\n\n    public static String restPatch(String pathAndQuery, JSONObject body, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "PATCH", body.toString(), true, token, true);\n    }\n\n    public static String restDelete(String pathAndQuery, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "DELETE", null, true, token, true);\n    }\n'''
if 'public static String restPost(' not in api:
    if needle not in api:
        raise SystemExit('restGet não encontrado em ApiClient')
    api = api.replace(needle, addition, 1)
api_path.write_text(api, encoding='utf-8')

# Permite invalidar o cache do avatar após atualizar o nome do perfil.
avatar_path = Path('app/src/main/java/com/clickgo/passageiro/PassengerAvatar.java')
avatar = avatar_path.read_text(encoding='utf-8')
if 'public static void reset()' not in avatar:
    point = '''    public static String initials() {\n        return initials(fullName);\n    }\n'''
    reset = '''    public static void reset() {\n        loaded = false;\n        loading.set(false);\n        fullName = "Passageiro";\n        photo = null;\n    }\n\n''' + point
    if point not in avatar:
        raise SystemExit('Ponto de reset do avatar não encontrado')
    avatar = avatar.replace(point, reset, 1)
avatar_path.write_text(avatar, encoding='utf-8')

# Versão 1.5.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
build = build.replace('versionCode 14', 'versionCode 15', 1)
build = build.replace("versionName '1.4-native-beta'", "versionName '1.5-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

print('Passageiro v1.5: menu funcional conectado ao Supabase.')
