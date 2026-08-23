from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text = path.read_text(encoding='utf-8')

# Imports para abrir a navegação externa no ponto exato de embarque.
if 'import android.content.Intent;' not in text:
    text = text.replace('import android.content.pm.PackageManager;\n', 'import android.content.pm.PackageManager;\nimport android.content.Intent;\n', 1)
if 'import android.net.Uri;' not in text:
    text = text.replace('import android.os.Bundle;\n', 'import android.os.Bundle;\nimport android.net.Uri;\n', 1)

old_render = '''    private void renderRide(JSONObject r){if(operationBox==null)return;operationBox.removeAllViews();String s=r.optString("status","accepted");operationTitle.setText(s.equals("accepted")?"Corrida aceita":s.equals("driver_arriving")?"A caminho do passageiro":"Corrida em andamento");LinearLayout c=card(DARK,Color.rgb(65,65,65));c.addView(text("Embarque: "+r.optString("origin_label",""),14,Color.WHITE,true));c.addView(text("Destino: "+r.optString("destination_label",""),14,GRAY,false));Button b;String action;if(s.equals("accepted")){b=primary("Estou a caminho");action="arrived";}else if(s.equals("driver_arriving")){b=primary("Iniciar corrida");action="start";}else{b=primary("Finalizar corrida");action="complete";}c.addView(space(8));c.addView(b,match(dp(56)));b.setOnClickListener(v->advance(r.optString("id"),action));operationBox.addView(c,wrap());DriverMapRenderer.render(map,currentLocation,r,dp(5));}\n'''

new_render = '''    private void renderRide(JSONObject r) {
        if (operationBox == null) return;
        operationBox.removeAllViews();
        String s = r.optString("status", "accepted");
        operationTitle.setText(s.equals("accepted") ? "Corrida aceita"
                : s.equals("driver_arriving") ? "A caminho do passageiro"
                : "Corrida em andamento");

        LinearLayout c = card(DARK, Color.rgb(65,65,65));
        c.addView(text("Embarque: " + r.optString("origin_label", ""), 14, Color.WHITE, true));
        c.addView(text("Destino: " + r.optString("destination_label", ""), 14, GRAY, false));

        if (s.equals("accepted")) {
            c.addView(space(10));
            Button going = primary("Estou indo");
            c.addView(going, match(dp(58)));
            c.addView(space(8));
            Button navigate = darkButton("🧭 Abrir rota até passageiro");
            c.addView(navigate, match(dp(54)));
            going.setOnClickListener(v -> markGoingAndNavigate(r));
            navigate.setOnClickListener(v -> openNavigationToPassenger(r));
        } else if (s.equals("driver_arriving")) {
            c.addView(space(10));
            Button navigate = darkButton("🧭 Abrir rota até passageiro");
            c.addView(navigate, match(dp(54)));
            c.addView(space(8));
            Button start = primary("Iniciar corrida");
            c.addView(start, match(dp(58)));
            navigate.setOnClickListener(v -> openNavigationToPassenger(r));
            start.setOnClickListener(v -> advance(r.optString("id"), "start"));
        } else {
            c.addView(space(10));
            Button destination = darkButton("🧭 Abrir rota até destino");
            c.addView(destination, match(dp(54)));
            c.addView(space(8));
            Button complete = primary("Finalizar corrida");
            c.addView(complete, match(dp(58)));
            destination.setOnClickListener(v -> openNavigationToDestination(r));
            complete.setOnClickListener(v -> advance(r.optString("id"), "complete"));
        }

        operationBox.addView(c, wrap());
        DriverMapRenderer.render(map, currentLocation, r, dp(5));
    }\n'''

if old_render not in text:
    raise SystemExit('renderRide final não encontrado para aplicar navegação do passageiro')
text = text.replace(old_render, new_render, 1)

anchor = '''    private void advance(String rideId,String action){io.execute(()->{try{DriverRepository.advanceRide(token,rideId,action);if(action.equals("complete")){JSONObject w=DriverRepository.wallet(token);balance=w.optDouble("operational_balance",balance);}ui.post(()->{if(walletText!=null)walletText.setText(walletLabel());toast(action.equals("complete")?"Corrida concluída.":"Status atualizado.");});refreshOperation();}catch(Exception e){ui.post(()->toast(msg(e)));}});}\n'''

helpers = '''    private void markGoingAndNavigate(JSONObject ride) {
        if (ride == null) return;
        String rideId = ride.optString("id", "");
        if (rideId.isBlank()) {
            toast("Corrida inválida.");
            return;
        }
        io.execute(() -> {
            try {
                DriverRepository.advanceRide(token, rideId, "arrived");
                ui.post(() -> {
                    toast("Status atualizado: a caminho do passageiro.");
                    openNavigationToPassenger(ride);
                    refreshOperation();
                });
            } catch (Exception e) {
                ui.post(() -> toast(msg(e)));
            }
        });
    }

    private void openNavigationToPassenger(JSONObject ride) {
        if (ride == null) return;
        double lat = ride.optDouble("origin_lat", Double.NaN);
        double lng = ride.optDouble("origin_lng", Double.NaN);
        String label = ride.optString("origin_label", "Embarque do passageiro");
        openNavigation(lat, lng, label);
    }

    private void openNavigationToDestination(JSONObject ride) {
        if (ride == null) return;
        double lat = ride.optDouble("destination_lat", Double.NaN);
        double lng = ride.optDouble("destination_lng", Double.NaN);
        String label = ride.optString("destination_label", "Destino da corrida");
        openNavigation(lat, lng, label);
    }

    private void openNavigation(double lat, double lng, String label) {
        if (!Double.isFinite(lat) || !Double.isFinite(lng)) {
            toast("A localização desta corrida não está disponível.");
            return;
        }
        try {
            String destination = lat + "," + lng;
            Uri uri = Uri.parse("https://www.google.com/maps/dir/?api=1&destination="
                    + Uri.encode(destination) + "&travelmode=driving");
            Intent maps = new Intent(Intent.ACTION_VIEW, uri);
            maps.setPackage("com.google.android.apps.maps");
            if (maps.resolveActivity(getPackageManager()) != null) {
                startActivity(maps);
                return;
            }

            Intent anyMap = new Intent(Intent.ACTION_VIEW, uri);
            if (anyMap.resolveActivity(getPackageManager()) != null) {
                startActivity(Intent.createChooser(anyMap, "Abrir rota para " + (label == null ? "local" : label)));
                return;
            }
            toast("Nenhum aplicativo de mapas disponível.");
        } catch (Exception e) {
            toast("Não foi possível abrir o mapa.");
        }
    }

''' + anchor

if anchor not in text:
    raise SystemExit('advance final não encontrado para inserir helpers de navegação')
text = text.replace(anchor, helpers, 1)

# Nova versão nativa do motorista.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\\s+(\\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\\s+'[^']+'", "versionName '1.4-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Motorista v1.4 PRIME: Estou indo + rota até passageiro/destino aplicados.')
