from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.16 PRIME
# - recupera corrida ativa ao voltar/abrir o app e impede nova corrida simultânea;
# - muda claramente da busca para o acompanhamento quando o motorista aceita;
# - barra fixa com mensagens e cancelamento respeitando as regras do painel;
# - foto, avaliação e veículo do motorista no acompanhamento;
# - autocomplete Mapbox/fallback a partir de 2 caracteres no destino e favoritos.

field='''    private String arrivedNotifiedRideId = "";\n'''
extra='''    private String arrivedNotifiedRideId = "";\n    private boolean restoringActiveRide;\n    private boolean activeRideScreenVisible;\n    private boolean trackingUiActive;\n    private Runnable favoriteAddressSearch;\n    private int favoriteSearchSeq;\n'''
if 'private boolean restoringActiveRide;' not in text:
    if field not in text: raise SystemExit('campo arrivedNotifiedRideId não encontrado')
    text=text.replace(field,extra,1)

# Ao retornar do segundo plano, verifica no banco se existe uma corrida ainda ativa.
old='''    @Override protected void onResume() {\n        super.onResume();\n        if (map != null) map.onResume();\n    }'''
new='''    @Override protected void onResume() {\n        super.onResume();\n        if (map != null) map.onResume();\n        if(token!=null&&!token.isBlank()&&activeRideId==null&&!restoringActiveRide) restoreActiveRideIfNeeded(false);\n    }'''
if old in text:
    text=text.replace(old,new,1)
elif 'restoreActiveRideIfNeeded(false)' not in text:
    raise SystemExit('onResume não encontrado')

# Nunca limpa uma corrida ativa ao tentar voltar para a home.
home_old='''        activeRideId = null;\n        homeMapMode = true;'''
home_new='''        if(activeRideId!=null&&!activeRideId.isBlank()){showActiveRide();return;}\n        activeRideScreenVisible=false;\n        homeMapMode = true;'''
if home_old not in text: raise SystemExit('reset de activeRideId na home não encontrado')
text=text.replace(home_old,home_new,1)

# Recuperação da corrida ativa a partir do Supabase, inclusive depois de o Android recriar o processo.
anchor='''    private void showHome() {\n'''
restore=r'''    private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing){
        if(restoringActiveRide||token==null||token.isBlank())return;
        restoringActiveRide=true;
        io.execute(()->{
            try{
                JSONArray rows=new JSONArray(ApiClient.restGet("rides?status=in.(searching,accepted,driver_arriving,in_progress)&select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,payment_method_preference,driver_id&order=requested_at.desc&limit=1",token));
                if(rows.length()==0){
                    ui.post(()->{restoringActiveRide=false;activeRideId=null;trackingUiActive=false;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();if(goHomeWhenMissing)showHome();});
                    return;
                }
                JSONObject r=rows.getJSONObject(0);
                String id=r.optString("id","");String status=r.optString("status","searching");
                double olat=r.optDouble("origin_lat",Double.NaN),olng=r.optDouble("origin_lng",Double.NaN),dlat=r.optDouble("destination_lat",Double.NaN),dlng=r.optDouble("destination_lng",Double.NaN);
                ui.post(()->{
                    restoringActiveRide=false;
                    if(id.isBlank())return;
                    activeRideId=id;activeRideStatus=status;trackingUiActive=(status.equals("accepted")||status.equals("driver_arriving")||status.equals("in_progress"));
                    if(Double.isFinite(olat)&&Double.isFinite(olng))origin=new GeoPoint(olat,olng);
                    if(Double.isFinite(dlat)&&Double.isFinite(dlng))destination=new GeoPoint(dlat,dlng);
                    originLabel=cleanLabel(r.optString("origin_label",originLabel));destinationLabel=cleanLabel(r.optString("destination_label",destinationLabel));activePaymentMethod=r.optString("payment_method_preference",activePaymentMethod);
                    getPreferences(MODE_PRIVATE).edit().putString("active_ride_id",id).apply();
                    showActiveRide();
                });
            }catch(Exception e){ui.post(()->{restoringActiveRide=false;if(goHomeWhenMissing)showHome();});}
        });
    }

'''
if 'private void restoreActiveRideIfNeeded(boolean goHomeWhenMissing)' not in text:
    if anchor not in text: raise SystemExit('showHome para inserir restore não encontrado')
    text=text.replace(anchor,restore+anchor,1)

# A pesquisa começa mais cedo e responde mais rápido; o endpoint usa Mapbox como primeira fonte.
text=text.replace('''        if (safeQuery.length() < 3) {''','''        if (safeQuery.length() < 2) {''',1)
text=text.replace('''        ui.postDelayed(pendingAddressSearch, 650);''','''        ui.postDelayed(pendingAddressSearch, 280);''',1)
# Alguns encadeamentos antigos podem manter a versão sem safeQuery.
text=text.replace('''        if (query.length() < 3) return;''','''        if (query.length() < 2) return;''',1)

# Antes de criar outra corrida, bloqueia se já houver uma ativa em memória.
request_anchor='''    private void requestRide() {\n        if (destroyed || isFinishing()) return;'''
request_new='''    private void requestRide() {\n        if (destroyed || isFinishing()) return;\n        if(activeRideId!=null&&!activeRideId.isBlank()){toast("Você já possui uma corrida em andamento.");showActiveRide();return;}'''
if request_anchor not in text: raise SystemExit('requestRide final não encontrado')
text=text.replace(request_anchor,request_new,1)

created='''                    activeRideId = finalRideId;\n                    showActiveRide();'''
created_new='''                    activeRideId = finalRideId;\n                    activeRideStatus="searching";trackingUiActive=false;activeRideScreenVisible=false;\n                    getPreferences(MODE_PRIVATE).edit().putString("active_ride_id",finalRideId).apply();\n                    showActiveRide();'''
if created not in text: raise SystemExit('atribuição finalRideId não encontrada')
text=text.replace(created,created_new,1)

# Tela ativa com dois estados claros: procurando e acompanhamento. Ações ficam fixas no rodapé.
pattern=r'''    private void showActiveRide\(\) \{.*?\n    \}\n\n    private void startRidePolling\(\) \{'''
replacement=r'''    private void showActiveRide() {
        if(activeRideId==null||activeRideId.isBlank()){restoreActiveRideIfNeeded(true);return;}
        stopRidePolling();stopHomeDriverPolling();stopPassengerLiveLocation();homeMapMode=false;releaseMap();activeRideScreenVisible=true;

        FrameLayout screen=new FrameLayout(this);screen.setBackgroundColor(LIGHT);
        LinearLayout body=vertical(LIGHT);body.setPadding(dp(18),dp(18),dp(18),dp(122));
        body.addView(text("CLICK-GO",17,BLACK,true));body.addView(space(8));
        activeStatus=text(trackingUiActive?"Corrida em andamento":"Procurando motorista mais próximo…",25,BLACK,true);body.addView(activeStatus,lpMatchWrap());
        activeFare=text(selectedOption==null?"":money(selectedOption.fare),20,BLACK,true);body.addView(activeFare,lpMatchWrap());body.addView(space(12));

        if(!trackingUiActive){
            LinearLayout searching=card(Color.WHITE,Color.rgb(228,228,228),22,18);TextView icon=text("⌖",46,YELLOW,true);icon.setGravity(Gravity.CENTER);searching.addView(icon);TextView copy=text("Sua chamada já foi enviada aos motoristas próximos. Assim que um motorista aceitar, esta tela mudará automaticamente para o acompanhamento em tempo real.",15,GRAY,false);copy.setGravity(Gravity.CENTER);searching.addView(copy);body.addView(searching,lpMatchWrap());body.addView(space(14));
        }else{
            LinearLayout driverCard=card(Color.WHITE,Color.rgb(226,226,226),20,14);LinearLayout driverRow=horizontal();driverRow.setGravity(Gravity.CENTER_VERTICAL);
            activeDriverPhoto=new ImageView(this);activeDriverPhoto.setScaleType(ImageView.ScaleType.CENTER_CROP);activeDriverPhoto.setImageDrawable(PassengerAvatar.markerDrawable(this));driverRow.addView(activeDriverPhoto,new LinearLayout.LayoutParams(dp(72),dp(72)));
            LinearLayout driverCopy=vertical(Color.TRANSPARENT);driverCopy.setPadding(dp(12),0,0,0);activeDriverName=text("Carregando motorista…",18,BLACK,true);activeDriverVehicle=text("Carregando dados do veículo…",13,GRAY,false);activeDriverRating=text("",13,BLACK,true);driverCopy.addView(activeDriverName);driverCopy.addView(activeDriverVehicle);driverCopy.addView(activeDriverRating);driverRow.addView(driverCopy,new LinearLayout.LayoutParams(0,dp(76),1));driverCard.addView(driverRow);body.addView(driverCard,lpMatchWrap());body.addView(space(12));

            FrameLayout mapFrame=new FrameLayout(this);map=new MapView(this);map.setTileSource(TileSourceFactory.MAPNIK);loadMapboxBasemap(map,"streets-v12");map.setMultiTouchControls(true);mapFrame.addView(map,new FrameLayout.LayoutParams(-1,-1));body.addView(mapFrame,lpMatch(dp(310)));body.addView(space(12));
            LinearLayout routeCard=card(Color.WHITE,Color.rgb(226,226,226),20,14);routeCard.addView(text("EMBARQUE",11,GRAY,true));routeCard.addView(text(cleanLabel(originLabel),14,BLACK,true));routeCard.addView(space(7));routeCard.addView(text("DESTINO",11,GRAY,true));routeCard.addView(text(cleanLabel(destinationLabel),14,BLACK,true));body.addView(routeCard,lpMatchWrap());body.addView(space(10));
            activeWaitInfo=text("Acompanhando sua corrida em tempo real.",13,GRAY,false);LinearLayout waitCard=card(Color.rgb(255,248,219),Color.rgb(242,215,107),16,12);waitCard.addView(activeWaitInfo);body.addView(waitCard,lpMatchWrap());
        }

        ScrollView content=new ScrollView(this);content.setFillViewport(true);content.addView(body,new ScrollView.LayoutParams(-1,-2));screen.addView(content,new FrameLayout.LayoutParams(-1,-1));
        LinearLayout actions=horizontal();actions.setGravity(Gravity.CENTER_VERTICAL);actions.setPadding(dp(12),dp(10),dp(12),dp(10));actions.setBackground(round(Color.WHITE,22,Color.rgb(225,225,225)));
        Button chat=secondaryLight("💬");Button cancel=secondaryLight("CANCELAR CORRIDA");cancel.setTextColor(Color.rgb(185,45,45));actions.addView(chat,new LinearLayout.LayoutParams(dp(62),dp(58)));actions.addView(spaceH(9));actions.addView(cancel,new LinearLayout.LayoutParams(0,dp(58),1));
        FrameLayout.LayoutParams actionsLp=new FrameLayout.LayoutParams(-1,FrameLayout.LayoutParams.WRAP_CONTENT);actionsLp.gravity=Gravity.BOTTOM;actionsLp.leftMargin=dp(10);actionsLp.rightMargin=dp(10);actionsLp.bottomMargin=dp(8);screen.addView(actions,actionsLp);
        chat.setOnClickListener(v->openRideChat(activeRideId));cancel.setOnClickListener(v->previewCancel());
        screen.setOnApplyWindowInsetsListener((v,insets)->{int b=0;if(Build.VERSION.SDK_INT>=Build.VERSION_CODES.R)b=insets.getInsets(WindowInsets.Type.systemBars()).bottom;else b=insets.getSystemWindowInsetBottom();actionsLp.bottomMargin=dp(8)+b;actions.setLayoutParams(actionsLp);body.setPadding(dp(18),dp(18),dp(18),dp(122)+b);return insets;});screen.requestApplyInsets();
        setContentView(screen);
        if(trackingUiActive&&map!=null){drawRoute();startPassengerLiveLocation();}
        startRidePolling();
    }

    private void startRidePolling() {'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showActiveRide final não encontrado')

# Polling final: ao aceitar, muda imediatamente para acompanhamento; depois atualiza foto/veículo/GPS.
pattern=r'''    private void startRidePolling\(\) \{.*?\n    \}\n\n    private void stopRidePolling\(\) \{'''
replacement=r'''    private void startRidePolling() {
        stopRidePolling();
        ridePoll=new Runnable(){@Override public void run(){
            if(activeRideId==null||destroyed||isFinishing())return;final String rideId=activeRideId;
            io.execute(()->{try{
                JSONArray rows=new JSONArray(ApiClient.restGet("rides?id=eq."+rideId+"&select=id,status,estimated_fare,final_fare,driver_id,arrived_at,wait_free_seconds,wait_fee_per_minute,wait_charge_amount,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,payment_method_preference",token));
                if(rows.length()==0){ui.postDelayed(ridePoll,2200);return;}JSONObject ride=rows.getJSONObject(0);String status=ride.optString("status","searching"),driverId=ride.optString("driver_id","");double baseFare=ride.isNull("final_fare")?ride.optDouble("estimated_fare",0):ride.optDouble("final_fare",0),recordedWait=ride.optDouble("wait_charge_amount",0);
                JSONObject driverLocation=null,driverCard=null,waitSnapshot=null;
                if(!driverId.isBlank()){
                    JSONArray locs=new JSONArray(ApiClient.restGet("driver_locations?driver_id=eq."+driverId+"&select=lat,lng,heading,speed_kmh,updated_at&limit=1",token));if(locs.length()>0)driverLocation=locs.getJSONObject(0);
                    if(!driverId.equals(renderedDriverId)){JSONArray cards=new JSONArray(ApiClient.rpc("get_passenger_current_driver_card",new JSONObject().put("p_ride_id",rideId),token));if(cards.length()>0)driverCard=cards.getJSONObject(0);}
                }
                if(status.equals("driver_arriving")){JSONArray waits=new JSONArray(ApiClient.rpc("get_ride_wait_snapshot",new JSONObject().put("p_ride_id",rideId),token));if(waits.length()>0)waitSnapshot=waits.getJSONObject(0);}
                JSONObject finalLocation=driverLocation,finalCard=driverCard,finalWait=waitSnapshot;double displayFare=baseFare;if(status.equals("driver_arriving")&&finalWait!=null)displayFare+=finalWait.optDouble("live_wait_charge",0);else if(status.equals("in_progress")&&ride.isNull("final_fare"))displayFare+=recordedWait;double finalDisplayFare=displayFare;
                Bitmap driverPhoto=null;if(finalCard!=null){String avatar=finalCard.optString("avatar_url","");if(!avatar.isBlank())try(InputStream in=new URL(avatar).openStream()){driverPhoto=BitmapFactory.decodeStream(in);}catch(Exception ignored){}}Bitmap finalPhoto=driverPhoto;
                ui.post(()->{
                    if(destroyed||isFinishing()||activeRideId==null||!rideId.equals(activeRideId))return;
                    activeRideStatus=status;getPreferences(MODE_PRIVATE).edit().putString("active_ride_id",rideId).apply();
                    boolean shouldTrack=(status.equals("accepted")||status.equals("driver_arriving")||status.equals("in_progress"))&&!driverId.isBlank();
                    if(shouldTrack&&!trackingUiActive){trackingUiActive=true;renderedDriverId=null;showActiveRide();return;}
                    if(activeStatus!=null)activeStatus.setText(status.equals("accepted")?"Motorista a caminho":status.equals("driver_arriving")?"Seu motorista chegou":status.equals("in_progress")?"Corrida em andamento":statusLabel(status));if(activeFare!=null)activeFare.setText(money(finalDisplayFare));
                    if(finalCard!=null&&trackingUiActive){renderedDriverId=driverId;activeDriverVehicleType=finalCard.optString("vehicle_type","car");String name=finalCard.optString("full_name","Motorista CLICK-GO"),make=finalCard.optString("vehicle_make",""),model=finalCard.optString("vehicle_model",""),year=finalCard.isNull("vehicle_year")?"":String.valueOf(finalCard.optInt("vehicle_year")),color=finalCard.optString("vehicle_color",""),plate=finalCard.optString("vehicle_plate","");String vehicle=(make+" "+model+" "+year).trim();if(!color.isBlank())vehicle+=" · "+color;if(!plate.isBlank())vehicle+=" · "+plate;if(activeDriverName!=null)activeDriverName.setText(name);if(activeDriverVehicle!=null)activeDriverVehicle.setText(vehicle.isBlank()?"Veículo do motorista":vehicle);if(activeDriverRating!=null)activeDriverRating.setText("★ "+String.format(Locale.getDefault(),"%.1f",finalCard.optDouble("rating",0)));if(activeDriverPhoto!=null&&finalPhoto!=null)activeDriverPhoto.setImageBitmap(finalPhoto);}
                    if(activeWaitInfo!=null){if(status.equals("driver_arriving")&&finalWait!=null){int remaining=finalWait.optInt("remaining_free_seconds",0),billable=finalWait.optInt("billable_seconds",0);double fee=finalWait.optDouble("wait_fee_per_minute",0),charge=finalWait.optDouble("live_wait_charge",0);activeWaitInfo.setText(remaining>0?"⏱ Tolerância restante: "+formatClock(remaining)+" · depois "+money(fee)+"/min":"⏱ Espera tarifada: "+formatClock(billable)+" · "+money(charge));}else if(status.equals("accepted"))activeWaitInfo.setText("Motorista a caminho do embarque.");else if(status.equals("in_progress"))activeWaitInfo.setText(recordedWait>0?"Corrida em andamento · espera registrada: "+money(recordedWait):"Corrida em andamento.");}
                    if(status.equals("driver_arriving")&&!rideId.equals(arrivedNotifiedRideId)){arrivedNotifiedRideId=rideId;try{android.os.Vibrator vib=(android.os.Vibrator)getSystemService(VIBRATOR_SERVICE);if(vib!=null){if(Build.VERSION.SDK_INT>=26)vib.vibrate(android.os.VibrationEffect.createOneShot(700,android.os.VibrationEffect.DEFAULT_AMPLITUDE));else vib.vibrate(700);}}catch(Exception ignored){}new AlertDialog.Builder(this).setTitle("Seu motorista chegou!").setMessage("O motorista está no local de embarque.").setPositiveButton("OK",null).show();}
                    if(trackingUiActive)renderActiveDriver(finalLocation);
                    if(status.equals("completed")||status.equals("cancelled")){activeRideId=null;activeRideScreenVisible=false;trackingUiActive=false;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();stopRidePolling();stopPassengerLiveLocation();releaseMap();showEndState(status,finalDisplayFare,rideId);}else ui.postDelayed(ridePoll,2000);
                });
            }catch(Exception e){ui.postDelayed(ridePoll,3500);}});
        }};ui.post(ridePoll);
    }

    private void stopRidePolling() {'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('startRidePolling final não encontrado')

# Limpa a trava somente quando a corrida realmente terminou/cancelou.
end_anchor='''    private void showEndState(String status,double fare,String rideId){'''
end_new='''    private void showEndState(String status,double fare,String rideId){\n        activeRideScreenVisible=false;trackingUiActive=false;activeRideId=null;getPreferences(MODE_PRIVATE).edit().remove("active_ride_id").apply();'''
if end_anchor not in text: raise SystemExit('showEndState final não encontrado')
text=text.replace(end_anchor,end_new,1)

# Favoritos: busca enquanto digita e permite escolher uma sugestão antes de salvar.
pattern=r'''    private void showAddFavorite\(\) \{.*?\n    \}\n\n    private void confirmDeleteFavorite'''
replacement=r'''    private void showAddFavorite() {
        LinearLayout content=showSectionShell("Adicionar favorito");EditText label=editLight("Nome: Casa, Trabalho...");EditText address=editLight("Comece a digitar o endereço");LinearLayout suggestions=vertical(Color.TRANSPARENT);Button save=primary("Salvar favorito");final double[] chosenLat={Double.NaN},chosenLng={Double.NaN};final String[] chosenAddress={""};
        content.addView(label,lpMatch(dp(56)));content.addView(space(9));content.addView(address,lpMatch(dp(56)));content.addView(suggestions,lpMatchWrap());content.addView(space(14));content.addView(save,lpMatch(dp(56)));
        address.addTextChangedListener(new TextWatcher(){@Override public void beforeTextChanged(CharSequence s,int start,int count,int after){}@Override public void afterTextChanged(Editable s){}@Override public void onTextChanged(CharSequence s,int start,int before,int count){String q=s.toString().trim();chosenLat[0]=Double.NaN;chosenLng[0]=Double.NaN;chosenAddress[0]="";scheduleFavoriteLookup(q,suggestions,address,chosenLat,chosenLng,chosenAddress);}});
        save.setOnClickListener(v->{String name=label.getText().toString().trim(),addr=address.getText().toString().trim();if(name.isBlank()||addr.length()<2){toast("Informe um nome e escolha o endereço.");return;}save.setEnabled(false);save.setText("Salvando…");io.execute(()->{try{double lat=chosenLat[0],lng=chosenLng[0];String resolved=chosenAddress[0];if(!Double.isFinite(lat)||!Double.isFinite(lng)){String url=BuildConfig.GEOCODE_URL+"?q="+URLEncoder.encode(addr,StandardCharsets.UTF_8.toString());if(origin!=null)url+="&lat="+origin.getLatitude()+"&lng="+origin.getLongitude();JSONObject result=new JSONObject(ApiClient.absoluteGet(url));JSONArray matches=result.optJSONArray("results");if(matches==null||matches.length()==0)throw new Exception("Endereço não encontrado.");JSONObject first=matches.getJSONObject(0);lat=first.optDouble("lat",Double.NaN);lng=first.optDouble("lng",Double.NaN);resolved=cleanLabel(first.optString("label",addr));}if(!Double.isFinite(lat)||!Double.isFinite(lng))throw new Exception("Endereço sem coordenadas válidas.");String uid=ensureUserId();ApiClient.restPost("passenger_favorites",new JSONObject().put("passenger_id",uid).put("label",name).put("address",resolved.isBlank()?addr:resolved).put("lat",lat).put("lng",lng),token);ui.post(()->{toast("Favorito salvo.");showFavorites();});}catch(Exception e){ui.post(()->{save.setEnabled(true);save.setText("Salvar favorito");toast(message(e));});}});});
    }

    private void scheduleFavoriteLookup(String query,LinearLayout target,EditText address,double[] chosenLat,double[] chosenLng,String[] chosenAddress){
        final int seq=++favoriteSearchSeq;if(favoriteAddressSearch!=null)ui.removeCallbacks(favoriteAddressSearch);target.removeAllViews();if(query==null||query.trim().length()<2)return;TextView loading=text("Buscando endereços…",12,GRAY,false);loading.setPadding(dp(8),dp(8),dp(8),dp(8));target.addView(loading);String q=query.trim().length()>120?query.trim().substring(0,120):query.trim();favoriteAddressSearch=()->io.execute(()->{try{String url=BuildConfig.GEOCODE_URL+"?q="+URLEncoder.encode(q,StandardCharsets.UTF_8.toString());if(origin!=null)url+="&lat="+origin.getLatitude()+"&lng="+origin.getLongitude();JSONObject root=new JSONObject(ApiClient.absoluteGet(url));JSONArray rows=root.optJSONArray("results");ui.post(()->{if(seq!=favoriteSearchSeq||!target.isAttachedToWindow())return;target.removeAllViews();if(rows==null||rows.length()==0){target.addView(text("Nenhum endereço encontrado.",12,GRAY,false));return;}for(int i=0;i<Math.min(rows.length(),6);i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;String label=cleanLabel(r.optString("label",""));double lat=r.optDouble("lat",Double.NaN),lng=r.optDouble("lng",Double.NaN);if(label.isBlank()||!Double.isFinite(lat)||!Double.isFinite(lng))continue;TextView row=text("📍 "+label,14,BLACK,false);row.setPadding(dp(12),dp(10),dp(12),dp(10));row.setBackground(round(Color.WHITE,12,Color.rgb(230,230,230)));row.setOnClickListener(v->{++favoriteSearchSeq;if(favoriteAddressSearch!=null)ui.removeCallbacks(favoriteAddressSearch);chosenLat[0]=lat;chosenLng[0]=lng;chosenAddress[0]=label;address.setText(label);address.setSelection(address.length());target.removeAllViews();hideKeyboard();});target.addView(row,lpMatchWrap());target.addView(space(5));}});}catch(Exception ignored){ui.post(()->{if(seq==favoriteSearchSeq&&target.isAttachedToWindow()){target.removeAllViews();target.addView(text("Busca temporariamente indisponível.",12,GRAY,false));}});}});ui.postDelayed(favoriteAddressSearch,280);
    }

    private void confirmDeleteFavorite'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1: raise SystemExit('showAddFavorite final não encontrado')

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.16-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.16 PRIME: corrida persistente, tracking, cancelamento e autocomplete aplicados.')
