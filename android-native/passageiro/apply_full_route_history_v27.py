from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

old='''rides?select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,payment_method_preference&order=requested_at.desc&limit=50'''
new='''rides?select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,payment_method_preference,origin_lat,origin_lng,destination_lat,destination_lng,arrived_at,arrived_lat,arrived_lng,started_at,started_lat,started_lng,completed_at,completed_lat,completed_lng,wait_charge_amount&order=requested_at.desc&limit=50'''
if old not in text: raise SystemExit('consulta do histórico do passageiro não encontrada')
text=text.replace(old,new,1)

old_card='''                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));\n                        content.addView(card, lpMatchWrap());\n'''
new_card='''                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));\n                        card.addView(space(7));\n                        card.addView(text("GPS origem: " + rideCoords(ride,"origin_lat","origin_lng"), 12, GRAY, false));\n                        card.addView(text("GPS destino: " + rideCoords(ride,"destination_lat","destination_lng"), 12, GRAY, false));\n                        card.addView(text("GPS chegada: " + rideCoords(ride,"arrived_lat","arrived_lng"), 12, GRAY, false));\n                        card.addView(text("GPS início: " + rideCoords(ride,"started_lat","started_lng"), 12, GRAY, false));\n                        card.addView(text("GPS fim: " + rideCoords(ride,"completed_lat","completed_lng"), 12, GRAY, false));\n                        double waitCharge=ride.optDouble("wait_charge_amount",0);\n                        if(waitCharge>0) card.addView(text("Espera: " + money(waitCharge), 12, BLACK, true));\n                        card.addView(space(8));\n                        Button gps=secondaryLight("📍 Ver todos os pontos GPS");\n                        card.addView(gps, lpMatch(dp(48)));\n                        gps.setOnClickListener(v -> showPassengerRoutePoints(ride));\n                        content.addView(card, lpMatchWrap());\n'''
if old_card not in text: raise SystemExit('card do histórico do passageiro não encontrado')
text=text.replace(old_card,new_card,1)

anchor='''    private void showPayments() {\n'''
helper=r'''    private String rideCoords(JSONObject ride,String latKey,String lngKey) {
        if(ride==null||ride.isNull(latKey)||ride.isNull(lngKey)) return "—";
        return String.format(Locale.getDefault(),"%.6f, %.6f",ride.optDouble(latKey),ride.optDouble(lngKey));
    }

    private void showPassengerRoutePoints(JSONObject ride) {
        String rideId=ride.optString("id","");
        if(rideId.isBlank()){toast("Corrida inválida.");return;}
        io.execute(() -> {
            try {
                JSONArray points=new JSONArray(ApiClient.restGet("ride_location_points?ride_id=eq."+rideId+"&select=id,lat,lng,heading,speed_kmh,phase,recorded_at&order=recorded_at.asc",token));
                StringBuilder b=new StringBuilder();
                b.append("Origem: ").append(rideCoords(ride,"origin_lat","origin_lng")).append("\n");
                b.append("Destino: ").append(rideCoords(ride,"destination_lat","destination_lng")).append("\n");
                b.append("Chegada: ").append(rideCoords(ride,"arrived_lat","arrived_lng")).append("\n");
                b.append("Início: ").append(rideCoords(ride,"started_lat","started_lng")).append("\n");
                b.append("Fim: ").append(rideCoords(ride,"completed_lat","completed_lng")).append("\n\n");
                b.append("Pontos GPS registrados: ").append(points.length()).append("\n\n");
                for(int i=0;i<points.length();i++){
                    JSONObject p=points.optJSONObject(i);if(p==null)continue;
                    b.append(i+1).append(". ")
                     .append(String.format(Locale.getDefault(),"%.6f, %.6f",p.optDouble("lat"),p.optDouble("lng")))
                     .append(" · ").append(p.optString("phase",""));
                    if(!p.isNull("speed_kmh")) b.append(" · ").append(String.format(Locale.getDefault(),"%.0f km/h",p.optDouble("speed_kmh")));
                    if(!p.isNull("heading")) b.append(" · rumo ").append(String.format(Locale.getDefault(),"%.0f°",p.optDouble("heading")));
                    String date=p.optString("recorded_at","");if(date.length()>=16)date=date.substring(0,16).replace('T',' ');
                    b.append(" · ").append(date).append("\n");
                }
                String result=b.toString();
                ui.post(() -> new AlertDialog.Builder(this).setTitle("Trajeto e coordenadas").setMessage(result).setPositiveButton("Fechar",null).show());
            } catch(Exception e) { ui.post(() -> toast(message(e))); }
        });
    }

'''
if anchor not in text: raise SystemExit('showPayments anchor não encontrado')
text=text.replace(anchor,helper+anchor,1)

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.7-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.7 PRIME: histórico completo de pontos GPS aplicado.')
