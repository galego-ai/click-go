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

if home_old not in text:
    raise SystemExit('Trecho da home não encontrado para aplicar avatar')
if marker_old not in text:
    raise SystemExit('Trecho do marcador não encontrado para aplicar avatar')

text = text.replace(home_old, home_new, 1)
text = text.replace(marker_old, marker_new, 1)
path.write_text(text, encoding='utf-8')
print('Avatar do passageiro aplicado ao marcador de embarque.')
