from pathlib import Path
import re

root=Path('app')
main=root/'src/main/java/com/clickgo/motorista/MainActivity.java'
repo_path=root/'src/main/java/com/clickgo/motorista/DriverRepository.java'
build_path=root/'build.gradle'
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Avaliação do passageiro após concluir a corrida.
repo_anchor='''    public static void advanceRide(String token, String rideId, String action) throws Exception {\n'''
repo_method='''    public static JSONObject submitPassengerRating(String token, String rideId, int rating, String comment) throws Exception {\n        String raw = ApiClient.rpc("submit_driver_passenger_rating", new JSONObject()\n                .put("p_ride_id", rideId)\n                .put("p_rating", rating)\n                .put("p_comment", comment == null || comment.trim().isEmpty() ? JSONObject.NULL : comment.trim()), token);\n        return new JSONObject(raw);\n    }\n\n'''
if 'submitPassengerRating' not in repo:
    if repo_anchor not in repo: raise SystemExit('advanceRide não encontrado no DriverRepository')
    repo=repo.replace(repo_anchor,repo_method+repo_anchor,1)

# A finalização passa por um resumo comercial + avaliação.
old='''            done.setOnClickListener(v->advance(r.optString("id"),"complete"));'''
new='''            done.setOnClickListener(v->completeRideCommercial(r));'''
if old in text:
    text=text.replace(old,new,1)
elif 'completeRideCommercial(r)' not in text:
    raise SystemExit('Botão FINALIZAR CORRIDA v2.4 não encontrado')

anchor='''    private void markGoingAndNavigate(JSONObject ride) {\n'''
methods=r'''    private void completeRideCommercial(JSONObject ride) {
        if (ride == null) return;
        String rideId = ride.optString("id", "");
        if (rideId.isBlank()) { toast("Corrida inválida."); return; }
        io.execute(() -> {
            try {
                DriverRepository.advanceRide(token, rideId, "complete");
                JSONObject w = DriverRepository.wallet(token);
                balance = w.optDouble("operational_balance", balance);
                double fare = ride.optDouble("final_fare", ride.optDouble("estimated_fare", 0));
                try {
                    JSONArray history = DriverRepository.rideHistory(token, userId);
                    for (int i=0;i<history.length();i++) {
                        JSONObject row=history.optJSONObject(i);
                        if(row!=null && rideId.equals(row.optString("id"))) {
                            fare=row.optDouble("final_fare", row.optDouble("estimated_fare", fare));
                            break;
                        }
                    }
                } catch(Exception ignored) {}
                double finalFare=fare;
                ui.post(() -> {
                    if(walletText!=null)walletText.setText(walletLabel());
                    refreshOperation();
                    showPassengerRating(rideId, finalFare);
                });
            } catch(Exception e) {
                ui.post(() -> toast(msg(e)));
            }
        });
    }

    private void showPassengerRating(String rideId, double fare) {
        LinearLayout wrap=vertical(Color.WHITE);
        wrap.setPadding(dp(20),dp(18),dp(20),dp(12));
        wrap.addView(text("Corrida concluída ✓",24,BLACK,true));
        wrap.addView(text("Valor total: "+privateMoney(fare),19,BLACK,true));
        wrap.addView(space(14));
        wrap.addView(text("Como foi o passageiro?",18,BLACK,true));
        wrap.addView(text("Sua avaliação ajuda a manter a comunidade CLICK-GO confiável.",13,Color.DKGRAY,false));
        wrap.addView(space(10));

        Spinner stars=new Spinner(this);
        String[] labels={"★★★★★  5 - Excelente","★★★★☆  4 - Muito bom","★★★☆☆  3 - Regular","★★☆☆☆  2 - Ruim","★☆☆☆☆  1 - Muito ruim"};
        stars.setAdapter(new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,labels));
        wrap.addView(stars,match(dp(56)));
        wrap.addView(space(10));
        EditText comment=new EditText(this);
        comment.setHint("Comentário opcional");
        comment.setTextColor(BLACK);comment.setHintTextColor(Color.GRAY);comment.setMinLines(3);comment.setGravity(Gravity.TOP);
        comment.setPadding(dp(12),dp(10),dp(12),dp(10));comment.setBackground(round(Color.rgb(247,247,247),12,Color.rgb(220,220,220)));
        wrap.addView(comment,new LinearLayout.LayoutParams(-1,dp(110)));

        new AlertDialog.Builder(this)
                .setView(wrap)
                .setNegativeButton("Agora não",null)
                .setPositiveButton("Enviar avaliação",(d,w)->{
                    int rating=5-stars.getSelectedItemPosition();
                    String note=comment.getText().toString().trim();
                    io.execute(()->{try{DriverRepository.submitPassengerRating(token,rideId,rating,note);ui.post(()->toast("Avaliação enviada. Obrigado!"));}catch(Exception e){ui.post(()->toast(msg(e)));}});
                }).show();
    }

'''
if 'private void completeRideCommercial(JSONObject ride)' not in text:
    if anchor not in text: raise SystemExit('markGoingAndNavigate não encontrado')
    text=text.replace(anchor,methods+anchor,1)

m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.5-prime'",build,count=1)

main.write_text(text,encoding='utf-8')
repo_path.write_text(repo,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v2.5 PRIME: resumo de conclusão e avaliação do passageiro aplicados.')
