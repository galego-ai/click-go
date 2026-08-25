package com.clickgo.passageiro;

import android.content.Context;
import android.graphics.Color;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import java.util.Locale;

/**
 * Mapa isolado para o acompanhamento de uma corrida ativa.
 *
 * A tela de acompanhamento não usa osmdroid. Isso evita que a transição
 * "procurando -> motorista aceitou" dependa do ciclo de layout/Projection do
 * MapView, que pode entrar em ANR em alguns aparelhos quando a tela é criada
 * enquanto o layout ainda está mudando.
 */
public final class PassengerLiveMap extends WebView {
    private boolean pageReady;
    private Double originLat;
    private Double originLng;
    private Double destinationLat;
    private Double destinationLng;
    private Double driverLat;
    private Double driverLng;
    private double driverHeading;
    private String driverVehicleType = "car";
    private Double passengerLat;
    private Double passengerLng;

    public PassengerLiveMap(Context context) {
        super(context);
        setBackgroundColor(Color.rgb(238, 238, 238));
        setOverScrollMode(OVER_SCROLL_NEVER);
        setVerticalScrollBarEnabled(false);
        setHorizontalScrollBarEnabled(false);

        WebSettings settings = getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setAllowFileAccess(false);
        settings.setAllowContentAccess(false);
        settings.setLoadsImagesAutomatically(true);
        settings.setMediaPlaybackRequiresUserGesture(true);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

        setWebViewClient(new WebViewClient() {
            @Override public void onPageFinished(WebView view, String url) {
                pageReady = true;
                flushState();
            }
        });
        loadDataWithBaseURL("https://click-go.local/", html(), "text/html", "UTF-8", null);
    }

    public void setRoute(double oLat, double oLng, double dLat, double dLng) {
        originLat = oLat;
        originLng = oLng;
        destinationLat = dLat;
        destinationLng = dLng;
        if (pageReady) emitRoute();
    }

    public void updateDriver(double lat, double lng, double heading, String vehicleType) {
        driverLat = lat;
        driverLng = lng;
        driverHeading = Double.isFinite(heading) ? heading : 0.0;
        driverVehicleType = vehicleType == null || vehicleType.isBlank() ? "car" : vehicleType;
        if (pageReady) emitDriver();
    }

    public void updatePassenger(double lat, double lng) {
        passengerLat = lat;
        passengerLng = lng;
        if (pageReady) emitPassenger();
    }

    public void destroySafely() {
        pageReady = false;
        try { stopLoading(); } catch (Exception ignored) {}
        try { setWebViewClient(null); } catch (Exception ignored) {}
        try { loadUrl("about:blank"); } catch (Exception ignored) {}
        try { clearHistory(); } catch (Exception ignored) {}
        try { removeAllViews(); } catch (Exception ignored) {}
        try { destroy(); } catch (Exception ignored) {}
    }

    private void flushState() {
        emitRoute();
        emitDriver();
        emitPassenger();
    }

    private void emitRoute() {
        if (!pageReady || originLat == null || originLng == null || destinationLat == null || destinationLng == null) return;
        evaluateJavascript(String.format(Locale.US,
                "window.cgSetRoute&&window.cgSetRoute(%.7f,%.7f,%.7f,%.7f);",
                originLat, originLng, destinationLat, destinationLng), null);
    }

    private void emitDriver() {
        if (!pageReady || driverLat == null || driverLng == null) return;
        String safeType = driverVehicleType.toLowerCase(Locale.ROOT).contains("moto") ? "moto" : "car";
        evaluateJavascript(String.format(Locale.US,
                "window.cgSetDriver&&window.cgSetDriver(%.7f,%.7f,%.2f,'%s');",
                driverLat, driverLng, driverHeading, safeType), null);
    }

    private void emitPassenger() {
        if (!pageReady || passengerLat == null || passengerLng == null) return;
        evaluateJavascript(String.format(Locale.US,
                "window.cgSetPassenger&&window.cgSetPassenger(%.7f,%.7f);",
                passengerLat, passengerLng), null);
    }

    private String html() {
        return "<!doctype html><html><head>"
                + "<meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no'>"
                + "<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>"
                + "<style>html,body,#map{height:100%;width:100%;margin:0;background:#eee;font-family:Arial,sans-serif}"
                + "#loading{position:absolute;z-index:999;left:50%;top:50%;transform:translate(-50%,-50%);background:#fff;padding:9px 13px;border-radius:12px;color:#222;font-size:12px;box-shadow:0 2px 10px #9996}"
                + ".cg-vehicle{width:40px;height:40px;border-radius:50%;background:#ffd400;border:3px solid #111;display:flex;align-items:center;justify-content:center;box-shadow:0 3px 10px #0005;font-size:21px}"
                + ".cg-passenger{width:18px;height:18px;border-radius:50%;background:#111;border:5px solid #ffd400;box-shadow:0 2px 8px #0004}"
                + ".cg-end{width:18px;height:18px;border-radius:50%;background:#ef4444;border:4px solid white;box-shadow:0 2px 8px #0004}</style>"
                + "</head><body><div id='map'></div><div id='loading'>Carregando mapa...</div>"
                + "<script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>"
                + "<script>(function(){'use strict';let map,routeLayer,originMarker,destMarker,driverMarker,passengerMarker,lastDriver=null;"
                + "function icon(html,size){return L.divIcon({html:html,className:'',iconSize:[size,size],iconAnchor:[size/2,size/2]});}"
                + "function boot(){if(!window.L){setTimeout(boot,120);return;}map=L.map('map',{zoomControl:false,attributionControl:false,preferCanvas:true}).setView([-14.5247,-49.1408],14);"
                + "L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,updateWhenIdle:true,keepBuffer:1}).addTo(map);"
                + "document.getElementById('loading').style.display='none';setTimeout(function(){map.invalidateSize(false);},80);}"
                + "function straight(o,d){if(routeLayer)map.removeLayer(routeLayer);routeLayer=L.polyline([o,d],{color:'#111',weight:5,opacity:.82}).addTo(map);}"
                + "window.cgSetRoute=function(olat,olng,dlat,dlng){if(!map){setTimeout(function(){cgSetRoute(olat,olng,dlat,dlng);},120);return;}let o=[olat,olng],d=[dlat,dlng];"
                + "if(originMarker)map.removeLayer(originMarker);if(destMarker)map.removeLayer(destMarker);originMarker=L.circleMarker(o,{radius:8,color:'#111',weight:3,fillColor:'#ffd400',fillOpacity:1}).addTo(map);destMarker=L.marker(d,{icon:icon(\"<div class='cg-end'></div>\",26)}).addTo(map);"
                + "straight(o,d);map.fitBounds(L.latLngBounds([o,d]).pad(.25),{animate:false,maxZoom:16});"
                + "let url='https://router.project-osrm.org/route/v1/driving/'+olng+','+olat+';'+dlng+','+dlat+'?overview=simplified&geometries=geojson&steps=false';"
                + "fetch(url).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(!j.routes||!j.routes.length)return;let c=j.routes[0].geometry.coordinates.map(p=>[p[1],p[0]]);if(routeLayer)map.removeLayer(routeLayer);routeLayer=L.polyline(c,{color:'#111',weight:5,opacity:.9}).addTo(map);}).catch(function(){});};"
                + "window.cgSetDriver=function(lat,lng,heading,type){if(!map){setTimeout(function(){cgSetDriver(lat,lng,heading,type);},120);return;}let emoji=type==='moto'?'🏍':'🚗';let h=\"<div class='cg-vehicle'><span style='display:inline-block;transform:rotate(\"+heading+\"deg)'>\"+emoji+\"</span></div>\";"
                + "let p=[lat,lng];if(!driverMarker){driverMarker=L.marker(p,{icon:icon(h,46),zIndexOffset:900}).addTo(map);}else{driverMarker.setLatLng(p);driverMarker.setIcon(icon(h,46));}lastDriver=p;};"
                + "window.cgSetPassenger=function(lat,lng){if(!map)return;let p=[lat,lng];if(!passengerMarker)passengerMarker=L.marker(p,{icon:icon(\"<div class='cg-passenger'></div>\",28),zIndexOffset:700}).addTo(map);else passengerMarker.setLatLng(p);};"
                + "boot();})();</script></body></html>";
    }
}
