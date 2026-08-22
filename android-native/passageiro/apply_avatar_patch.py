from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

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
search_new = '''                String searchText = query;
                if (originLabel != null && originLabel.contains("·")) {
                    String[] regionParts = originLabel.split("·");
                    String regionHint = regionParts[regionParts.length - 1].trim();
                    if (!regionHint.isBlank() && !query.toLowerCase(Locale.ROOT).contains(regionHint.toLowerCase(Locale.ROOT))) {
                        searchText = query + ", " + regionHint;
                    }
                }
                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(searchText, StandardCharsets.UTF_8.toString());
                if (origin != null) {
                    url += "&lat=" + origin.getLatitude() + "&lng=" + origin.getLongitude();
                }
'''

if home_old not in text:
    raise SystemExit('Trecho da home não encontrado para aplicar avatar')
if marker_old not in text:
    raise SystemExit('Trecho do marcador não encontrado para aplicar avatar')
if search_old not in text:
    raise SystemExit('Trecho da busca não encontrado para regionalizar')

text = text.replace(home_old, home_new, 1)
text = text.replace(marker_old, marker_new, 1)
text = text.replace(search_old, search_new, 1)
path.write_text(text, encoding='utf-8')
print('Avatar e busca regionalizada aplicados ao App Passageiro.')
