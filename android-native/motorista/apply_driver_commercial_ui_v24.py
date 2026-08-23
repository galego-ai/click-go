from pathlib import Path
import re

root=Path('app')
main=root/'src/main/java/com/clickgo/motorista/MainActivity.java'
build_path=root/'build.gradle'
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# CLICK-GO Motorista v2.4 PRIME — UI comercial de condução
# -----------------------------------------------------------------------------
# Objetivos:
# - chamado grande, legível e com contagem regressiva;
# - ações de corrida com um único verbo operacional por etapa;
# - navegação externa preservada;
# - bolha flutuante/som da v2.3 preservados;
# - ganhos diário/semanal no menu;
# - versão final de piloto sem PIN/SOS.

# Estado do contador da oferta.
field='''    private boolean overlayPrompted;\n'''
fields='''    private boolean overlayPrompted;\n    private Runnable offerCountdown;\n    private TextView offerCountdownText;\n    private long offerCountdownEndsAt;\n'''
if field in text and 'private Runnable offerCountdown;' not in text:
    text=text.replace(field,fields,1)

# Métodos de contagem regressiva. O backend continua sendo a fonte da expiração;
# este relógio é UX e força refresh ao zerar.
anchor='''    private void startRideCallSound(String offerId) {\n'''
countdown=r'''    private void stopOfferCountdown() {
        if (offerCountdown != null) ui.removeCallbacks(offerCountdown);
        offerCountdown = null;
        offerCountdownText = null;
        offerCountdownEndsAt = 0L;
    }

    private void startOfferCountdown(TextView view) {
        stopOfferCountdown();
        offerCountdownText = view;
        offerCountdownEndsAt = System.currentTimeMillis() + 20_000L;
        offerCountdown = new Runnable() {
            @Override public void run() {
                if (offerCountdownText == null || destroyed) return;
                long remaining = Math.max(0L, offerCountdownEndsAt - System.currentTimeMillis());
                int seconds = (int)Math.ceil(remaining / 1000.0);
                offerCountdownText.setText("⏱ " + seconds + "s para responder");
                offerCountdownText.setTextColor(seconds <= 5 ? Color.rgb(248,113,113) : YELLOW);
                if (remaining <= 0L) {
                    stopRideCallSound(true);
                    stopOfferCountdown();
                    refreshOperation();
                    return;
                }
                ui.postDelayed(this, 250L);
            }
        };
        ui.post(offerCountdown);
    }

'''
if 'private void startOfferCountdown(TextView view)' not in text:
    if anchor not in text: raise SystemExit('Som de chamada v2.3 não encontrado')
    text=text.replace(anchor,countdown+anchor,1)

# Oferta comercial: origem/destino, distância, ETA, valor e contador.
pattern=r'''    private void renderOffer\(JSONObject o\)\{.*?\n    \}\n(?=    private void respond\(String id,boolean accept\))'''
replacement=r'''    private void renderOffer(JSONObject o){
        if(operationBox==null)return;
        operationBox.removeAllViews();
        if(o==null){
            stopOfferCountdown();
            stopRideCallSound(true);
            operationTitle.setText("Aguardando chamadas…");
            DriverMapRenderer.render(map,currentLocation,null,dp(5));
            return;
        }

        startRideCallSound(o.optString("offer_id",""));
        operationTitle.setText("🔔 NOVA CORRIDA");
        LinearLayout c=card(DARK,YELLOW);
        c.setPadding(dp(18),dp(18),dp(18),dp(18));

        LinearLayout head=horizontal();
        head.setGravity(Gravity.CENTER_VERTICAL);
        TextView category=text(o.optString("category_name","CLICK-GO"),20,Color.WHITE,true);
        head.addView(category,new LinearLayout.LayoutParams(0,dp(38),1));
        TextView timer=text("⏱ 20s para responder",14,YELLOW,true);
        timer.setGravity(Gravity.CENTER_VERTICAL|Gravity.RIGHT);
        head.addView(timer,new LinearLayout.LayoutParams(dp(150),dp(38)));
        c.addView(head);
        c.addView(space(10));

        c.addView(text("📍 EMBARQUE",11,GRAY,true));
        TextView pickup=text(o.optString("origin_label","Local de embarque"),16,Color.WHITE,true);
        pickup.setMaxLines(2); c.addView(pickup);
        c.addView(space(9));
        c.addView(text("🏁 DESTINO",11,GRAY,true));
        TextView destination=text(o.optString("destination_label","Destino"),15,Color.LTGRAY,false);
        destination.setMaxLines(2); c.addView(destination);
        c.addView(space(10));

        String distance=o.has("distance_to_pickup_km")
                ? String.format(Locale.getDefault(),"%.1f km",o.optDouble("distance_to_pickup_km",0)) : "—";
        String eta=o.has("eta_to_pickup_min") ? (o.optInt("eta_to_pickup_min",0)+" min") : "—";
        LinearLayout metrics=horizontal();
        LinearLayout km=vertical(Color.TRANSPARENT); km.addView(text("ATÉ O PASSAGEIRO",10,GRAY,true)); km.addView(text(distance,17,Color.WHITE,true));
        LinearLayout tm=vertical(Color.TRANSPARENT); tm.addView(text("PREVISÃO",10,GRAY,true)); tm.addView(text(eta,17,Color.WHITE,true));
        metrics.addView(km,new LinearLayout.LayoutParams(0,dp(48),1)); metrics.addView(tm,new LinearLayout.LayoutParams(0,dp(48),1));
        c.addView(metrics);

        double gross=o.optDouble("estimated_fare",o.optDouble("estimated_driver_earning",0));
        double earning=o.optDouble("estimated_driver_earning",gross);
        c.addView(text("VALOR ESTIMADO",11,GRAY,true));
        c.addView(text(privateMoney(gross),26,YELLOW,true));
        if(Math.abs(earning-gross)>0.009)c.addView(text("Seu ganho estimado: "+privateMoney(earning),13,Color.LTGRAY,true));
        c.addView(space(12));

        LinearLayout actions=horizontal();
        Button no=darkButton("RECUSAR");
        Button yes=primary("ACEITAR");
        actions.addView(no,new LinearLayout.LayoutParams(0,dp(60),1));
        actions.addView(spaceH(8));
        actions.addView(yes,new LinearLayout.LayoutParams(0,dp(60),1));
        c.addView(actions);
        operationBox.addView(c,wrap());

        yes.setOnClickListener(v->respond(o.optString("offer_id"),true));
        no.setOnClickListener(v->respond(o.optString("offer_id"),false));
        startOfferCountdown(timer);
        DriverMapRenderer.render(map,currentLocation,o,dp(5));
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderOffer v2.3 não encontrado')

# Ao responder, encerra som e contador.
pattern=r'''    private void respond\(String id,boolean accept\)\{.*?\n    \}\n(?=    private void renderRide\(JSONObject r\))'''
replacement=r'''    private void respond(String id,boolean accept){
        stopOfferCountdown();
        stopRideCallSound(true);
        io.execute(()->{try{
            DriverRepository.respondOffer(token,id,accept);
            ui.post(()->toast(accept?"Corrida aceita. Siga até o passageiro.":"Chamada recusada."));
            refreshOperation();
        }catch(Exception e){ui.post(()->toast(msg(e)));}});
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('respond v2.3 não encontrado')

# Fluxo de condução minimalista.
pattern=r'''    private void renderRide\(JSONObject r\) \{.*?\n    \}\n(?=    private void markGoingAndNavigate\(JSONObject ride\))'''
replacement=r'''    private void renderRide(JSONObject r) {
        stopOfferCountdown();
        stopRideCallSound(true);
        if(operationBox==null)return;
        operationBox.removeAllViews();
        String s=r.optString("status","accepted");
        operationTitle.setText(s.equals("accepted")?"INDO AO PASSAGEIRO":s.equals("driver_arriving")?"NO LOCAL DE EMBARQUE":"CORRIDA EM ANDAMENTO");

        LinearLayout c=card(DARK,Color.rgb(65,65,65));
        c.setPadding(dp(18),dp(18),dp(18),dp(18));
        c.addView(text("📍 EMBARQUE",11,GRAY,true));
        TextView pickup=text(r.optString("origin_label",""),15,Color.WHITE,true); pickup.setMaxLines(2); c.addView(pickup);
        c.addView(space(8));
        c.addView(text("🏁 DESTINO",11,GRAY,true));
        TextView destination=text(r.optString("destination_label",""),15,Color.LTGRAY,false); destination.setMaxLines(2); c.addView(destination);
        if(r.has("estimated_fare")){c.addView(space(8));c.addView(text("Valor estimado: "+privateMoney(r.optDouble("estimated_fare",0)),15,YELLOW,true));}
        c.addView(space(12));

        if(s.equals("accepted")){
            Button nav=darkButton("🧭 ABRIR NAVEGAÇÃO"); c.addView(nav,match(dp(56))); c.addView(space(9));
            Button arrived=primary("CHEGUEI AO LOCAL"); c.addView(arrived,match(dp(62)));
            nav.setOnClickListener(v->openNavigationToPassenger(r));
            arrived.setOnClickListener(v->advance(r.optString("id"),"arrived"));
        }else if(s.equals("driver_arriving")){
            int free=r.optInt("wait_free_seconds",300); double fee=r.optDouble("wait_fee_per_minute",0.50);
            c.addView(text("⏱ Tolerância de espera: "+Math.max(0,free/60)+" min · depois "+money(fee)+"/min",13,YELLOW,true));
            c.addView(space(9));
            Button nav=darkButton("🧭 VER LOCAL DE EMBARQUE"); c.addView(nav,match(dp(54))); c.addView(space(9));
            Button start=primary("INICIAR CORRIDA"); c.addView(start,match(dp(64)));
            nav.setOnClickListener(v->openNavigationToPassenger(r));
            start.setOnClickListener(v->advance(r.optString("id"),"start"));
        }else{
            double wait=r.optDouble("wait_charge_amount",0); if(wait>0)c.addView(text("Espera registrada: "+money(wait),13,YELLOW,true));
            Button nav=darkButton("🧭 NAVEGAR ATÉ O DESTINO"); c.addView(nav,match(dp(56))); c.addView(space(9));
            Button done=primary("FINALIZAR CORRIDA"); c.addView(done,match(dp(66)));
            nav.setOnClickListener(v->openNavigationToDestination(r));
            done.setOnClickListener(v->advance(r.optString("id"),"complete"));
        }
        operationBox.addView(c,wrap());
        DriverMapRenderer.render(map,currentLocation,r,dp(5));
        drawDriverRoadRoute(r);
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderRide final não encontrado')

# Home: rótulos mais diretos, preservando menu, carteira e mapa.
text=text.replace('primary(online?"● ONLINE — ficar offline":"○ OFFLINE — ficar online")','primary(online?"● VOCÊ ESTÁ ONLINE — FICAR OFFLINE":"FICAR ONLINE")',1)
text=text.replace('operationTitle = text(online?"Aguardando chamadas…":"Fique online para receber corridas."','operationTitle = text(online?"Aguardando chamadas…":"Fique online para começar."',1)

# Ganhos diário/semanal: cálculo somente sobre o histórico já baixado.
old='''double total=0;int completed=0;for(int i=0;i<history.length();i++){JSONObject r=history.optJSONObject(i);if(r!=null&&"completed".equals(r.optString("status"))){completed++;total+=r.optDouble("final_fare",0);}}double bal=w.optDouble("operational_balance",balance);String mode=w.optString("billing_mode",billingMode);double finalTotal=total;int finalCompleted=completed;ui.post(()->{body.removeView(loading);LinearLayout c=card(DARK,Color.rgb(55,55,55));c.addView(text("Saldo operacional",13,GRAY,false));c.addView(text(money(bal),30,YELLOW,true));c.addView(space(10));c.addView(text(mode.equals("monthly")?"Cobrança: mensalidade":"Cobrança: taxa por corrida",14,Color.WHITE,true));body.addView(c);body.addView(space(10));LinearLayout stats=card(DARK,Color.rgb(55,55,55));stats.addView(text("Últimas corridas concluídas: "+finalCompleted,15,Color.WHITE,true));stats.addView(text("Valor bruto somado no histórico: "+money(finalTotal),14,GRAY,false));body.addView(stats);'''
new='''double total=0,today=0,week=0;int completed=0,todayCount=0;java.time.LocalDate nowDate=java.time.LocalDate.now();java.time.LocalDate weekStart=nowDate.minusDays(6);for(int i=0;i<history.length();i++){JSONObject r=history.optJSONObject(i);if(r!=null&&"completed".equals(r.optString("status"))){completed++;double value=r.optDouble("final_fare",0);total+=value;String rawDate=r.optString("completed_at","");if(rawDate.length()>=10)try{java.time.LocalDate d=java.time.LocalDate.parse(rawDate.substring(0,10));if(d.equals(nowDate)){today+=value;todayCount++;}if(!d.isBefore(weekStart)&&!d.isAfter(nowDate))week+=value;}catch(Exception ignored){}}}double bal=w.optDouble("operational_balance",balance);String mode=w.optString("billing_mode",billingMode);double finalTotal=total,finalToday=today,finalWeek=week;int finalCompleted=completed,finalTodayCount=todayCount;ui.post(()->{body.removeView(loading);LinearLayout daily=card(DARK,Color.rgb(87,73,0));daily.addView(text("HOJE",12,YELLOW,true));daily.addView(text(privateMoney(finalToday),30,Color.WHITE,true));daily.addView(text(finalTodayCount+" corrida(s) concluída(s)",13,GRAY,false));body.addView(daily);body.addView(space(10));LinearLayout weekly=card(DARK,Color.rgb(55,55,55));weekly.addView(text("ÚLTIMOS 7 DIAS",12,GRAY,true));weekly.addView(text(privateMoney(finalWeek),24,YELLOW,true));body.addView(weekly);body.addView(space(10));LinearLayout c=card(DARK,Color.rgb(55,55,55));c.addView(text("Saldo operacional",13,GRAY,false));c.addView(text(privateMoney(bal),30,YELLOW,true));c.addView(space(10));c.addView(text(mode.equals("monthly")?"Cobrança: mensalidade":"Cobrança: taxa por corrida",14,Color.WHITE,true));body.addView(c);body.addView(space(10));LinearLayout stats=card(DARK,Color.rgb(55,55,55));stats.addView(text("Corridas concluídas no histórico: "+finalCompleted,15,Color.WHITE,true));stats.addView(text("Valor bruto no histórico: "+privateMoney(finalTotal),14,GRAY,false));body.addView(stats);'''
if old in text:
    text=text.replace(old,new,1)
elif 'ÚLTIMOS 7 DIAS' not in text:
    raise SystemExit('showEarnings final não encontrado')

# Contador não pode sobreviver a navegação/logout/destruição.
text=text.replace('    private void showLogin() {\n        stopRideCallSound(true);','    private void showLogin() {\n        stopOfferCountdown();\n        stopRideCallSound(true);',1)
text=text.replace('    private void logout(){stopRideCallSound(true);','    private void logout(){stopOfferCountdown();stopRideCallSound(true);',1)
text=text.replace('        destroyed = true; stopRideCallSound(true);','        destroyed = true; stopOfferCountdown(); stopRideCallSound(true);',1)

# Versão.
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.4-prime'",build,count=1)

main.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v2.4 PRIME: UI comercial, contador de chamada e ganhos diário/semanal aplicados.')
