from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
text=main_path.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')

# Cliente REST/RPC do taxímetro.
repo_anchor='''    public static void advanceRide(String token, String rideId, String action) throws Exception {\n        ApiClient.rpc("advance_driver_ride", new JSONObject().put("p_ride_id", rideId).put("p_action", action), token);\n    }\n'''
repo_methods='''    public static JSONArray taximeterCategories(String token) throws Exception {\n        return new JSONArray(ApiClient.rpc("get_my_taximeter_categories", new JSONObject(), token));\n    }\n\n    public static JSONObject runningTaximeter(String token, String userId) throws Exception {\n        JSONArray rows = new JSONArray(ApiClient.restGet("driver_taximeter_sessions?driver_id=eq." + userId + "&status=eq.running&select=id,category_id,status,base_fare,price_per_km,price_per_minute,minimum_fare,multiplier,started_at,last_tick_at,distance_m,elapsed_seconds,current_amount&limit=1", token));\n        return rows.length() > 0 ? rows.getJSONObject(0) : null;\n    }\n\n    public static JSONObject startTaximeter(String token, String categoryId, double lat, double lng) throws Exception {\n        return new JSONObject(ApiClient.rpc("start_driver_taximeter", new JSONObject()\n                .put("p_category_id", categoryId).put("p_lat", lat).put("p_lng", lng), token));\n    }\n\n    public static JSONObject tickTaximeter(String token, String sessionId, double lat, double lng) throws Exception {\n        return new JSONObject(ApiClient.rpc("tick_driver_taximeter", new JSONObject()\n                .put("p_session_id", sessionId).put("p_lat", lat).put("p_lng", lng), token));\n    }\n\n    public static JSONObject finishTaximeter(String token, String sessionId, double lat, double lng, String payment) throws Exception {\n        return new JSONObject(ApiClient.rpc("finish_driver_taximeter", new JSONObject()\n                .put("p_session_id", sessionId).put("p_lat", lat).put("p_lng", lng).put("p_payment_method", payment), token));\n    }\n\n    public static JSONObject cancelTaximeter(String token, String sessionId) throws Exception {\n        return new JSONObject(ApiClient.rpc("cancel_driver_taximeter", new JSONObject().put("p_session_id", sessionId), token));\n    }\n\n    public static JSONArray taximeterHistory(String token, String userId) throws Exception {\n        return new JSONArray(ApiClient.restGet("driver_taximeter_sessions?driver_id=eq." + userId + "&status=in.(finished,cancelled)&select=id,status,started_at,ended_at,distance_m,elapsed_seconds,final_amount,payment_method&order=started_at.desc&limit=10", token));\n    }\n\n'''+repo_anchor
if 'public static JSONArray taximeterCategories' not in repo:
    if repo_anchor not in repo: raise SystemExit('advanceRide não encontrado no DriverRepository')
    repo=repo.replace(repo_anchor,repo_methods,1)
repo_path.write_text(repo,encoding='utf-8')

# Estado da tela de taxímetro. Não depende mais do antigo módulo PIN/SOS.
field_anchor='''    private boolean showMoney = true;\n'''
field_extra='''    private boolean showMoney = true;\n    private Runnable taximeterPoll;\n    private String taximeterSessionId = "";\n'''
if 'private Runnable taximeterPoll;' not in text:
    if field_anchor not in text: raise SystemExit('campo showMoney não encontrado')
    text=text.replace(field_anchor,field_extra,1)

# Entra no menu principal do motorista.
menu_anchor='''        body.addView(menuCard("🚘", "Corridas", "Corrida atual e tela principal", () -> showHome())); body.addView(space(9));\n'''
menu_extra=menu_anchor+'''        body.addView(menuCard("🚕", "Taxímetro / Maçaneta", "Corrida livre com bandeirada, km e minuto", () -> showTaximeter())); body.addView(space(9));\n'''
if '"Taxímetro / Maçaneta"' not in text:
    if menu_anchor not in text: raise SystemExit('menu Corridas não encontrado')
    text=text.replace(menu_anchor,menu_extra,1)

# Ao sair da tela do taxímetro, para apenas o polling visual; a sessão continua no servidor.
menu_head='''    private void showDriverMenu(){\n        stopPolling(); releaseMap();\n'''
if menu_head in text:
    text=text.replace(menu_head,'''    private void showDriverMenu(){\n        stopPolling(); stopTaximeterUiPolling(); releaseMap();\n''',1)

home_head='''    private void showHome() {\n'''
if home_head in text and 'private void showHome() {\n        stopTaximeterUiPolling();' not in text:
    text=text.replace(home_head,'''    private void showHome() {\n        stopTaximeterUiPolling();\n''',1)

# Tela completa do taxímetro clássico com maçaneta LIVRE/OCUPADO.
method_anchor='''    private void showDriverProfile(){\n'''
methods=r'''    private void showTaximeter(){
        stopPolling(); stopTaximeterUiPolling(); releaseMap();
        LinearLayout body=pageShell("Taxímetro / Maçaneta","Modo de corrida livre. Usa a tarifa da categoria autorizada pela franquia.");
        LinearLayout content=vertical(BLACK); body.addView(content); setContentView(scroll(body,BLACK));
        loadTaximeterScreen(content);
    }

    private void loadTaximeterScreen(LinearLayout content){
        content.removeAllViews();TextView loading=text("Carregando taxímetro…",14,GRAY,false);content.addView(loading);
        io.execute(()->{try{
            JSONObject running=DriverRepository.runningTaximeter(token,userId);
            JSONArray categories=DriverRepository.taximeterCategories(token);
            JSONArray history=DriverRepository.taximeterHistory(token,userId);
            ui.post(()->{content.removeAllViews();if(running!=null)renderRunningTaximeter(content,running);else renderFreeTaximeter(content,categories);renderTaximeterHistory(content,history);});
        }catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void renderFreeTaximeter(LinearLayout content,JSONArray categories){
        LinearLayout status=card(DARK,Color.rgb(22,101,52));status.addView(text("MAÇANETA",12,GRAY,true));status.addView(text("LIVRE",32,Color.rgb(74,222,128),true));status.addView(text("Gire a maçaneta para OCUPADO quando o passageiro embarcar.",13,GRAY,false));content.addView(status);content.addView(space(12));
        if(categories==null||categories.length()==0){content.addView(text("Nenhuma categoria autorizada para o taxímetro.",14,Color.rgb(248,113,113),true));return;}
        String[] labels=new String[categories.length()];for(int i=0;i<categories.length();i++){JSONObject c=categories.optJSONObject(i);labels[i]=c==null?"Categoria":c.optString("category_name","Categoria")+" · base "+money(c.optDouble("base_fare",0))+" · km "+money(c.optDouble("price_per_km",0))+" · min "+money(c.optDouble("price_per_minute",0));}
        android.widget.Spinner spinner=new android.widget.Spinner(this);android.widget.ArrayAdapter<String> adapter=new android.widget.ArrayAdapter<>(this,android.R.layout.simple_spinner_item,labels);adapter.setDropDownViewResource(android.R.layout.simple_spinner_dropdown_item);spinner.setAdapter(adapter);content.addView(spinner,match(dp(58)));content.addView(space(10));
        Button start=primary("↻ Girar maçaneta · OCUPADO");content.addView(start,match(dp(62)));start.setOnClickListener(v->{int ix=spinner.getSelectedItemPosition();JSONObject c=categories.optJSONObject(Math.max(0,ix));if(c==null)return;confirmStartTaximeter(c.optString("category_id",""));});
    }

    private void confirmStartTaximeter(String categoryId){
        if(categoryId==null||categoryId.isBlank()){toast("Categoria inválida.");return;}
        new android.app.AlertDialog.Builder(this).setTitle("Iniciar taxímetro?").setMessage("A maçaneta mudará de LIVRE para OCUPADO e a cobrança começará pela tarifa configurada.").setNegativeButton("Cancelar",null).setPositiveButton("OCUPADO",(d,w)->startTaximeter(categoryId)).show();
    }

    private void startTaximeter(String categoryId){
        Location loc=bestLocation();if(loc==null){startLocationWatch();toast("Aguardando GPS. Tente novamente em alguns segundos.");return;}
        io.execute(()->{try{JSONObject result=DriverRepository.startTaximeter(token,categoryId,loc.getLatitude(),loc.getLongitude());taximeterSessionId=result.optString("session_id","");ui.post(()->{toast("Taxímetro iniciado. Maçaneta em OCUPADO.");showTaximeter();});}catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

    private void renderRunningTaximeter(LinearLayout content,JSONObject session){
        taximeterSessionId=session.optString("id",taximeterSessionId);
        LinearLayout status=card(DARK,YELLOW);status.addView(text("MAÇANETA",12,GRAY,true));status.addView(text("OCUPADO",29,YELLOW,true));content.addView(status);content.addView(space(10));
        LinearLayout meter=card(Color.rgb(5,5,5),YELLOW);TextView amount=text(privateMoney(session.optDouble("current_amount",0)),42,YELLOW,true);amount.setGravity(Gravity.CENTER);TextView meta=text(taximeterMeta(session.optDouble("distance_m",0),session.optInt("elapsed_seconds",0),session.optDouble("multiplier",1)),14,Color.LTGRAY,true);meta.setGravity(Gravity.CENTER);meter.addView(text("VALOR NO TAXÍMETRO",12,GRAY,true));meter.addView(amount);meter.addView(meta);content.addView(meter);content.addView(space(10));
        LinearLayout rates=card(DARK,Color.rgb(55,55,55));rates.addView(text("Bandeirada: "+privateMoney(session.optDouble("base_fare",0)),14,Color.WHITE,true));rates.addView(text("Por km: "+privateMoney(session.optDouble("price_per_km",0)),13,GRAY,false));rates.addView(text("Por minuto: "+privateMoney(session.optDouble("price_per_minute",0)),13,GRAY,false));rates.addView(text("Tarifa mínima: "+privateMoney(session.optDouble("minimum_fare",0)),13,GRAY,false));content.addView(rates);content.addView(space(10));
        Button finish=primary("↻ Finalizar · maçaneta LIVRE");Button cancel=darkButton("Cancelar sessão");cancel.setTextColor(Color.rgb(248,113,113));content.addView(finish,match(dp(60)));content.addView(space(8));content.addView(cancel,match(dp(54)));finish.setOnClickListener(v->chooseTaximeterPayment());cancel.setOnClickListener(v->confirmCancelTaximeter());startTaximeterUiPolling(taximeterSessionId,amount,meta);
    }

    private String taximeterMeta(double distanceM,int seconds,double multiplier){return String.format(Locale.getDefault(),"%02d:%02d:%02d · %.2f km · bandeira x%.2f",seconds/3600,(seconds%3600)/60,seconds%60,distanceM/1000.0,multiplier);}

    private void startTaximeterUiPolling(String sessionId,TextView amount,TextView meta){
        stopTaximeterUiPolling();taximeterPoll=new Runnable(){public void run(){if(destroyed||sessionId==null||sessionId.isBlank())return;Location loc=bestLocation();if(loc==null){ui.postDelayed(this,5000);return;}io.execute(()->{try{JSONObject r=DriverRepository.tickTaximeter(token,sessionId,loc.getLatitude(),loc.getLongitude());ui.post(()->{if(amount!=null)amount.setText(privateMoney(r.optDouble("amount",0)));if(meta!=null)meta.setText(taximeterMeta(r.optDouble("distance_m",0),r.optInt("elapsed_seconds",0),1));});}catch(Exception ignored){}});ui.postDelayed(this,5000);}};ui.post(taximeterPoll);
    }

    private void stopTaximeterUiPolling(){if(taximeterPoll!=null)ui.removeCallbacks(taximeterPoll);taximeterPoll=null;}

    private void chooseTaximeterPayment(){
        if(taximeterSessionId==null||taximeterSessionId.isBlank())return;String[] labels={"Dinheiro","PIX direto","Cartão / maquininha"};String[] values={"cash","pix_external","card_machine"};new android.app.AlertDialog.Builder(this).setTitle("Forma de pagamento").setItems(labels,(d,which)->finishTaximeter(values[which])).setNegativeButton("Cancelar",null).show();
    }

    private void finishTaximeter(String payment){
        Location loc=bestLocation();if(loc==null){toast("GPS indisponível para finalizar.");return;}String id=taximeterSessionId;io.execute(()->{try{JSONObject r=DriverRepository.finishTaximeter(token,id,loc.getLatitude(),loc.getLongitude(),payment);ui.post(()->{toast("Taxímetro finalizado em "+money(r.optDouble("final_amount",0))+".");taximeterSessionId="";showTaximeter();});}catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

    private void confirmCancelTaximeter(){if(taximeterSessionId==null||taximeterSessionId.isBlank())return;new android.app.AlertDialog.Builder(this).setTitle("Cancelar taxímetro?").setMessage("A sessão ficará registrada como cancelada.").setNegativeButton("Voltar",null).setPositiveButton("Cancelar sessão",(d,w)->cancelTaximeter()).show();}

    private void cancelTaximeter(){String id=taximeterSessionId;io.execute(()->{try{DriverRepository.cancelTaximeter(token,id);ui.post(()->{taximeterSessionId="";toast("Taxímetro cancelado. Maçaneta em LIVRE.");showTaximeter();});}catch(Exception e){ui.post(()->toast(msg(e)));}});}

    private void renderTaximeterHistory(LinearLayout content,JSONArray rows){
        if(rows==null||rows.length()==0)return;content.addView(space(16));content.addView(text("Últimos taxímetros",18,Color.WHITE,true));content.addView(space(8));for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));String status=r.optString("status","");c.addView(text(shortDate(r.optString("started_at","")),13,Color.WHITE,true));c.addView(text(String.format(Locale.getDefault(),"%.2f km · %s",r.optDouble("distance_m",0)/1000.0,taximeterMeta(0,r.optInt("elapsed_seconds",0),1).split(" · ")[0]),12,GRAY,false));c.addView(text(status.equals("finished")?privateMoney(r.optDouble("final_amount",0)):"cancelado",15,status.equals("finished")?YELLOW:GRAY,true));content.addView(c);content.addView(space(7));}
    }

'''
if 'private void showTaximeter()' not in text:
    if method_anchor not in text: raise SystemExit('showDriverProfile não encontrado para inserir taxímetro')
    text=text.replace(method_anchor,methods+method_anchor,1)

# v1.9 PRIME.
build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.9-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
main_path.write_text(text,encoding='utf-8')
print('Motorista v1.9 PRIME: taxímetro/maçaneta livre integrado ao menu sem dependência do módulo PIN/SOS.')
