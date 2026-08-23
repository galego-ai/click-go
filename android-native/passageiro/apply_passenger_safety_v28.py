from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

# Campos da segurança na corrida ativa.
field='''    private ImageView activeDriverPhoto;\n    private String renderedDriverId;\n'''
fields='''    private ImageView activeDriverPhoto;\n    private String renderedDriverId;\n    private TextView activeSafetyInfo;\n    private Location lastPassengerLiveLocation;\n'''
if field in text and 'private TextView activeSafetyInfo;' not in text:
    text=text.replace(field,fields,1)

# Adiciona cartão de PIN/SOS logo abaixo da espera.
old='''        body.addView(waitCard,lpMatchWrap());\n        body.addView(space(12));\n\n        Button share = primary("Compartilhar acompanhamento");\n        Button cancel = secondaryLight("Cancelar corrida");\n        body.addView(share,lpMatch(dp(56)));\n        body.addView(space(8));\n        body.addView(cancel,lpMatch(dp(56)));\n        share.setOnClickListener(v -> shareActiveRide());\n        cancel.setOnClickListener(v -> previewCancel());\n'''
new='''        body.addView(waitCard,lpMatchWrap());\n        body.addView(space(12));\n\n        LinearLayout safetyCard=card(Color.WHITE,Color.rgb(229,231,235),18,14);\n        safetyCard.addView(text("🛡 Segurança da corrida",17,BLACK,true));\n        activeSafetyInfo=text("O PIN aparecerá quando um motorista aceitar a corrida.",13,GRAY,false);\n        activeSafetyInfo.setPadding(0,dp(5),0,dp(9));\n        safetyCard.addView(activeSafetyInfo);\n        Button sos=secondaryLight("🆘 SOS");\n        sos.setTextColor(Color.WHITE);\n        sos.setBackground(round(Color.rgb(185,28,28),16,Color.rgb(185,28,28)));\n        safetyCard.addView(sos,lpMatch(dp(52)));\n        sos.setOnClickListener(v->confirmPassengerSos());\n        body.addView(safetyCard,lpMatchWrap());\n        body.addView(space(12));\n\n        Button share = primary("Compartilhar acompanhamento");\n        Button cancel = secondaryLight("Cancelar corrida");\n        body.addView(share,lpMatch(dp(56)));\n        body.addView(space(8));\n        body.addView(cancel,lpMatch(dp(56)));\n        share.setOnClickListener(v -> shareActiveRide());\n        cancel.setOnClickListener(v -> previewCancel());\n'''
if old not in text: raise SystemExit('ações da corrida ativa v2.7 não encontradas')
text=text.replace(old,new,1)

# Polling busca também PIN e alertas ativos.
old_poll='''                        JSONObject driverLocation = null;\n                        JSONObject driverCard = null;\n                        JSONObject waitSnapshot = null;\n\n                        if (!driverId.isBlank()) {'''
new_poll='''                        JSONObject driverLocation = null;\n                        JSONObject driverCard = null;\n                        JSONObject waitSnapshot = null;\n                        JSONObject safetySnapshot = null;\n                        JSONArray safetyAlerts = new JSONArray();\n\n                        try {\n                            safetySnapshot=new JSONObject(ApiClient.rpc("get_passenger_ride_safety",new JSONObject().put("p_ride_id",rideId),token));\n                            safetyAlerts=new JSONArray(ApiClient.rpc("get_ride_safety_alerts",new JSONObject().put("p_ride_id",rideId),token));\n                        } catch(Exception ignored) {}\n\n                        if (!driverId.isBlank()) {'''
if old_poll not in text: raise SystemExit('polling v2.6 não encontrado')
text=text.replace(old_poll,new_poll,1)

old_final='''                        JSONObject finalLocation=driverLocation;\n                        JSONObject finalCard=driverCard;\n                        JSONObject finalWait=waitSnapshot;\n                        double displayFare=baseFare;\n'''
new_final='''                        JSONObject finalLocation=driverLocation;\n                        JSONObject finalCard=driverCard;\n                        JSONObject finalWait=waitSnapshot;\n                        JSONObject finalSafety=safetySnapshot;\n                        JSONArray finalSafetyAlerts=safetyAlerts;\n                        double displayFare=baseFare;\n'''
if old_final not in text: raise SystemExit('variáveis finais v2.6 não encontradas')
text=text.replace(old_final,new_final,1)

# Mostra PIN e alertas na interface.
ui_anchor='''                            if (activeWaitInfo!=null) {\n                                if (status.equals("driver_arriving") && finalWait!=null) {'''
# Não substituímos o bloco; inserimos segurança imediatamente após ele por um marcador estável posterior.
post_wait='''                            renderActiveDriver(finalLocation);\n                            if (status.equals("completed") || status.equals("cancelled")) {'''
safety_ui='''                            if(activeSafetyInfo!=null){\n                                String safetyText="🛡 Segurança ativa";\n                                if(finalSafety!=null){\n                                    boolean verified=!finalSafety.isNull("pin_verified_at")&&!finalSafety.optString("pin_verified_at","").isBlank();\n                                    String pin=finalSafety.optString("pin","");\n                                    if((status.equals("accepted")||status.equals("driver_arriving"))&&!verified&&!pin.isBlank())\n                                        safetyText="🔐 PIN para iniciar: "+pin+"\\nConfira motorista, foto, veículo e placa antes de informar o código.";\n                                    else if(verified||status.equals("in_progress")) safetyText="✓ PIN confirmado — embarque validado.";\n                                }\n                                int openAlerts=0;String latest="";\n                                for(int i=0;i<finalSafetyAlerts.length();i++){JSONObject a=finalSafetyAlerts.optJSONObject(i);if(a!=null&&"open".equals(a.optString("status"))){openAlerts++;if(latest.isBlank())latest="route_deviation".equals(a.optString("alert_type"))?"Possível desvio de rota detectado":"SOS acionado";}}\n                                if(openAlerts>0)safetyText += "\\n⚠ "+latest+(openAlerts>1?" · "+openAlerts+" alertas ativos":"");\n                                activeSafetyInfo.setText(safetyText);\n                            }\n\n                            renderActiveDriver(finalLocation);\n                            if (status.equals("completed") || status.equals("cancelled")) {'''
if post_wait not in text: raise SystemExit('fim do polling v2.6 não encontrado')
text=text.replace(post_wait,safety_ui,1)

# Guarda a última localização do passageiro para o SOS.
old_send='''    private void sendPassengerLiveLocation(Location location) {\n        String rideId=activeRideId; if(rideId==null||location==null)return;\n        io.execute(() -> { try { ApiClient.rpc("update_passenger_live_location",new JSONObject().put("p_ride_id",rideId).put("p_lat",location.getLatitude()).put("p_lng",location.getLongitude()).put("p_accuracy_m",location.hasAccuracy()?location.getAccuracy():JSONObject.NULL),token); } catch(Exception ignored) {} });\n    }\n'''
new_send='''    private void sendPassengerLiveLocation(Location location) {\n        String rideId=activeRideId; if(rideId==null||location==null)return;\n        lastPassengerLiveLocation=location;\n        io.execute(() -> { try { ApiClient.rpc("update_passenger_live_location",new JSONObject().put("p_ride_id",rideId).put("p_lat",location.getLatitude()).put("p_lng",location.getLongitude()).put("p_accuracy_m",location.hasAccuracy()?location.getAccuracy():JSONObject.NULL),token); } catch(Exception ignored) {} });\n    }\n'''
if old_send not in text: raise SystemExit('sendPassengerLiveLocation não encontrado')
text=text.replace(old_send,new_send,1)

anchor='''    private void showEndState(String status, double fare) {\n'''
helpers=r'''    private void confirmPassengerSos() {
        if(activeRideId==null||activeRideId.isBlank()){toast("Nenhuma corrida ativa.");return;}
        new AlertDialog.Builder(this)
                .setTitle("Acionar SOS?")
                .setMessage("O alerta será registrado pela CLICK-GO com sua localização quando disponível e ficará visível para a central de segurança.")
                .setNegativeButton("Cancelar",null)
                .setPositiveButton("Acionar SOS",(dialog,which)->triggerPassengerSos())
                .show();
    }

    private void triggerPassengerSos() {
        final String rideId=activeRideId;if(rideId==null)return;
        Location loc=lastPassengerLiveLocation;
        io.execute(()->{try{
            JSONObject body=new JSONObject().put("p_ride_id",rideId)
                    .put("p_lat",loc==null?JSONObject.NULL:loc.getLatitude())
                    .put("p_lng",loc==null?JSONObject.NULL:loc.getLongitude())
                    .put("p_message","SOS acionado pelo passageiro no app Android CLICK-GO.");
            JSONObject result=new JSONObject(ApiClient.rpc("trigger_ride_sos",body,token));
            ui.post(()->toast(result.optBoolean("ok",false)?"SOS registrado pela CLICK-GO.":"Não foi possível confirmar o SOS."));
        }catch(Exception e){ui.post(()->toast(message(e)));}});
    }

'''
if anchor not in text: raise SystemExit('showEndState anchor não encontrado')
text=text.replace(anchor,helpers+anchor,1)

# v2.8 PRIME.
build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.8-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.8 PRIME: PIN, SOS e alertas de segurança aplicados.')
