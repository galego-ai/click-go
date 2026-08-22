from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

fields_old = '''    private String originLabel = "Obtendo sua localização...";
    private String destinationLabel = "";
'''
fields_new = '''    private String originLabel = "Obtendo sua localização...";
    private String destinationLabel = "";
    private String originSearchContext = "";
'''

home_old = '''        setContentView(scroll(root, LIGHT));
        if (origin == null) obtainLocation(originView, false);
'''
home_new = '''        setContentView(scroll(root, LIGHT));
        PassengerAvatar.preload(this, token, () -> {
            if (map != null && origin != null && destination != null) drawRoute();
        });
        if (origin == null) obtainLocation(originView, false);
'''

marker_old = '''        start.setPosition(origin);
        start.setTitle("Embarque");
        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
'''
marker_new = '''        start.setPosition(origin);
        start.setTitle("Embarque");
        start.setIcon(PassengerAvatar.markerDrawable(this));
        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
'''

search_old = '''                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8.toString());
'''
search_new = '''                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8.toString());
                if (origin != null) {
                    url += "&lat=" + origin.getLatitude() + "&lng=" + origin.getLongitude();
                }
                if (originSearchContext != null && !originSearchContext.isBlank()) {
                    url += "&context=" + URLEncoder.encode(originSearchContext, StandardCharsets.UTF_8.toString());
                }
'''

reverse_old = '''                String resolved = shortAddress(addresses.get(0));
                if (resolved.isBlank()) return;
                ui.post(() -> {
                    if (destroyed || seq != locationSeq) return;
                    originLabel = resolved;
                    if (labelView != null && labelView.isAttachedToWindow()) labelView.setText(resolved);
                });
'''
reverse_new = '''                Address resolvedAddress = addresses.get(0);
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
'''

quick_old = '''        root.addView(quick);
        root.addView(space(18));
        root.addView(text("Digite ao menos 3 letras do destino. A localização atual é usada como origem, mas você pode alterá-la.", 13, GRAY, false));
'''
quick_new = '''        root.addView(quick);
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
'''

loading_old = '''        TextView loading = text("Buscando endereços…", 13, GRAY, false);
'''
loading_new = '''        TextView loading = text("Buscando endereços e locais próximos…", 13, GRAY, false);
'''

parse_old = '''                        String label = cleanLabel(row.optString("label", ""));
                        double lat = row.optDouble("lat", Double.NaN);
                        double lng = row.optDouble("lng", Double.NaN);
                        if (label.isBlank() || !Double.isFinite(lat) || !Double.isFinite(lng)) continue;
                        String key = label.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                        if (seen.add(key)) items.add(new SearchItem(label, lat, lng));
'''
parse_new = '''                        String label = cleanLabel(row.optString("label", ""));
                        String name = cleanLabel(row.optString("name", ""));
                        String subtitle = cleanLabel(row.optString("subtitle", ""));
                        String kind = row.optString("kind", "address");
                        double lat = row.optDouble("lat", Double.NaN);
                        double lng = row.optDouble("lng", Double.NaN);
                        if (label.isBlank() || !Double.isFinite(lat) || !Double.isFinite(lng)) continue;
                        String key = label.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                        if (seen.add(key)) items.add(new SearchItem(label, name, subtitle, kind, lat, lng));
'''

render_old = '''    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
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
'''
render_new = '''    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
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
'''

search_item_old = '''    private static class SearchItem {
        final String label;
        final double lat;
        final double lng;
        SearchItem(String label, double lat, double lng) {
            this.label = label;
            this.lat = lat;
            this.lng = lng;
        }
    }
'''
search_item_new = '''    private static class SearchItem {
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
'''

checks = [
    ('campos de contexto', fields_old),('home', home_old),('marcador', marker_old),('busca', search_old),
    ('geocodificação reversa', reverse_old),('atalhos', quick_old),('carregamento', loading_old),
    ('parse de resultados', parse_old),('render de resultados', render_old),('SearchItem', search_item_old),
]
for name, snippet in checks:
    if snippet not in text:
        raise SystemExit(f'Trecho de {name} não encontrado')

for old,new in [
    (fields_old,fields_new),(home_old,home_new),(marker_old,marker_new),(search_old,search_new),(reverse_old,reverse_new),
    (quick_old,quick_new),(loading_old,loading_new),(parse_old,parse_new),(render_old,render_new),(search_item_old,search_item_new)
]:
    text = text.replace(old,new,1)

path.write_text(text, encoding='utf-8')
print('Passageiro v0.6: avatar, cidade/UF e busca de comércios/locais aplicados.')
