from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# v2.37 PRIME
# - protege a abertura inicial/home contra excecoes sincronas que fechavam a Activity;
# - protege o mapa real do historico contra falha/morte do renderer WebView;
# - usa o smoke de rede ja existente para abrir um mapa de historico real durante CI;
# - o fallback de mapa mantem o app aberto mesmo quando WebView nao consegue renderizar.

# 1) Navegacao inicial e retorno para home com fallback seguro.
old_start = '        if (token == null || token.isBlank()) showLogin(); else showHome();\n'
if old_start in text:
    text = text.replace(old_start, '        openInitialPassengerScreenSafely();\n', 1)
elif 'openInitialPassengerScreenSafely();' not in text:
    raise SystemExit('v2.37: ponto de inicializacao nao encontrado')

helper_anchor = '    private void showLogin() {\n'
helpers = r'''    private void openInitialPassengerScreenSafely() {
        try {
            if (token == null || token.isBlank()) showLogin(); else showHome();
        } catch (Throwable fatal) {
            try { releaseMap(); } catch (Throwable ignored) {}
            try { stopRidePolling(); } catch (Throwable ignored) {}
            try { stopHomeDriverPolling(); } catch (Throwable ignored) {}
            try { stopPassengerLiveLocation(); } catch (Throwable ignored) {}
            token = null;
            try { getPreferences(MODE_PRIVATE).edit().remove("access_token").apply(); } catch (Throwable ignored) {}
            try { showLogin(); } catch (Throwable ignored) {}
            toast("O aplicativo recuperou a tela apos uma falha. Entre novamente se necessario.");
        }
    }

    private void safeShowHome() {
        if (destroyed) return;
        try {
            showHome();
        } catch (Throwable fatal) {
            try { releaseMap(); } catch (Throwable ignored) {}
            try { stopRidePolling(); } catch (Throwable ignored) {}
            try { stopHomeDriverPolling(); } catch (Throwable ignored) {}
            try { stopPassengerLiveLocation(); } catch (Throwable ignored) {}
            token = null;
            try { getPreferences(MODE_PRIVATE).edit().remove("access_token").apply(); } catch (Throwable ignored) {}
            try { showLogin(); } catch (Throwable ignored) {}
            toast("Nao foi possivel abrir a tela inicial. A sessao foi reiniciada com seguranca.");
        }
    }

'''
if 'private void openInitialPassengerScreenSafely()' not in text:
    if helper_anchor not in text:
        raise SystemExit('v2.37: ancora showLogin nao encontrada')
    text = text.replace(helper_anchor, helpers + helper_anchor, 1)

# Retornos recentes para a home devem passar pela protecao.
text = text.replace('        showHome();\n    }\n\n    private String jsEsc', '        safeShowHome();\n    }\n\n    private String jsEsc', 1)
text = text.replace('ui.post(this::showHome);', 'ui.post(this::safeShowHome);')

# 2) Mapa do historico: separar criacao do dialogo e tratar WebView renderer crash.
old_method = r'''    private void showPassengerHistoryMap(JSONObject ride){
        String rideId=ride.optString("id","");if(rideId.isBlank()){toast("Corrida inválida.");return;}
        io.execute(()->{try{
            JSONArray points=new JSONArray(ApiClient.restGet("ride_location_points?ride_id=eq."+rideId+"&select=lat,lng,phase,recorded_at&order=recorded_at.asc",token));
            String html=historyMapHtml(ride,points);
            ui.post(()->{
                android.webkit.WebView web=new android.webkit.WebView(this);android.webkit.WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
                web.setWebViewClient(new android.webkit.WebViewClient());web.setContentDescription("clickgo_history_real_map");
                AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Mapa da corrida").setView(web).setPositiveButton("Fechar",null).create();dialog.setOnDismissListener(d->{try{web.destroy();}catch(Exception ignored){}});dialog.show();
                if(dialog.getWindow()!=null)dialog.getWindow().setLayout(-1,(int)(getResources().getDisplayMetrics().heightPixels*0.82));
                web.loadDataWithBaseURL("https://click-go-ten.vercel.app/",html,"text/html","UTF-8",null);
            });
        }catch(Exception e){ui.post(()->toast(message(e)));}});
    }
'''
new_method = r'''    private void showHistoryMapDialog(String html){
        if(destroyed)return;
        try{
            final android.widget.FrameLayout holder=new android.widget.FrameLayout(this);
            final TextView fallback=text("Mapa temporariamente indisponivel.\nA corrida continua salva no seu historico.",14,GRAY,false);
            fallback.setGravity(Gravity.CENTER);fallback.setPadding(dp(22),dp(22),dp(22),dp(22));fallback.setVisibility(android.view.View.GONE);
            holder.addView(fallback,new android.widget.FrameLayout.LayoutParams(-1,-1));
            final android.webkit.WebView web=new android.webkit.WebView(this);
            android.webkit.WebSettings s=web.getSettings();s.setJavaScriptEnabled(true);s.setDomStorageEnabled(true);s.setAllowFileAccess(false);s.setAllowContentAccess(false);s.setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
            if(android.os.Build.VERSION.SDK_INT>=android.os.Build.VERSION_CODES.O)web.setRendererPriorityPolicy(android.webkit.WebView.RENDERER_PRIORITY_IMPORTANT,false);
            web.setContentDescription("clickgo_history_real_map");
            web.setWebViewClient(new android.webkit.WebViewClient(){
                @Override public boolean onRenderProcessGone(android.webkit.WebView view,android.webkit.RenderProcessGoneDetail detail){
                    try{holder.removeView(view);}catch(Throwable ignored){}
                    try{view.removeAllViews();}catch(Throwable ignored){}
                    try{view.destroy();}catch(Throwable ignored){}
                    fallback.setVisibility(android.view.View.VISIBLE);fallback.bringToFront();
                    return true;
                }
            });
            holder.addView(web,0,new android.widget.FrameLayout.LayoutParams(-1,-1));
            AlertDialog dialog=new AlertDialog.Builder(this).setTitle("Mapa da corrida").setView(holder).setPositiveButton("Fechar",null).create();
            dialog.setOnDismissListener(d->{try{holder.removeView(web);}catch(Throwable ignored){}try{web.stopLoading();}catch(Throwable ignored){}try{web.loadUrl("about:blank");}catch(Throwable ignored){}try{web.destroy();}catch(Throwable ignored){}});
            dialog.show();
            if(dialog.getWindow()!=null)dialog.getWindow().setLayout(-1,(int)(getResources().getDisplayMetrics().heightPixels*0.82));
            web.loadDataWithBaseURL("https://click-go-ten.vercel.app/",html,"text/html","UTF-8",null);
        }catch(Throwable fatal){toast("Nao foi possivel abrir o mapa desta corrida agora.");}
    }

    private void showPassengerHistoryMap(JSONObject ride){
        String rideId=ride.optString("id","");if(rideId.isBlank()){toast("Corrida invalida.");return;}
        runIo(()->{try{
            JSONArray points=new JSONArray(ApiClient.restGet("ride_location_points?ride_id=eq."+rideId+"&select=lat,lng,phase,recorded_at&order=recorded_at.asc",token));
            String html=historyMapHtml(ride,points);
            ui.post(()->showHistoryMapDialog(html));
        }catch(Exception e){ui.post(()->toast(message(e)));}});
    }

    private void showHistoryMapSmoke(){
        try{
            JSONObject ride=new JSONObject().put("origin_lat",-14.52472).put("origin_lng",-49.14083).put("destination_lat",-14.53110).put("destination_lng",-49.13610).put("_origin_address","Embarque de teste").put("_destination_address","Destino de teste");
            JSONArray pts=new JSONArray();pts.put(new JSONArray().put(-14.52472).put(-49.14083));pts.put(new JSONArray().put(-14.52730).put(-49.13900));pts.put(new JSONArray().put(-14.53110).put(-49.13610));
            showHistoryMapDialog(historyMapHtml(ride,pts));
        }catch(Throwable ignored){}
    }
'''
if old_method in text:
    text = text.replace(old_method, new_method, 1)
elif 'private void showHistoryMapDialog(String html)' not in text:
    raise SystemExit('v2.37: metodo do mapa do historico nao encontrado')

# O smoke de rede do PR passa a exercitar o WebView real do historico sem depender de login.
network_smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_home_network_smoke",false)){token="network-smoke-invalid-token";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Localização de teste com serviços ativos";showHome();return;}'
network_smoke_v237 = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_home_network_smoke",false)){token="network-smoke-invalid-token";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Localização de teste com serviços ativos";showHome();ui.postDelayed(this::showHistoryMapSmoke,1500);return;}'
if network_smoke in text:
    text = text.replace(network_smoke, network_smoke_v237, 1)
elif 'ui.postDelayed(this::showHistoryMapSmoke,1500)' not in text:
    raise SystemExit('v2.37: smoke de rede nao encontrado')

for required in ['openInitialPassengerScreenSafely','safeShowHome','showHistoryMapDialog','onRenderProcessGone','showHistoryMapSmoke','clickgo_history_real_map']:
    if required not in text:
        raise SystemExit('v2.37 incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m:
    build=build[:m.start(1)]+str(max(int(m.group(1))+1,237))+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.37-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.37 PRIME: protecao de fechamento inesperado e mapa historico crash-safe aplicados.')
