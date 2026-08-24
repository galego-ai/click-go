from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.14 PRIME
# - safe-area real calculada pela navigation bar;
# - carros/motos online com ícones próprios;
# - motorista ativo se move no mesmo marker, com tipo correto;
# - aviso de chegada + cancelar chamado/corrida;
# - avaliação por estrelas clicáveis;
# - histórico com endereço legível + mapa.

# Imports gráficos para ícones de carro/moto.
if 'import android.graphics.Canvas;' not in text:
    text=text.replace('import android.graphics.Color;\n','import android.graphics.Color;\nimport android.graphics.Canvas;\nimport android.graphics.Paint;\n',1)

# Estado do veículo ativo e aviso único de chegada.
field='''    private String activePaymentMethod = "";\n'''
extra='''    private String activePaymentMethod = "";\n    private String activeDriverVehicleType = "car";\n    private String arrivedNotifiedRideId = "";\n'''
if 'private String activeDriverVehicleType' not in text:
    if field not in text: raise SystemExit('activePaymentMethod não encontrado')
    text=text.replace(field,extra,1)

# Ícones vetoriais simples de carro/moto, independentes de URL configurada.
anchor='''    private BitmapDrawable markerIconCached(String url){\n'''
helpers=r'''    private BitmapDrawable vehicleMarkerIcon(String raw){
        String kind=raw==null?"":raw.toLowerCase(Locale.ROOT);
        boolean moto=kind.contains("moto")||kind.contains("motorcycle");
        int size=dp(46);Bitmap bmp=Bitmap.createBitmap(size,size,Bitmap.Config.ARGB_8888);Canvas c=new Canvas(bmp);Paint p=new Paint(Paint.ANTI_ALIAS_FLAG);
        p.setColor(Color.rgb(255,212,0));c.drawCircle(size/2f,size/2f,size*.46f,p);p.setStyle(Paint.Style.STROKE);p.setStrokeWidth(dp(2));p.setColor(BLACK);c.drawCircle(size/2f,size/2f,size*.43f,p);p.setStyle(Paint.Style.FILL);
        if(moto){float y=size*.62f,r=size*.10f;c.drawCircle(size*.30f,y,r,p);c.drawCircle(size*.70f,y,r,p);p.setStrokeWidth(dp(3));p.setStyle(Paint.Style.STROKE);c.drawLine(size*.30f,y,size*.48f,size*.42f,p);c.drawLine(size*.48f,size*.42f,size*.70f,y,p);c.drawLine(size*.44f,size*.44f,size*.62f,size*.44f,p);c.drawLine(size*.60f,size*.44f,size*.67f,size*.34f,p);p.setStyle(Paint.Style.FILL);}else{android.graphics.RectF body=new android.graphics.RectF(size*.20f,size*.40f,size*.80f,size*.66f);c.drawRoundRect(body,dp(5),dp(5),p);android.graphics.RectF roof=new android.graphics.RectF(size*.32f,size*.29f,size*.68f,size*.51f);c.drawRoundRect(roof,dp(5),dp(5),p);p.setColor(Color.WHITE);c.drawRect(size*.38f,size*.33f,size*.49f,size*.44f,p);c.drawRect(size*.52f,size*.33f,size*.63f,size*.44f,p);p.setColor(BLACK);c.drawCircle(size*.32f,size*.68f,size*.075f,p);c.drawCircle(size*.68f,size*.68f,size*.075f,p);}
        return new BitmapDrawable(getResources(),bmp);
    }

'''
if 'private BitmapDrawable vehicleMarkerIcon' not in text:
    if anchor not in text: raise SystemExit('markerIconCached não encontrado')
    text=text.replace(anchor,helpers+anchor,1)

# Home: se categoria não tem imagem customizada, usa carro/moto nativo.
old='''BitmapDrawable icon=icons.get(u);if(icon!=null)m.setIcon(icon);'''
new='''BitmapDrawable icon=icons.get(u);if(icon==null)icon=vehicleMarkerIcon(r.optString("category_name","car"));m.setIcon(icon);'''
if old in text:
    text=text.replace(old,new,2)
elif 'vehicleMarkerIcon(r.optString("category_name"' not in text:
    raise SystemExit('Marcador de motorista próximo não encontrado')

# Safe area: a barra de navegação define a margem inferior do cartão e do botão localizar.
old='''        setContentView(root);\n        applySafeInsets(root);'''
new='''        setContentView(root);\n        root.setOnApplyWindowInsetsListener((v,insets)->{\n            int topInset=0,bottomInset=0;\n            if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.R){android.graphics.Insets bars=insets.getInsets(WindowInsets.Type.systemBars());topInset=bars.top;bottomInset=bars.bottom;}\n            else{topInset=insets.getSystemWindowInsetTop();bottomInset=insets.getSystemWindowInsetBottom();}\n            v.setPadding(0,topInset,0,0);\n            bottomLp.bottomMargin=dp(12)+bottomInset;bottom.setLayoutParams(bottomLp);\n            locateLp.bottomMargin=dp(226)+bottomInset;locate.setLayoutParams(locateLp);\n            return insets;\n        });\n        root.requestApplyInsets();'''
if old not in text: raise SystemExit('safe inset da home não encontrado')
text=text.replace(old,new,1)

# Na corrida ativa, mantém área extra abaixo dos botões e usa Mapbox como mapa base.
text=text.replace('''        body.setPadding(dp(18), dp(20), dp(18), dp(26));''','''        body.setPadding(dp(18), dp(20), dp(18), dp(84));''',1)
text=text.replace('''        map.setTileSource(TileSourceFactory.MAPNIK);\n        map.setMultiTouchControls(true);\n        mapFrame.addView(map,new FrameLayout.LayoutParams(-1,-1));''','''        map.setTileSource(TileSourceFactory.MAPNIK);\n        loadMapboxBasemap(map,"streets-v12");\n        map.setMultiTouchControls(true);\n        mapFrame.addView(map,new FrameLayout.LayoutParams(-1,-1));''',1)
text=text.replace('''        Button cancel = secondaryLight("Cancelar corrida");''','''        Button cancel = secondaryLight("CANCELAR CHAMADO / CORRIDA");''',1)

# Registra tipo do veículo e mostra aviso de chegada uma única vez.
needle='''                                if (activeDriverRating!=null) activeDriverRating.setText("★ "+String.format(Locale.getDefault(),"%.1f",finalCard.optDouble("rating",0)));'''
if needle in text:
    text=text.replace(needle,needle+'\n                                activeDriverVehicleType=finalCard.optString("vehicle_type","car");',1)
elif 'activeDriverVehicleType=finalCard' not in text:
    raise SystemExit('Cartão do motorista não encontrado')

status_anchor='''                            if (activeFare!=null) activeFare.setText(money(finalDisplayFare));'''
arrival='''                            if (activeFare!=null) activeFare.setText(money(finalDisplayFare));\n                            if(status.equals("driver_arriving")&&!rideId.equals(arrivedNotifiedRideId)){\n                                arrivedNotifiedRideId=rideId;\n                                try{android.os.Vibrator vib=(android.os.Vibrator)getSystemService(VIBRATOR_SERVICE);if(vib!=null){if(Build.VERSION.SDK_INT>=26)vib.vibrate(android.os.VibrationEffect.createOneShot(700,android.os.VibrationEffect.DEFAULT_AMPLITUDE));else vib.vibrate(700);}}catch(Exception ignored){}\n                                new AlertDialog.Builder(this).setTitle("Seu motorista chegou!").setMessage("O motorista está no local de embarque.").setPositiveButton("OK",null).show();\n                            }'''
if status_anchor not in text: raise SystemExit('activeFare status não encontrado')
text=text.replace(status_anchor,arrival,1)

# Motorista ativo: atualiza o MESMO marcador para dar sensação de movimento em tempo real.
pattern=r'''    private void renderActiveDriver\(JSONObject loc\) \{.*?\n    \}\n\n    private void drawActiveDriverRoadRoute'''
replacement=r'''    private void renderActiveDriver(JSONObject loc) {
        if(map==null)return;
        if(loc==null){if(activeDriverMarker!=null){map.getOverlays().remove(activeDriverMarker);activeDriverMarker=null;map.invalidate();}return;}
        double lat=loc.optDouble("lat",Double.NaN),lng=loc.optDouble("lng",Double.NaN);if(!Double.isFinite(lat)||!Double.isFinite(lng))return;
        if(activeDriverMarker==null){activeDriverMarker=new Marker(map);activeDriverMarker.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_CENTER);activeDriverMarker.setTitle("Motorista em tempo real");map.getOverlays().add(activeDriverMarker);}else if(!map.getOverlays().contains(activeDriverMarker))map.getOverlays().add(activeDriverMarker);
        activeDriverMarker.setPosition(new GeoPoint(lat,lng));activeDriverMarker.setIcon(vehicleMarkerIcon(activeDriverVehicleType));
        if(loc.has("heading"))try{activeDriverMarker.setRotation((float)loc.optDouble("heading",0));}catch(Exception ignored){}
        map.invalidate();drawActiveDriverRoadRoute(loc);
    }

    private void drawActiveDriverRoadRoute'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('renderActiveDriver v2.11 não encontrado')

# Atualização mais frequente para acompanhamento visual.
text=text.replace('''} else ui.postDelayed(ridePoll,2500);''','''} else ui.postDelayed(ridePoll,2000);''',1)

# Avaliação final por estrelas clicáveis, sem Spinner/lista.
pattern=r'''    private void showEndState\(String status, double fare, String rideId\) \{.*?\n    \}\n\n(?=    private void previewCancel\(\))'''
replacement=r'''    private void showEndState(String status,double fare,String rideId){
        LinearLayout body=vertical(Color.WHITE);body.setPadding(dp(24),dp(42),dp(24),dp(90));TextView icon=text(status.equals("completed")?"✓":"×",46,status.equals("completed")?Color.rgb(22,163,74):Color.rgb(220,70,55),true);icon.setGravity(Gravity.CENTER);body.addView(icon);TextView title=text(status.equals("completed")?"Você chegou!":"Corrida cancelada",30,BLACK,true);title.setGravity(Gravity.CENTER);body.addView(title);TextView fv=text(money(fare),28,BLACK,true);fv.setGravity(Gravity.CENTER);body.addView(fv);body.addView(space(20));
        if(status.equals("completed")){LinearLayout card=card(Color.rgb(250,250,250),Color.rgb(230,230,230),20,16);card.addView(text("Como foi sua viagem?",20,BLACK,true));card.addView(text("Toque nas estrelas para avaliar o motorista",13,GRAY,false));final int[] selected={5};LinearLayout stars=horizontal();stars.setGravity(Gravity.CENTER);TextView[] sv=new TextView[5];for(int i=0;i<5;i++){final int value=i+1;TextView s=text("★",40,Color.rgb(255,193,7),true);s.setGravity(Gravity.CENTER);sv[i]=s;stars.addView(s,new LinearLayout.LayoutParams(0,dp(54),1));s.setOnClickListener(v->{selected[0]=value;for(int j=0;j<5;j++)sv[j].setTextColor(j<value?Color.rgb(255,193,7):Color.rgb(210,210,210));});}card.addView(stars);EditText comment=editLight("Comentário opcional");comment.setSingleLine(false);comment.setMinLines(3);comment.setGravity(Gravity.TOP);card.addView(comment,new LinearLayout.LayoutParams(-1,dp(105)));Button send=primary("ENVIAR AVALIAÇÃO");card.addView(space(8));card.addView(send,lpMatch(dp(58)));send.setOnClickListener(v->{String note=comment.getText().toString().trim();send.setEnabled(false);io.execute(()->{try{ApiClient.rpc("submit_passenger_ride_rating",new JSONObject().put("p_ride_id",rideId).put("p_rating",selected[0]).put("p_comment",note.isBlank()?JSONObject.NULL:note),token);ui.post(()->send.setText("AVALIAÇÃO ENVIADA ✓"));}catch(Exception e){ui.post(()->{send.setEnabled(true);toast(message(e));});}});});body.addView(card,lpMatchWrap());body.addView(space(16));}
        Button again=primary("NOVA CORRIDA");body.addView(again,lpMatch(dp(60)));again.setOnClickListener(v->{destination=null;destinationLabel="";activePaymentMethod="";arrivedNotifiedRideId="";showHome();});setContentView(scroll(body,Color.WHITE));
    }

'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showEndState v2.12 não encontrado')

# Histórico: coordenadas antigas são convertidas para endereço; botão abre o mapa.
history_query='''"rides?select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,payment_method_preference&order=requested_at.desc&limit=50",'''
new_query='''"rides?select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,final_fare,requested_at,payment_method_preference&order=requested_at.desc&limit=50",'''
if history_query in text:text=text.replace(history_query,new_query,1)
elif 'origin_lat,origin_lng,destination_label,destination_lat,destination_lng' not in text:raise SystemExit('Query do histórico não encontrada')

anchor='''    private void showHistory() {\n'''
helpers=r'''    private boolean historyCoordinateLike(String value){if(value==null)return true;String s=value.trim().toLowerCase(Locale.ROOT);if(s.isBlank())return true;return s.matches("^-?\\d{1,3}[.,]\\d{3,}\\s*[,;/]\\s*-?\\d{1,3}[.,]\\d{3,}$")||s.contains("latitude")||s.contains("longitude");}
    private String resolveHistoryAddress(String label,double lat,double lng){if(!historyCoordinateLike(label))return cleanLabel(label);if(!Double.isFinite(lat)||!Double.isFinite(lng))return "Endereço não informado";try{String url=BuildConfig.GEOCODE_URL+"?reverse=1&lat="+lat+"&lng="+lng;JSONObject root=new JSONObject(ApiClient.absoluteGet(url));JSONArray r=root.optJSONArray("results");if(r!=null&&r.length()>0){String v=cleanLabel(r.getJSONObject(0).optString("label",""));if(!v.isBlank())return v;}}catch(Exception ignored){}return "Localização da corrida";}
    private void openPassengerHistoryMap(double oLat,double oLng,double dLat,double dLng){double lat=Double.isFinite(dLat)?dLat:oLat,lng=Double.isFinite(dLng)?dLng:oLng;if(!Double.isFinite(lat)||!Double.isFinite(lng)){toast("Localização não disponível.");return;}try{startActivity(new android.content.Intent(android.content.Intent.ACTION_VIEW,android.net.Uri.parse("geo:"+lat+","+lng+"?q="+lat+","+lng)));}catch(Exception e){toast("Não foi possível abrir o mapa.");}}

'''
if 'private String resolveHistoryAddress' not in text:
    if anchor not in text:raise SystemExit('showHistory não encontrado')
    text=text.replace(anchor,helpers+anchor,1)

# Resolve os endereços antes de renderizar.
needle='''                ui.post(() -> {\n                    if (destroyed || !content.isAttachedToWindow()) return;'''
insert='''                for(int j=0;j<rows.length();j++){JSONObject rr=rows.optJSONObject(j);if(rr==null)continue;double ol=rr.optDouble("origin_lat",Double.NaN),og=rr.optDouble("origin_lng",Double.NaN),dl=rr.optDouble("destination_lat",Double.NaN),dg=rr.optDouble("destination_lng",Double.NaN);rr.put("_origin_address",resolveHistoryAddress(rr.optString("origin_label",""),ol,og));rr.put("_destination_address",resolveHistoryAddress(rr.optString("destination_label",""),dl,dg));}\n                ui.post(() -> {\n                    if (destroyed || !content.isAttachedToWindow()) return;'''
# Primeira ocorrência após showHistory.
pos=text.find('    private void showHistory() {')
if pos<0:raise SystemExit('showHistory ausente')
idx=text.find(needle,pos)
if idx<0:raise SystemExit('ui.post do histórico não encontrado')
text=text[:idx]+text[idx:].replace(needle,insert,1)

text=text.replace('''String route = cleanLabel(ride.optString("origin_label", "")) + "\\n→ " + cleanLabel(ride.optString("destination_label", ""));''','''String route = ride.optString("_origin_address","Endereço não informado") + "\\n→ " + ride.optString("_destination_address","Endereço não informado");''',1)
# Adiciona botão mapa no card do histórico.
needle='''                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));\n                        content.addView(card, lpMatchWrap());'''
replacement='''                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));\n                        Button mapBtn=smallButton("VER NO MAPA");double ol=ride.optDouble("origin_lat",Double.NaN),og=ride.optDouble("origin_lng",Double.NaN),dl=ride.optDouble("destination_lat",Double.NaN),dg=ride.optDouble("destination_lng",Double.NaN);mapBtn.setOnClickListener(v->openPassengerHistoryMap(ol,og,dl,dg));card.addView(space(8));card.addView(mapBtn,lpMatch(dp(46)));\n                        content.addView(card, lpMatchWrap());'''
if needle not in text:raise SystemExit('Card histórico não encontrado')
text=text.replace(needle,replacement,1)

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.14-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.14 PRIME: safe-area, veículos ao vivo, chegada, cancelamento, estrelas e histórico por endereço aplicados.')
