from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

# Sequências descartam respostas antigas de categorias e motoristas.
anchor = '    private int locationSeq = 0;\n'
if anchor not in text:
    raise SystemExit('locationSeq não encontrado')
if 'private int optionsLoadSeq = 0;' not in text:
    text = text.replace(anchor, anchor + '    private int optionsLoadSeq = 0;\n    private int nearbyDriversSeq = 0;\n', 1)

# Carrega categorias + pagamentos no background e renderiza UMA única vez.
pattern = r'''    private void loadOptions\(\) \{.*?\n    \}\n\n    private void renderOptions\(JSONObject settings\) \{'''
replacement = r'''    private void loadOptions() {
        final int seq = ++optionsLoadSeq;
        final LinearLayout targetBox = categoryBox;
        final TextView targetSubtitle = optionsSubtitle;
        final Button targetButton = requestRideButton;
        rideOptions.clear();
        selectedOption = null;
        paymentValues.clear();
        io.execute(() -> {
            try {
                if (origin == null || destination == null) throw new Exception("Origem ou destino inválido.");
                JSONObject body = new JSONObject()
                        .put("p_origin_lat", origin.getLatitude())
                        .put("p_origin_lng", origin.getLongitude())
                        .put("p_destination_lat", destination.getLatitude())
                        .put("p_destination_lng", destination.getLongitude());
                JSONArray rows = new JSONArray(ApiClient.rpc("get_passenger_ride_options", body, token));
                List<RideOption> loaded = new ArrayList<>();
                for (int i = 0; i < rows.length(); i++) {
                    JSONObject row = rows.optJSONObject(i);
                    if (row == null || row.isNull("category_id")) continue;
                    loaded.add(new RideOption(
                            row.optString("category_id"), row.optString("category_name"),
                            row.optString("required_vehicle_type"), row.optDouble("distance_km"),
                            row.optDouble("duration_min"), row.optDouble("fare"),
                            row.optString("city_id"), row.optString("city_name"), row.optString("state")));
                }

                JSONObject settings = null;
                List<String> payments = new ArrayList<>();
                boolean paymentFailed = false;
                if (!loaded.isEmpty()) {
                    try {
                        RideOption first = loaded.get(0);
                        JSONArray payRows = new JSONArray(ApiClient.rpc(
                                "get_effective_payment_settings",
                                new JSONObject().put("p_city_id", first.cityId), token));
                        settings = payRows.length() > 0 ? payRows.optJSONObject(0) : new JSONObject();
                        if (settings == null) settings = new JSONObject();
                        if (settings.optBoolean("pix_enabled")) payments.add("pix");
                        if (settings.optBoolean("card_app_enabled")) payments.add("card");
                        if (settings.optBoolean("card_machine_enabled")) payments.add("card_machine");
                        if (settings.optBoolean("cash_enabled")) payments.add("cash");
                    } catch (Exception ignored) {
                        paymentFailed = true;
                    }
                }

                JSONObject finalSettings = settings;
                boolean finalPaymentFailed = paymentFailed;
                ui.post(() -> {
                    if (destroyed || isFinishing() || seq != optionsLoadSeq) return;
                    if (categoryBox != targetBox || targetBox == null || !targetBox.isAttachedToWindow()) return;
                    rideOptions.clear();
                    rideOptions.addAll(loaded);
                    paymentValues.clear();
                    paymentValues.addAll(payments);
                    selectedOption = rideOptions.isEmpty() ? null : rideOptions.get(0);
                    renderOptionsSafely(finalSettings);
                    if (finalPaymentFailed && optionsSubtitle != null && optionsSubtitle.isAttachedToWindow()) {
                        optionsSubtitle.setText(optionsSubtitle.getText() + " · pagamentos temporariamente indisponíveis");
                    }
                });
            } catch (Exception error) {
                String msg = message(error);
                ui.post(() -> {
                    if (destroyed || isFinishing() || seq != optionsLoadSeq) return;
                    if (categoryBox != targetBox || targetBox == null || !targetBox.isAttachedToWindow()) return;
                    try {
                        targetBox.removeAllViews();
                        targetBox.addView(unavailable("Serviço indisponível", msg));
                        if (targetSubtitle != null) targetSubtitle.setText("");
                        if (targetButton != null) targetButton.setEnabled(false);
                    } catch (RuntimeException ignored) {}
                });
            }
        });
    }

    private void renderOptionsSafely(JSONObject settings) {
        if (destroyed || isFinishing() || categoryBox == null || !categoryBox.isAttachedToWindow()) return;
        try {
            renderOptions(settings);
        } catch (RuntimeException error) {
            try {
                categoryBox.removeAllViews();
                categoryBox.addView(unavailable("Não foi possível atualizar as categorias", "Tente novamente."));
                if (optionsSubtitle != null) optionsSubtitle.setText("");
                if (requestRideButton != null) requestRideButton.setEnabled(false);
            } catch (RuntimeException ignored) {}
        }
    }

    private void renderOptions(JSONObject settings) {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('loadOptions/renderOptions não encontrado')

# Clique em categoria também usa renderização protegida.
old_click = '''            item.setOnClickListener(v -> {\n                selectedOption = option;\n                renderOptions(settings);\n            });\n'''
new_click = '''            item.setOnClickListener(v -> {\n                selectedOption = option;\n                renderOptionsSafely(settings);\n            });\n'''
if old_click in text:
    text = text.replace(old_click, new_click, 1)

# Apenas a resposta mais recente de motoristas pode alterar os overlays.
pattern = r'''    private void renderNearbyDrivers\(\) \{.*?\n    \}\n\n    private void renderActiveDriver\(JSONObject loc\) \{'''
replacement = r'''    private void renderNearbyDrivers() {
        if (map == null || origin == null || selectedOption == null || activeRideId != null) return;
        final int seq = ++nearbyDriversSeq;
        final MapView target = map;
        final String categoryId = selectedOption.id;
        final double lat0 = origin.getLatitude();
        final double lng0 = origin.getLongitude();
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject()
                        .put("p_lat", lat0).put("p_lng", lng0)
                        .put("p_category_id", categoryId).put("p_radius_km", 12);
                JSONArray rows = new JSONArray(ApiClient.rpc("get_passenger_nearby_online_drivers", body, token));
                ui.post(() -> {
                    if (destroyed || isFinishing() || seq != nearbyDriversSeq || map != target) return;
                    if (!target.isAttachedToWindow() || selectedOption == null || !categoryId.equals(selectedOption.id) || activeRideId != null) return;
                    try {
                        Set<String> seen = new HashSet<>();
                        for (int i = 0; i < rows.length(); i++) {
                            JSONObject row = rows.optJSONObject(i);
                            if (row == null) continue;
                            String id = row.optString("driver_id", "");
                            double lat = row.optDouble("lat", Double.NaN);
                            double lng = row.optDouble("lng", Double.NaN);
                            if (id.isBlank() || !Double.isFinite(lat) || !Double.isFinite(lng)) continue;
                            seen.add(id);
                            Marker marker = optionDriverMarkers.get(id);
                            if (marker == null) {
                                marker = new Marker(target);
                                marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER);
                                optionDriverMarkers.put(id, marker);
                            }
                            if (!target.getOverlays().contains(marker)) target.getOverlays().add(marker);
                            marker.setPosition(new GeoPoint(lat, lng));
                            marker.setTitle(row.optString("category_name", "Motorista online") + " · "
                                    + String.format(Locale.getDefault(), "%.1f km", row.optDouble("distance_km", 0)));
                        }
                        List<String> stale = new ArrayList<>();
                        for (String id : optionDriverMarkers.keySet()) if (!seen.contains(id)) stale.add(id);
                        for (String id : stale) {
                            Marker marker = optionDriverMarkers.remove(id);
                            if (marker != null) target.getOverlays().remove(marker);
                        }
                        target.invalidate();
                    } catch (RuntimeException ignored) {}
                });
            } catch (Exception ignored) {}
        });
    }

    private void renderActiveDriver(JSONObject loc) {'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('renderNearbyDrivers não encontrado')

# Renderização de motoristas é adiada levemente para a lista estabilizar.
needle = '        renderNearbyDrivers();\n'
if needle in text:
    text = text.replace(needle, '        ui.postDelayed(this::renderNearbyDrivers, 220);\n', 1)

# Versão.
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.3-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Passageiro v2.3 PRIME: categorias renderizadas uma vez e atualizações concorrentes serializadas.')
