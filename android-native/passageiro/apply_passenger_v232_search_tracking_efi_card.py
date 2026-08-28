from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
api_path=Path('app/src/main/java/com/clickgo/passageiro/ApiClient.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
api=api_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.32 PRIME
# - popup circular com cronometro real durante a busca
# - rota ao vivo motorista -> embarque e depois motorista -> destino
# - cadastro seguro de cartao Efi via WebView/tokenizacao oficial

field_anchor='    private Runnable callTimerRunnable;\n'
fields='''    private Runnable callTimerRunnable;\n    private AlertDialog driverSearchDialog;\n    private SearchTimerRing driverSearchRing;\n    private long driverFoundElapsedMs=0L;\n    private String liveRoutePhase="";\n    private long liveRouteUpdatedAtMs=0L;\n    private AlertDialog efiCardDialog;\n'''
if 'private AlertDialog driverSearchDialog;' not in text:
    if field_anchor not in text: raise SystemExit('campos do cronometro v2.31 nao encontrados')
    text=text.replace(field_anchor,fields,1)

old_search='''        if(!trackingUiActive){\n            callTimerText=text("Chamando motorista há 00:00",15,Color.rgb(155,105,0),true);\n            callTimerText.setGravity(Gravity.LEFT);\n            callTimerText.setPadding(0,dp(5),0,dp(3));\n            body.addView(callTimerText,lpMatchWrap());\n            if(callStartedAtMs<=0L)callStartedAtMs=System.currentTimeMillis();\n            startCallTimer();\n        }\n'''
new_search='''        if(!trackingUiActive){\n            if(callStartedAtMs<=0L)callStartedAtMs=System.currentTimeMillis();\n            startCallTimer();\n        }else if(driverFoundElapsedMs>0L){\n            TextView found=text("Motorista encontrado em "+formatCallElapsed(driverFoundElapsedMs),14,Color.rgb(126,86,0),true);\n            found.setPadding(0,dp(5),0,dp(3));\n            body.addView(found,lpMatchWrap());\n        }\n'''
if old_search in text:
    text=text.replace(old_search,new_search,1)
elif 'Motorista encontrado em ' not in text:
    raise SystemExit('bloco visual do contador v2.31 nao encontrado')

pat=r'''    private void startCallTimer\(\)\{.*?\n    private String formatCallElapsed\(long elapsedMs\)\{.*?\n    \}\n\n'''
helpers=r'''    private final class SearchTimerRing extends View {
        private final android.graphics.Paint track=new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
        private final android.graphics.Paint progress=new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
        private final android.graphics.Paint valuePaint=new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
        private final android.graphics.Paint labelPaint=new android.graphics.Paint(android.graphics.Paint.ANTI_ALIAS_FLAG);
        private final android.graphics.RectF oval=new android.graphics.RectF();
        private long elapsedMs=0L;
        SearchTimerRing(android.content.Context context){
            super(context);setContentDescription("clickgo_search_timer_popup");setMinimumHeight(dp(210));setMinimumWidth(dp(210));
            track.setStyle(android.graphics.Paint.Style.STROKE);track.setStrokeWidth(dp(12));track.setStrokeCap(android.graphics.Paint.Cap.ROUND);track.setColor(Color.rgb(232,232,232));
            progress.setStyle(android.graphics.Paint.Style.STROKE);progress.setStrokeWidth(dp(12));progress.setStrokeCap(android.graphics.Paint.Cap.ROUND);progress.setColor(YELLOW);
            valuePaint.setColor(BLACK);valuePaint.setTextAlign(android.graphics.Paint.Align.CENTER);valuePaint.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);valuePaint.setTextSize(dp(34));
            labelPaint.setColor(Color.rgb(95,95,95));labelPaint.setTextAlign(android.graphics.Paint.Align.CENTER);labelPaint.setTypeface(android.graphics.Typeface.DEFAULT_BOLD);labelPaint.setTextSize(dp(12));
        }
        void setElapsed(long value){elapsedMs=Math.max(0L,value);invalidate();}
        @Override protected void onDraw(android.graphics.Canvas canvas){
            super.onDraw(canvas);float size=Math.min(getWidth(),getHeight());float cx=getWidth()/2f,cy=getHeight()/2f;float radius=Math.max(dp(60),size/2f-dp(22));
            canvas.drawCircle(cx,cy,radius,track);oval.set(cx-radius,cy-radius,cx+radius,cy+radius);
            float cycle=(elapsedMs%60000L)/60000f;float sweep=elapsedMs<=0L?0f:(cycle==0f?360f:Math.max(8f,cycle*360f));canvas.drawArc(oval,-90f,sweep,false,progress);
            canvas.drawText(formatCallElapsed(elapsedMs),cx,cy+dp(10),valuePaint);canvas.drawText("TEMPO DE BUSCA",cx,cy+dp(38),labelPaint);
        }
    }

    private void startCallTimer(){
        if(callStartedAtMs<=0L)callStartedAtMs=System.currentTimeMillis();
        if(driverSearchDialog==null||!driverSearchDialog.isShowing()){
            ui.post(()->{
                if(destroyed||isFinishing()||trackingUiActive||activeRideId==null)return;
                LinearLayout box=vertical(Color.WHITE);box.setPadding(dp(24),dp(22),dp(24),dp(20));
                TextView title=text("Procurando motorista",22,BLACK,true);title.setGravity(Gravity.CENTER);box.addView(title,lpMatchWrap());
                TextView sub=text("Chamando o motorista CLICK-GO mais próximo",14,GRAY,false);sub.setGravity(Gravity.CENTER);sub.setPadding(0,dp(5),0,dp(8));box.addView(sub,lpMatchWrap());
                driverSearchRing=new SearchTimerRing(this);box.addView(driverSearchRing,lpMatch(dp(230)));
                TextView hint=text("O círculo acompanha o tempo real até um motorista aceitar.",12,GRAY,false);hint.setGravity(Gravity.CENTER);hint.setPadding(0,dp(4),0,dp(12));box.addView(hint,lpMatchWrap());
                Button cancel=secondaryLight("Cancelar chamada");cancel.setOnClickListener(v->previewCancel());box.addView(cancel,lpMatch(dp(52)));
                driverSearchDialog=new AlertDialog.Builder(this).setView(box).create();driverSearchDialog.setCancelable(false);driverSearchDialog.setCanceledOnTouchOutside(false);driverSearchDialog.show();
                if(driverSearchDialog.getWindow()!=null)driverSearchDialog.getWindow().setBackgroundDrawable(round(Color.WHITE,24,Color.TRANSPARENT));
            });
        }
        if(callTimerRunnable!=null)ui.removeCallbacks(callTimerRunnable);
        callTimerRunnable=new Runnable(){@Override public void run(){
            if(destroyed||isFinishing()||trackingUiActive||activeRideId==null)return;
            long elapsed=Math.max(0L,System.currentTimeMillis()-callStartedAtMs);
            if(driverSearchRing!=null)driverSearchRing.setElapsed(elapsed);
            ui.postDelayed(this,250L);
        }};ui.post(callTimerRunnable);
    }

    private void stopCallTimer(){
        if(trackingUiActive&&callStartedAtMs>0L&&driverFoundElapsedMs<=0L)driverFoundElapsedMs=Math.max(0L,System.currentTimeMillis()-callStartedAtMs);
        if(callTimerRunnable!=null)ui.removeCallbacks(callTimerRunnable);callTimerRunnable=null;callTimerText=null;
        AlertDialog old=driverSearchDialog;driverSearchDialog=null;driverSearchRing=null;if(old!=null&&old.isShowing())try{old.dismiss();}catch(Exception ignored){}
    }

    private String formatCallElapsed(long elapsedMs){
        long total=Math.max(0L,elapsedMs/1000L);long minutes=total/60L,seconds=total%60L;return String.format(Locale.getDefault(),"%02d:%02d",minutes,seconds);
    }

'''
text,n=re.subn(pat,helpers,text,count=1,flags=re.S)
if n!=1 and 'class SearchTimerRing extends View' not in text:
    raise SystemExit('helpers do contador v2.31 nao encontrados')

route_anchor='    private void renderActiveDriver(JSONObject loc) {'
route_helper=r'''    private void updateLiveTrackingRoute(String status,JSONObject loc){
        if(liveTrackingMap==null||loc==null||origin==null||destination==null)return;
        double lat=loc.optDouble("lat",Double.NaN),lng=loc.optDouble("lng",Double.NaN);if(!Double.isFinite(lat)||!Double.isFinite(lng))return;
        String phase=("in_progress".equals(status)?"trip":(("accepted".equals(status)||"driver_arriving".equals(status))?"pickup":""));if(phase.isBlank())return;
        long now=System.currentTimeMillis();if(phase.equals(liveRoutePhase)&&now-liveRouteUpdatedAtMs<9000L)return;
        liveRoutePhase=phase;liveRouteUpdatedAtMs=now;
        if("trip".equals(phase))liveTrackingMap.setRoute(lat,lng,destination.getLatitude(),destination.getLongitude());
        else liveTrackingMap.setRoute(lat,lng,origin.getLatitude(),origin.getLongitude());
    }

'''
if 'private void updateLiveTrackingRoute(' not in text:
    if route_anchor not in text: raise SystemExit('renderActiveDriver nao encontrado')
    text=text.replace(route_anchor,route_helper+route_anchor,1)
if 'updateLiveTrackingRoute(status,finalLocation);' not in text:
    if 'renderActiveDriver(finalLocation);' not in text: raise SystemExit('ponto de atualizacao GPS da corrida nao encontrado')
    text=text.replace('renderActiveDriver(finalLocation);','renderActiveDriver(finalLocation);\n                            updateLiveTrackingRoute(status,finalLocation);',1)

if 'public static String functionPost(' not in api:
    anchor='''    public static String restGet(String pathAndQuery, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "GET", null, true, token, true);\n    }\n'''
    addition=anchor+'''\n    public static String functionPost(String function, JSONObject body, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/functions/v1/" + function, "POST", body == null ? "{}" : body.toString(), true, token, true);\n    }\n'''
    if anchor not in api: raise SystemExit('restGet do ApiClient nao encontrado')
    api=api.replace(anchor,addition,1)

text=text.replace('''passenger_payment_methods?select=id,method_type,provider,brand,last4,is_default,active&active=eq.true&order=created_at.desc''','''passenger_payment_methods?select=id,method_type,provider,brand,last4,is_default,active&active=eq.true&method_type=eq.card&provider=eq.efi&order=is_default.desc,created_at.desc''',1)
pay_anchor='''        content.addView(availability, lpMatchWrap());\n        content.addView(space(14));\n        content.addView(text("Cartões salvos", 18, BLACK, true));\n'''
pay_repl='''        content.addView(availability, lpMatchWrap());\n        content.addView(space(14));\n        Button addEfi=primary("+ Cadastrar cartão Efí");\n        addEfi.setContentDescription("clickgo_add_efi_card");\n        addEfi.setOnClickListener(v -> showEfiCardRegistration());\n        content.addView(addEfi,lpMatch(dp(56)));\n        content.addView(space(14));\n        content.addView(text("Cartões Efí salvos", 18, BLACK, true));\n'''
if 'clickgo_add_efi_card' not in text:
    if pay_anchor not in text: raise SystemExit('renderPayments nao encontrado')
    text=text.replace(pay_anchor,pay_repl,1)
text=text.replace('Nenhum cartão salvo nesta conta.','Nenhum cartão Efí cadastrado nesta conta.',1)

old_default='''                String uid = ensureUserId();\n                ApiClient.restPatch("passenger_payment_methods?passenger_id=eq." + uid, new JSONObject().put("is_default", false), token);\n                ApiClient.restPatch("passenger_payment_methods?id=eq." + id, new JSONObject().put("is_default", true), token);\n'''
new_default='''                ApiClient.rpc("passenger_set_default_efi_card",new JSONObject().put("p_method_id",id),token);\n'''
if old_default in text:text=text.replace(old_default,new_default,1)
old_delete='''                        ApiClient.restDelete("passenger_payment_methods?id=eq." + id, token);\n'''
new_delete='''                        ApiClient.functionPost("efi-card",new JSONObject().put("action","delete_method").put("method_id",id),token);\n'''
if old_delete in text:text=text.replace(old_delete,new_delete,1)

payment_method_anchor='    private TextView paymentStatus(String label, boolean enabled) {'
efi_helpers=r'''    private void showEfiCardRegistration(){
        io.execute(()->{try{
            JSONObject cfg=new JSONObject(ApiClient.functionPost("efi-card",new JSONObject().put("action","config"),token));
            String account=cfg.optString("account_identifier","");String environment=cfg.optString("environment","production");
            if(!cfg.optBoolean("configured",false)||account.isBlank())throw new Exception("Identificador de conta Efí não configurado.");
            ui.post(()->showEfiCardWebView(account,environment));
        }catch(Exception e){String m=message(e);ui.post(()->toast(m));}});
    }

    private void showEfiCardWebView(String account,String environment){
        if(destroyed||isFinishing())return;
        android.webkit.WebView web=new android.webkit.WebView(this);android.webkit.WebSettings settings=web.getSettings();settings.setJavaScriptEnabled(true);settings.setDomStorageEnabled(true);settings.setAllowFileAccess(false);settings.setAllowContentAccess(false);settings.setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebViewClient(new android.webkit.WebViewClient());web.addJavascriptInterface(new EfiCardBridge(),"ClickGoCard");web.setContentDescription("clickgo_efi_card_form");
        efiCardDialog=new AlertDialog.Builder(this).setTitle("Cadastrar cartão Efí").setView(web).setNegativeButton("Cancelar",null).create();efiCardDialog.setOnDismissListener(d->{try{web.removeJavascriptInterface("ClickGoCard");web.destroy();}catch(Exception ignored){}efiCardDialog=null;});efiCardDialog.show();
        if(efiCardDialog.getWindow()!=null){efiCardDialog.getWindow().setLayout(-1,(int)(getResources().getDisplayMetrics().heightPixels*0.88));}
        web.loadDataWithBaseURL("https://click-go-ten.vercel.app/",efiCardHtml(account,environment),"text/html","UTF-8",null);
    }

    private String efiCardHtml(String account,String environment){
        String a=account.replace("\\","\\\\").replace("'","\\'");String env="sandbox".equalsIgnoreCase(environment)?"sandbox":"production";
        return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta charset='utf-8'>"+
          "<style>body{font-family:Arial,sans-serif;background:#fff;margin:0;padding:18px;color:#111}h2{margin:0 0 4px}.note{font-size:12px;color:#666;margin-bottom:15px}.row{display:flex;gap:10px}.field{margin:9px 0;flex:1}label{display:block;font-size:12px;font-weight:700;margin-bottom:5px}input{box-sizing:border-box;width:100%;padding:13px;border:1px solid #ccc;border-radius:10px;font-size:16px}button{width:100%;padding:15px;border:0;border-radius:12px;background:#ffd400;color:#111;font-weight:800;font-size:16px;margin-top:12px}.status{min-height:20px;margin-top:10px;font-size:13px;color:#555}.secure{background:#fff8d8;padding:10px;border-radius:10px;font-size:12px}</style>"+
          "<script src='https://cdn.jsdelivr.net/npm/payment-token-efi@3.4.1/dist/payment-token-efi-umd.min.js'></script></head><body>"+
          "<h2>Cartão no app</h2><div class='note'>Tokenização segura pela Efí Bank. O CLICK-GO não recebe nem armazena o número completo ou CVV.</div>"+
          "<div class='field'><label>Número do cartão</label><input id='number' inputmode='numeric' autocomplete='cc-number' maxlength='23'></div>"+
          "<div class='field'><label>Nome impresso no cartão</label><input id='name' autocomplete='cc-name'></div>"+
          "<div class='field'><label>CPF do titular</label><input id='doc' inputmode='numeric' maxlength='14'></div>"+
          "<div class='row'><div class='field'><label>Mês</label><input id='month' inputmode='numeric' maxlength='2' placeholder='MM'></div><div class='field'><label>Ano</label><input id='year' inputmode='numeric' maxlength='4' placeholder='AAAA'></div><div class='field'><label>CVV</label><input id='cvv' type='password' inputmode='numeric' maxlength='4'></div></div>"+
          "<div class='secure'>🔒 O cartão será convertido em um token reutilizável da Efí para cobranças de corridas autorizadas.</div><button id='save'>Cadastrar cartão</button><div id='status' class='status'></div>"+
          "<script>const account='"+a+"',environment='"+env+"';const status=document.getElementById('status');const digits=v=>(v||'').replace(/\\D/g,'');document.getElementById('number').addEventListener('input',e=>{let v=digits(e.target.value).slice(0,19);e.target.value=v.replace(/(.{4})/g,'$1 ').trim()});document.getElementById('doc').addEventListener('input',e=>{e.target.value=digits(e.target.value).slice(0,11)});document.getElementById('save').onclick=async()=>{const btn=document.getElementById('save');try{btn.disabled=true;status.textContent='Validando cartão com a Efí…';const number=digits(document.getElementById('number').value),cvv=digits(document.getElementById('cvv').value),expirationMonth=digits(document.getElementById('month').value),expirationYear=digits(document.getElementById('year').value),holderName=document.getElementById('name').value.trim(),holderDocument=digits(document.getElementById('doc').value);if(number.length<13||cvv.length<3||expirationMonth.length<1||expirationYear.length!==4||holderName.length<3||holderDocument.length!==11)throw new Error('Confira todos os dados do cartão.');const blocked=await EfiPay.CreditCard.isScriptBlocked();if(blocked)throw new Error('O módulo de segurança da Efí foi bloqueado neste aparelho.');const brand=await EfiPay.CreditCard.setCardNumber(number).verifyCardBrand();if(!brand||brand==='undefined'||brand==='unsupported')throw new Error('Bandeira do cartão não suportada pela Efí.');const result=await EfiPay.CreditCard.setAccount(account).setEnvironment(environment).setCreditCardData({brand:brand,number:number,cvv:cvv,expirationMonth:expirationMonth.padStart(2,'0'),expirationYear:expirationYear,holderName:holderName,holderDocument:holderDocument,reuse:true}).getPaymentToken();if(!result||!result.payment_token)throw new Error('A Efí não retornou o token do cartão.');window.ClickGoCard.onToken(JSON.stringify({payment_token:result.payment_token,card_mask:result.card_mask||'',brand:brand}));status.textContent='Cartão tokenizado. Salvando…';}catch(e){btn.disabled=false;const m=(e&&e.error_description)||(e&&e.message)||'Não foi possível cadastrar o cartão.';status.textContent=m;window.ClickGoCard.onError(String(m));}};</script></body></html>";
    }

    private final class EfiCardBridge{
        @android.webkit.JavascriptInterface public void onToken(String payload){
            io.execute(()->{try{JSONObject r=new JSONObject(payload);String paymentToken=r.optString("payment_token","");String mask=r.optString("card_mask","");String brand=r.optString("brand","");if(paymentToken.length()<20)throw new Exception("Token Efí inválido.");
                JSONObject saved=new JSONObject(ApiClient.functionPost("efi-card",new JSONObject().put("action","save_method").put("payment_token",paymentToken).put("card_mask",mask).put("brand",brand),token));if(!saved.optBoolean("ok",false))throw new Exception(saved.optString("error","Não foi possível salvar o cartão."));
                ui.post(()->{if(efiCardDialog!=null&&efiCardDialog.isShowing())efiCardDialog.dismiss();toast("Cartão Efí cadastrado com segurança.");showPayments();});
            }catch(Exception e){String m=message(e);ui.post(()->toast(m));}});
        }
        @android.webkit.JavascriptInterface public void onError(String message){if(message!=null&&!message.isBlank())ui.post(()->toast(message));}
    }

    private String defaultEfiCardId() throws Exception{
        JSONArray rows=new JSONArray(ApiClient.restGet("passenger_payment_methods?select=id&method_type=eq.card&provider=eq.efi&active=eq.true&is_default=eq.true&limit=1",token));
        if(rows.length()==0)rows=new JSONArray(ApiClient.restGet("passenger_payment_methods?select=id&method_type=eq.card&provider=eq.efi&active=eq.true&order=created_at.desc&limit=1",token));
        if(rows.length()==0)throw new Exception("Cadastre um cartão Efí em Formas de pagamento antes de solicitar a corrida.");return rows.getJSONObject(0).optString("id","");
    }

'''
if 'private void showEfiCardRegistration()' not in text:
    if payment_method_anchor not in text: raise SystemExit('paymentStatus nao encontrado para helpers Efi')
    text=text.replace(payment_method_anchor,efi_helpers+payment_method_anchor,1)

body_anchor='''                JSONObject body = new JSONObject()\n                        .put("p_origin_label", cleanLabel(originLabel))'''
if 'String selectedCardId=payment.equals("card")?defaultEfiCardId():"";' not in text:
    if body_anchor not in text: raise SystemExit('body de create_passenger_ride nao encontrado')
    text=text.replace(body_anchor,'''                String selectedCardId=payment.equals("card")?defaultEfiCardId():"";\n                JSONObject body = new JSONObject()\n                        .put("p_origin_label", cleanLabel(originLabel))''',1)
    payment_end='''.put("p_payment_method", payment);'''
    if payment_end not in text: raise SystemExit('p_payment_method nao encontrado')
    text=text.replace(payment_end,'''.put("p_payment_method", payment);\n                if(!selectedCardId.isBlank())body.put("p_payment_method_id",selectedCardId);''',1)

start='''        callStartedAtMs=System.currentTimeMillis();\n'''
if 'driverFoundElapsedMs=0L;' not in text:
    if start not in text: raise SystemExit('inicio do contador nao encontrado')
    text=text.replace(start,start+'        driverFoundElapsedMs=0L;\n        liveRoutePhase="";liveRouteUpdatedAtMs=0L;\n',1)

end='''        stopCallTimer();\n        callStartedAtMs=0L;\n'''
if end in text and 'driverFoundElapsedMs=0L;\n        liveRoutePhase="";' not in text[text.find(end):text.find(end)+200]:
    text=text.replace(end,end+'        driverFoundElapsedMs=0L;\n        liveRoutePhase="";liveRouteUpdatedAtMs=0L;\n',1)

for required in ['clickgo_search_timer_popup','Motorista encontrado em ','updateLiveTrackingRoute(status,finalLocation)','clickgo_add_efi_card','EfiPay.CreditCard','reuse:true','p_payment_method_id','functionPost("efi-card"']:
    if required not in text and required not in api: raise SystemExit('v2.32 incompleto: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 232',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.32-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
api_path.write_text(api,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.32 PRIME: popup circular, rastreamento por fase e cartao Efi aplicados.')
