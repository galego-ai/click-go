from pathlib import Path

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

helpers='''
    private void drawRouteOverlays(List<GeoPoint> routePoints) {
        if (map == null || origin == null || destination == null) return;
        map.getOverlays().clear();
        Marker start = new Marker(map);
        start.setPosition(origin);
        start.setTitle("Embarque");
        start.setIcon(PassengerAvatar.markerDrawable(this));
        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        map.getOverlays().add(start);
        Marker end = new Marker(map);
        end.setPosition(destination);
        end.setTitle("Destino");
        end.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        map.getOverlays().add(end);
        Polyline line = new Polyline();
        line.setPoints(routePoints);
        line.getOutlinePaint().setStrokeWidth(dp(6));
        line.getOutlinePaint().setColor(Color.rgb(48, 92, 220));
        map.getOverlays().add(line);
        try { map.zoomToBoundingBox(BoundingBox.fromGeoPoints(routePoints), true, dp(70)); } catch (Exception ignored) {}
        map.invalidate();
    }

    private void showMapPicker(boolean forOrigin, TextView originView) {
        cancelAddressSearch();
        LinearLayout root = vertical(Color.WHITE);
        TextView title = text(forOrigin ? "Marque o local de embarque" : "Marque o destino", 20, BLACK, true);
        title.setPadding(dp(16), dp(14), dp(16), dp(10));
        root.addView(title, lpMatch(dp(58)));
        FrameLayout frame = new FrameLayout(this);
        MapView picker = new MapView(this);
        picker.setTileSource(TileSourceFactory.MAPNIK);
        picker.setMultiTouchControls(true);
        GeoPoint initial = forOrigin ? origin : (destination != null ? destination : origin);
        if (initial == null) initial = new GeoPoint(-14.52472, -49.14083);
        picker.getController().setZoom(16.0);
        picker.getController().setCenter(initial);
        frame.addView(picker, new FrameLayout.LayoutParams(-1, -1));
        Marker selected = new Marker(picker);
        selected.setPosition(initial);
        selected.setTitle(forOrigin ? "Embarque" : "Destino");
        selected.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        picker.getOverlays().add(selected);
        final GeoPoint[] chosen = { initial };
        MapEventsOverlay events = new MapEventsOverlay(new MapEventsReceiver() {
            @Override public boolean singleTapConfirmedHelper(GeoPoint point) {
                chosen[0] = point; selected.setPosition(point); picker.invalidate(); return true;
            }
            @Override public boolean longPressHelper(GeoPoint point) { return singleTapConfirmedHelper(point); }
        });
        picker.getOverlays().add(0, events);
        TextView tip = text("Toque no mapa para mover o marcador.", 13, Color.WHITE, true);
        tip.setPadding(dp(12),0,dp(12),0); tip.setGravity(Gravity.CENTER); tip.setBackground(round(Color.argb(220,17,17,17),14,Color.TRANSPARENT));
        FrameLayout.LayoutParams tipLp = new FrameLayout.LayoutParams(-2, dp(42)); tipLp.gravity = Gravity.TOP|Gravity.CENTER_HORIZONTAL; tipLp.topMargin = dp(14); frame.addView(tip, tipLp);
        root.addView(frame, new LinearLayout.LayoutParams(-1, 0, 1));
        LinearLayout actions = horizontal(); actions.setPadding(dp(14),dp(12),dp(14),dp(14));
        Button back = secondaryLight("Voltar"); Button confirm = primary("Confirmar local");
        actions.addView(back,new LinearLayout.LayoutParams(0,dp(56),1)); actions.addView(spaceH(8)); actions.addView(confirm,new LinearLayout.LayoutParams(0,dp(56),2)); root.addView(actions);
        back.setOnClickListener(v -> { picker.onDetach(); showHome(); });
        confirm.setOnClickListener(v -> {
            GeoPoint point = chosen[0];
            if (forOrigin) { origin = point; originLabel = "Local marcado no mapa"; if (originView != null) originView.setText(originLabel); picker.onDetach(); showHome(); }
            else { destination = point; destinationLabel = "Destino marcado no mapa"; picker.onDetach(); showOptions(); }
        });
        setContentView(root);
    }

'''

missing=[]
if 'private void drawRouteOverlays(List<GeoPoint> routePoints)' not in text: missing.append('route')
if 'private void showMapPicker(boolean forOrigin, TextView originView)' not in text: missing.append('picker')
if missing:
    marker='    private void loadOptions() {'
    if marker not in text: raise SystemExit('loadOptions não encontrado para restaurar auxiliares')
    insertion=''
    if 'route' in missing:
        start=helpers.index('    private void drawRouteOverlays')
        end=helpers.index('    private void showMapPicker')
        insertion+=helpers[start:end]
    if 'picker' in missing:
        start=helpers.index('    private void showMapPicker')
        insertion+=helpers[start:]
    text=text.replace(marker,insertion+marker,1)
    path.write_text(text,encoding='utf-8')
print('Auxiliares de mapa PRIME preservados:', ','.join(missing) if missing else 'já presentes')
