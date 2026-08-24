from pathlib import Path
import re

main = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path = Path('app/build.gradle')
text = main.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Motorista v2.7 PRIME
# - nova oferta aparece em pop-up central, sem exigir rolagem da tela;
# - aceitar/recusar e contador ficam sempre visíveis;
# - o botão "olho" passa a ocultar somente o saldo/carteira da home;
# - valores de corrida, histórico e taxímetro permanecem sempre visíveis.

# Estado do pop-up da oferta.
field = '''    private long offerCountdownEndsAt;\n'''
fields = '''    private long offerCountdownEndsAt;\n    private android.app.AlertDialog offerDialog;\n    private String offerDialogId = "";\n'''
if 'private android.app.AlertDialog offerDialog;' not in text:
    if field not in text:
        raise SystemExit('Campos do contador de oferta não encontrados')
    text = text.replace(field, fields, 1)

# Helper para fechar o pop-up com segurança.
anchor = '''    private void stopOfferCountdown() {\n'''
helper = r'''    private void dismissOfferDialog() {
        if (offerDialog != null) {
            try { if (offerDialog.isShowing()) offerDialog.dismiss(); } catch (Exception ignored) {}
        }
        offerDialog = null;
        offerDialogId = "";
    }

'''
if 'private void dismissOfferDialog()' not in text:
    if anchor not in text:
        raise SystemExit('stopOfferCountdown não encontrado')
    text = text.replace(anchor, helper + anchor, 1)

# Ao expirar visualmente, fecha o pop-up e atualiza a oferta real no backend.
text = text.replace(
    '''                if (remaining <= 0L) {\n                    stopRideCallSound(true);\n                    stopOfferCountdown();\n                    refreshOperation();''',
    '''                if (remaining <= 0L) {\n                    stopRideCallSound(true);\n                    stopOfferCountdown();\n                    dismissOfferDialog();\n                    refreshOperation();''',
    1,
)

# Oferta: deixa de ocupar o conteúdo rolável e passa a abrir como diálogo central.
pattern = r'''    private void renderOffer\(JSONObject o\)\{.*?\n    \}\n(?=    private void respond\(String id,boolean accept\))'''
replacement = r'''    private void renderOffer(JSONObject o){
        if(operationBox==null)return;
        operationBox.removeAllViews();

        if(o==null){
            stopOfferCountdown();
            stopRideCallSound(true);
            dismissOfferDialog();
            operationTitle.setText("Aguardando chamadas…");
            DriverMapRenderer.render(map,currentLocation,null,dp(5));
            return;
        }

        final String offerId=o.optString("offer_id","");
        if(offerId.isBlank())return;
        startRideCallSound(offerId);
        operationTitle.setText("Nova corrida recebida");
        operationBox.addView(text("Responda pelo aviso que apareceu na tela.",13,GRAY,false));
        DriverMapRenderer.render(map,currentLocation,o,dp(5));

        // O polling roda a cada poucos segundos. Não recria o mesmo pop-up.
        if(offerDialog!=null && offerDialog.isShowing() && offerId.equals(offerDialogId))return;

        stopOfferCountdown();
        dismissOfferDialog();
        offerDialogId=offerId;

        LinearLayout content=vertical(BLACK);
        content.setPadding(dp(20),dp(18),dp(20),dp(18));

        TextView badge=text("NOVA CORRIDA",13,YELLOW,true);
        badge.setGravity(Gravity.CENTER);
        content.addView(badge);
        content.addView(space(7));

        TextView category=text(o.optString("category_name","CLICK-GO"),24,Color.WHITE,true);
        category.setGravity(Gravity.CENTER);
        content.addView(category);

        TextView timer=text("⏱ 20s para responder",15,YELLOW,true);
        timer.setGravity(Gravity.CENTER);
        content.addView(timer);
        content.addView(space(14));

        LinearLayout route=card(DARK,Color.rgb(64,64,64));
        route.addView(text("📍 EMBARQUE",11,GRAY,true));
        TextView pickup=text(o.optString("origin_label","Local de embarque"),16,Color.WHITE,true);
        pickup.setMaxLines(2);
        route.addView(pickup);
        route.addView(space(10));
        route.addView(text("🏁 DESTINO",11,GRAY,true));
        TextView destination=text(o.optString("destination_label","Destino"),15,Color.LTGRAY,false);
        destination.setMaxLines(2);
        route.addView(destination);
        content.addView(route,wrap());
        content.addView(space(12));

        String distance=o.has("distance_to_pickup_km")
                ? String.format(Locale.getDefault(),"%.1f km",o.optDouble("distance_to_pickup_km",0)) : "—";
        String eta=o.has("eta_to_pickup_min") ? o.optInt("eta_to_pickup_min",0)+" min" : "—";
        LinearLayout metrics=horizontal();
        LinearLayout km=vertical(Color.TRANSPARENT);
        km.addView(text("ATÉ O PASSAGEIRO",10,GRAY,true));
        km.addView(text(distance,17,Color.WHITE,true));
        LinearLayout tm=vertical(Color.TRANSPARENT);
        tm.addView(text("PREVISÃO",10,GRAY,true));
        tm.addView(text(eta,17,Color.WHITE,true));
        metrics.addView(km,new LinearLayout.LayoutParams(0,dp(48),1));
        metrics.addView(tm,new LinearLayout.LayoutParams(0,dp(48),1));
        content.addView(metrics);

        double gross=o.optDouble("estimated_fare",o.optDouble("estimated_driver_earning",0));
        double earning=o.optDouble("estimated_driver_earning",gross);
        content.addView(text("VALOR ESTIMADO",11,GRAY,true));
        TextView fare=text(money(gross),28,YELLOW,true);
        content.addView(fare);
        if(Math.abs(earning-gross)>0.009){
            content.addView(text("Seu ganho estimado: "+money(earning),13,Color.LTGRAY,true));
        }
        content.addView(space(14));

        LinearLayout actions=horizontal();
        Button no=darkButton("RECUSAR");
        Button yes=primary("ACEITAR");
        actions.addView(no,new LinearLayout.LayoutParams(0,dp(62),1));
        actions.addView(spaceH(9));
        actions.addView(yes,new LinearLayout.LayoutParams(0,dp(62),1));
        content.addView(actions);

        android.app.AlertDialog dialog=new android.app.AlertDialog.Builder(this)
                .setView(content)
                .create();
        dialog.setCancelable(false);
        dialog.setCanceledOnTouchOutside(false);
        offerDialog=dialog;

        yes.setOnClickListener(v->{ dismissOfferDialog(); respond(offerId,true); });
        no.setOnClickListener(v->{ dismissOfferDialog(); respond(offerId,false); });

        dialog.setOnShowListener(d->{
            if(dialog.getWindow()!=null){
                dialog.getWindow().setBackgroundDrawableResource(android.R.color.transparent);
                int width=getResources().getDisplayMetrics().widthPixels-dp(28);
                dialog.getWindow().setLayout(Math.max(dp(300),width),android.view.ViewGroup.LayoutParams.WRAP_CONTENT);
            }
        });
        dialog.show();
        startOfferCountdown(timer);
    }
'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('renderOffer comercial não encontrado')

# Fecha o pop-up antes de responder e ao entrar em uma corrida ativa.
text = text.replace(
    '''    private void respond(String id,boolean accept){\n        stopOfferCountdown();''',
    '''    private void respond(String id,boolean accept){\n        dismissOfferDialog();\n        stopOfferCountdown();''',
    1,
)
text = text.replace(
    '''    private void renderRide(JSONObject r) {\n        stopOfferCountdown();''',
    '''    private void renderRide(JSONObject r) {\n        dismissOfferDialog();\n        stopOfferCountdown();''',
    1,
)

# O olho é apenas privacidade da carteira na tela inicial.
# privateMoney deixa de depender do olho, portanto valores de corrida/taxímetro/histórico não somem.
text, n = re.subn(
    r'''    private String privateMoney\(double v\)\{return showMoney\?money\(v\):"R\$ ••••";\}''',
    '''    private String privateMoney(double v){return money(v);}''',
    text,
    count=1,
)
if n != 1:
    raise SystemExit('privateMoney não encontrado')

# walletLabel é o único valor que respeita showMoney.
text, n = re.subn(
    r'''    private String walletLabel\(\)\{return billingMode\.equals\("monthly"\)\?"Plano mensal":"Carteira operacional: "\+privateMoney\(balance\);\}''',
    '''    private String walletLabel(){return billingMode.equals("monthly")?"Plano mensal":"Carteira operacional: "+(showMoney?money(balance):"R$ ••••");}''',
    text,
    count=1,
)
if n != 1:
    raise SystemExit('walletLabel privado não encontrado')

# Não deixa um diálogo aberto sobreviver ao login/logout/destruição.
text = text.replace(
    '''    private void showLogin() {\n        stopOfferCountdown();''',
    '''    private void showLogin() {\n        dismissOfferDialog();\n        stopOfferCountdown();''',
    1,
)
text = text.replace(
    '''    private void logout(){stopOfferCountdown();''',
    '''    private void logout(){dismissOfferDialog();stopOfferCountdown();''',
    1,
)
text = text.replace(
    '''        destroyed = true; stopOfferCountdown();''',
    '''        destroyed = true; dismissOfferDialog(); stopOfferCountdown();''',
    1,
)

# Versão.
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.7-prime'", build, count=1)

main.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Motorista v2.7 PRIME: oferta em pop-up e olho restrito à carteira da home.')
