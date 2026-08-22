from pathlib import Path

path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = path.read_text(encoding='utf-8')

# No seletor de destino, a foto começa na origem e é ela própria que o passageiro arrasta.
old_initial = '''        GeoPoint initial = forOrigin ? origin : (destination != null ? destination : origin);\n'''
new_initial = '''        GeoPoint initial = forOrigin ? origin : origin;\n        if (!forOrigin && destination != null) initial = origin != null ? origin : destination;\n'''
if old_initial not in text:
    raise SystemExit('Inicialização do seletor não encontrada')
text = text.replace(old_initial, new_initial, 1)

old_marker = '''        selected.setTitle(forOrigin ? "Embarque escolhido" : "Destino escolhido");\n        selected.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);\n        selected.setDraggable(true);\n'''
new_marker = '''        selected.setTitle(forOrigin ? "Embarque escolhido" : "Arraste sua foto até o destino");\n        if (!forOrigin) selected.setIcon(PassengerAvatar.markerDrawable(this));\n        selected.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);\n        selected.setDraggable(true);\n'''
if old_marker not in text:
    raise SystemExit('Marcador móvel não encontrado')
text = text.replace(old_marker, new_marker, 1)

old_tip = '''        TextView tip = text(forOrigin ? "Toque no mapa ou arraste o marcador para ajustar o embarque." : "Toque no mapa ou arraste o marcador para escolher o DESTINO.", 13, Color.WHITE, true);\n'''
new_tip = '''        TextView tip = text(forOrigin ? "Toque no mapa ou arraste o marcador para ajustar o embarque." : "Arraste sua FOTO da origem até o destino, ou toque no ponto desejado.", 13, Color.WHITE, true);\n'''
if old_tip not in text:
    raise SystemExit('Texto de ajuda não encontrado')
text = text.replace(old_tip, new_tip, 1)

# Na tela da rota, a foto representa o destino escolhido. A origem continua como marcador de embarque.
old_start_icon = '''        start.setTitle("Embarque");\n        start.setIcon(PassengerAvatar.markerDrawable(this));\n        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);\n'''
new_start_icon = '''        start.setTitle("Embarque");\n        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);\n'''
if old_start_icon not in text:
    raise SystemExit('Ícone antigo de origem não encontrado')
text = text.replace(old_start_icon, new_start_icon, 1)

old_end = '''        end.setPosition(destination);\n        end.setTitle("Destino");\n        end.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);\n'''
new_end = '''        end.setPosition(destination);\n        end.setTitle("Destino");\n        end.setIcon(PassengerAvatar.markerDrawable(this));\n        end.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);\n'''
if old_end not in text:
    raise SystemExit('Marcador de destino da rota não encontrado')
text = text.replace(old_end, new_end, 1)

# Versão 1.3
build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
build = build.replace('versionCode 12', 'versionCode 13', 1)
build = build.replace("versionName '1.2-native-beta'", "versionName '1.3-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Passageiro v1.3: foto do perfil é o marcador arrastável do destino.')
