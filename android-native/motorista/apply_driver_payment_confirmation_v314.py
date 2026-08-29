from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# RPCs da confirmação de recebimento e recuperação de uma confirmação pendente.
repo_anchor='''    public static JSONObject submitPassengerRating(String token, String rideId, int rating, String comment) throws Exception {\n'''
repo_methods='''    public static JSONObject confirmRidePayment(String token, String rideId) throws Exception {\n        return new JSONObject(ApiClient.rpc("confirm_driver_ride_payment", new JSONObject().put("p_ride_id", rideId), token));\n    }\n\n    public static JSONObject pendingPaymentConfirmation(String token, String userId) throws Exception {\n        JSONArray rows = new JSONArray(ApiClient.restGet("rides?driver_id=eq." + userId + "&status=eq.completed&driver_payment_confirmed_at=is.null&select=id,estimated_fare,final_fare,payment_method_preference,completed_at&order=completed_at.desc&limit=1", token));\n        return rows.length() > 0 ? rows.getJSONObject(0) : null;\n    }\n\n'''
if 'public static JSONObject confirmRidePayment(' not in repo:
    if repo_anchor not in repo: raise SystemExit('submitPassengerRating não encontrado no DriverRepository final')
    repo=repo.replace(repo_anchor,repo_methods+repo_anchor,1)

# Evita abrir duas confirmações ao mesmo tempo.
field_anchor='''    private boolean destroyed;\n'''
if 'private boolean paymentConfirmationShowing;' not in text:
    if field_anchor not in text: raise SystemExit('campo destroyed não encontrado')
    text=text.replace(field_anchor,field_anchor+'    private boolean paymentConfirmationShowing;\n',1)

# A corrida continua sendo concluída como antes, mas a avaliação só abre depois do recebimento confirmado.
old_call='''                    showPassengerRating(rideId, finalFare);'''
new_call='''                    showRidePaymentConfirmation(rideId, finalFare);'''
if old_call in text:
    text=text.replace(old_call,new_call,1)
elif 'showRidePaymentConfirmation(rideId, finalFare);' not in text:
    raise SystemExit('chamada da avaliação após conclusão não encontrada')

# Se o app for fechado após concluir a corrida e antes de confirmar, a tela volta automaticamente no próximo acesso.
home_anchor='''        loadHomeTaximeter(homeTaximeter);\n'''
if '        resumePendingPaymentConfirmation();\n' not in text:
    if home_anchor not in text: raise SystemExit('loadHomeTaximeter da home não encontrado')
    text=text.replace(home_anchor,home_anchor+'        resumePendingPaymentConfirmation();\n',1)

rating_anchor='''    private void showPassengerRating(String rideId, double fare) {\n'''
methods=r'''    private void resumePendingPaymentConfirmation() {
        if (paymentConfirmationShowing || token == null || token.isBlank() || userId == null || userId.isBlank()) return;
        io.execute(() -> {
            try {
                JSONObject pending = DriverRepository.pendingPaymentConfirmation(token, userId);
                if (pending == null) return;
                String rideId = pending.optString("id", "");
                double fare = pending.optDouble("final_fare", pending.optDouble("estimated_fare", 0));
                if (!rideId.isBlank()) ui.post(() -> showRidePaymentConfirmation(rideId, fare));
            } catch (Exception ignored) {}
        });
    }

    private void showRidePaymentConfirmation(String rideId, double fare) {
        if (paymentConfirmationShowing || rideId == null || rideId.isBlank() || destroyed || isFinishing()) return;
        paymentConfirmationShowing = true;

        LinearLayout wrap = vertical(Color.WHITE);
        wrap.setPadding(dp(20), dp(20), dp(20), dp(12));
        wrap.addView(text("Corrida concluída ✓", 22, BLACK, true));
        wrap.addView(space(8));
        wrap.addView(text("CONFIRME O RECEBIMENTO", 13, Color.DKGRAY, true));
        TextView amount = text(privateMoney(fare), 34, BLACK, true);
        amount.setGravity(Gravity.CENTER);
        wrap.addView(space(8));
        wrap.addView(amount);
        wrap.addView(space(10));
        wrap.addView(text("Confirme somente depois que o valor da corrida tiver sido recebido do passageiro. A avaliação será liberada em seguida.", 14, Color.DKGRAY, false));

        android.app.AlertDialog dialog = new android.app.AlertDialog.Builder(this)
                .setView(wrap)
                .setCancelable(false)
                .setPositiveButton("CONFIRMAR RECEBIMENTO", null)
                .create();
        dialog.setOnDismissListener(d -> paymentConfirmationShowing = false);
        dialog.setOnShowListener(d -> {
            Button confirm = dialog.getButton(android.app.AlertDialog.BUTTON_POSITIVE);
            confirm.setOnClickListener(v -> {
                confirm.setEnabled(false);
                confirm.setText("CONFIRMANDO...");
                io.execute(() -> {
                    try {
                        JSONObject result = DriverRepository.confirmRidePayment(token, rideId);
                        double confirmedAmount = result.optDouble("amount", fare);
                        ui.post(() -> {
                            confirm.setEnabled(true);
                            dialog.dismiss();
                            toast("Recebimento confirmado: " + privateMoney(confirmedAmount));
                            showPassengerRating(rideId, confirmedAmount);
                        });
                    } catch (Exception e) {
                        ui.post(() -> {
                            confirm.setEnabled(true);
                            confirm.setText("CONFIRMAR RECEBIMENTO");
                            toast(msg(e));
                        });
                    }
                });
            });
        });
        dialog.show();
    }

'''
if 'private void showRidePaymentConfirmation(' not in text:
    if rating_anchor not in text: raise SystemExit('showPassengerRating não encontrado')
    text=text.replace(rating_anchor,methods+rating_anchor,1)

# Deixa explícito na home que o taxímetro abre uma viagem própria. O backend v3.13 continua sendo a autoridade:
# somente franquias liberadas pela Matriz conseguem iniciar a sessão e o motorista fica fora das chamadas normais.
text=text.replace('primary("INICIAR TAXÍMETRO")','primary("ABRIR TAXÍMETRO / FAZER VIAGEM")')
text=text.replace('categoria(s) liberada(s) · tarifas definidas pelo franqueado','categoria(s) liberada(s) · tarifas do franqueado · autorização da Matriz ativa')
text=text.replace('Modo de corrida livre. Usa a tarifa da categoria autorizada pela franquia.','Faça viagens com taxímetro usando somente categorias e tarifas autorizadas para sua franquia.')

for required in [
    'confirm_driver_ride_payment',
    'CONFIRME O RECEBIMENTO',
    'CONFIRMAR RECEBIMENTO',
    'showRidePaymentConfirmation(rideId, finalFare)',
    'resumePendingPaymentConfirmation()',
    'ABRIR TAXÍMETRO / FAZER VIAGEM',
    'Taxímetro não disponível nesta franquia.',
    'taximeter_enabled_by_matrix'
]:
    if required not in text+repo: raise SystemExit('Motorista v3.14 incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(max(int(m.group(1))+1,314))+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.14-prime'",build,count=1)

main_path.write_text(text,encoding='utf-8')
repo_path.write_text(repo,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.14 PRIME: recebimento confirmado antes da avaliação e taxímetro com acesso de viagem explícito.')
