from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

# Imports usados pelo cartão do motorista.
if 'import android.widget.ImageView;' not in text:
    text=text.replace('import android.widget.FrameLayout;\n','import android.widget.FrameLayout;\nimport android.widget.ImageView;\n',1)
if 'import android.graphics.Bitmap;' not in text:
    text=text.replace('import android.graphics.Color;\n','import android.graphics.Color;\nimport android.graphics.Bitmap;\nimport android.graphics.BitmapFactory;\n',1)
if 'import java.net.URL;' not in text:
    text=text.replace('import java.net.URLEncoder;\n','import java.net.URLEncoder;\nimport java.net.URL;\nimport java.io.InputStream;\n',1)

# Campos da tela da corrida ativa.
field='''    private TextView activeFare;\n'''
extra='''    private TextView activeFare;\n    private TextView activeDriverName;\n    private TextView activeDriverVehicle;\n    private TextView activeDriverRating;\n    private TextView activeWaitInfo;\n    private ImageView activeDriverPhoto;\n    private String renderedDriverId;\n'''
if field in text and 'private TextView activeDriverName;' not in text:
    text=text.replace(field,extra,1)

# Substitui a tela estável v2.5 por uma tela com UM único mapa de corrida ativa.
pattern=r'''    private void showActiveRide\(\) \{.*?\n    \}\n\n    private void startRidePolling\(\) \{'''
replacement=r'''    private void showActiveRide() {
        stopRidePolling();
        stopHomeDriverPolling();
        homeMapMode = false;
        releaseMap();
        renderedDriverId = null;

        LinearLayout body = vertical(LIGHT);
        body.setPadding(dp(18), dp(20), dp(18), dp(26));
        body.addView(text("CLICK-GO", 18, BLACK, true));
        body.addView(space(10));

        activeStatus = text("Procurando motorista mais próximo…", 25, BLACK, true);
        body.addView(activeStatus, lpMatchWrap());
        activeFare = text(selectedOption == null ? "" : money(selectedOption.fare), 21, BLACK, true);
        body.addView(activeFare, lpMatchWrap());
        body.addView(space(12));

        LinearLayout driverCard = card(Color.WHITE, Color.rgb(226,226,226), 20, 14);
        LinearLayout driverRow = horizontal();
        driverRow.setGravity(Gravity.CENTER_VERTICAL);
        activeDriverPhoto = new ImageView(this);
        activeDriverPhoto.setScaleType(ImageView.ScaleType.CENTER_CROP);
        activeDriverPhoto.setImageDrawable(PassengerAvatar.markerDrawable(this));
        driverRow.addView(activeDriverPhoto, new LinearLayout.LayoutParams(dp(68),dp(68)));
        LinearLayout driverCopy = vertical(Color.TRANSPARENT);
        driverCopy.setPadding(dp(12),0,0,0);
        activeDriverName = text("Aguardando motorista…",18,BLACK,true);
        activeDriverVehicle = text("Os dados aparecerão assim que a corrida for aceita.",13,GRAY,false);
        activeDriverRating = text("",13,BLACK,true);
        driverCopy.addView(activeDriverName);
        driverCopy.addView(activeDriverVehicle);
        driverCopy.addView(activeDriverRating);
        driverRow.addView(driverCopy,new LinearLayout.LayoutParams(0,dp(72),1));
        driverCard.addView(driverRow);
        body.addView(driverCard,lpMatchWrap());
        body.addView(space(12));

        FrameLayout mapFrame = new FrameLayout(this);
        map = new MapView(this);
        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        mapFrame.addView(map,new FrameLayout.LayoutParams(-1,-1));
        body.addView(mapFrame,lpMatch(dp(310)));
        body.addView(space(12));

        LinearLayout routeCard = card(Color.WHITE, Color.rgb(226,226,226), 20, 14);
        routeCard.addView(text("EMBARQUE",11,GRAY,true));
        routeCard.addView(text(cleanLabel(originLabel),14,BLACK,true));
        routeCard.addView(space(7));
        routeCard.addView(text("DESTINO",11,GRAY,true));
        routeCard.addView(text(cleanLabel(destinationLabel),14,BLACK,true));
        body.addView(routeCard,lpMatchWrap());
        body.addView(space(10));

        activeWaitInfo = text("A tolerância de espera será mostrada quando o motorista chegar ao embarque.",13,GRAY,false);
        LinearLayout waitCard = card(Color.rgb(255,248,219),Color.rgb(242,215,107),16,12);
        waitCard.addView(activeWaitInfo);
        body.addView(waitCard,lpMatchWrap());
        body.addView(space(12));

        Button share = primary("Compartilhar acompanhamento");
        Button cancel = secondaryLight("Cancelar corrida");
        body.addView(share,lpMatch(dp(56)));
        body.addView(space(8));
        body.addView(cancel,lpMatch(dp(56)));
        share.setOnClickListener(v -> shareActiveRide());
        cancel.setOnClickListener(v -> previewCancel());

        setContentView(scroll(body,LIGHT));
        drawRoute();
        startPassengerLiveLocation();
        startRidePolling();
    }

    private void startRidePolling() {'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1:
    raise SystemExit('showActiveRide v2.5 não encontrado')

# Polling: status + motorista/veículo + GPS + relógio de espera vindo do banco.
pattern=r'''    private void startRidePolling\(\) \{.*?\n    \}\n\n    private void stopRidePolling\(\) \{'''
replacement=r'''    private void startRidePolling() {
        stopRidePolling();
        ridePoll = new Runnable() {
            @Override public void run() {
                if (activeRideId == null || destroyed || isFinishing()) return;
                final String rideId = activeRideId;
                io.execute(() -> {
                    try {
                        JSONArray rows = new JSONArray(ApiClient.restGet(
                                "rides?id=eq." + rideId + "&select=id,status,estimated_fare,final_fare,driver_id,arrived_at,wait_free_seconds,wait_fee_per_minute,wait_charge_amount", token));
                        if (rows.length() == 0) { ui.postDelayed(ridePoll,3000); return; }
                        JSONObject ride = rows.getJSONObject(0);
                        String status = ride.optString("status","searching");
                        String driverId = ride.optString("driver_id","");
                        double baseFare = ride.isNull("final_fare") ? ride.optDouble("estimated_fare",0) : ride.optDouble("final_fare",0);
                        double recordedWait = ride.optDouble("wait_charge_amount",0);

                        JSONObject driverLocation = null;
                        JSONObject driverCard = null;
                        JSONObject waitSnapshot = null;

                        if (!driverId.isBlank()) {
                            JSONArray locs = new JSONArray(ApiClient.restGet("driver_locations?driver_id=eq." + driverId + "&select=lat,lng,heading,speed_kmh,updated_at&limit=1",token));
                            if (locs.length()>0) driverLocation=locs.getJSONObject(0);
                            if (!driverId.equals(renderedDriverId)) {
                                JSONArray cards = new JSONArray(ApiClient.rpc("get_passenger_current_driver_card",new JSONObject().put("p_ride_id",rideId),token));
                                if (cards.length()>0) driverCard=cards.getJSONObject(0);
                            }
                        }
                        if (status.equals("driver_arriving")) {
                            JSONArray waits = new JSONArray(ApiClient.rpc("get_ride_wait_snapshot",new JSONObject().put("p_ride_id",rideId),token));
                            if (waits.length()>0) waitSnapshot=waits.getJSONObject(0);
                        }

                        JSONObject finalLocation=driverLocation;
                        JSONObject finalCard=driverCard;
                        JSONObject finalWait=waitSnapshot;
                        double displayFare=baseFare;
                        if (status.equals("driver_arriving") && finalWait!=null) displayFare += finalWait.optDouble("live_wait_charge",0);
                        else if (status.equals("in_progress") && ride.isNull("final_fare")) displayFare += recordedWait;
                        double finalDisplayFare=displayFare;

                        Bitmap driverPhoto=null;
                        if (finalCard!=null) {
                            String avatar=finalCard.optString("avatar_url","");
                            if (!avatar.isBlank()) try(InputStream in=new URL(avatar).openStream()){driverPhoto=BitmapFactory.decodeStream(in);}catch(Exception ignored){}
                        }
                        Bitmap finalPhoto=driverPhoto;

                        ui.post(() -> {
                            if (destroyed || isFinishing() || activeRideId==null || !rideId.equals(activeRideId)) return;
                            if (activeStatus!=null) {
                                activeStatus.setText(status.equals("accepted")?"Motorista a caminho":status.equals("driver_arriving")?"Motorista chegou ao embarque":status.equals("in_progress")?"Corrida em andamento":statusLabel(status));
                            }
                            if (activeFare!=null) activeFare.setText(money(finalDisplayFare));

                            if (finalCard!=null) {
                                renderedDriverId=driverId;
                                String name=finalCard.optString("full_name","Motorista CLICK-GO");
                                String make=finalCard.optString("vehicle_make","");
                                String model=finalCard.optString("vehicle_model","");
                                String year=finalCard.isNull("vehicle_year")?"":String.valueOf(finalCard.optInt("vehicle_year"));
                                String color=finalCard.optString("vehicle_color","");
                                String plate=finalCard.optString("vehicle_plate","");
                                String vehicle=(make+" "+model+" "+year).trim();
                                if (!color.isBlank()) vehicle += " · "+color;
                                if (!plate.isBlank()) vehicle += " · "+plate;
                                if (activeDriverName!=null) activeDriverName.setText(name);
                                if (activeDriverVehicle!=null) activeDriverVehicle.setText(vehicle.isBlank()?"Veículo do motorista":vehicle);
                                if (activeDriverRating!=null) activeDriverRating.setText("★ "+String.format(Locale.getDefault(),"%.1f",finalCard.optDouble("rating",0)));
                                if (activeDriverPhoto!=null && finalPhoto!=null) activeDriverPhoto.setImageBitmap(finalPhoto);
                            }

                            if (activeWaitInfo!=null) {
                                if (status.equals("driver_arriving") && finalWait!=null) {
                                    int remaining=finalWait.optInt("remaining_free_seconds",0);
                                    int billable=finalWait.optInt("billable_seconds",0);
                                    double fee=finalWait.optDouble("wait_fee_per_minute",0);
                                    double charge=finalWait.optDouble("live_wait_charge",0);
                                    activeWaitInfo.setText(remaining>0
                                            ? "⏱ Tolerância restante: "+formatClock(remaining)+" · depois "+money(fee)+"/min"
                                            : "⏱ Espera tarifada: "+formatClock(billable)+" · "+money(charge)+" ("+money(fee)+"/min)");
                                } else if (status.equals("in_progress") && recordedWait>0) {
                                    activeWaitInfo.setText("Espera registrada no embarque: "+money(recordedWait));
                                } else if (status.equals("accepted")) {
                                    activeWaitInfo.setText("A tolerância começa somente quando o motorista tocar em ‘Cheguei ao embarque’. ");
                                } else {
                                    activeWaitInfo.setText("Corrida em andamento.");
                                }
                            }

                            renderActiveDriver(finalLocation);
                            if (status.equals("completed") || status.equals("cancelled")) {
                                activeRideId=null; stopRidePolling(); stopPassengerLiveLocation(); releaseMap(); showEndState(status,finalDisplayFare);
                            } else ui.postDelayed(ridePoll,2500);
                        });
                    } catch(Exception ignored) {
                        ui.postDelayed(ridePoll,4000);
                    }
                });
            }
        };
        ui.post(ridePoll);
    }

    private void stopRidePolling() {'''
text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
if n!=1:
    raise SystemExit('startRidePolling v2.5 não encontrado')

# Relógio mm:ss.
marker='''    private void stopRidePolling() {'''
# Insere helper antes de showEndState para evitar interferir no corpo do stopRidePolling.
anchor='''    private void showEndState(String status, double fare) {\n'''
helper='''    private String formatClock(int seconds) {\n        int value=Math.max(0,seconds);\n        return String.format(Locale.getDefault(),"%02d:%02d",value/60,value%60);\n    }\n\n'''
if anchor not in text:
    raise SystemExit('showEndState não encontrado')
if 'private String formatClock(int seconds)' not in text:
    text=text.replace(anchor,helper+anchor,1)

# v2.6 PRIME.
build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.6-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.6 PRIME: motorista/veículo, rastreamento e espera ao vivo aplicados.')
