from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')

repo=repo.replace('rides?driver_id=eq." + userId + "&status=in.(accepted,driver_arriving,in_progress)&select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng&limit=1','rides?driver_id=eq." + userId + "&status=in.(accepted,driver_arriving,in_progress)&select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,arrived_at,wait_free_seconds,wait_fee_per_minute,wait_charge_amount&limit=1')
repo=repo.replace('rides?driver_id=eq." + userId + "&status=in.(completed,cancelled)&select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,completed_at,cancelled_at&order=requested_at.desc&limit=50','rides?driver_id=eq." + userId + "&status=in.(completed,cancelled)&select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,completed_at,cancelled_at,origin_lat,origin_lng,destination_lat,destination_lng,arrived_lat,arrived_lng,started_lat,started_lng,completed_lat,completed_lng,wait_charge_amount&order=requested_at.desc&limit=50')
repo_path.write_text(repo,encoding='utf-8')

if 'private boolean showMoney' not in text:
    text=text.replace('    private boolean destroyed;\n','    private boolean destroyed;\n    private boolean showMoney = true;\n',1)

head='''        top.addView(id,new LinearLayout.LayoutParams(0,dp(58),1)); Button menuBtn = darkButton("☰ Menu"); top.addView(menuBtn,new LinearLayout.LayoutParams(dp(96),dp(46))); root.addView(top); root.addView(space(14));\n'''
new_head='''        top.addView(id,new LinearLayout.LayoutParams(0,dp(58),1)); Button eyeBtn = darkButton(showMoney ? "👁" : "🙈"); top.addView(eyeBtn,new LinearLayout.LayoutParams(dp(58),dp(46))); top.addView(spaceH(6)); Button menuBtn = darkButton("☰ Menu"); top.addView(menuBtn,new LinearLayout.LayoutParams(dp(96),dp(46))); root.addView(top); root.addView(space(14));\n'''
if head not in text: raise SystemExit('cabeçalho final não encontrado')
text=text.replace(head,new_head,1)
click='''        menuBtn.setOnClickListener(v -> showDriverMenu()); onlineBtn.setOnClickListener(v -> toggleOnline()); setContentView(scroll(root,BLACK));\n'''
new_click='''        eyeBtn.setOnClickListener(v -> { showMoney=!showMoney; getPreferences(MODE_PRIVATE).edit().putBoolean("show_money",showMoney).apply(); showHome(); }); menuBtn.setOnClickListener(v -> showDriverMenu()); onlineBtn.setOnClickListener(v -> toggleOnline()); setContentView(scroll(root,BLACK));\n'''
if click not in text: raise SystemExit('clique menu não encontrado')
text=text.replace(click,new_click,1)
text=text.replace('balance = w.optDouble("operational_balance",0); billingMode = w.optString("billing_mode","wallet_per_ride");','balance = w.optDouble("operational_balance",0); billingMode = w.optString("billing_mode","wallet_per_ride"); showMoney=getPreferences(MODE_PRIVATE).getBoolean("show_money",true);',1)
text=text.replace('"Ganho estimado "+money(o.optDouble("estimated_driver_earning",0))','"Ganho estimado "+privateMoney(o.optDouble("estimated_driver_earning",0))')

pattern=r'''    private void renderRide\(JSONObject r\) \{.*?\n    \}\n(?=    private void markGoingAndNavigate\(JSONObject ride\))'''
replacement=r'''    private void renderRide(JSONObject r) {
        if(operationBox==null)return;
        operationBox.removeAllViews();
        String s=r.optString("status","accepted");
        operationTitle.setText(s.equals("accepted")?"A caminho do embarque":s.equals("driver_arriving")?"Aguardando passageiro":"Corrida em andamento");
        LinearLayout c=card(DARK,Color.rgb(65,65,65));
        c.addView(text("Embarque: "+r.optString("origin_label",""),14,Color.WHITE,true));
        c.addView(text("Destino: "+r.optString("destination_label",""),14,GRAY,false));
        c.addView(space(10));
        if(s.equals("accepted")){
            Button nav=darkButton("🧭 Abrir navegação"); c.addView(nav,match(dp(54))); c.addView(space(8));
            Button arrived=primary("📍 Cheguei ao embarque"); c.addView(arrived,match(dp(58)));
            nav.setOnClickListener(v->openNavigationToPassenger(r)); arrived.setOnClickListener(v->advance(r.optString("id"),"arrived"));
        }else if(s.equals("driver_arriving")){
            int free=r.optInt("wait_free_seconds",300); double fee=r.optDouble("wait_fee_per_minute",0.50);
            c.addView(text("⏱ Tolerância: "+Math.max(0,free/60)+" min",14,YELLOW,true));
            c.addView(text("Depois: "+money(fee)+" por minuto iniciado",13,GRAY,false)); c.addView(space(8));
            Button nav=darkButton("🧭 Abrir navegação"); c.addView(nav,match(dp(54))); c.addView(space(8));
            Button start=primary("▶ Iniciar corrida"); c.addView(start,match(dp(58)));
            nav.setOnClickListener(v->openNavigationToPassenger(r)); start.setOnClickListener(v->advance(r.optString("id"),"start"));
        }else{
            double wait=r.optDouble("wait_charge_amount",0); if(wait>0)c.addView(text("Espera: "+money(wait),13,YELLOW,true));
            Button nav=darkButton("🧭 Navegar até destino"); c.addView(nav,match(dp(54))); c.addView(space(8));
            Button done=primary("Finalizar corrida"); c.addView(done,match(dp(58)));
            nav.setOnClickListener(v->openNavigationToDestination(r)); done.setOnClickListener(v->advance(r.optString("id"),"complete"));
        }
        operationBox.addView(c,wrap()); DriverMapRenderer.render(map,currentLocation,r,dp(5)); drawDriverRoadRoute(r);
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderRide v1.5 não encontrado')

# Acrescenta coordenadas principais no histórico já existente.
hist='''if(fare>0)c.addView(text("Valor: "+money(fare),15,YELLOW,true));body.addView(c);'''
hist_new='''c.addView(text("GPS origem: "+coords(r,"origin_lat","origin_lng"),12,GRAY,false));c.addView(text("GPS destino: "+coords(r,"destination_lat","destination_lng"),12,GRAY,false));c.addView(text("GPS chegada: "+coords(r,"arrived_lat","arrived_lng"),12,GRAY,false));c.addView(text("GPS início: "+coords(r,"started_lat","started_lng"),12,GRAY,false));c.addView(text("GPS fim: "+coords(r,"completed_lat","completed_lng"),12,GRAY,false));if(fare>0)c.addView(text("Valor: "+privateMoney(fare),15,YELLOW,true));body.addView(c);'''
if hist not in text: raise SystemExit('histórico final não encontrado')
text=text.replace(hist,hist_new,1)

text=text.replace('private String walletLabel(){return billingMode.equals("monthly")?"Plano mensal":"Carteira operacional: "+money(balance);}','private String walletLabel(){return billingMode.equals("monthly")?"Plano mensal":"Carteira operacional: "+privateMoney(balance);}')
anchor='''    private String firstName(String v){'''
helpers='''    private String privateMoney(double v){return showMoney?money(v):"R$ ••••";}\n    private String coords(JSONObject r,String a,String b){if(r==null||r.isNull(a)||r.isNull(b))return "—";return String.format(Locale.getDefault(),"%.6f, %.6f",r.optDouble(a),r.optDouble(b));}\n'''
if anchor not in text: raise SystemExit('helper anchor não encontrado')
text=text.replace(anchor,helpers+anchor,1)

build_path=Path('app/build.gradle'); build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.6-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
main.write_text(text,encoding='utf-8')
print('Motorista v1.6 PRIME aplicado.')
