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

checks = [
    ('campos de contexto', fields_old),
    ('home', home_old),
    ('marcador', marker_old),
    ('busca', search_old),
    ('geocodificação reversa', reverse_old),
]
for name, snippet in checks:
    if snippet not in text:
        raise SystemExit(f'Trecho de {name} não encontrado')

text = text.replace(fields_old, fields_new, 1)
text = text.replace(home_old, home_new, 1)
text = text.replace(marker_old, marker_new, 1)
text = text.replace(search_old, search_new, 1)
text = text.replace(reverse_old, reverse_new, 1)
path.write_text(text, encoding='utf-8')
print('Avatar e busca local com cidade/UF aplicados ao App Passageiro.')
