from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

def repl(old, new, name):
    global text
    if old not in text:
        raise SystemExit(f'Trecho de {name} não encontrado')
    text = text.replace(old, new, 1)

repl('''    private String originLabel = "Obtendo sua localização...";
    private String destinationLabel = "";
''','''    private String originLabel = "Obtendo sua localização...";
    private String destinationLabel = "";
    private String originSearchContext = "";
''','campos de contexto')

repl('''        setContentView(scroll(root, LIGHT));
        if (origin == null) obtainLocation(originView, false);
''','''        setContentView(scroll(root, LIGHT));
        PassengerAvatar.preload(this, token, () -> {
            if (map != null && origin != null && destination != null) drawRoute();
        });
        if (origin == null) obtainLocation(originView, false);
''','home')

repl('''        start.setPosition(origin);
        start.setTitle("Embarque");
        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
''','''        start.setPosition(origin);
        start.setTitle("Embarque");
        start.setIcon(PassengerAvatar.markerDrawable(this));
        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
''','marcador')

repl('''                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8.toString());
''','''                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8.toString());
                if (origin != null) {
                    url += "&lat=" + origin.getLatitude() + "&lng=" + origin.getLongitude();
                }
                if (originSearchContext != null && !originSearchContext.isBlank()) {
                    url += "&context=" + URLEncoder.encode(originSearchContext, StandardCharsets.UTF_8.toString());
                }
''','busca regional')

repl('''                String resolved = shortAddress(addresses.get(0));
                if (resolved.isBlank()) return;
                ui.post(() -> {
                    if (destroyed || seq != locationSeq) return;
                    originLabel = resolved;
                    if (labelView != null && labelView.isAttachedToWindow()) labelView.setText(resolved);
                });
''','''                Address resolvedAddress = addresses.get(0);
                String resolved = shortAddress(resolvedAddress);
                String city = safe(resolvedAddress.getLocality());
                String state = safe(resolvedAddress.getAdminArea());
                String context = (city + " " + state).trim();
                if (resolved.isBlank()) return;
                ui.post(() -> {
                    if (destroyed || seq != locationSeq) return;
                    originLabel = resolved;
                    if (!context.isBlank()) originSearchContext = context;
                    if (labelView != null && labelView.isAttachedToWindow()) labelView.setText(resolved);
                });
''','geocodificação reversa')

repl('''        root.addView(quick);
        root.addView(space(18));
        root.addView(text("Digite ao menos 3 letras do destino. A localização atual é usada como origem, mas você pode alterá-la.", 13, GRAY, false));
''','''        root.addView(quick);
        root.addView(space(12));
        LinearLayout nearby = horizontal();
        Button markets = smallButton("Mercados");
        Button pharmacies = smallButton("Farmácias");
        Button hospitals = smallButton("Hospitais");
        nearby.addView(markets, new LinearLayout.LayoutParams(0, dp(46), 1));
        nearby.addView(spaceH(7));
        nearby.addView(pharmacies, new LinearLayout.LayoutParams(0, dp(46), 1));
        nearby.addView(spaceH(7));
        nearby.addView(hospitals, new LinearLayout.LayoutParams(0, dp(46), 1));
        markets.setOnClickListener(v -> { destInput.setText("supermercado"); destInput.setSelection(destInput.length()); });
        pharmacies.setOnClickListener(v -> { destInput.setText("farmácia"); destInput.setSelection(destInput.length()); });
        hospitals.setOnClickListener(v -> { destInput.setText("hospital"); destInput.setSelection(destInput.length()); });
        root.addView(nearby);
        root.addView(space(16));
        root.addView(text("Digite 3 letras de uma rua, endereço, comércio ou local. A busca prioriza opções próximas da sua localização.", 13, GRAY, false));
''','atalhos próximos')

repl('''        TextView loading = text("Buscando endereços…", 13, GRAY, false);
''','''        TextView loading = text("Buscando endereços e locais próximos…", 13, GRAY, false);
''','carregamento')

repl('''                        String label = cleanLabel(row.optString("label", ""));
                        double lat = row.optDouble("lat", Double.NaN);
                        double lng = row.optDouble("lng", Double.NaN);
''','''                        String label = cleanLabel(row.optString("label", ""));
                        String name = cleanLabel(row.optString("name", ""));
                        String subtitle = cleanLabel(row.optString("subtitle", ""));
                        String kind = row.optString("kind", "address");
                        double lat = row.optDouble("lat", Double.NaN);
                        double lng = row.optDouble("lng", Double.NaN);
''','dados dos locais')

repl('''                        if (seen.add(key)) items.add(new SearchItem(label, lat, lng));
''','''                        if (seen.add(key)) items.add(new SearchItem(label, name, subtitle, kind, lat, lng));
''','construtor dos resultados')

repl('''    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        target.removeAllViews();
        if (items.isEmpty()) {
            TextView empty = text("Nenhum endereço encontrado. Tente informar rua, número e cidade.", 13, GRAY, false);
            empty.setPadding(dp(8), dp(10), dp(8), dp(8));
            target.addView(empty, lpMatchWrap());
            return;
        }
        for (SearchItem item : items) {
            TextView row = text(item.label, 14, BLACK, false);
            row.setMaxLines(2);
            row.setEllipsize(TextUtils.TruncateAt.END);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(14), dp(9), dp(14), dp(9));
            row.setMinHeight(dp(58));
            row.setBackground(round(Color.rgb(250, 250, 250), 14, Color.rgb(228, 228, 228)));
            row.setClickable(true);
            row.setFocusable(true);
            row.setOnClickListener(v -> {
                ++searchSeq;
                cancelAddressSearchOnly();
                hideKeyboard();
                if (forOrigin) {
                    origin = new GeoPoint(item.lat, item.lng);
                    originLabel = item.label;
                    originView.setText(item.label);
                    if (dialog != null && dialog.isShowing()) dialog.dismiss();
                } else {
                    destination = new GeoPoint(item.lat, item.lng);
                    destinationLabel = item.label;
                    showOptions();
                }
            });
            target.addView(row, lpMatchWrap());
            target.addView(space(6));
        }
    }
''','''    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        target.removeAllViews();
        if (items.isEmpty()) {
            TextView empty = text("Nenhum endereço ou local encontrado. Tente informar outro nome, rua ou categoria.", 13, GRAY, false);
            empty.setPadding(dp(8), dp(10), dp(8), dp(8));
            target.addView(empty, lpMatchWrap());
            return;
        }
        for (SearchItem item : items) {
            LinearLayout row = horizontal();
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(12), dp(9), dp(12), dp(9));
            row.setMinimumHeight(dp(66));
            row.setBackground(round(Color.rgb(250, 250, 250), 14, Color.rgb(228, 228, 228)));
            TextView icon = text("place".equals(item.kind) ? "🏪" : "📍", 22, BLACK, false);
            icon.setGravity(Gravity.CENTER);
            row.addView(icon, new LinearLayout.LayoutParams(dp(40), dp(48)));
            LinearLayout labels = vertical(Color.TRANSPARENT);
            String title = item.name == null || item.name.isBlank() ? item.label : item.name;
            TextView titleView = text(title, 14, BLACK, true);
            titleView.setMaxLines(1);
            titleView.setEllipsize(TextUtils.TruncateAt.END);
            labels.addView(titleView);
            String detail = item.subtitle == null || item.subtitle.isBlank() ? item.label : item.subtitle;
            if (!detail.equals(title)) {
                TextView detailView = text(detail, 12, GRAY, false);
                detailView.setMaxLines(2);
                detailView.setEllipsize(TextUtils.TruncateAt.END);
                labels.addView(detailView);
            }
            row.addView(labels, new LinearLayout.LayoutParams(0, -2, 1));
            row.setClickable(true);
            row.setFocusable(true);
            row.setOnClickListener(v -> {
                ++searchSeq;
                cancelAddressSearchOnly();
                hideKeyboard();
                if (forOrigin) {
                    origin = new GeoPoint(item.lat, item.lng);
                    originLabel = item.label;
                    originView.setText(item.label);
                    if (dialog != null && dialog.isShowing()) dialog.dismiss();
                } else {
                    destination = new GeoPoint(item.lat, item.lng);
                    destinationLabel = item.label;
                    showOptions();
                }
            });
            target.addView(row, lpMatchWrap());
            target.addView(space(6));
        }
    }
''','lista de resultados')

repl('''    private static class SearchItem {
        final String label;
        final double lat;
        final double lng;
        SearchItem(String label, double lat, double lng) {
            this.label = label;
            this.lat = lat;
            this.lng = lng;
        }
    }
''','''    private static class SearchItem {
        final String label;
        final String name;
        final String subtitle;
        final String kind;
        final double lat;
        final double lng;
        SearchItem(String label, String name, String subtitle, String kind, double lat, double lng) {
            this.label = label;
            this.name = name == null ? "" : name;
            this.subtitle = subtitle == null ? "" : subtitle;
            this.kind = kind == null ? "address" : kind;
            this.lat = lat;
            this.lng = lng;
        }
    }
''','SearchItem')

path.write_text(text, encoding='utf-8')
print('Passageiro v0.6: busca regional, comércios e avatar aplicados.')
exec(Path('apply_menu_patch.py').read_text(encoding='utf-8'))
