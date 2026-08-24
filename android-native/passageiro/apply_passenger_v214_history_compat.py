from pathlib import Path
p=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=p.read_text(encoding='utf-8')

old='''rides?select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,payment_method_preference,origin_lat,origin_lng,destination_lat,destination_lng,arrived_at,arrived_lat,arrived_lng,started_at,started_lat,started_lng,completed_at,completed_lat,completed_lng,wait_charge_amount&order=requested_at.desc&limit=50'''
new='''rides?select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_fare,final_fare,requested_at,payment_method_preference,arrived_at,arrived_lat,arrived_lng,started_at,started_lat,started_lng,completed_at,completed_lat,completed_lng,wait_charge_amount&order=requested_at.desc&limit=50'''
if old in text:text=text.replace(old,new,1)

old_block='''                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));\n                        card.addView(space(7));\n                        card.addView(text("GPS origem: " + rideCoords(ride,"origin_lat","origin_lng"), 12, GRAY, false));\n                        card.addView(text("GPS destino: " + rideCoords(ride,"destination_lat","destination_lng"), 12, GRAY, false));\n                        card.addView(text("GPS chegada: " + rideCoords(ride,"arrived_lat","arrived_lng"), 12, GRAY, false));\n                        card.addView(text("GPS início: " + rideCoords(ride,"started_lat","started_lng"), 12, GRAY, false));\n                        card.addView(text("GPS fim: " + rideCoords(ride,"completed_lat","completed_lng"), 12, GRAY, false));\n                        double waitCharge=ride.optDouble("wait_charge_amount",0);\n                        if(waitCharge>0) card.addView(text("Espera: " + money(waitCharge), 12, BLACK, true));\n                        card.addView(space(8));\n                        Button gps=secondaryLight("📍 Ver todos os pontos GPS");\n                        card.addView(gps, lpMatch(dp(48)));\n                        gps.setOnClickListener(v -> showPassengerRoutePoints(ride));\n                        content.addView(card, lpMatchWrap());\n'''
new_block='''                        card.addView(text(when + " · " + paymentLabel(ride.optString("payment_method_preference", "cash")), 12, GRAY, false));\n                        double waitCharge=ride.optDouble("wait_charge_amount",0);\n                        if(waitCharge>0) card.addView(text("Espera: " + money(waitCharge), 12, BLACK, true));\n                        content.addView(card, lpMatchWrap());\n'''
if old_block in text:text=text.replace(old_block,new_block,1)
elif 'GPS origem:' in text:raise SystemExit('Bloco GPS do histórico não reconhecido')

p.write_text(text,encoding='utf-8')
print('Compatibilidade v2.14: histórico sem coordenadas visíveis e query normalizada.')
