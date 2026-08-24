from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# v2.8 PRIME: mapa-first inspirado em apps de mobilidade, sem copiar identidade de terceiros.
# Oferta vira modal central obrigatório; avaliação passa a ser por estrelas clicáveis;
# histórico usa endereço legível e oferece acesso ao mapa.

# Home map-first com informações essenciais e menu existente.
pattern=r'''    private void showHome\(\) \{.*?\n    \}\n\n(?=    private void toggleOnline\(\))'''
replacement=r'''    private void showHome() {
        PushRegistration.register(this,token,"driver");
        syncFloatingBubble();
        stopPolling();
        releaseMap();

        FrameLayout root=new FrameLayout(this);
        root.setBackgroundColor(Color.rgb(242,242,242));
        map=new MapView(this);
        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        root.addView(map,new FrameLayout.LayoutParams(-1,-1));

        LinearLayout top=horizontal();
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setPadding(dp(12),dp(10),dp(12),dp(10));
        top.setBackground(round(Color.WHITE,22,Color.rgb(230,230,230)));
        Button menuBtn=darkButton("☰");
        top.addView(menuBtn,new LinearLayout.LayoutParams(dp(52),dp(52)));
        ImageView avatar=new ImageView(this);
        avatar.setImageDrawable(ProfileAvatar.circleDrawable(this,avatarBitmap,fullName));
        avatar.setScaleType(ImageView.ScaleType.CENTER_CROP);
        top.addView(avatar,new LinearLayout.LayoutParams(dp(48),dp(48)));
        LinearLayout identity=vertical(Color.TRANSPARENT);
        identity.setPadding(dp(10),0,0,0);
        identity.addView(text(firstName(fullName),17,BLACK,true));
        identity.addView(text("★ "+String.format(Locale.getDefault(),"%.1f",rating)+" · "+statusLabel(),12,Color.DKGRAY,false));
        top.addView(identity,new LinearLayout.LayoutParams(0,dp(50),1));
        FrameLayout.LayoutParams topLp=new FrameLayout.LayoutParams(-1,dp(72));
        topLp.gravity=Gravity.TOP;topLp.leftMargin=dp(12);topLp.rightMargin=dp(12);topLp.topMargin=dp(12);
        root.addView(top,topLp);

        LinearLayout bottom=vertical(Color.WHITE);
        bottom.setPadding(dp(16),dp(14),dp(16),dp(16));
        bottom.setBackground(round(Color.WHITE,24,Color.rgb(225,225,225)));
        LinearLayout walletRow=horizontal();walletRow.setGravity(Gravity.CENTER_VERTICAL);
        LinearLayout walletCopy=vertical(Color.TRANSPARENT);
        walletCopy.addView(text("CLICK-GO MOTORISTA",11,Color.DKGRAY,true));
        walletText=text(walletLabel(),14,BLACK,true);walletCopy.addView(walletText);
        walletRow.addView(walletCopy,new LinearLayout.LayoutParams(0,dp(44),1));
        TextView state=text(online?"ONLINE":"OFFLINE",12,online?GREEN:Color.DKGRAY,true);state.setGravity(Gravity.CENTER);
        walletRow.addView(state,new LinearLayout.LayoutParams(dp(82),dp(40)));
        bottom.addView(walletRow);
        bottom.addView(space(8));

        Button onlineBtn=primary(online?"FICAR OFFLINE":"FICAR ONLINE");
        if(online){onlineBtn.setBackground(round(BLACK,18,BLACK));onlineBtn.setTextColor(Color.WHITE);}
        bottom.addView(onlineBtn,match(dp(60)));
        bottom.addView(space(10));
        operationTitle=text(online?"Aguardando chamadas":"Fique online para receber corridas",15,BLACK,true);
        bottom.addView(operationTitle);
        operationBox=vertical(Color.WHITE);bottom.addView(operationBox,wrap());

        FrameLayout.LayoutParams bottomLp=new FrameLayout.LayoutParams(-1,FrameLayout.LayoutParams.WRAP_CONTENT);
        bottomLp.gravity=Gravity.BOTTOM;bottomLp.leftMargin=dp(12);bottomLp.rightMargin=dp(12);bottomLp.bottomMargin=dp(14);
        root.addView(bottom,bottomLp);

        menuBtn.setOnClickListener(v->showDriverMenu());
        onlineBtn.setOnClickListener(v->toggleOnline());
        setContentView(root);
        if(online){startLocationWatch();startPolling();}else DriverMapRenderer.render(map,currentLocation,null,dp(5));
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showHome final não encontrado')

# Oferta sempre em modal central, sem cartão operacional embaixo.
pattern=r'''    private void renderOffer\(JSONObject o\)\{.*?\n    \}\n(?=    private void respond\(String id,boolean accept\))'''
replacement=r'''    private void renderOffer(JSONObject o){
        if(operationBox==null)return;
        operationBox.removeAllViews();
        if(o==null){
            stopOfferCountdown();stopRideCallSound(true);dismissOfferDialog();
            operationTitle.setText("Aguardando chamadas");
            DriverMapRenderer.render(map,currentLocation,null,dp(5));
            return;
        }
        final String offerId=o.optString("offer_id","");
        if(offerId.isBlank())return;
        startRideCallSound(offerId);
        operationTitle.setText("Nova chamada recebida");
        operationBox.addView(text("Abra o aviso central para responder.",12,Color.DKGRAY,false));
        DriverMapRenderer.render(map,currentLocation,o,dp(5));
        drawDriverRoadRoute(o);
        if(offerDialog!=null&&offerDialog.isShowing()&&offerId.equals(offerDialogId))return;
        stopOfferCountdown();dismissOfferDialog();offerDialogId=offerId;

        LinearLayout c=vertical(Color.WHITE);c.setPadding(dp(20),dp(18),dp(20),dp(18));
        TextView badge=text("NOVA CORRIDA",12,Color.rgb(80,80,80),true);badge.setGravity(Gravity.CENTER);c.addView(badge);
        TextView cat=text(o.optString("category_name","CLICK-GO"),25,BLACK,true);cat.setGravity(Gravity.CENTER);c.addView(cat);
        TextView timer=text("20s para responder",15,Color.rgb(217,148,0),true);timer.setGravity(Gravity.CENTER);c.addView(timer);c.addView(space(14));
        LinearLayout route=card(Color.rgb(247,247,247),Color.rgb(225,225,225));
        route.addView(text("EMBARQUE",10,Color.DKGRAY,true));route.addView(text(o.optString("origin_label","Local de embarque"),16,BLACK,true));route.addView(space(9));
        route.addView(text("DESTINO",10,Color.DKGRAY,true));route.addView(text(o.optString("destination_label","Destino"),14,Color.DKGRAY,false));c.addView(route,wrap());c.addView(space(12));
        String d=o.has("distance_to_pickup_km")?String.format(Locale.getDefault(),"%.1f km",o.optDouble("distance_to_pickup_km",0)):"—";
        String eta=o.has("eta_to_pickup_min")?o.optInt("eta_to_pickup_min",0)+" min":"—";
        LinearLayout metrics=horizontal();metrics.addView(text("Até você: "+d,14,BLACK,true),new LinearLayout.LayoutParams(0,dp(40),1));metrics.addView(text("Previsão: "+eta,14,BLACK,true),new LinearLayout.LayoutParams(0,dp(40),1));c.addView(metrics);
        double gross=o.optDouble("estimated_fare",o.optDouble("estimated_driver_earning",0));
        TextView fare=text(money(gross),30,BLACK,true);fare.setGravity(Gravity.CENTER);c.addView(fare);c.addView(space(12));
        LinearLayout actions=horizontal();Button no=darkButton("RECUSAR");Button yes=primary("ACEITAR");actions.addView(no,new LinearLayout.LayoutParams(0,dp(62),1));actions.addView(spaceH(10));actions.addView(yes,new LinearLayout.LayoutParams(0,dp(62),1));c.addView(actions);

        android.app.AlertDialog dialog=new android.app.AlertDialog.Builder(this).setView(c).create();
        dialog.setCancelable(false);dialog.setCanceledOnTouchOutside(false);offerDialog=dialog;
        yes.setOnClickListener(v->{dismissOfferDialog();respond(offerId,true);});no.setOnClickListener(v->{dismissOfferDialog();respond(offerId,false);});
        dialog.setOnShowListener(x->{android.view.Window w=dialog.getWindow();if(w!=null){w.setBackgroundDrawableResource(android.R.color.transparent);w.addFlags(android.view.WindowManager.LayoutParams.FLAG_DIM_BEHIND);android.view.WindowManager.LayoutParams lp=w.getAttributes();lp.dimAmount=.72f;lp.width=getResources().getDisplayMetrics().widthPixels-dp(24);w.setAttributes(lp);}});
        dialog.show();
        if(dialog.getWindow()!=null)dialog.getWindow().setLayout(getResources().getDisplayMetrics().widthPixels-dp(24),android.view.ViewGroup.LayoutParams.WRAP_CONTENT);
        startOfferCountdown(timer);
    }
'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderOffer v2.7 não encontrado')

# Avaliação do passageiro com 5 estrelas clicáveis.
pattern=r'''    private void showPassengerRating\(String rideId, double fare\) \{.*?\n    \}\n\n(?=    private void markGoingAndNavigate)'''
replacement=r'''    private void showPassengerRating(String rideId,double fare){
        LinearLayout wrap=vertical(Color.WHITE);wrap.setPadding(dp(20),dp(18),dp(20),dp(14));
        wrap.addView(text("Corrida concluída",24,BLACK,true));wrap.addView(text("Valor: "+money(fare),18,BLACK,true));wrap.addView(space(14));wrap.addView(text("Como foi o passageiro?",18,BLACK,true));
        final int[] selected={5};LinearLayout stars=horizontal();stars.setGravity(Gravity.CENTER);
        TextView[] starViews=new TextView[5];
        for(int i=0;i<5;i++){final int value=i+1;TextView s=text("★",38,Color.rgb(255,193,7),true);s.setGravity(Gravity.CENTER);starViews[i]=s;stars.addView(s,new LinearLayout.LayoutParams(0,dp(52),1));s.setOnClickListener(v->{selected[0]=value;for(int j=0;j<5;j++)starViews[j].setTextColor(j<value?Color.rgb(255,193,7):Color.rgb(210,210,210));});}
        wrap.addView(stars);EditText comment=new EditText(this);comment.setHint("Comentário opcional");comment.setTextColor(BLACK);comment.setHintTextColor(Color.GRAY);comment.setMinLines(3);comment.setGravity(Gravity.TOP);comment.setPadding(dp(12),dp(10),dp(12),dp(10));comment.setBackground(round(Color.rgb(247,247,247),12,Color.rgb(220,220,220)));wrap.addView(comment,new LinearLayout.LayoutParams(-1,dp(105)));
        new AlertDialog.Builder(this).setView(wrap).setNegativeButton("Agora não",null).setPositiveButton("Enviar",(d,w)->{String note=comment.getText().toString().trim();io.execute(()->{try{DriverRepository.submitPassengerRating(token,rideId,selected[0],note);ui.post(()->toast("Avaliação enviada."));}catch(Exception e){ui.post(()->toast(msg(e)));}});}).show();
    }

'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showPassengerRating não encontrado')

# Histórico: inclui coordenadas para botão mapa e resolve labels antigas que eram coordenadas.
repo=repo.replace('select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,completed_at,cancelled_at','select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,final_fare,requested_at,completed_at,cancelled_at',1)

# Helpers de histórico.
anchor='''    private void showRideHistory(){\n'''
helpers=r'''    private boolean coordinateLike(String value){
        if(value==null)return true;String s=value.trim().toLowerCase(Locale.ROOT);if(s.isBlank())return true;
        return s.matches("^-?\\d{1,3}[.,]\\d{3,}\\s*[,;/]\\s*-?\\d{1,3}[.,]\\d{3,}$")||s.contains("latitude")||s.contains("longitude");
    }

    private String historyAddress(String label,double lat,double lng){
        if(!coordinateLike(label))return label;
        if(!Double.isFinite(lat)||!Double.isFinite(lng))return "Endereço não informado";
        try{String url="https://click-go-ten.vercel.app/api/geocode?reverse=1&lat="+lat+"&lng="+lng;JSONObject root=new JSONObject(ApiClient.absoluteGet(url));JSONArray rows=root.optJSONArray("results");if(rows!=null&&rows.length()>0){String v=rows.getJSONObject(0).optString("label","").trim();if(!v.isBlank())return v;}}catch(Exception ignored){}
        return String.format(Locale.getDefault(),"Local %.5f, %.5f",lat,lng);
    }

    private void openHistoryMap(double oLat,double oLng,double dLat,double dLng){
        double lat=Double.isFinite(dLat)?dLat:oLat,lng=Double.isFinite(dLng)?dLng:oLng;if(!Double.isFinite(lat)||!Double.isFinite(lng)){toast("Localização não disponível.");return;}
        try{android.content.Intent i=new android.content.Intent(android.content.Intent.ACTION_VIEW,android.net.Uri.parse("geo:"+lat+","+lng+"?q="+lat+","+lng));startActivity(i);}catch(Exception e){toast("Não foi possível abrir o mapa.");}
    }

'''
if helpers.strip() not in text:
    if anchor not in text: raise SystemExit('showRideHistory não encontrado')
    text=text.replace(anchor,helpers+anchor,1)

# Substitui histórico por versão com endereços legíveis e botão mapa.
pattern=r'''    private void showRideHistory\(\)\{.*?\n    \}\n\n(?=    private void showEarnings\(\))'''
replacement=r'''    private void showRideHistory(){
        LinearLayout body=pageShell("Histórico de corridas","Endereços, valores e acesso rápido ao mapa.");TextView loading=text("Carregando histórico…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONArray rows=DriverRepository.rideHistory(token,userId);for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;double ol=r.optDouble("origin_lat",Double.NaN),og=r.optDouble("origin_lng",Double.NaN),dl=r.optDouble("destination_lat",Double.NaN),dg=r.optDouble("destination_lng",Double.NaN);r.put("_origin",historyAddress(r.optString("origin_label",""),ol,og));r.put("_destination",historyAddress(r.optString("destination_label",""),dl,dg));}
            ui.post(()->{body.removeView(loading);if(rows.length()==0){body.addView(text("Nenhuma corrida no histórico.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));String status=r.optString("status","");double fare=r.optDouble("final_fare",r.optDouble("estimated_fare",0));c.addView(text(status.equals("completed")?"Corrida concluída":"Corrida "+status,15,status.equals("completed")?Color.rgb(74,222,128):YELLOW,true));c.addView(text("De: "+r.optString("_origin","Endereço não informado"),14,Color.WHITE,false));c.addView(text("Para: "+r.optString("_destination","Endereço não informado"),14,GRAY,false));if(fare>0)c.addView(text("Valor: "+money(fare),15,YELLOW,true));Button mapBtn=darkButton("VER NO MAPA");double ol=r.optDouble("origin_lat",Double.NaN),og=r.optDouble("origin_lng",Double.NaN),dl=r.optDouble("destination_lat",Double.NaN),dg=r.optDouble("destination_lng",Double.NaN);mapBtn.setOnClickListener(v->openHistoryMap(ol,og,dl,dg));c.addView(space(8));c.addView(mapBtn,match(dp(48)));body.addView(c);body.addView(space(9));}});
        }catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showRideHistory final não encontrado')

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.8-prime'",build,count=1)
main.write_text(text,encoding='utf-8');repo_path.write_text(repo,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v2.8 PRIME: UI mapa-first, popup central, estrelas e histórico por endereço aplicados.')
