from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# v3.0 PRIME
# - popup mostra passageiro, nota, histórico de corridas e pagamento;
# - menu vira uma lista textual clicável, sem cards/botões grandes.

pattern=r'''    private void renderOffer\(JSONObject o\)\{.*?\n    \}\n(?=    private void respond\(String id,boolean accept\))'''
replacement=r'''    private void renderOffer(JSONObject o){
        if(operationBox==null)return;
        operationBox.removeAllViews();
        if(o==null){
            stopOfferCountdown();stopRideCallSound(true);dismissOfferDialog();
            operationTitle.setText("Aguardando chamadas");
            DriverMapRenderer.render(map,currentLocation,null,dp(5));
            return;
        }
        final String offerId=o.optString("offer_id","");
        if(offerId.isBlank())return;
        startRideCallSound(offerId);
        operationTitle.setText("Nova chamada recebida");
        DriverMapRenderer.render(map,currentLocation,o,dp(5));
        drawDriverRoadRoute(o);
        if(offerDialog!=null&&offerDialog.isShowing()&&offerId.equals(offerDialogId))return;
        stopOfferCountdown();dismissOfferDialog();offerDialogId=offerId;

        LinearLayout c=vertical(Color.WHITE);c.setPadding(dp(20),dp(18),dp(20),dp(18));
        TextView badge=text("NOVA CORRIDA",12,Color.rgb(90,90,90),true);badge.setGravity(Gravity.CENTER);c.addView(badge);
        TextView cat=text(o.optString("category_name","CLICK-GO"),24,BLACK,true);cat.setGravity(Gravity.CENTER);c.addView(cat);
        TextView timer=text("20s para responder",15,Color.rgb(217,148,0),true);timer.setGravity(Gravity.CENTER);c.addView(timer);c.addView(space(12));

        String passenger=o.optString("passenger_name","Passageiro CLICK-GO").trim();
        if(passenger.isBlank())passenger="Passageiro CLICK-GO";
        long ratingCount=o.optLong("passenger_rating_count",0), completed=o.optLong("passenger_completed_rides",0);
        double passengerRating=o.optDouble("passenger_rating",0);
        LinearLayout passengerCard=card(Color.rgb(250,250,250),Color.rgb(226,226,226));
        LinearLayout passengerRow=horizontal();passengerRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView avatar=text(initials(passenger),18,YELLOW,true);avatar.setGravity(Gravity.CENTER);avatar.setBackground(round(BLACK,28,BLACK));
        passengerRow.addView(avatar,new LinearLayout.LayoutParams(dp(56),dp(56)));
        LinearLayout passengerCopy=vertical(Color.TRANSPARENT);passengerCopy.setPadding(dp(12),0,0,0);
        passengerCopy.addView(text(passenger,18,BLACK,true));
        String ratingText=ratingCount>0?"★ "+String.format(Locale.getDefault(),"%.1f",passengerRating)+" · "+ratingCount+" avaliação(ões)":"Novo passageiro · sem avaliações ainda";
        passengerCopy.addView(text(ratingText,13,Color.DKGRAY,false));
        passengerCopy.addView(text(completed+" corrida(s) concluída(s) na CLICK-GO",12,Color.DKGRAY,false));
        passengerRow.addView(passengerCopy,new LinearLayout.LayoutParams(0,dp(62),1));passengerCard.addView(passengerRow);
        c.addView(passengerCard,wrap());c.addView(space(10));

        LinearLayout route=card(Color.rgb(247,247,247),Color.rgb(225,225,225));
        route.addView(text("EMBARQUE",10,Color.DKGRAY,true));route.addView(text(o.optString("origin_label","Local de embarque"),16,BLACK,true));route.addView(space(9));
        route.addView(text("DESTINO",10,Color.DKGRAY,true));route.addView(text(o.optString("destination_label","Destino"),14,Color.DKGRAY,false));c.addView(route,wrap());c.addView(space(10));

        String d=o.has("distance_to_pickup_km")?String.format(Locale.getDefault(),"%.1f km",o.optDouble("distance_to_pickup_km",0)):"—";
        String eta=o.has("eta_to_pickup_min")?o.optInt("eta_to_pickup_min",0)+" min":"—";
        LinearLayout metrics=horizontal();metrics.addView(text("Até o embarque: "+d,13,BLACK,true),new LinearLayout.LayoutParams(0,dp(38),1));metrics.addView(text("Previsão: "+eta,13,BLACK,true),new LinearLayout.LayoutParams(0,dp(38),1));c.addView(metrics);
        c.addView(text("Pagamento: "+offerPaymentLabel(o.optString("payment_method","")),13,Color.DKGRAY,true));
        c.addView(space(5));
        double gross=o.optDouble("estimated_fare",o.optDouble("estimated_driver_earning",0));
        TextView fare=text(money(gross),30,BLACK,true);fare.setGravity(Gravity.CENTER);c.addView(fare);c.addView(space(12));
        LinearLayout actions=horizontal();Button no=darkButton("RECUSAR");Button yes=primary("ACEITAR");actions.addView(no,new LinearLayout.LayoutParams(0,dp(62),1));actions.addView(spaceH(10));actions.addView(yes,new LinearLayout.LayoutParams(0,dp(62),1));c.addView(actions);

        android.app.AlertDialog dialog=new android.app.AlertDialog.Builder(this).setView(c).create();
        dialog.setCancelable(false);dialog.setCanceledOnTouchOutside(false);offerDialog=dialog;
        yes.setOnClickListener(v->{dismissOfferDialog();respond(offerId,true);});no.setOnClickListener(v->{dismissOfferDialog();respond(offerId,false);});
        dialog.setOnShowListener(x->{android.view.Window w=dialog.getWindow();if(w!=null){w.setBackgroundDrawableResource(android.R.color.transparent);w.addFlags(android.view.WindowManager.LayoutParams.FLAG_DIM_BEHIND);android.view.WindowManager.LayoutParams lp=w.getAttributes();lp.dimAmount=.72f;lp.width=getResources().getDisplayMetrics().widthPixels-dp(24);w.setAttributes(lp);}});
        dialog.show();
        if(dialog.getWindow()!=null)dialog.getWindow().setLayout(getResources().getDisplayMetrics().widthPixels-dp(24),android.view.ViewGroup.LayoutParams.WRAP_CONTENT);
        startOfferCountdown(timer);
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1:raise SystemExit('renderOffer final não encontrado')

pattern=r'''    private void showDriverMenu\(\)\{.*?\n    \}\n\n    private View menuCard'''
replacement=r'''    private void showDriverMenu(){
        stopPolling();releaseMap();
        LinearLayout body=vertical(Color.WHITE);body.setPadding(dp(22),dp(28),dp(22),dp(32));
        LinearLayout top=horizontal();top.setGravity(Gravity.CENTER_VERTICAL);
        TextView back=menuLink("← Voltar ao mapa",()->showHome());top.addView(back,new LinearLayout.LayoutParams(0,dp(52),1));
        body.addView(top);body.addView(space(12));
        body.addView(text("Menu",30,BLACK,true));body.addView(text(firstName(fullName)+" · ★ "+String.format(Locale.getDefault(),"%.1f",rating),14,Color.DKGRAY,false));body.addView(space(18));
        body.addView(menuLink("Corridas",()->showHome()));
        body.addView(menuLink("Histórico",()->showRideHistory()));
        body.addView(menuLink("Ganhos e carteira",()->showEarnings()));
        body.addView(menuLink("Perfil e veículo",()->showDriverProfile()));
        if(!"approved".equalsIgnoreCase(driverStatus))body.addView(menuLink("Documentos",()->showDocuments()));
        body.addView(menuLink("Suporte",()->showSupport()));
        body.addView(menuLink("Configurações",()->showDriverSettings()));
        body.addView(space(18));
        TextView exit=menuLink("Sair da conta",()->logout());exit.setTextColor(Color.rgb(190,55,55));body.addView(exit);
        setContentView(scroll(body,Color.WHITE));
    }

    private View menuCard'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1:raise SystemExit('showDriverMenu final não encontrado')

anchor='''    private String firstName(String v){'''
helpers=r'''    private TextView menuLink(String label,Runnable action){
        TextView row=text(label+"   ›",18,BLACK,true);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(4),dp(8),dp(4),dp(8));row.setBackground(round(Color.WHITE,0,Color.rgb(232,232,232)));row.setOnClickListener(v->action.run());return row;
    }
    private String initials(String value){String s=value==null?"":value.trim();if(s.isBlank())return"CG";String[] p=s.split("\\s+");String a=p[0].substring(0,1).toUpperCase(Locale.ROOT);String b=p.length>1?p[p.length-1].substring(0,1).toUpperCase(Locale.ROOT):"";return a+b;}
    private String offerPaymentLabel(String value){if("pix".equals(value))return"PIX";if("card".equals(value))return"Cartão no app";if("card_machine".equals(value))return"Cartão com motorista";if("cash".equals(value))return"Dinheiro";return value==null||value.isBlank()?"Conforme corrida":value;}
'''
if anchor not in text:raise SystemExit('helper firstName não encontrado')
if 'private TextView menuLink(' not in text:text=text.replace(anchor,helpers+anchor,1)

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.0-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v3.0 PRIME: passageiro no popup e menu textual aplicados.')
