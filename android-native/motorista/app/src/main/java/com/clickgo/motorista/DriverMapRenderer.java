package com.clickgo.motorista;

import android.graphics.Color;
import android.location.Location;

import org.json.JSONObject;
import org.osmdroid.util.BoundingBox;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.Marker;
import org.osmdroid.views.overlay.Polyline;

import java.util.ArrayList;
import java.util.List;

public final class DriverMapRenderer {
    private DriverMapRenderer() {}

    public static void render(MapView map, Location current, JSONObject target, int strokeWidth) {
        if (map == null) return;
        map.getOverlays().clear();
        List<GeoPoint> points = new ArrayList<>();
        if (current != null) {
            GeoPoint me = new GeoPoint(current.getLatitude(), current.getLongitude());
            marker(map, me, "Você");
            points.add(me);
        }
        if (target != null) {
            double oLat = target.optDouble("origin_lat", Double.NaN);
            double oLng = target.optDouble("origin_lng", Double.NaN);
            double dLat = target.optDouble("destination_lat", Double.NaN);
            double dLng = target.optDouble("destination_lng", Double.NaN);
            if (Double.isFinite(oLat) && Double.isFinite(oLng)) {
                GeoPoint origin = new GeoPoint(oLat, oLng);
                marker(map, origin, "Passageiro / embarque");
                points.add(origin);
            }
            if (Double.isFinite(dLat) && Double.isFinite(dLng)) {
                GeoPoint dest = new GeoPoint(dLat, dLng);
                marker(map, dest, "Destino");
                points.add(dest);
            }
            if (points.size() >= 2) {
                Polyline line = new Polyline();
                line.setPoints(points);
                line.getOutlinePaint().setStrokeWidth(strokeWidth);
                line.getOutlinePaint().setColor(Color.rgb(255,212,0));
                map.getOverlays().add(line);
            }
        }
        if (points.size() > 1) {
            try { map.zoomToBoundingBox(BoundingBox.fromGeoPoints(points), true, 55); } catch (Exception ignored) {}
        } else if (points.size() == 1) {
            map.getController().setZoom(15.0);
            map.getController().setCenter(points.get(0));
        }
        map.invalidate();
    }

    private static void marker(MapView map, GeoPoint point, String title) {
        Marker marker = new Marker(map);
        marker.setPosition(point);
        marker.setTitle(title);
        marker.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        map.getOverlays().add(marker);
    }
}
