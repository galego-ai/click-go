from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

# v2.5 PRIME: remove o segundo MapView da etapa de escolha da viagem.
# A home continua com mapa + motoristas online; a etapa de categoria vira uma tela leve.
pattern = r'''    private void showOptions\(\) \{.*?\n    \}\n\n    private void drawRoute\(\) \{'''
replacement = r'''    private void showOptions() {
        cancelAddressSearch();
        hideKeyboard();
        nearbyDriversSeq++;
        stopHomeDriverPolling();
        homeMapMode = false;
        releaseMap();
        homePassengerMarker = null;
        activeDriverMarker = null;
        homeDriverMarkers.clear();
        optionDriverMarkers.clear();

        if (origin == null || destination == null) {
            toast("Defina origem e destino antes de continuar.");
            showDestinationSearch();
            return;
        }

        LinearLayout body = vertical(LIGHT);
        body.setPadding(dp(18), dp(20), dp(18), dp(26));

        LinearLayout top = horizontal();
        top.setGravity(Gravity.CENTER_VERTICAL);
        Button back = secondaryLight("← Voltar");
        top.addView(back, new LinearLayout.LayoutParams(dp(112), dp(52)));
        TextView brand = text("CLICK-GO", 18, BLACK, true);
        brand.setGravity(Gravity.RIGHT | Gravity.CENTER_VERTICAL);
        top.addView(brand, new LinearLayout.LayoutParams(0, dp(52), 1));
        body.addView(top);
        body.addView(space(18));

        body.addView(text("Escolha sua viagem", 28, BLACK, true));
        body.addView(space(10));

        LinearLayout routeCard = card(Color.WHITE, Color.rgb(228, 228, 228), 20, 16);
        routeCard.addView(text("EMBARQUE", 11, GRAY, true));
        TextView from = text(cleanLabel(originLabel), 15, BLACK, true);
        from.setMaxLines(2);
        routeCard.addView(from);
        routeCard.addView(space(10));
        routeCard.addView(text("DESTINO", 11, GRAY, true));
        TextView to = text(cleanLabel(destinationLabel), 15, BLACK, true);
        to.setMaxLines(2);
        routeCard.addView(to);
        body.addView(routeCard, lpMatchWrap());
        body.addView(space(16));

        optionsSubtitle = text("Buscando categorias disponíveis…", 14, GRAY, false);
        body.addView(optionsSubtitle);
        body.addView(space(10));

        categoryBox = vertical(LIGHT);
        body.addView(categoryBox, lpMatchWrap());
        body.addView(space(10));

        body.addView(text("Forma de pagamento", 13, GRAY, true));
        paymentSpinner = new Spinner(this);
        body.addView(paymentSpinner, lpMatch(dp(56)));
        body.addView(space(14));

        requestRideButton = primary("Aguarde…");
        requestRideButton.setEnabled(false);
        body.addView(requestRideButton, lpMatch(dp(60)));
        body.addView(space(8));
        TextView requestStatus = text("", 13, GRAY, false);
        requestStatus.setGravity(Gravity.CENTER);
        requestStatus.setTag("ride_request_status");
        body.addView(requestStatus, lpMatchWrap());

        back.setOnClickListener(v -> showDestinationSearch());
        requestRideButton.setOnClickListener(v -> requestRide());
        setContentView(scroll(body, LIGHT));
        loadOptions();
    }

    private void drawRoute() {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('showOptions/drawRoute final não encontrado')

# Renderização estável: não recria toda a lista ao tocar numa categoria.
pattern = r'''    private void renderOptions\(JSONObject settings\) \{.*?\n    \}\n\n    private void requestRide\(\) \{'''
replacement = r'''    private void renderOptions(JSONObject settings) {
        if (destroyed || isFinishing() || categoryBox == null || !categoryBox.isAttachedToWindow()) return;
        categoryBox.removeAllViews();

        if (rideOptions.isEmpty()) {
            categoryBox.addView(unavailable("Sem categoria disponível", "Ainda não há uma categoria ativa para esta rota."));
            if (optionsSubtitle != null) optionsSubtitle.setText("");
            if (requestRideButton != null) requestRideButton.setEnabled(false);
            return;
        }

        if (selectedOption == null) selectedOption = rideOptions.get(0);
        RideOption first = rideOptions.get(0);
        if (optionsSubtitle != null) {
            optionsSubtitle.setText(String.format(Locale.getDefault(), "%.1f km · aprox. %.0f min · %s/%s", first.distance, first.duration, first.city, first.state));
        }

        for (RideOption option : rideOptions) {
            Button item = secondaryLight(vehicleIcon(option.vehicle) + "  " + option.name + "   " + money(option.fare));
            item.setGravity(Gravity.LEFT | Gravity.CENTER_VERTICAL);
            item.setPadding(dp(16), 0, dp(12), 0);
            item.setOnClickListener(v -> {
                selectedOption = option;
                if (optionsSubtitle != null) {
                    optionsSubtitle.setText("Selecionado: " + option.name + " · " + String.format(Locale.getDefault(), "%.1f km · %.0f min", option.distance, option.duration));
                }
                if (requestRideButton != null) {
                    requestRideButton.setText("Solicitar " + option.name + " · " + money(option.fare));
                }
            });
            categoryBox.addView(item, lpMatch(dp(62)));
            categoryBox.addView(space(8));
        }

        List<String> display = new ArrayList<>();
        for (String payment : paymentValues) display.add(paymentLabel(payment));
        if (display.isEmpty()) display.add("Nenhuma forma de pagamento disponível");
        if (paymentSpinner != null) {
            paymentSpinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, display));
        }

        boolean canRequest = !paymentValues.isEmpty() && selectedOption != null;
        if (requestRideButton != null) {
            requestRideButton.setEnabled(canRequest);
            requestRideButton.setText(canRequest
                    ? "Solicitar " + selectedOption.name + " · " + money(selectedOption.fare)
                    : "Pagamento indisponível");
        }
    }

    private void requestRide() {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('renderOptions/requestRide final não encontrado')

# Solicitação robusta: valida tudo, cria a corrida, valida o UUID e só então troca de tela.
pattern = r'''    private void requestRide\(\) \{.*?\n    \}\n\n    private void showActiveRide\(\) \{'''
replacement = r'''    private void requestRide() {
        if (destroyed || isFinishing()) return;
        if (origin == null || destination == null) {
            toast("Origem ou destino inválido. Escolha o destino novamente.");
            return;
        }
        if (selectedOption == null) {
            toast("Escolha uma categoria.");
            return;
        }
        if (paymentValues.isEmpty() || paymentSpinner == null) {
            toast("Nenhuma forma de pagamento disponível.");
            return;
        }

        int index = paymentSpinner.getSelectedItemPosition();
        if (index < 0) index = 0;
        index = Math.min(index, paymentValues.size() - 1);
        final String payment = paymentValues.get(index);
        final RideOption option = selectedOption;
        final Button targetButton = requestRideButton;

        if (targetButton != null) {
            targetButton.setEnabled(false);
            targetButton.setText("Criando corrida…");
        }
        TextView requestStatus = findViewWithTag("ride_request_status");
        if (requestStatus != null) requestStatus.setText("Conectando ao motorista mais próximo…");

        io.execute(() -> {
            try {
                JSONObject body = new JSONObject()
                        .put("p_origin_label", cleanLabel(originLabel))
                        .put("p_origin_lat", origin.getLatitude())
                        .put("p_origin_lng", origin.getLongitude())
                        .put("p_destination_label", cleanLabel(destinationLabel))
                        .put("p_destination_lat", destination.getLatitude())
                        .put("p_destination_lng", destination.getLongitude())
                        .put("p_category_id", option.id)
                        .put("p_payment_method", payment);

                String raw = ApiClient.rpc("create_passenger_ride", body, token);
                String rideId = raw == null ? "" : raw.trim();
                if (rideId.startsWith("\"") && rideId.endsWith("\"") && rideId.length() >= 2) {
                    rideId = rideId.substring(1, rideId.length() - 1);
                }
                java.util.UUID.fromString(rideId);
                final String finalRideId = rideId;

                ui.post(() -> {
                    if (destroyed || isFinishing()) return;
                    activeRideId = finalRideId;
                    showActiveRide();
                });
            } catch (Exception e) {
                String msg = message(e);
                ui.post(() -> {
                    if (destroyed || isFinishing()) return;
                    toast(msg);
                    TextView status = findViewWithTag("ride_request_status");
                    if (status != null) status.setText("Não foi possível criar a corrida. Tente novamente.");
                    if (targetButton != null && targetButton.isAttachedToWindow()) {
                        targetButton.setEnabled(true);
                        targetButton.setText("Solicitar " + option.name + " · " + money(option.fare));
                    }
                });
            }
        });
    }

    private void showActiveRide() {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('requestRide/showActiveRide final não encontrado')

# Tela de busca sem MapView: evita novo ciclo de tiles/overlays enquanto o dispatch acontece.
pattern = r'''    private void showActiveRide\(\) \{.*?\n    \}\n\n    private void startRidePolling\(\) \{'''
replacement = r'''    private void showActiveRide() {
        stopRidePolling();
        stopHomeDriverPolling();
        homeMapMode = false;
        releaseMap();

        LinearLayout body = vertical(LIGHT);
        body.setPadding(dp(22), dp(30), dp(22), dp(28));
        body.addView(text("CLICK-GO", 18, BLACK, true));
        body.addView(space(26));

        TextView icon = text("⌖", 48, YELLOW, true);
        icon.setGravity(Gravity.CENTER);
        body.addView(icon, lpMatchWrap());

        activeStatus = text("Procurando motorista mais próximo…", 26, BLACK, true);
        activeStatus.setGravity(Gravity.CENTER);
        body.addView(activeStatus, lpMatchWrap());
        body.addView(space(10));

        TextView info = text("Sua corrida foi criada. Aguarde enquanto enviamos a chamada aos motoristas elegíveis próximos.", 15, GRAY, false);
        info.setGravity(Gravity.CENTER);
        body.addView(info, lpMatchWrap());
        body.addView(space(22));

        LinearLayout routeCard = card(Color.WHITE, Color.rgb(228, 228, 228), 20, 16);
        routeCard.addView(text(cleanLabel(originLabel) + "  →  " + cleanLabel(destinationLabel), 14, BLACK, true));
        if (selectedOption != null) {
            routeCard.addView(space(8));
            routeCard.addView(text(selectedOption.name, 15, BLACK, true));
        }
        activeFare = text(selectedOption == null ? "" : money(selectedOption.fare), 20, BLACK, true);
        routeCard.addView(activeFare);
        body.addView(routeCard, lpMatchWrap());
        body.addView(space(18));

        Button cancel = secondaryLight("Cancelar corrida");
        body.addView(cancel, lpMatch(dp(56)));
        cancel.setOnClickListener(v -> previewCancel());

        setContentView(scroll(body, LIGHT));
        startRidePolling();
    }

    private void startRidePolling() {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('showActiveRide/startRidePolling final não encontrado')

# Polling enxuto: não toca no mapa durante a busca; apenas acompanha estado da corrida.
pattern = r'''    private void startRidePolling\(\) \{.*?\n    \}\n\n    private void stopRidePolling\(\) \{'''
replacement = r'''    private void startRidePolling() {
        stopRidePolling();
        ridePoll = new Runnable() {
            @Override public void run() {
                if (activeRideId == null || destroyed || isFinishing()) return;
                final String rideId = activeRideId;
                io.execute(() -> {
                    try {
                        JSONArray rows = new JSONArray(ApiClient.restGet(
                                "rides?id=eq." + rideId + "&select=id,status,estimated_fare,final_fare,driver_id", token));
                        if (rows.length() == 0) {
                            ui.postDelayed(this, 3000);
                            return;
                        }

                        JSONObject ride = rows.getJSONObject(0);
                        String status = ride.optString("status", "searching");
                        String driverId = ride.optString("driver_id", "");
                        double fare = ride.isNull("final_fare") ? ride.optDouble("estimated_fare") : ride.optDouble("final_fare");

                        ui.post(() -> {
                            if (destroyed || isFinishing() || activeRideId == null || !rideId.equals(activeRideId)) return;
                            if (activeStatus != null && activeStatus.isAttachedToWindow()) {
                                if ((status.equals("accepted") || status.equals("driver_arriving")) && !driverId.isBlank()) {
                                    activeStatus.setText(status.equals("accepted") ? "Motorista aceitou a corrida" : "Motorista a caminho");
                                } else {
                                    activeStatus.setText(statusLabel(status));
                                }
                            }
                            if (activeFare != null && activeFare.isAttachedToWindow()) activeFare.setText(money(fare));

                            if (status.equals("completed") || status.equals("cancelled")) {
                                activeRideId = null;
                                stopRidePolling();
                                showEndState(status, fare);
                            } else {
                                ui.postDelayed(ridePoll, 2500);
                            }
                        });
                    } catch (Exception ignored) {
                        ui.postDelayed(ridePoll, 4000);
                    }
                });
            }
        };
        ui.post(ridePoll);
    }

    private void stopRidePolling() {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('startRidePolling/stopRidePolling final não encontrado')

# v2.5 PRIME
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.5-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Passageiro v2.5 PRIME: tela de categorias sem segundo mapa e solicitação/dispatch estabilizados.')
