from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Garante que a home encerre qualquer polling visual anterior antes de redesenhar o taxímetro.
home_stop='''        stopPolling();\n        releaseMap();\n'''
if home_stop in text and 'stopPolling();\n        stopTaximeterUiPolling();\n        releaseMap();' not in text:
    text=text.replace(home_stop,'''        stopPolling();\n        stopTaximeterUiPolling();\n        releaseMap();\n''',1)

# Taxímetro compacto passa a fazer parte da tela inicial, acima do botão ONLINE/OFFLINE.
anchor='''        bottom.addView(walletRow);\n        bottom.addView(space(8));\n\n        Button onlineBtn=primary(online?"FICAR OFFLINE":"FICAR ONLINE");\n'''
replacement='''        bottom.addView(walletRow);\n        bottom.addView(space(8));\n\n        LinearLayout homeTaximeter=card(Color.rgb(250,250,250),Color.rgb(225,225,225));\n        homeTaximeter.setPadding(dp(12),dp(10),dp(12),dp(10));\n        homeTaximeter.addView(text("TAXÍMETRO",11,Color.DKGRAY,true));\n        homeTaximeter.addView(text("Carregando…",14,BLACK,true));\n        bottom.addView(homeTaximeter);\n        bottom.addView(space(9));\n\n        Button onlineBtn=primary(online?"FICAR OFFLINE":"FICAR ONLINE");\n'''
if anchor not in text:
    raise SystemExit('Âncora da home para inserir taxímetro não encontrada')
text=text.replace(anchor,replacement,1)

# Carrega o estado real do taxímetro assim que a tela inicial é mostrada.
load_anchor='''        setContentView(root);\n        loadDriverHomeAd(adSlot);\n        if(online){startLocationWatch();startPolling();}else DriverMapRenderer.render(map,currentLocation,null,dp(5));\n'''
load_replacement='''        setContentView(root);\n        loadDriverHomeAd(adSlot);\n        loadHomeTaximeter(homeTaximeter);\n        if(online){startLocationWatch();startPolling();}else DriverMapRenderer.render(map,currentLocation,null,dp(5));\n'''
if load_anchor not in text:
    raise SystemExit('Carregamento final da home não encontrado')
text=text.replace(load_anchor,load_replacement,1)

# Renderização compacta do taxímetro na home. As tarifas são sempre as da categoria criada/editada pelo franqueado.
helper_anchor='''    private void toggleOnline() {\n'''
helpers=r'''    private void loadHomeTaximeter(LinearLayout box){
        if(box==null)return;
        box.removeAllViews();
        box.addView(text("TAXÍMETRO",11,Color.DKGRAY,true));
        if(!"approved".equalsIgnoreCase(driverStatus)){
            box.addView(text("Disponível após aprovação do cadastro",14,Color.DKGRAY,true));
            return;
        }
        box.addView(text("Carregando…",14,BLACK,true));
        io.execute(()->{try{
            JSONObject running=DriverRepository.runningTaximeter(token,userId);
            JSONArray categories=DriverRepository.taximeterCategories(token);
            ui.post(()->renderHomeTaximeter(box,running,categories));
        }catch(Exception e){ui.post(()->{box.removeAllViews();box.addView(text("TAXÍMETRO",11,Color.DKGRAY,true));box.addView(text("Não foi possível carregar o taxímetro",14,Color.DKGRAY,true));});}});
    }

    private void renderHomeTaximeter(LinearLayout box,JSONObject running,JSONArray categories){
        if(box==null)return;
        box.removeAllViews();
        box.addView(text("TAXÍMETRO",11,Color.DKGRAY,true));
        if(running==null){
            TextView free=text("LIVRE",24,Color.rgb(22,163,74),true);box.addView(free);
            int count=categories==null?0:categories.length();
            box.addView(text(count>0?(count+" categoria(s) liberada(s) · tarifas definidas pelo franqueado"):"Nenhuma categoria liberada para taxímetro",12,Color.DKGRAY,false));
            if(count>0){Button open=primary("INICIAR TAXÍMETRO");open.setOnClickListener(v->showTaximeter());box.addView(space(7));box.addView(open,match(dp(48)));}
            return;
        }
        online=false;
        taximeterSessionId=running.optString("id",taximeterSessionId);
        box.addView(text("OCUPADO",15,Color.rgb(217,148,0),true));
        TextView amount=text(privateMoney(running.optDouble("current_amount",0)),30,BLACK,true);box.addView(amount);
        TextView meta=text(taximeterMeta(running.optDouble("distance_m",0),running.optInt("elapsed_seconds",0),running.optDouble("multiplier",1)),12,Color.DKGRAY,true);box.addView(meta);
        box.addView(text("Base "+privateMoney(running.optDouble("base_fare",0))+" · "+privateMoney(running.optDouble("price_per_km",0))+"/km · "+privateMoney(running.optDouble("price_per_minute",0))+"/min",11,Color.DKGRAY,false));
        Button open=primary("ABRIR / FINALIZAR TAXÍMETRO");open.setOnClickListener(v->showTaximeter());box.addView(space(7));box.addView(open,match(dp(48)));
        startTaximeterUiPolling(taximeterSessionId,amount,meta);
    }

'''
if 'private void loadHomeTaximeter(' not in text:
    if helper_anchor not in text: raise SystemExit('toggleOnline não encontrado')
    text=text.replace(helper_anchor,helpers+helper_anchor,1)

# Ao iniciar o taxímetro, o backend já deixa o motorista offline; voltamos para a home com o valor rodando nela.
start_old='''ui.post(()->{toast("Taxímetro iniciado. Maçaneta em OCUPADO.");showTaximeter();});'''
start_new='''online=false;ui.post(()->{toast("Taxímetro iniciado. Você ficou offline para novas chamadas.");showHome();});'''
if start_old not in text:
    raise SystemExit('Retorno do início do taxímetro não encontrado')
text=text.replace(start_old,start_new,1)

# Após finalizar/cancelar, retorna à tela inicial com o taxímetro novamente em LIVRE.
finish_old='''ui.post(()->{toast(notice);taximeterSessionId="";showTaximeter();});'''
finish_new='''ui.post(()->{toast(notice);taximeterSessionId="";showHome();});'''
if finish_old in text:text=text.replace(finish_old,finish_new,1)

cancel_old='''ui.post(()->{taximeterSessionId="";toast("Taxímetro cancelado. Maçaneta em LIVRE.");showTaximeter();});'''
cancel_new='''ui.post(()->{taximeterSessionId="";toast("Taxímetro cancelado. Maçaneta em LIVRE.");showHome();});'''
if cancel_old in text:text=text.replace(cancel_old,cancel_new,1)

# Validações estruturais da v3.8.
for required in ['loadHomeTaximeter(homeTaximeter)','ABRIR / FINALIZAR TAXÍMETRO','tarifas definidas pelo franqueado','showHome();']:
    if required not in text: raise SystemExit('Taxímetro na home incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.8-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v3.8 PRIME: taxímetro ativo na tela inicial e tarifas controladas pelo franqueado.')
