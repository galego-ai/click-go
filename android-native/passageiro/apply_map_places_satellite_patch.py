from pathlib import Path

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

def add_import(after,value):
    global text
    if value not in text:
        text=text.replace(after,after+value,1)

add_import('import org.osmdroid.tileprovider.tilesource.TileSourceFactory;\n','import org.osmdroid.tileprovider.tilesource.OnlineTileSourceBase;\n')
add_import('import org.osmdroid.util.BoundingBox;\n','import org.osmdroid.util.MapTileIndex;\n')

field_anchor='''    private static final int ORANGE = Color.rgb(255, 138, 61);\n'''
field_new='''    private static final int ORANGE = Color.rgb(255, 138, 61);\n    private static final OnlineTileSourceBase SATELLITE_SOURCE = new OnlineTileSourceBase(\n            "Esri World Imagery", 0, 19, 256, ".jpg",\n            new String[]{"https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/"}) {\n        @Override public String getTileURLString(long index) {\n            int z = MapTileIndex.getZoom(index);\n            int x = MapTileIndex.getX(index);\n            int y = MapTileIndex.getY(index);\n            return getBaseUrl() + z + "/" + y + "/" + x;\n        }\n    };\n'''
if field_anchor not in text: raise SystemExit('Constantes do mapa não encontradas')
text=text.replace(field_anchor,field_new,1)

state_anchor='''    private String destinationLabel = "";\n'''
state_new='''    private String destinationLabel = "";\n    private JSONArray nearbyBusinesses = new JSONArray();\n    private int businessLoadSeq = 0;\n'''
if state_anchor not in text: raise SystemExit('Estado do destino não encontrado')
text=text.replace(state_anchor,state_new,1)

map_anchor='''        mapFrame.addView(map, new FrameLayout.LayoutParams(-1, -1));\n\n        Button back = circleButton("←", 52);\n'''
map_new='''        mapFrame.addView(map, new FrameLayout.LayoutParams(-1, -1));\n        addMapModeButtons(mapFrame, map);\n\n        Button back = circleButton("←", 52);\n'''
if map_anchor not in text: raise SystemExit('Mapa principal não encontrado')
text=text.replace(map_anchor,map_new,1)

options_anchor='''        final MapView firstMap = map;\n        firstMap.post(() -> {\n            if (!destroyed && map == firstMap) drawRoute();\n        });\n        loadOptions();\n'''
if options_anchor not in text:
    options_anchor='''        setContentView(root);\n        drawRoute();\n        loadOptions();\n'''
    options_new='''        setContentView(root);\n        drawRoute();\n        loadNearbyBusinesses(origin, map);\n        loadOptions();\n'''
else:
    options_new='''        final MapView firstMap = map;\n        firstMap.post(() -> {\n            if (!destroyed && map == firstMap) {\n                drawRoute();\n                loadNearbyBusinesses(origin, firstMap);\n            }\n        });\n        loadOptions();\n'''
if options_anchor not in text: raise SystemExit('Final de showOptions não encontrado')
text=text.replace(options_anchor,options_new,1)

route_anchor='''        map.getOverlays().add(line);\n        final MapView routeMap = map;\n'''
route_new='''        map.getOverlays().add(line);\n        addBusinessMarkers(map);\n        final MapView routeMap = map;\n'''
if route_anchor in text:
    text=text.replace(route_anchor,route_new,1)
else:
    route_anchor='''        map.getOverlays().add(line);\n        try { map.zoomToBoundingBox(BoundingBox.fromGeoPoints(routePoints), true, dp(70)); } catch (Exception ignored) {}\n'''
    route_new='''        map.getOverlays().add(line);\n        addBusinessMarkers(map);\n        try { map.zoomToBoundingBox(BoundingBox.fromGeoPoints(routePoints), true, dp(70)); } catch (Exception ignored) {}\n'''
    if route_anchor not in text: raise SystemExit('Rota final não encontrada')
    text=text.replace(route_anchor,route_new,1)

# A linha frame.addView(picker...) é exclusiva do seletor. Não depende da expressão de initial.
picker_anchor='''        frame.addView(picker, new FrameLayout.LayoutParams(-1, -1));\n'''
picker_new='''        frame.addView(picker, new FrameLayout.LayoutParams(-1, -1));\n        addMapModeButtons(frame, picker);\n'''
if picker_anchor not in text: raise SystemExit('Frame do seletor de mapa não encontrado')
text=text.replace(picker_anchor,picker_new,1)

# Carrega empresas após initial já existir e sem interferir no gesto de arrastar.
business_picker_anchor='''        final GeoPoint[] chosen = { initial };\n'''
business_picker_new='''        final GeoPoint[] chosen = { initial };\n        loadNearbyBusinesses(initial, picker);\n'''
if business_picker_anchor not in text: raise SystemExit('Coordenada escolhida do seletor não encontrada')
text=text.replace(business_picker_anchor,business_picker_new,1)

helper_marker='''    private TextView drawerItem(String icon, String label) {\n'''
if helper_marker not in text:
    helper_marker='''    private LinearLayout showSectionShell(String title) {\n'''
helpers=r'''    private void addMapModeButtons(FrameLayout frame, MapView target) {
        LinearLayout modes = horizontal();
        modes.setPadding(dp(4), dp(4), dp(4), dp(4));
        modes.setBackground(round(Color.argb(235, 255, 255, 255), 16, Color.rgb(215, 215, 215)));
        Button street = smallButton("Rua");
        Button satellite = smallButton("Satélite");
        modes.addView(street, new LinearLayout.LayoutParams(dp(78), dp(42)));
        modes.addView(satellite, new LinearLayout.LayoutParams(dp(94), dp(42)));
        FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(-2, dp(50));
        lp.gravity = Gravity.BOTTOM | Gravity.RIGHT;
        lp.rightMargin = dp(14);
        lp.bottomMargin = dp(14);
        frame.addView(modes, lp);
        street.setOnClickListener(v -> {
            target.setTileSource(TileSourceFactory.MAPNIK);
            target.invalidate();
            toast("Mapa de ruas — cidades, bairros e vias.");
        });
        satellite.setOnClickListener(v -> {
            target.setTileSource(SATELLITE_SOURCE);
            target.invalidate();
            toast("Visualização por satélite. Use Rua para a leitura mais completa de bairros e vias.");
        });
    }

    private void loadNearbyBusinesses(GeoPoint center, MapView target) {
        if (center == null || target == null) return;
        final int seq = ++businessLoadSeq;
        final double lat = center.getLatitude();
        final double lng = center.getLongitude();
        io.execute(() -> {
            try {
                String url = "https://click-go-ten.vercel.app/api/google-places?lat=" + lat + "&lng=" + lng + "&radius=1600";
                JSONObject root = new JSONObject(ApiClient.absoluteGet(url));
                JSONArray rows = root.optJSONArray("places");
                if (rows == null || seq != businessLoadSeq) return;
                nearbyBusinesses = rows;
                ui.post(() -> {
                    if (destroyed || seq != businessLoadSeq) return;
                    addBusinessMarkers(target);
                    target.invalidate();
                });
            } catch (Exception ignored) {
                // Sem chave Google Places ou sem rede: o mapa permanece funcional.
            }
        });
    }

    private void addBusinessMarkers(MapView target) {
        JSONArray rows = nearbyBusinesses;
        if (target == null || rows == null) return;
        for (int i = 0; i < rows.length(); i++) {
            JSONObject place = rows.optJSONObject(i);
            if (place == null) continue;
            double lat = place.optDouble("lat", Double.NaN);
            double lng = place.optDouble("lng", Double.NaN);
            if (!Double.isFinite(lat) || !Double.isFinite(lng)) continue;
            Marker marker = new Marker(target);
            marker.setPosition(new GeoPoint(lat, lng));
            String name = place.optString("name", "Empresa");
            String phone = place.optString("phone", "").trim();
            String address = place.optString("address", "").trim();
            marker.setTitle(name);
            marker.setSnippet((!phone.isBlank() ? "Telefone: " + phone : "Telefone não informado")
                    + (!address.isBlank() ? "\n" + address : ""));
            GradientDrawable icon = new GradientDrawable();
            icon.setShape(GradientDrawable.OVAL);
            icon.setColor(YELLOW);
            icon.setStroke(dp(2), BLACK);
            icon.setSize(dp(18), dp(18));
            marker.setIcon(icon);
            marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_CENTER);
            target.getOverlays().add(marker);
        }
    }

'''
if helper_marker not in text: raise SystemExit('Ponto para helpers do mapa não encontrado')
text=text.replace(helper_marker,helpers+helper_marker,1)

build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
for old in ["versionCode 15","versionCode 14"]:
    if old in build:
        build=build.replace(old,"versionCode 16",1);break
for old in ["versionName '1.5-native-beta'","versionName '1.4-native-beta'"]:
    if old in build:
        build=build.replace(old,"versionName '1.6-native-beta'",1);break
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v1.6: Rua/Satélite e empresas Google com telefone preparados.')
