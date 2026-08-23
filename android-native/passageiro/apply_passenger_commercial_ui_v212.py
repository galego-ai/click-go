from pathlib import Path
import re

root=Path('app')
main=root/'src/main/java/com/clickgo/passageiro/MainActivity.java'
build_path=root/'build.gradle'
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# CLICK-GO Passageiro v2.12 PRIME — fluxo comercial simples e pós-corrida.
# -----------------------------------------------------------------------------

# Forma de pagamento usada no resumo final.
field='''    private String activeRideStatus = "searching";\n'''
fields='''    private String activeRideStatus = "searching";\n    private String activePaymentMethod = "";\n'''
if field in text and 'private String activePaymentMethod' not in text:
    text=text.replace(field,fields,1)

# Home map-first: copy simples e CTA claro.
text=text.replace('''        homeLocationText=text(originLabel,13,GRAY,false);homeLocationText.setSingleLine(true);homeLocationText.setEllipsize(TextUtils.TruncateAt.END);bottom.addView(homeLocationText);''','''        bottom.addView(text("Para onde vamos?",22,BLACK,true));\n        bottom.addView(space(4));\n        homeLocationText=text("📍 "+originLabel,13,GRAY,false);homeLocationText.setSingleLine(true);homeLocationText.setEllipsize(TextUtils.TruncateAt.END);bottom.addView(homeLocationText);''',1)
text=text.replace('''        Button where=primary("Onde vamos?");''','''        Button where=primary("ESCOLHER DESTINO");''',1)

# Ao atualizar GPS, mantém o ícone da origem no texto da home.
text=text.replace('''        if (labelView != null) labelView.setText(originLabel);''','''        if (labelView != null) labelView.setText(homeMapMode ? "📍 "+originLabel : originLabel);''',1)

# Seção de pagamento explícita antes do spinner.
needle='''        paymentSpinner = new Spinner(this);\n        bottom.addView(paymentSpinner, lpMatch(dp(54)));'''
replacement='''        bottom.addView(text("Forma de pagamento",14,BLACK,true));\n        bottom.addView(space(5));\n        paymentSpinner = new Spinner(this);\n        bottom.addView(paymentSpinner, lpMatch(dp(54)));'''
if needle in text:
    text=text.replace(needle,replacement,1)
elif 'Forma de pagamento' not in text:
    raise SystemExit('paymentSpinner da tela de opções não encontrado')

# CTA de solicitação no padrão CLICK-GO.
text=text.replace('''        requestRideButton.setText("Solicitar " + selectedOption.name + " · " + money(selectedOption.fare));''','''        requestRideButton.setText("CHAMAR " + selectedOption.name.toUpperCase(Locale.ROOT) + " · " + money(selectedOption.fare));''')
text=text.replace('''                        requestRideButton.setText("Solicitar " + option.name + " · " + money(option.fare));''','''                        requestRideButton.setText("CHAMAR " + option.name.toUpperCase(Locale.ROOT) + " · " + money(option.fare));''')

# Guarda forma de pagamento para a tela final.
needle='''        String payment = paymentValues.get(Math.min(index, paymentValues.size() - 1));\n'''
if needle in text:
    text=text.replace(needle,needle+'        activePaymentMethod = payment;\n',1)
elif 'activePaymentMethod = payment;' not in text:
    raise SystemExit('Forma de pagamento da solicitação não encontrada')

# Status da corrida: linguagem direta para passageiro.
text=text.replace('''        activeStatus = text("Corrida em andamento · procurando motorista", 25, BLACK, true);''','''        activeStatus = text("Procurando motorista…", 25, BLACK, true);''',1)
text=text.replace('''activeStatus.setText(status.equals("accepted")?"Corrida em andamento · motorista a caminho":status.equals("driver_arriving")?"Corrida em andamento · motorista no embarque":status.equals("in_progress")?"Corrida em andamento · a caminho do destino":"Corrida em andamento · "+statusLabel(status));''','''activeStatus.setText(status.equals("accepted")?"Motorista a caminho":status.equals("driver_arriving")?"Seu motorista chegou!":status.equals("in_progress")?"Em viagem para o destino":statusLabel(status));''',1)

# Quando o motorista ainda está a caminho, usa a posição ao vivo para uma ETA curta.
old='''                                } else if (status.equals("accepted")) {\n                                    activeWaitInfo.setText("A tolerância começa somente quando o motorista tocar em ‘Cheguei ao embarque’. ");\n                                } else {'''
new='''                                } else if (status.equals("accepted")) {\n                                    if(finalLocation!=null && origin!=null){\n                                        double dkm=passengerDistanceKm(finalLocation.optDouble("lat",Double.NaN),finalLocation.optDouble("lng",Double.NaN),origin.getLatitude(),origin.getLongitude());\n                                        int eta=(int)Math.max(1,Math.round(dkm*2.4));\n                                        activeWaitInfo.setText(Double.isFinite(dkm)?("🚗 Motorista a "+String.format(Locale.getDefault(),"%.1f km",dkm)+" · aprox. "+eta+" min"):"Motorista a caminho do embarque.");\n                                    }else activeWaitInfo.setText("Motorista a caminho do embarque.");\n                                } else {'''
if old in text:
    text=text.replace(old,new,1)
elif 'passengerDistanceKm' not in text:
    raise SystemExit('Bloco de espera/accepted não encontrado')

# Helper Haversine para ETA visual do motorista.
anchor='''    private String formatClock(int seconds) {\n'''
helper='''    private double passengerDistanceKm(double lat1,double lng1,double lat2,double lng2){\n        if(!Double.isFinite(lat1)||!Double.isFinite(lng1)||!Double.isFinite(lat2)||!Double.isFinite(lng2))return Double.NaN;\n        double r=6371.0,dLat=Math.toRadians(lat2-lat1),dLng=Math.toRadians(lng2-lng1);\n        double a=Math.sin(dLat/2)*Math.sin(dLat/2)+Math.cos(Math.toRadians(lat1))*Math.cos(Math.toRadians(lat2))*Math.sin(dLng/2)*Math.sin(dLng/2);\n        return r*2*Math.atan2(Math.sqrt(a),Math.sqrt(1-a));\n    }\n\n'''
if 'private double passengerDistanceKm' not in text:
    if anchor not in text: raise SystemExit('formatClock não encontrado')
    text=text.replace(anchor,helper+anchor,1)

# Preserva o rideId concluído para avaliação antes de zerar a corrida ativa.
old='''activeRideId=null; stopRidePolling(); stopPassengerLiveLocation(); releaseMap(); showEndState(status,finalDisplayFare);'''
new='''String finishedRideId=rideId; activeRideId=null; stopRidePolling(); stopPassengerLiveLocation(); releaseMap(); showEndState(status,finalDisplayFare,finishedRideId);'''
if old in text:
    text=text.replace(old,new,1)
elif 'showEndState(status,finalDisplayFare,finishedRideId)' not in text:
    raise SystemExit('Finalização do polling não encontrada')

# Tela final com resumo e avaliação real do motorista.
pattern=r'''    private void showEndState\(String status, double fare\) \{.*?\n    \}\n\n(?=    private void previewCancel\(\))'''
replacement=r'''    private void showEndState(String status, double fare, String rideId) {
        LinearLayout body = vertical(Color.WHITE);
        body.setPadding(dp(24), dp(42), dp(24), dp(34));
        TextView doneIcon=text(status.equals("completed")?"✓":"×",46,status.equals("completed")?Color.rgb(22,163,74):Color.rgb(220,70,55),true);
        doneIcon.setGravity(Gravity.CENTER);body.addView(doneIcon);
        TextView title=text(status.equals("completed")?"Você chegou!":"Corrida cancelada",30,BLACK,true);title.setGravity(Gravity.CENTER);body.addView(title);
        TextView fareView=text(money(fare),28,BLACK,true);fareView.setGravity(Gravity.CENTER);body.addView(fareView);
        if(!activePaymentMethod.isBlank()){TextView payment=text("Pagamento: "+paymentLabel(activePaymentMethod),14,GRAY,false);payment.setGravity(Gravity.CENTER);body.addView(payment);}
        body.addView(space(20));

        if(status.equals("completed")){
            LinearLayout ratingCard=card(Color.rgb(250,250,250),Color.rgb(230,230,230),20,16);
            ratingCard.addView(text("Como foi sua viagem?",20,BLACK,true));
            ratingCard.addView(text("Avalie o motorista",13,GRAY,false));
            ratingCard.addView(space(10));
            Spinner stars=new Spinner(this);
            String[] labels={"★★★★★  5 - Excelente","★★★★☆  4 - Muito bom","★★★☆☆  3 - Regular","★★☆☆☆  2 - Ruim","★☆☆☆☆  1 - Muito ruim"};
            stars.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));
            ratingCard.addView(stars,lpMatch(dp(56)));
            ratingCard.addView(space(8));
            EditText comment=editLight("Comentário opcional");comment.setSingleLine(false);comment.setMinLines(3);comment.setGravity(Gravity.TOP);comment.setPadding(dp(12),dp(10),dp(12),dp(10));
            ratingCard.addView(comment,new LinearLayout.LayoutParams(-1,dp(105)));
            ratingCard.addView(space(10));
            Button send=primary("ENVIAR AVALIAÇÃO");ratingCard.addView(send,lpMatch(dp(58)));
            send.setOnClickListener(v->{int rating=5-stars.getSelectedItemPosition();String note=comment.getText().toString().trim();send.setEnabled(false);io.execute(()->{try{ApiClient.rpc("submit_passenger_ride_rating",new JSONObject().put("p_ride_id",rideId).put("p_rating",rating).put("p_comment",note.isBlank()?JSONObject.NULL:note),token);ui.post(()->{toast("Avaliação enviada. Obrigado!");send.setText("AVALIAÇÃO ENVIADA ✓");});}catch(Exception e){ui.post(()->{send.setEnabled(true);toast(message(e));});}});});
            body.addView(ratingCard,lpMatchWrap());
            body.addView(space(16));
        }

        Button newRide = primary("NOVA CORRIDA");
        body.addView(newRide, lpMatch(dp(60)));
        newRide.setOnClickListener(v -> {
            destination = null;
            destinationLabel = "";
            activePaymentMethod = "";
            showHome();
        });
        setContentView(scroll(body,Color.WHITE));
    }

'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showEndState final não encontrado')

# Versão.
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.12-prime'",build,count=1)

main.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.12 PRIME: fluxo comercial, ETA, resumo e avaliação do motorista aplicados.')
