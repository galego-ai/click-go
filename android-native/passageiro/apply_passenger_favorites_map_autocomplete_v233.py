from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.33 PRIME
# Favoritos: sugestões automáticas a partir de 2 caracteres + escolha do ponto no mapa.

pattern=re.compile(r'''    private void showAddFavorite\(\) \{.*?\n    \}\n\n(?=    private void confirmDeleteFavorite)''',re.S)
replacement=r'''    private void showAddFavorite() {
        LinearLayout content = showSectionShell("Adicionar favorito");
        EditText label = editLight("Nome: Casa, Trabalho...");
        EditText address = editLight("Digite o endereço");
        TextView helper = text("Digite 2 ou mais caracteres para ver sugestões automáticas.", 12, GRAY, false);
        LinearLayout suggestions = vertical(Color.TRANSPARENT);
        Button mapPick = secondaryLight("🗺 Escolher no mapa");
        Button save = primary("Salvar favorito");
        final double[] selected = {Double.NaN, Double.NaN};
        final boolean[] applyingSuggestion = {false};
        final int[] searchVersion = {0};
        final Runnable[] delayedSearch = {null};

        content.addView(label, lpMatch(dp(56)));
        content.addView(space(9));
        content.addView(address, lpMatch(dp(56)));
        content.addView(helper, lpMatchWrap());
        content.addView(suggestions, lpMatchWrap());
        content.addView(space(9));
        content.addView(mapPick, lpMatch(dp(54)));
        content.addView(space(14));
        content.addView(save, lpMatch(dp(56)));

        address.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {}
            @Override public void afterTextChanged(Editable editable) {
                if (applyingSuggestion[0]) return;
                selected[0] = Double.NaN;
                selected[1] = Double.NaN;
                searchVersion[0]++;
                if (delayedSearch[0] != null) ui.removeCallbacks(delayedSearch[0]);
                suggestions.removeAllViews();
                String query = editable == null ? "" : editable.toString().trim();
                if (query.length() < 2) return;
                int version = searchVersion[0];
                delayedSearch[0] = () -> searchFavoriteSuggestions(query, suggestions, address, selected, applyingSuggestion, version, searchVersion);
                ui.postDelayed(delayedSearch[0], 320L);
            }
        });

        mapPick.setOnClickListener(v -> {
            if (delayedSearch[0] != null) ui.removeCallbacks(delayedSearch[0]);
            searchVersion[0]++;
            suggestions.removeAllViews();
            hideKeyboard();
            showFavoriteMapPicker(address, selected, applyingSuggestion, suggestions);
        });

        save.setOnClickListener(v -> {
            String name = label.getText().toString().trim();
            String addr = address.getText().toString().trim();
            if (name.isBlank() || addr.length() < 2) { toast("Informe um nome e escolha o endereço."); return; }
            save.setEnabled(false);
            save.setText("Salvando favorito…");
            final double chosenLat = selected[0];
            final double chosenLng = selected[1];
            io.execute(() -> {
                try {
                    double lat = chosenLat;
                    double lng = chosenLng;
                    String resolved = addr;
                    if (Double.isFinite(lat) && Double.isFinite(lng)) {
                        resolved = resolveFavoriteAddress(lat, lng, addr);
                    } else {
                        StringBuilder url = new StringBuilder(BuildConfig.GEOCODE_URL)
                                .append("?q=").append(URLEncoder.encode(addr, StandardCharsets.UTF_8.toString()));
                        if (origin != null) url.append("&lat=").append(origin.getLatitude()).append("&lng=").append(origin.getLongitude());
                        if (originSearchContext != null && !originSearchContext.isBlank())
                            url.append("&context=").append(URLEncoder.encode(originSearchContext, StandardCharsets.UTF_8.toString()));
                        JSONObject result = new JSONObject(ApiClient.absoluteGet(url.toString()));
                        JSONArray matches = result.optJSONArray("results");
                        if (matches == null || matches.length() == 0) throw new Exception("Endereço não encontrado. Escolha uma sugestão ou marque no mapa.");
                        JSONObject first = matches.getJSONObject(0);
                        lat = first.optDouble("lat", Double.NaN);
                        lng = first.optDouble("lng", Double.NaN);
                        if (!Double.isFinite(lat) || !Double.isFinite(lng)) throw new Exception("Endereço sem coordenadas válidas.");
                        resolved = cleanLabel(first.optString("label", addr));
                    }
                    String uid = ensureUserId();
                    JSONObject body = new JSONObject()
                            .put("passenger_id", uid)
                            .put("label", name)
                            .put("address", resolved)
                            .put("lat", lat)
                            .put("lng", lng);
                    ApiClient.restPost("passenger_favorites", body, token);
                    ui.post(() -> { toast("Favorito salvo."); showFavorites(); });
                } catch (Exception e) {
                    ui.post(() -> { save.setEnabled(true); save.setText("Salvar favorito"); toast(message(e)); });
                }
            });
        });
    }

    private void searchFavoriteSuggestions(String query, LinearLayout target, EditText address, double[] selected,
                                           boolean[] applyingSuggestion, int version, int[] searchVersion) {
        final double biasLat = origin == null ? Double.NaN : origin.getLatitude();
        final double biasLng = origin == null ? Double.NaN : origin.getLongitude();
        io.execute(() -> {
            List<SearchItem> items = new ArrayList<>();
            try {
                StringBuilder url = new StringBuilder(BuildConfig.GEOCODE_URL)
                        .append("?q=").append(URLEncoder.encode(query, StandardCharsets.UTF_8.toString()));
                if (Double.isFinite(biasLat) && Double.isFinite(biasLng))
                    url.append("&lat=").append(biasLat).append("&lng=").append(biasLng);
                if (originSearchContext != null && !originSearchContext.isBlank())
                    url.append("&context=").append(URLEncoder.encode(originSearchContext, StandardCharsets.UTF_8.toString()));
                JSONObject root = new JSONObject(ApiClient.absoluteGet(url.toString()));
                JSONArray rows = root.optJSONArray("results");
                Set<String> seen = new HashSet<>();
                if (rows != null) {
                    for (int i = 0; i < rows.length() && items.size() < 6; i++) {
                        JSONObject row = rows.optJSONObject(i);
                        if (row == null) continue;
                        String full = cleanLabel(row.optString("label", ""));
                        double lat = row.optDouble("lat", Double.NaN);
                        double lng = row.optDouble("lng", Double.NaN);
                        if (full.isBlank() || !Double.isFinite(lat) || !Double.isFinite(lng)) continue;
                        String key = full.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                        if (!seen.add(key)) continue;
                        items.add(new SearchItem(full, cleanLabel(row.optString("name", full)), cleanLabel(row.optString("subtitle", "")), row.optString("kind", "address"), lat, lng));
                    }
                }
            } catch (Exception ignored) {}
            if (items.isEmpty()) items.addAll(nativeAddressFallback(query, biasLat, biasLng));
            final List<SearchItem> result = new ArrayList<>(items);
            ui.post(() -> {
                if (destroyed || isFinishing() || version != searchVersion[0] || target.getParent() == null) return;
                target.removeAllViews();
                if (result.isEmpty()) {
                    TextView empty = text("Nenhum endereço encontrado. Continue digitando ou escolha no mapa.", 12, GRAY, false);
                    empty.setPadding(dp(8), dp(8), dp(8), dp(8));
                    target.addView(empty, lpMatchWrap());
                    return;
                }
                for (SearchItem item : result) {
                    LinearLayout row = card(Color.WHITE, Color.rgb(228,228,228), 14, 11);
                    row.setClickable(true);
                    row.setFocusable(true);
                    row.addView(text(item.label, 14, BLACK, true));
                    if (item.subtitle != null && !item.subtitle.isBlank()) row.addView(text(item.subtitle, 12, GRAY, false));
                    row.setOnClickListener(v -> {
                        applyingSuggestion[0] = true;
                        selected[0] = item.lat;
                        selected[1] = item.lng;
                        address.setText(item.label);
                        address.setSelection(address.length());
                        applyingSuggestion[0] = false;
                        searchVersion[0]++;
                        target.removeAllViews();
                        hideKeyboard();
                    });
                    target.addView(row, lpMatchWrap());
                    target.addView(space(6));
                }
            });
        });
    }

    private void showFavoriteMapPicker(EditText address, double[] selected, boolean[] applyingSuggestion, LinearLayout suggestions) {
        LinearLayout root = vertical(Color.WHITE);
        root.setPadding(dp(12), dp(12), dp(12), dp(12));
        root.addView(text("Escolher endereço no mapa", 20, BLACK, true));
        TextView tip = text("Toque no mapa para posicionar o marcador no endereço desejado.", 12, GRAY, false);
        tip.setPadding(0, dp(5), 0, dp(9));
        root.addView(tip);

        FrameLayout frame = new FrameLayout(this);
        MapView picker = new MapView(this);
        picker.setTileSource(TileSourceFactory.MAPNIK);
        picker.setMultiTouchControls(true);
        GeoPoint initial;
        if (Double.isFinite(selected[0]) && Double.isFinite(selected[1])) initial = new GeoPoint(selected[0], selected[1]);
        else if (origin != null) initial = origin;
        else initial = new GeoPoint(-14.52472, -49.14083);
        picker.getController().setZoom(16.0);
        picker.getController().setCenter(initial);
        frame.addView(picker, new FrameLayout.LayoutParams(-1, -1));
        Marker marker = new Marker(picker);
        marker.setPosition(initial);
        marker.setTitle("Endereço favorito");
        marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        picker.getOverlays().add(marker);
        final GeoPoint[] chosen = {initial};
        MapEventsOverlay events = new MapEventsOverlay(new MapEventsReceiver() {
            @Override public boolean singleTapConfirmedHelper(GeoPoint point) {
                chosen[0] = point;
                marker.setPosition(point);
                picker.getController().animateTo(point);
                picker.invalidate();
                return true;
            }
            @Override public boolean longPressHelper(GeoPoint point) { return singleTapConfirmedHelper(point); }
        });
        picker.getOverlays().add(0, events);
        root.addView(frame, new LinearLayout.LayoutParams(-1, dp(430)));
        root.addView(space(10));

        LinearLayout actions = horizontal();
        Button cancel = secondaryLight("Cancelar");
        Button confirm = primary("Usar este local");
        actions.addView(cancel, new LinearLayout.LayoutParams(0, dp(54), 1));
        actions.addView(spaceH(8));
        actions.addView(confirm, new LinearLayout.LayoutParams(0, dp(54), 2));
        root.addView(actions);

        AlertDialog dialog = new AlertDialog.Builder(this).setView(root).create();
        dialog.setOnDismissListener(d -> { try { picker.onDetach(); } catch (Exception ignored) {} });
        cancel.setOnClickListener(v -> dialog.dismiss());
        confirm.setOnClickListener(v -> {
            GeoPoint point = chosen[0];
            selected[0] = point.getLatitude();
            selected[1] = point.getLongitude();
            applyingSuggestion[0] = true;
            address.setText("Local marcado no mapa");
            address.setSelection(address.length());
            applyingSuggestion[0] = false;
            suggestions.removeAllViews();
            dialog.dismiss();
            io.execute(() -> {
                String resolved = resolveFavoriteAddress(point.getLatitude(), point.getLongitude(), "Local marcado no mapa");
                ui.post(() -> {
                    if (destroyed || isFinishing() || !address.isAttachedToWindow()) return;
                    applyingSuggestion[0] = true;
                    address.setText(resolved);
                    address.setSelection(address.length());
                    applyingSuggestion[0] = false;
                });
            });
        });
        dialog.show();
        if (dialog.getWindow() != null) dialog.getWindow().setLayout(getResources().getDisplayMetrics().widthPixels - dp(20), android.view.ViewGroup.LayoutParams.WRAP_CONTENT);
    }

    private String resolveFavoriteAddress(double lat, double lng, String fallback) {
        try {
            String url = BuildConfig.GEOCODE_URL + "?reverse=1&lat=" + lat + "&lng=" + lng;
            JSONObject root = new JSONObject(ApiClient.absoluteGet(url));
            JSONArray rows = root.optJSONArray("results");
            if (rows != null && rows.length() > 0) {
                String label = cleanLabel(rows.getJSONObject(0).optString("label", ""));
                if (!label.isBlank()) return label;
            }
        } catch (Exception ignored) {}
        return fallback == null || fallback.isBlank() ? "Local marcado no mapa" : fallback;
    }

'''
text,n=pattern.subn(replacement,text,count=1)
if n!=1:
    raise SystemExit('showAddFavorite final não encontrado para v2.33')

for required in ['Escolher no mapa','Digite 2 ou mais caracteres','searchFavoriteSuggestions','showFavoriteMapPicker','resolveFavoriteAddress']:
    if required not in text:
        raise SystemExit('Favoritos v2.33 incompletos: '+required)

build=re.sub(r'versionCode\s+\d+','versionCode 233',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.33-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.33 PRIME: favoritos com mapa e sugestões automáticas aplicados.')
