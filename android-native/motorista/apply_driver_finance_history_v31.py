from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
api_path=Path('app/src/main/java/com/clickgo/motorista/ApiClient.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
api=api_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# -----------------------------------------------------------------------------
# Repository/API: route previews, real earnings, operational wallet and Efí Pix.
# -----------------------------------------------------------------------------
if 'public static String functionsPost(' not in api:
    anchor='''    public static String absoluteGet(String url) throws Exception { return request(url, "GET", null, false, null, false); }\n'''
    add='''    public static String absoluteGet(String url) throws Exception { return request(url, "GET", null, false, null, false); }\n    public static String functionsPost(String function, JSONObject body, String token) throws Exception { return request(BuildConfig.SUPABASE_URL + "/functions/v1/" + function, "POST", body.toString(), true, token, true); }\n'''
    if anchor not in api: raise SystemExit('ApiClient absoluteGet não encontrado')
    api=api.replace(anchor,add,1)

if 'public static JSONArray routePreviews(' not in repo:
    anchor='''    public static JSONArray documents(String token, String userId) throws Exception {\n'''
    methods=r'''    public static JSONArray routePreviews(String token) throws Exception {
        return new JSONArray(ApiClient.rpc("get_my_ride_route_previews", new JSONObject().put("p_limit",50).put("p_max_points",36), token));
    }

    public static JSONArray earningsHistory(String token) throws Exception {
        return new JSONArray(ApiClient.rpc("get_my_driver_earnings_history", new JSONObject().put("p_limit",50), token));
    }

    public static JSONArray operationalTransactions(String token,String userId) throws Exception {
        return new JSONArray(ApiClient.restGet("driver_operational_transactions?driver_id=eq."+userId+"&select=id,ride_id,transaction_type,source,amount,status,reason,created_at&order=created_at.desc&limit=60",token));
    }

    public static JSONObject createDriverRecharge(String token,double amount) throws Exception {
        return new JSONObject(ApiClient.functionsPost("efi-pix",new JSONObject().put("action","create_driver_recharge").put("amount",amount),token));
    }

    public static JSONObject checkPix(String token,String txid) throws Exception {
        return new JSONObject(ApiClient.functionsPost("efi-pix",new JSONObject().put("action","status").put("txid",txid),token));
    }

'''
    if anchor not in repo: raise SystemExit('DriverRepository documents anchor não encontrado')
    repo=repo.replace(anchor,methods+anchor,1)

# Privacy state dedicated to earnings. Wallet keeps the existing showMoney state.
if 'private boolean showEarningsMoney = true;' not in text:
    m=re.search(r'(\s*private\s+boolean\s+showMoney\s*=\s*(?:true|false)\s*;)',text)
    if not m: raise SystemExit('showMoney não encontrado')
    text=text[:m.end()]+'''\n    private boolean showEarningsMoney = true;'''+text[m.end():]

# v3.0 menu: split earnings from operational credit wallet.
pattern=r'''    private void showDriverMenu\(\)\{.*?\n    \}\n\n    private View menuCard'''
replacement=r'''    private void showDriverMenu(){
        stopPolling();releaseMap();
        LinearLayout body=vertical(Color.WHITE);body.setPadding(dp(22),dp(28),dp(22),dp(32));
        LinearLayout top=horizontal();top.setGravity(Gravity.CENTER_VERTICAL);
        TextView back=menuLink("← Voltar ao mapa",()->showHome());top.addView(back,new LinearLayout.LayoutParams(0,dp(52),1));
        body.addView(top);body.addView(space(12));
        body.addView(text("Menu",30,BLACK,true));body.addView(text(firstName(fullName)+" · ★ "+String.format(Locale.getDefault(),"%.1f",rating),14,Color.DKGRAY,false));body.addView(space(18));
        body.addView(menuLink("Corridas",()->showHome()));
        body.addView(menuLink("Histórico",()->showRideHistory()));
        body.addView(menuLink("Ganhos",()->showEarnings()));
        body.addView(menuLink("Carteira de créditos",()->showOperationalWallet()));
        body.addView(menuLink("Perfil e veículo",()->showDriverProfile()));
        if(!"approved".equalsIgnoreCase(driverStatus))body.addView(menuLink("Documentos",()->showDocuments()));
        body.addView(menuLink("Suporte",()->showSupport()));
        body.addView(menuLink("Configurações",()->showDriverSettings()));
        body.addView(space(18));
        TextView exit=menuLink("Sair da conta",()->logout());exit.setTextColor(Color.rgb(190,55,55));body.addView(exit);
        setContentView(scroll(body,Color.WHITE));
    }

    private View menuCard'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showDriverMenu v3.0 não encontrado')

# History: Canvas preview from stored GPS points, no map tile/API request per card.
pattern=r'''    private void showRideHistory\(\)\{.*?\n    \}\n\n(?=    private void showEarnings\(\))'''
replacement=r'''    private void showRideHistory(){
        LinearLayout body=pageShell("Histórico de corridas","A rota concluída aparece no próprio cartão, sem carregar mapa interativo.");TextView loading=text("Carregando histórico…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));
        io.execute(()->{try{
            JSONArray rows=DriverRepository.rideHistory(token,userId),previewRows=DriverRepository.routePreviews(token);java.util.HashMap<String,JSONArray> previews=new java.util.HashMap<>();
            for(int i=0;i<previewRows.length();i++){JSONObject x=previewRows.optJSONObject(i);if(x!=null)previews.put(x.optString("ride_id",""),x.optJSONArray("points"));}
            for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;double ol=r.optDouble("origin_lat",Double.NaN),og=r.optDouble("origin_lng",Double.NaN),dl=r.optDouble("destination_lat",Double.NaN),dg=r.optDouble("destination_lng",Double.NaN);r.put("_origin",historyAddress(r.optString("origin_label",""),ol,og));r.put("_destination",historyAddress(r.optString("destination_label",""),dl,dg));}
            ui.post(()->{body.removeView(loading);if(rows.length()==0){body.addView(text("Nenhuma corrida no histórico.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));String status=r.optString("status","");double fare=r.optDouble("final_fare",r.optDouble("estimated_fare",0));c.addView(text(status.equals("completed")?"Corrida concluída":"Corrida "+status,15,status.equals("completed")?Color.rgb(74,222,128):YELLOW,true));c.addView(text("De: "+r.optString("_origin","Endereço não informado"),14,Color.WHITE,false));c.addView(text("Para: "+r.optString("_destination","Endereço não informado"),14,GRAY,false));if(fare>0)c.addView(text("Valor: "+money(fare),15,YELLOW,true));JSONArray pts=previews.get(r.optString("id",""));if(status.equals("completed")&&pts!=null&&pts.length()>1){c.addView(space(9));RideRoutePreviewView preview=new RideRoutePreviewView(this);preview.setPoints(pts);c.addView(preview,new LinearLayout.LayoutParams(-1,dp(118)));}Button mapBtn=darkButton("VER NO MAPA");double ol=r.optDouble("origin_lat",Double.NaN),og=r.optDouble("origin_lng",Double.NaN),dl=r.optDouble("destination_lat",Double.NaN),dg=r.optDouble("destination_lng",Double.NaN);mapBtn.setOnClickListener(v->openHistoryMap(ol,og,dl,dg));c.addView(space(8));c.addView(mapBtn,match(dp(48)));body.addView(c);body.addView(space(9));}});
        }catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showRideHistory final não encontrado')

# Earnings: gross fare, wallet debit and actual net per ride, all covered by a privacy eye.
pattern=r'''    private void showEarnings\(\)\{.*?\n    \}\n\n(?=    private void showPaymentSettings\(\))'''
replacement=r'''    private void showEarnings(){
        LinearLayout body=pageShell("Ganhos","Valores das corridas separados dos créditos usados para operar.");
        Button eye=darkButton(showEarningsMoney?"◉ Ocultar valores":"○ Mostrar valores");body.addView(eye,match(dp(50)));body.addView(space(12));TextView loading=text("Carregando ganhos…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));eye.setOnClickListener(v->{showEarningsMoney=!showEarningsMoney;showEarnings();});
        io.execute(()->{try{JSONArray rows=DriverRepository.earningsHistory(token);double gross=0,discount=0,net=0;for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;gross+=r.optDouble("gross_fare",0);discount+=r.optDouble("wallet_discount",0);net+=r.optDouble("net_earning",0);}double fg=gross,fd=discount,fn=net;ui.post(()->{body.removeView(loading);LinearLayout total=card(DARK,Color.rgb(75,65,18));total.addView(text("GANHO REAL",12,YELLOW,true));total.addView(text(earningMoney(fn),31,Color.WHITE,true));total.addView(text("Bruto das corridas: "+earningMoney(fg),13,GRAY,false));total.addView(text("Descontos da carteira: - "+earningMoney(fd),13,Color.rgb(248,170,120),false));body.addView(total);body.addView(space(12));body.addView(text("Por corrida",18,Color.WHITE,true));body.addView(space(7));if(rows.length()==0){body.addView(text("Nenhuma corrida concluída ainda.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));c.addView(text(shortDate(r.optString("completed_at",""))+" · "+financePaymentLabel(r.optString("payment_method","")),12,GRAY,false));c.addView(text(r.optString("origin_label","Origem")+" → "+r.optString("destination_label","Destino"),13,Color.WHITE,false));double g=r.optDouble("gross_fare",0),d=r.optDouble("wallet_discount",0),n=r.optDouble("net_earning",0);c.addView(space(6));c.addView(text("Valor da corrida: "+earningMoney(g),14,Color.WHITE,true));c.addView(text("Desconto da carteira: - "+earningMoney(d),13,Color.rgb(248,170,120),false));c.addView(text("Ganho real: "+earningMoney(n),17,YELLOW,true));body.addView(c);body.addView(space(8));}});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private String earningMoney(double value){return showEarningsMoney?money(value):"R$ ••••";}
    private String financePaymentLabel(String value){if("pix".equals(value))return"PIX";if("card".equals(value))return"Cartão";if("card_machine".equals(value))return"Maquininha";if("cash".equals(value))return"Dinheiro";return value==null||value.isBlank()?"Pagamento":value;}

    private void showOperationalWallet(){
        LinearLayout body=pageShell("Carteira de créditos","Saldo usado para taxas operacionais. Seus ganhos ficam separados.");Button eye=darkButton(showMoney?"◉ Ocultar saldo":"○ Mostrar saldo");body.addView(eye,match(dp(50)));body.addView(space(10));TextView loading=text("Carregando carteira…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));eye.setOnClickListener(v->{showMoney=!showMoney;showOperationalWallet();});
        io.execute(()->{try{JSONObject w=DriverRepository.wallet(token);JSONArray txs=DriverRepository.operationalTransactions(token,userId);double bal=w.optDouble("operational_balance",balance),fee=w.optDouble("ride_fee",0);String mode=w.optString("billing_mode",billingMode);ui.post(()->{body.removeView(loading);LinearLayout c=card(DARK,Color.rgb(75,65,18));c.addView(text("SALDO DE CRÉDITOS",12,YELLOW,true));c.addView(text(showMoney?money(bal):"R$ ••••",31,Color.WHITE,true));c.addView(text(mode.equals("monthly")?"Seu cadastro está no plano mensal.":"Desconto configurado por corrida: "+money(fee),13,GRAY,false));body.addView(c);body.addView(space(10));if(!mode.equals("monthly")){Button pix=primary("RECARREGAR VIA PIX");body.addView(pix,match(dp(58)));pix.setOnClickListener(v->openDriverPixRecharge());body.addView(space(14));}body.addView(text("Extrato da carteira",18,Color.WHITE,true));body.addView(space(7));if(txs.length()==0){body.addView(text("Nenhuma movimentação ainda.",14,GRAY,false));return;}for(int i=0;i<txs.length();i++){JSONObject t=txs.optJSONObject(i);if(t==null)continue;boolean credit="credit".equals(t.optString("transaction_type",""));LinearLayout row=card(DARK,Color.rgb(55,55,55));row.addView(text((credit?"+ ":"- ")+(showMoney?money(t.optDouble("amount",0)):"R$ ••••"),16,credit?Color.rgb(74,222,128):Color.rgb(248,150,120),true));String reason=t.optString("reason","");row.addView(text(reason.isBlank()?t.optString("source","Movimentação"):reason,13,Color.WHITE,false));row.addView(text(shortDate(t.optString("created_at","")),12,GRAY,false));body.addView(row);body.addView(space(7));}});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void openDriverPixRecharge(){
        LinearLayout wrap=vertical(Color.WHITE);wrap.setPadding(dp(20),dp(18),dp(20),dp(12));wrap.addView(text("Recarregar carteira via PIX",22,BLACK,true));wrap.addView(text("O crédito entra na carteira operacional após a confirmação da Efí.",13,Color.DKGRAY,false));wrap.addView(space(10));EditText amount=new EditText(this);amount.setHint("Valor da recarga (mínimo R$ 5,00)");amount.setInputType(android.text.InputType.TYPE_CLASS_NUMBER|android.text.InputType.TYPE_NUMBER_FLAG_DECIMAL);amount.setTextColor(BLACK);amount.setHintTextColor(Color.GRAY);amount.setBackground(round(Color.rgb(247,247,247),12,Color.rgb(220,220,220)));amount.setPadding(dp(12),0,dp(12),0);wrap.addView(amount,match(dp(56)));
        new AlertDialog.Builder(this).setView(wrap).setNegativeButton("Cancelar",null).setPositiveButton("Gerar PIX",(d,w)->{String raw=amount.getText().toString().trim().replace(',','.');double value;try{value=Double.parseDouble(raw);}catch(Exception e){toast("Informe um valor válido.");return;}if(value<5||value>5000){toast("A recarga deve ficar entre R$ 5,00 e R$ 5.000,00.");return;}toast("Gerando PIX…");io.execute(()->{try{JSONObject pix=DriverRepository.createDriverRecharge(token,value);ui.post(()->showDriverPixResult(pix));}catch(Exception e){ui.post(()->toast(msg(e)));}});}).show();
    }

    private void showDriverPixResult(JSONObject pix){
        String code=pix.optString("qrcode",""),image=pix.optString("qrcode_image",""),txid=pix.optString("txid","");double value=pix.optDouble("amount",0);LinearLayout wrap=vertical(Color.WHITE);wrap.setPadding(dp(18),dp(16),dp(18),dp(12));wrap.addView(text("PIX da recarga",22,BLACK,true));wrap.addView(text(money(value),25,BLACK,true));android.graphics.Bitmap qr=decodePixImage(image);if(qr!=null){ImageView iv=new ImageView(this);iv.setImageBitmap(qr);iv.setScaleType(ImageView.ScaleType.FIT_CENTER);wrap.addView(iv,new LinearLayout.LayoutParams(-1,dp(230)));}EditText copy=new EditText(this);copy.setText(code);copy.setTextColor(BLACK);copy.setTextSize(12);copy.setMinLines(3);copy.setFocusable(false);copy.setBackground(round(Color.rgb(247,247,247),10,Color.rgb(220,220,220)));copy.setPadding(dp(10),dp(8),dp(10),dp(8));wrap.addView(copy,new LinearLayout.LayoutParams(-1,dp(94)));Button copyBtn=darkButton("COPIAR PIX");Button check=primary("VERIFICAR PAGAMENTO");wrap.addView(space(8));wrap.addView(copyBtn,match(dp(50)));wrap.addView(space(7));wrap.addView(check,match(dp(54)));AlertDialog dialog=new AlertDialog.Builder(this).setView(wrap).setNegativeButton("Fechar",null).create();copyBtn.setOnClickListener(v->{android.content.ClipboardManager cm=(android.content.ClipboardManager)getSystemService(CLIPBOARD_SERVICE);if(cm!=null)cm.setPrimaryClip(android.content.ClipData.newPlainText("PIX CLICK-GO",code));toast("Código PIX copiado.");});check.setOnClickListener(v->{if(txid.isBlank())return;check.setEnabled(false);io.execute(()->{try{JSONObject status=DriverRepository.checkPix(token,txid);ui.post(()->{check.setEnabled(true);if("paid".equals(status.optString("status",""))){dialog.dismiss();toast("Pagamento confirmado. Carteira atualizada.");showOperationalWallet();}else toast("Pagamento ainda não confirmado pela Efí.");});}catch(Exception e){ui.post(()->{check.setEnabled(true);toast(msg(e));});}});});dialog.show();
    }

    private android.graphics.Bitmap decodePixImage(String value){
        try{if(value==null||value.isBlank())return null;String raw=value;int comma=raw.indexOf(',');if(raw.startsWith("data:")&&comma>=0)raw=raw.substring(comma+1);byte[] bytes=android.util.Base64.decode(raw,android.util.Base64.DEFAULT);return android.graphics.BitmapFactory.decodeByteArray(bytes,0,bytes.length);}catch(Exception ignored){return null;}
    }

'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showEarnings/showPaymentSettings boundary não encontrado')

build=re.sub(r'versionCode\s+\d+','versionCode 31',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '3.1-prime'",build,count=1)
main.write_text(text,encoding='utf-8');repo_path.write_text(repo,encoding='utf-8');api_path.write_text(api,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v3.1 PRIME: mini-rota, ganhos reais, carteira separada e recarga PIX aplicados.')
