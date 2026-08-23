from pathlib import Path
import re

root=Path('app')
main=root/'src/main/java/com/clickgo/motorista/MainActivity.java'
repo_path=root/'src/main/java/com/clickgo/motorista/DriverRepository.java'
gradle=root/'build.gradle'
push_reg=root/'src/main/java/com/clickgo/motorista/PushRegistration.java'
push_service=root/'src/main/java/com/clickgo/motorista/ClickGoMessagingService.java'

text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=gradle.read_text(encoding='utf-8')

# Atualiza Firebase para a linha recomendada em agosto/2026.
build=build.replace("com.google.firebase:firebase-bom:33.16.0","com.google.firebase:firebase-bom:34.17.0")

# Torna o refresh do token FCM independente do nome interno das SharedPreferences da Activity.
if push_reg.exists():
    pr=push_reg.read_text(encoding='utf-8')
    anchor='''        ensureChannel(activity);\n'''
    extra='''        ensureChannel(activity);\n        activity.getSharedPreferences("clickgo_push",Context.MODE_PRIVATE).edit().putString("access_token",accessToken==null?"":accessToken).apply();\n'''
    if 'putString("access_token"' not in pr and anchor in pr:
        pr=pr.replace(anchor,extra,1)
    push_reg.write_text(pr,encoding='utf-8')
if push_service.exists():
    ps=push_service.read_text(encoding='utf-8')
    ps=ps.replace('getSharedPreferences("MainActivity",MODE_PRIVATE).getString("access_token",null)','getSharedPreferences("clickgo_push",MODE_PRIVATE).getString("access_token",null)')
    push_service.write_text(ps,encoding='utf-8')

# RPCs financeiros do taxímetro.
repo_anchor='''    public static JSONArray taximeterHistory(String token, String userId) throws Exception {\n'''
repo_methods='''    public static JSONObject taximeterFinancialSummary(String token) throws Exception {\n        return new JSONObject(ApiClient.rpc("get_my_taximeter_financial_summary", new JSONObject(), token));\n    }\n\n    public static JSONObject settleTaximeterPendingFees(String token) throws Exception {\n        return new JSONObject(ApiClient.rpc("settle_driver_taximeter_pending_fees", new JSONObject().put("p_driver_id", JSONObject.NULL), token));\n    }\n\n'''
if 'taximeterFinancialSummary' not in repo:
    if repo_anchor not in repo: raise SystemExit('taximeterHistory não encontrado no DriverRepository')
    repo=repo.replace(repo_anchor,repo_methods+repo_anchor,1)
repo_path.write_text(repo,encoding='utf-8')

# Carrega o resumo financeiro junto com o taxímetro.
old_load='''            JSONObject running=DriverRepository.runningTaximeter(token,userId);\n            JSONArray categories=DriverRepository.taximeterCategories(token);\n            JSONArray history=DriverRepository.taximeterHistory(token,userId);\n            ui.post(()->{content.removeAllViews();if(running!=null)renderRunningTaximeter(content,running);else renderFreeTaximeter(content,categories);renderTaximeterHistory(content,history);});\n'''
new_load='''            JSONObject running=DriverRepository.runningTaximeter(token,userId);\n            JSONArray categories=DriverRepository.taximeterCategories(token);\n            JSONArray history=DriverRepository.taximeterHistory(token,userId);\n            JSONObject financial=DriverRepository.taximeterFinancialSummary(token);\n            ui.post(()->{content.removeAllViews();if(running!=null)renderRunningTaximeter(content,running);else renderFreeTaximeter(content,categories);renderTaximeterFinancial(content,financial);renderTaximeterHistory(content,history);});\n'''
if old_load in text:
    text=text.replace(old_load,new_load,1)
elif 'renderTaximeterFinancial(content,financial)' not in text:
    raise SystemExit('loadTaximeterScreen não encontrado')

# Mensagem de fechamento com bruto/taxa/situação.
old_finish='''    private void finishTaximeter(String payment){\n        Location loc=bestLocation();if(loc==null){toast("GPS indisponível para finalizar.");return;}String id=taximeterSessionId;io.execute(()->{try{JSONObject r=DriverRepository.finishTaximeter(token,id,loc.getLatitude(),loc.getLongitude(),payment);ui.post(()->{toast("Taxímetro finalizado em "+money(r.optDouble("final_amount",0))+".");taximeterSessionId="";showTaximeter();});}catch(Exception e){ui.post(()->toast(msg(e)));}});\n    }\n'''
new_finish='''    private void finishTaximeter(String payment){\n        Location loc=bestLocation();if(loc==null){toast("GPS indisponível para finalizar.");return;}String id=taximeterSessionId;io.execute(()->{try{JSONObject r=DriverRepository.finishTaximeter(token,id,loc.getLatitude(),loc.getLongitude(),payment);JSONObject fin=r.optJSONObject("financial");double fee=fin==null?0:fin.optDouble("fee_amount",0);String feeStatus=fin==null?"":fin.optString("status","");String notice=fee>0?("Taxímetro "+money(r.optDouble("final_amount",0))+" · taxa "+money(fee)+(feeStatus.equals("pending")?" pendente.":" quitada.")):("Taxímetro finalizado em "+money(r.optDouble("final_amount",0))+" · sem taxa operacional.");ui.post(()->{toast(notice);taximeterSessionId="";showTaximeter();});}catch(Exception e){ui.post(()->toast(msg(e)));}});\n    }\n'''
if old_finish in text:
    text=text.replace(old_finish,new_finish,1)
elif 'feeStatus.equals("pending")' not in text:
    raise SystemExit('finishTaximeter não encontrado')

# Card financeiro e quitação de pendências.
history_anchor='''    private void renderTaximeterHistory(LinearLayout content,JSONArray rows){\n'''
finance_methods=r'''    private void renderTaximeterFinancial(LinearLayout content,JSONObject fin){
        if(fin==null)return;content.addView(space(12));LinearLayout c=card(DARK,Color.rgb(87,73,0));c.addView(text("FINANCEIRO DO TAXÍMETRO · 30 DIAS",12,YELLOW,true));JSONObject rule=fin.optJSONObject("effective_rule");String mode=rule==null?"none":rule.optString("fee_mode","none");double ruleValue=rule==null?0:rule.optDouble("fee_value",0);String ruleLabel=mode.equals("percentage")?String.format(Locale.getDefault(),"%.2f%% por corrida",ruleValue):mode.equals("fixed")?money(ruleValue)+" por corrida":"Sem taxa";c.addView(text("Regra atual: "+ruleLabel,14,Color.WHITE,true));c.addView(text("Bruto: "+privateMoney(fin.optDouble("gross_amount",0))+" · taxas: "+privateMoney(fin.optDouble("fee_amount",0)),13,GRAY,false));c.addView(text("Líquido: "+privateMoney(fin.optDouble("driver_net_amount",0))+" · carteira: "+privateMoney(fin.optDouble("wallet_balance",0)),13,Color.LTGRAY,false));double pending=fin.optDouble("pending_amount",0);c.addView(text("Pendente: "+privateMoney(pending),14,pending>0?Color.rgb(251,191,36):Color.rgb(74,222,128),true));if(pending>0){Button pay=primary("Quitar pendências com saldo da carteira");c.addView(space(8));c.addView(pay,match(dp(54)));pay.setOnClickListener(v->settleTaximeterPendingFees());}content.addView(c);
    }

    private void settleTaximeterPendingFees(){
        io.execute(()->{try{JSONObject r=DriverRepository.settleTaximeterPendingFees(token);int count=r.optInt("settled_count",0);double total=r.optDouble("settled_amount",0);double pending=r.optDouble("pending_amount",0);ui.post(()->{toast(count>0?(count+" taxa(s) quitada(s): "+money(total)):(pending>0?"Saldo insuficiente para a próxima pendência.":"Não há taxas pendentes."));showTaximeter();});}catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

'''
if 'private void renderTaximeterFinancial' not in text:
    if history_anchor not in text: raise SystemExit('renderTaximeterHistory não encontrado')
    text=text.replace(history_anchor,finance_methods+history_anchor,1)

# v2.1 PRIME.
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.1-prime'",build,count=1)

gradle.write_text(build,encoding='utf-8')
main.write_text(text,encoding='utf-8')
print('Motorista v2.1 PRIME: financeiro do taxímetro + FCM BoM 34.17.0 + refresh de token robusto.')
