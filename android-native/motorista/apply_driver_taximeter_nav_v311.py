from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
bubble_path=Path('app/src/main/java/com/clickgo/motorista/DriverFloatingBubbleService.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
bubble=bubble_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# 1) Estado auxiliar para início automático assim que o GPS estiver disponível.
# -----------------------------------------------------------------------------
field='    private String taximeterSessionId = "";\n'
if 'private String pendingTaximeterCategoryId' not in text:
    if field not in text: raise SystemExit('Campo taximeterSessionId não encontrado')
    text=text.replace(field,field+'    private String pendingTaximeterCategoryId = "";\n    private int pendingTaximeterGpsAttempts;\n',1)

# -----------------------------------------------------------------------------
# 2) Barra rápida fixa: Home + Taxímetro.
# -----------------------------------------------------------------------------
anchor='    private void showTaximeter(){\n'
quick_nav=r'''    private LinearLayout driverQuickNav(boolean homeSelected){
        LinearLayout row=horizontal();row.setGravity(Gravity.CENTER);
        Button home=darkButton("⌂  Home");
        Button meter=darkButton("🚕  Taxímetro");
        if(homeSelected){home.setBackground(round(YELLOW,16,YELLOW));home.setTextColor(BLACK);}
        else{meter.setBackground(round(YELLOW,16,YELLOW));meter.setTextColor(BLACK);}
        home.setOnClickListener(v->showHome());
        meter.setOnClickListener(v->showTaximeter());
        row.addView(home,new LinearLayout.LayoutParams(0,dp(54),1));
        row.addView(spaceH(8));
        row.addView(meter,new LinearLayout.LayoutParams(0,dp(54),1));
        return row;
    }

'''
if 'private LinearLayout driverQuickNav(' not in text:
    if anchor not in text: raise SystemExit('showTaximeter não encontrado para navegação')
    text=text.replace(anchor,quick_nav+anchor,1)

# Coloca os ícones na Home, imediatamente antes do ONLINE/OFFLINE.
home_anchor='''        bottom.addView(homeTaximeter);\n        bottom.addView(space(9));\n\n        Button onlineBtn=primary(online?"FICAR OFFLINE":"FICAR ONLINE");\n'''
home_repl='''        bottom.addView(homeTaximeter);\n        bottom.addView(space(9));\n        bottom.addView(driverQuickNav(true));\n        bottom.addView(space(10));\n\n        Button onlineBtn=primary(online?"FICAR OFFLINE":"FICAR ONLINE");\n'''
if home_anchor not in text: raise SystemExit('Âncora Home/Taxímetro não encontrada')
text=text.replace(home_anchor,home_repl,1)

# -----------------------------------------------------------------------------
# 3) Tela completa do taxímetro com atalho Home + Taxímetro e GPS ativo.
# -----------------------------------------------------------------------------
pattern=re.compile(r'''    private void showTaximeter\(\)\{.*?\n    \}\n\n(?=    private void loadTaximeterScreen)''',re.S)
replacement=r'''    private void showTaximeter(){
        stopPolling();stopTaximeterUiPolling();releaseMap();
        ensureTaximeterGps();
        LinearLayout body=pageShell("Taxímetro / Maçaneta","Modo de corrida livre. Usa a tarifa da categoria autorizada pela franquia.");
        body.addView(driverQuickNav(false));body.addView(space(10));
        LinearLayout content=vertical(BLACK);body.addView(content);setContentView(scroll(body,BLACK));
        loadTaximeterScreen(content);
    }

'''
text,n=pattern.subn(replacement,text,count=1)
if n!=1: raise SystemExit('showTaximeter final não pôde ser atualizado')

# -----------------------------------------------------------------------------
# 4) GPS contínuo e início automático do taxímetro assim que houver posição.
# -----------------------------------------------------------------------------
start_pattern=re.compile(r'''    private void startTaximeter\(String categoryId\)\{.*?\n    \}\n\n(?=    private void renderRunningTaximeter)''',re.S)
start_replacement=r'''    private Location taximeterLocation(){
        if(currentLocation!=null)return currentLocation;
        return bestLocation();
    }

    private void ensureTaximeterGps(){
        if(!hasLocation()){
            try{requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},REQ_LOCATION);}catch(Exception ignored){}
            return;
        }
        startLocationWatch();
    }

    private void startTaximeter(String categoryId){
        if(categoryId==null||categoryId.isBlank()){toast("Categoria inválida.");return;}
        pendingTaximeterCategoryId=categoryId;pendingTaximeterGpsAttempts=0;
        ensureTaximeterGps();
        retryPendingTaximeterStart();
    }

    private void retryPendingTaximeterStart(){
        if(destroyed||pendingTaximeterCategoryId==null||pendingTaximeterCategoryId.isBlank())return;
        if(!hasLocation())return;
        Location loc=taximeterLocation();
        if(loc==null){
            pendingTaximeterGpsAttempts++;
            if(pendingTaximeterGpsAttempts>=15){pendingTaximeterCategoryId="";toast("Não foi possível obter o GPS. Ative a localização e tente novamente.");return;}
            ui.postDelayed(this::retryPendingTaximeterStart,1000);
            return;
        }
        String categoryId=pendingTaximeterCategoryId;pendingTaximeterCategoryId="";
        doStartTaximeter(categoryId,loc);
    }

    private void doStartTaximeter(String categoryId,Location loc){
        io.execute(()->{try{
            JSONObject result=DriverRepository.startTaximeter(token,categoryId,loc.getLatitude(),loc.getLongitude());
            taximeterSessionId=result.optString("session_id","");online=false;
            ui.post(()->{stopRideCallSound(true);stopFloatingBubble();toast("Taxímetro iniciado. Você ficou offline para novas chamadas.");showHome();});
        }catch(Exception e){ui.post(()->toast(msg(e)));}});
    }

'''
text,n=start_pattern.subn(start_replacement,text,count=1)
if n!=1: raise SystemExit('startTaximeter final não pôde ser atualizado')

# Corrida OCUPADO sempre mantém localização ativa.
running_call='startTaximeterUiPolling(taximeterSessionId,amount,meta,session.optDouble("multiplier",1));'
if running_call not in text: raise SystemExit('Polling da tela completa não encontrado')
text=text.replace(running_call,'ensureTaximeterGps();'+running_call,1)

home_call='startTaximeterUiPolling(taximeterSessionId,amount,meta,running.optDouble("multiplier",1));'
if home_call not in text: raise SystemExit('Polling do taxímetro na Home não encontrado')
text=text.replace(home_call,'ensureTaximeterGps();'+home_call,1)

# Polling usa a posição realmente acompanhada pelo app e deixa de falhar silenciosamente.
poll_pattern=re.compile(r'''    private void startTaximeterUiPolling\(String sessionId,TextView amount,TextView meta,double multiplier\)\{.*?\n    \}\n\n(?=    private void stopTaximeterUiPolling)''',re.S)
poll_replacement=r'''    private void startTaximeterUiPolling(String sessionId,TextView amount,TextView meta,double multiplier){
        stopTaximeterUiPolling();ensureTaximeterGps();
        taximeterPoll=new Runnable(){public void run(){
            if(destroyed||sessionId==null||sessionId.isBlank())return;
            Location loc=taximeterLocation();
            if(loc==null){if(meta!=null)meta.setText("Obtendo GPS para atualizar o taxímetro…");ui.postDelayed(this,1200);return;}
            io.execute(()->{try{
                JSONObject r=DriverRepository.tickTaximeter(token,sessionId,loc.getLatitude(),loc.getLongitude());
                ui.post(()->{if(amount!=null)amount.setText(privateMoney(r.optDouble("amount",0)));if(meta!=null)meta.setText(taximeterMeta(r.optDouble("distance_m",0),r.optInt("elapsed_seconds",0),multiplier));});
            }catch(Exception e){ui.post(()->{if(meta!=null)meta.setText("Falha ao atualizar · "+msg(e));});}});
            ui.postDelayed(this,5000);
        }};
        ui.post(taximeterPoll);
    }

'''
text,n=poll_pattern.subn(poll_replacement,text,count=1)
if n!=1: raise SystemExit('Polling do taxímetro não pôde ser atualizado')

# Finalização usa a posição viva, não apenas lastKnownLocation.
text=text.replace('Location loc=bestLocation();if(loc==null){toast("GPS indisponível para finalizar.");return;}String id=taximeterSessionId;',
                  'Location loc=taximeterLocation();if(loc==null){ensureTaximeterGps();toast("Obtendo GPS para finalizar. Tente novamente em instantes.");return;}String id=taximeterSessionId;',1)

# Se o menu for aberto durante o taxímetro, encerra apenas o polling visual; a sessão continua.
text=text.replace('    private void showDriverMenu(){\n        stopPolling(); releaseMap();',
                  '    private void showDriverMenu(){\n        stopPolling(); stopTaximeterUiPolling(); releaseMap();',1)

# Permissão concedida durante a tentativa de iniciar taxímetro retoma automaticamente.
perm_pattern=re.compile(r'''    @Override public void onRequestPermissionsResult\(int r,String\[\] p,int\[\] g\)\{.*?\}\n''',re.S)
perm_replacement='''    @Override public void onRequestPermissionsResult(int r,String[] p,int[] g){
        super.onRequestPermissionsResult(r,p,g);
        if(r==REQ_LOCATION&&g.length>0&&g[0]==PackageManager.PERMISSION_GRANTED){startLocationWatch();if(pendingTaximeterCategoryId!=null&&!pendingTaximeterCategoryId.isBlank())ui.postDelayed(this::retryPendingTaximeterStart,500);}
        else if(r==REQ_LOCATION)toast("O GPS é necessário para corridas e para o taxímetro.");
    }
'''
text,n=perm_pattern.subn(perm_replacement,text,count=1)
if n!=1: raise SystemExit('onRequestPermissionsResult não encontrado')

# -----------------------------------------------------------------------------
# 5) A bolinha GO deve sempre levar à HOME, nunca reabrir a tela anterior.
# -----------------------------------------------------------------------------
old_open='Intent open=new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP);'
new_open='Intent open=new Intent(this,MainActivity.class).putExtra("clickgo_open_home",true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP);'
if old_open not in bubble: raise SystemExit('PendingIntent da bolinha não encontrado')
bubble=bubble.replace(old_open,new_open,1)

old_method='private void openApp(){try{startActivity(new Intent(this,MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP));}catch(Exception ignored){}}'
new_method='private void openApp(){try{startActivity(new Intent(this,MainActivity.class).putExtra("clickgo_open_home",true).addFlags(Intent.FLAG_ACTIVITY_NEW_TASK|Intent.FLAG_ACTIVITY_SINGLE_TOP|Intent.FLAG_ACTIVITY_CLEAR_TOP));}catch(Exception ignored){}}'
if old_method not in bubble: raise SystemExit('Clique da bolinha não encontrado')
bubble=bubble.replace(old_method,new_method,1)

# Activity já aberta recebe o clique da bolinha e reconstrói a Home.
if 'protected void onNewIntent(android.content.Intent intent)' not in text:
    destroy_anchor='    @Override protected void onDestroy() {\n'
    method='''    @Override protected void onNewIntent(android.content.Intent intent) {
        super.onNewIntent(intent);setIntent(intent);
        if(intent!=null&&intent.getBooleanExtra("clickgo_open_home",false)&&token!=null&&!token.isBlank())showHome();
    }

'''
    if destroy_anchor not in text: raise SystemExit('onDestroy não encontrado para onNewIntent')
    text=text.replace(destroy_anchor,method+destroy_anchor,1)

# Validações estruturais.
for required in ['driverQuickNav(true)','driverQuickNav(false)','⌂  Home','🚕  Taxímetro','ensureTaximeterGps();','retryPendingTaximeterStart','clickgo_open_home']:
    if required not in text and required not in bubble: raise SystemExit('v3.11 incompleta: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.11-prime'",build,count=1)

main_path.write_text(text,encoding='utf-8')
bubble_path.write_text(bubble,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.11 PRIME: taxímetro corrigido, Home/Taxímetro fixos e bolinha retorna à Home.')
