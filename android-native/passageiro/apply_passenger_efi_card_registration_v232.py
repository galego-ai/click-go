from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
api_path=Path('app/src/main/java/com/clickgo/passageiro/ApiClient.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
api=api_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.32 PRIME
# Escopo exclusivo: cadastrar cartão Efí em Formas de pagamento.
# PIX e demais fluxos permanecem inalterados.

field_anchor='    private String token;\n'
if 'private AlertDialog efiCardDialog;' not in text:
    if field_anchor not in text:
        raise SystemExit('campo token nao encontrado')
    text=text.replace(field_anchor,field_anchor+'    private AlertDialog efiCardDialog;\n',1)

if 'public static String functionPost(' not in api:
    anchor='''    public static String restGet(String pathAndQuery, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "GET", null, true, token, true);\n    }\n'''
    addition=anchor+'''\n    public static String functionPost(String function, JSONObject body, String token) throws Exception {\n        return request(BuildConfig.SUPABASE_URL + "/functions/v1/" + function, "POST", body == null ? "{}" : body.toString(), true, token, true);\n    }\n'''
    if anchor not in api:
        raise SystemExit('restGet do ApiClient nao encontrado')
    api=api.replace(anchor,addition,1)

pay_anchor='''        content.addView(availability, lpMatchWrap());\n        content.addView(space(14));\n        content.addView(text("Cartões salvos", 18, BLACK, true));\n'''
pay_repl='''        content.addView(availability, lpMatchWrap());\n        content.addView(space(14));\n        Button addEfi=primary("+ Cadastrar cartão Efí");\n        addEfi.setContentDescription("clickgo_add_efi_card");\n        addEfi.setOnClickListener(v -> showEfiCardRegistration());\n        content.addView(addEfi,lpMatch(dp(56)));\n        content.addView(space(14));\n        content.addView(text("Cartões salvos", 18, BLACK, true));\n'''
if 'clickgo_add_efi_card' not in text:
    if pay_anchor not in text:
        raise SystemExit('renderPayments nao encontrado')
    text=text.replace(pay_anchor,pay_repl,1)

payment_method_anchor='    private TextView paymentStatus(String label, boolean enabled) {'
efi_helpers=r'''    private void showEfiCardRegistration(){
        io.execute(()->{try{
            JSONObject cfg=new JSONObject(ApiClient.functionPost("efi-card",new JSONObject().put("action","config"),token));
            String account=cfg.optString("account_identifier","");
            String environment=cfg.optString("environment","production");
            if(!cfg.optBoolean("configured",false)||account.isBlank())throw new Exception("Identificador de conta Efí não configurado.");
            ui.post(()->showEfiCardWebView(account,environment));
        }catch(Exception e){String m=message(e);ui.post(()->toast(m));}});
    }

    private void showEfiCardWebView(String account,String environment){
        if(destroyed||isFinishing())return;
        android.webkit.WebView web=new android.webkit.WebView(this);
        android.webkit.WebSettings settings=web.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setMixedContentMode(android.webkit.WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        web.setWebViewClient(new android.webkit.WebViewClient());
        web.addJavascriptInterface(new EfiCardBridge(),"ClickGoCard");
        web.setContentDescription("clickgo_efi_card_form");
        efiCardDialog=new AlertDialog.Builder(this)
                .setTitle("Cadastrar cartão Efí")
                .setView(web)
                .setNegativeButton("Cancelar",null)
                .create();
        efiCardDialog.setOnDismissListener(d->{try{web.removeJavascriptInterface("ClickGoCard");web.destroy();}catch(Exception ignored){}efiCardDialog=null;});
        efiCardDialog.show();
        if(efiCardDialog.getWindow()!=null)efiCardDialog.getWindow().setLayout(-1,(int)(getResources().getDisplayMetrics().heightPixels*0.88));
        web.loadDataWithBaseURL("https://click-go-ten.vercel.app/",efiCardHtml(account,environment),"text/html","UTF-8",null);
    }

    private String efiCardHtml(String account,String environment){
        String a=account.replace("\\","\\\\").replace("'","\\'");
        String env="sandbox".equalsIgnoreCase(environment)?"sandbox":"production";
        return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1'><meta charset='utf-8'>"+
          "<style>body{font-family:Arial,sans-serif;background:#fff;margin:0;padding:18px;color:#111}h2{margin:0 0 4px}.note{font-size:12px;color:#666;margin-bottom:15px}.row{display:flex;gap:10px}.field{margin:9px 0;flex:1}label{display:block;font-size:12px;font-weight:700;margin-bottom:5px}input{box-sizing:border-box;width:100%;padding:13px;border:1px solid #ccc;border-radius:10px;font-size:16px}button{width:100%;padding:15px;border:0;border-radius:12px;background:#ffd400;color:#111;font-weight:800;font-size:16px;margin-top:12px}.status{min-height:20px;margin-top:10px;font-size:13px;color:#555}.secure{background:#fff8d8;padding:10px;border-radius:10px;font-size:12px}</style>"+
          "<script src='https://cdn.jsdelivr.net/npm/payment-token-efi@3.4.1/dist/payment-token-efi-umd.min.js'></script></head><body>"+
          "<h2>Cartão no app</h2><div class='note'>Tokenização segura pela Efí Bank. O CLICK-GO não recebe nem armazena o número completo ou CVV.</div>"+
          "<div class='field'><label>Número do cartão</label><input id='number' inputmode='numeric' autocomplete='cc-number' maxlength='23'></div>"+
          "<div class='field'><label>Nome impresso no cartão</label><input id='name' autocomplete='cc-name'></div>"+
          "<div class='field'><label>CPF do titular</label><input id='doc' inputmode='numeric' maxlength='14'></div>"+
          "<div class='row'><div class='field'><label>Mês</label><input id='month' inputmode='numeric' maxlength='2' placeholder='MM'></div><div class='field'><label>Ano</label><input id='year' inputmode='numeric' maxlength='4' placeholder='AAAA'></div><div class='field'><label>CVV</label><input id='cvv' type='password' inputmode='numeric' maxlength='4'></div></div>"+
          "<div class='secure'>🔒 Os dados sensíveis são enviados diretamente para tokenização da Efí.</div><button id='save'>Cadastrar cartão</button><div id='status' class='status'></div>"+
          "<script>const account='"+a+"',environment='"+env+"';const status=document.getElementById('status');const digits=v=>(v||'').replace(/\\D/g,'');document.getElementById('number').addEventListener('input',e=>{let v=digits(e.target.value).slice(0,19);e.target.value=v.replace(/(.{4})/g,'$1 ').trim()});document.getElementById('doc').addEventListener('input',e=>{e.target.value=digits(e.target.value).slice(0,11)});document.getElementById('save').onclick=async()=>{const btn=document.getElementById('save');try{btn.disabled=true;status.textContent='Validando cartão com a Efí…';const number=digits(document.getElementById('number').value),cvv=digits(document.getElementById('cvv').value),expirationMonth=digits(document.getElementById('month').value),expirationYear=digits(document.getElementById('year').value),holderName=document.getElementById('name').value.trim(),holderDocument=digits(document.getElementById('doc').value);if(number.length<13||cvv.length<3||expirationMonth.length<1||expirationYear.length!==4||holderName.length<3||holderDocument.length!==11)throw new Error('Confira todos os dados do cartão.');const blocked=await EfiPay.CreditCard.isScriptBlocked();if(blocked)throw new Error('O módulo de segurança da Efí foi bloqueado neste aparelho.');const brand=await EfiPay.CreditCard.setCardNumber(number).verifyCardBrand();if(!brand||brand==='undefined'||brand==='unsupported')throw new Error('Bandeira do cartão não suportada pela Efí.');const result=await EfiPay.CreditCard.setAccount(account).setEnvironment(environment).setCreditCardData({brand:brand,number:number,cvv:cvv,expirationMonth:expirationMonth.padStart(2,'0'),expirationYear:expirationYear,holderName:holderName,holderDocument:holderDocument,reuse:true}).getPaymentToken();if(!result||!result.payment_token)throw new Error('A Efí não retornou o token do cartão.');window.ClickGoCard.onToken(JSON.stringify({payment_token:result.payment_token,card_mask:result.card_mask||'',brand:brand}));status.textContent='Cartão tokenizado. Salvando…';}catch(e){btn.disabled=false;const m=(e&&e.error_description)||(e&&e.message)||'Não foi possível cadastrar o cartão.';status.textContent=m;window.ClickGoCard.onError(String(m));}};</script></body></html>";
    }

    private final class EfiCardBridge{
        @android.webkit.JavascriptInterface public void onToken(String payload){
            io.execute(()->{try{
                JSONObject r=new JSONObject(payload);
                String paymentToken=r.optString("payment_token","");
                String mask=r.optString("card_mask","");
                String brand=r.optString("brand","");
                if(paymentToken.length()<20)throw new Exception("Token Efí inválido.");
                JSONObject saved=new JSONObject(ApiClient.functionPost("efi-card",new JSONObject().put("action","save_method").put("payment_token",paymentToken).put("card_mask",mask).put("brand",brand),token));
                if(!saved.optBoolean("ok",false))throw new Exception(saved.optString("error","Não foi possível salvar o cartão."));
                ui.post(()->{if(efiCardDialog!=null&&efiCardDialog.isShowing())efiCardDialog.dismiss();toast("Cartão Efí cadastrado com segurança.");showPayments();});
            }catch(Exception e){String m=message(e);ui.post(()->toast(m));}});
        }
        @android.webkit.JavascriptInterface public void onError(String message){if(message!=null&&!message.isBlank())ui.post(()->toast(message));}
    }

'''
if 'private void showEfiCardRegistration()' not in text:
    if payment_method_anchor not in text:
        raise SystemExit('paymentStatus nao encontrado para inserir cadastro Efi')
    text=text.replace(payment_method_anchor,efi_helpers+payment_method_anchor,1)

for required in ['clickgo_add_efi_card','showEfiCardRegistration','EfiPay.CreditCard','reuse:true','functionPost("efi-card"']:
    if required not in text and required not in api:
        raise SystemExit('cadastro de cartao Efi incompleto: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 232',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.32-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
api_path.write_text(api,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.32 PRIME: cadastro de cartão Efi adicionado em Formas de pagamento; PIX preservado.')
