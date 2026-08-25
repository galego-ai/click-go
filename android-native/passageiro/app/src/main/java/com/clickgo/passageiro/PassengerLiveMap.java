package com.clickgo.passageiro;

import android.content.Context;
import android.graphics.Color;
import android.os.Build;
import android.view.Gravity;
import android.view.ViewGroup;
import android.webkit.RenderProcessGoneDetail;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.FrameLayout;
import android.widget.TextView;

import java.util.Locale;

/**
 * Crash-safe map for active-ride tracking.
 *
 * The WebView renderer is isolated from the Activity. If Android/HyperOS kills
 * that renderer, the broken WebView is disposed and the ride controls remain
 * available instead of the passenger app closing.
 */
public final class PassengerLiveMap extends FrameLayout {
    private WebView web;
    private final TextView fallback;
    private boolean pageReady;
    private boolean disposed;
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

        fallback = new TextView(context);
        fallback.setText("Mapa temporariamente indisponível\nO acompanhamento da corrida continua ativo.");
        fallback.setTextColor(Color.rgb(70, 70, 70));
        fallback.setTextSize(13);
        fallback.setGravity(Gravity.CENTER);
        fallback.setPadding(dp(22), dp(22), dp(22), dp(22));
        fallback.setVisibility(GONE);
        addView(fallback, new FrameLayout.LayoutParams(-1, -1));

        createWebView(context);
    }

    private void createWebView(Context context) {
        if (disposed) return;
        try {
            WebView candidate = new WebView(context);
            web = candidate;
            candidate.setBackgroundColor(Color.rgb(238, 238, 238));
            candidate.setOverScrollMode(OVER_SCROLL_NEVER);
            candidate.setVerticalScrollBarEnabled(false);
            candidate.setHorizontalScrollBarEnabled(false);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.O) {
                candidate.setRendererPriorityPolicy(WebView.RENDERER_PRIORITY_IMPORTANT, false);
            }

            WebSettings settings = candidate.getSettings();
            settings.setJavaScriptEnabled(true);
            settings.setDomStorageEnabled(true);
            settings.setAllowFileAccess(false);
            settings.setAllowContentAccess(false);
            settings.setLoadsImagesAutomatically(true);
            settings.setMediaPlaybackRequiresUserGesture(true);
            settings.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

            candidate.setWebViewClient(new WebViewClient() {
                @Override public void onPageFinished(WebView view, String url) {
                    if (disposed || view != web) return;
                    pageReady = true;
                    flushState();
                }

                @Override public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                    if (view == web) {
                        pageReady = false;
                        web = null;
                        PassengerLiveMap.this.post(() -> disposeBrokenRenderer(view));
                    }
                    // Returning true tells Android that this renderer loss was handled.
                    return true;
                }
            });

            addView(candidate, 0, new FrameLayout.LayoutParams(-1, -1));
            candidate.loadDataWithBaseURL("https://click-go.local/", html(), "text/html", "UTF-8", null);
        } catch (Throwable ignored) {
            WebView failed = web;
            web = null;
            pageReady = false;
            if (failed != null) {
                try { removeView(failed); } catch (Throwable ignored2) {}
                try { failed.destroy(); } catch (Throwable ignored2) {}
            }
            showFallback();
        }
    }

    public void setRoute(double oLat, double oLng, double dLat, double dLng) {
        if (disposed) return;
        originLat = oLat;
        originLng = oLng;
        destinationLat = dLat;
        destinationLng = dLng;
        if (pageReady) emitRoute();
    }

    public void updateDriver(double lat, double lng, double heading, String vehicleType) {
        if (disposed) return;
        driverLat = lat;
        driverLng = lng;
        driverHeading = Double.isFinite(heading) ? heading : 0.0;
        driverVehicleType = vehicleType == null || vehicleType.isBlank() ? "car" : vehicleType;
        if (pageReady) emitDriver();
    }

    public void updatePassenger(double lat, double lng) {
        if (disposed) return;
        passengerLat = lat;
        passengerLng = lng;
        if (pageReady) emitPassenger();
    }

    public void destroySafely() {
        if (disposed) return;
        disposed = true;
        pageReady = false;
        WebView current = web;
        web = null;
        if (current == null) return;
        try { current.stopLoading(); } catch (Throwable ignored) {}
        try { current.setWebViewClient(null); } catch (Throwable ignored) {}
        try { current.loadUrl("about:blank"); } catch (Throwable ignored) {}
        try { current.clearHistory(); } catch (Throwable ignored) {}
        try {
            if (current.getParent() instanceof ViewGroup) ((ViewGroup) current.getParent()).removeView(current);
        } catch (Throwable ignored) {}
        try { current.removeAllViews(); } catch (Throwable ignored) {}
        try { current.destroy(); } catch (Throwable ignored) {}
    }

    private void disposeBrokenRenderer(WebView broken) {
        try {
            if (broken.getParent() instanceof ViewGroup) ((ViewGroup) broken.getParent()).removeView(broken);
        } catch (Throwable ignored) {}
        try { broken.removeAllViews(); } catch (Throwable ignored) {}
        try { broken.destroy(); } catch (Throwable ignored) {}
        if (!disposed) showFallback();
    }

    private void showFallback() {
        if (disposed) return;
        fallback.bringToFront();
        fallback.setVisibility(VISIBLE);
    }

    private void flushState() {
        emitRoute();
        emitDriver();
        emitPassenger();
    }

    private void emitRoute() {
        if (!pageReady || disposed || originLat == null || originLng == null || destinationLat == null || destinationLng == null) return;
        safeEval(String.format(Locale.US,
                "window.cgSetRoute&&window.cgSetRoute(%.7f,%.7f,%.7f,%.7f);",
                originLat, originLng, destinationLat, destinationLng));
    }

    private void emitDriver() {
        if (!pageReady || disposed || driverLat == null || driverLng == null) return;
        String safeType = driverVehicleType.toLowerCase(Locale.ROOT).contains("moto") ? "moto" : "car";
        safeEval(String.format(Locale.US,
                "window.cgSetDriver&&window.cgSetDriver(%.7f,%.7f,%.2f,'%s');",
                driverLat, driverLng, driverHeading, safeType));
    }

    private void emitPassenger() {
        if (!pageReady || disposed || passengerLat == null || passengerLng == null) return;
        safeEval(String.format(Locale.US,
                "window.cgSetPassenger&&window.cgSetPassenger(%.7f,%.7f);",
                passengerLat, passengerLng));
    }

    private void safeEval(String script) {
        WebView current = web;
        if (!pageReady || disposed || current == null || script == null) return;
        try { current.evaluateJavascript(script, null); } catch (Throwable ignored) {
            pageReady = false;
        }
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
                + "<script>(function(){'use strict';let map,routeLayer,originMarker,destMarker,driverMarker,passengerMarker,lastDriver=null,failed=false,attempts=0;"
                + "function icon(html,size){return L.divIcon({html:html,className:'',iconSize:[size,size],iconAnchor:[size/2,size/2]});}"
                + "function boot(){if(!window.L){if(++attempts>40){failed=true;document.getElementById('loading').innerText='Mapa indisponível. A corrida continua ativa.';return;}setTimeout(boot,150);return;}map=L.map('map',{zoomControl:false,attributionControl:false,preferCanvas:true}).setView([-14.5247,-49.1408],14);"
                + "L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,updateWhenIdle:true,keepBuffer:1}).addTo(map);"
                + "document.getElementById('loading').style.display='none';setTimeout(function(){map.invalidateSize(false);},80);}"
                + "function straight(o,d){if(routeLayer)map.removeLayer(routeLayer);routeLayer=L.polyline([o,d],{color:'#111',weight:5,opacity:.82}).addTo(map);}"
                + "window.cgSetRoute=function(olat,olng,dlat,dlng){if(failed)return;if(!map){setTimeout(function(){cgSetRoute(olat,olng,dlat,dlng);},120);return;}let o=[olat,olng],d=[dlat,dlng];"
                + "if(originMarker)map.removeLayer(originMarker);if(destMarker)map.removeLayer(destMarker);originMarker=L.circleMarker(o,{radius:8,color:'#111',weight:3,fillColor:'#ffd400',fillOpacity:1}).addTo(map);destMarker=L.marker(d,{icon:icon(\"<div class='cg-end'></div>\",26)}).addTo(map);"
                + "straight(o,d);map.fitBounds(L.latLngBounds([o,d]).pad(.25),{animate:false,maxZoom:16});"
                + "let url='https://router.project-osrm.org/route/v1/driving/'+olng+','+olat+';'+dlng+','+dlat+'?overview=simplified&geometries=geojson&steps=false';"
                + "fetch(url).then(r=>r.ok?r.json():Promise.reject()).then(j=>{if(!j.routes||!j.routes.length)return;let c=j.routes[0].geometry.coordinates.map(p=>[p[1],p[0]]);if(routeLayer)map.removeLayer(routeLayer);routeLayer=L.polyline(c,{color:'#111',weight:5,opacity:.9}).addTo(map);}).catch(function(){});};"
                + "window.cgSetDriver=function(lat,lng,heading,type){if(failed)return;if(!map){setTimeout(function(){cgSetDriver(lat,lng,heading,type);},120);return;}let emoji=type==='moto'?'🏍':'🚗';let h=\"<div class='cg-vehicle'><span style='display:inline-block;transform:rotate(\"+heading+\"deg)'>\"+emoji+\"</span></div>\";"
                + "let p=[lat,lng];if(!driverMarker){driverMarker=L.marker(p,{icon:icon(h,46),zIndexOffset:900}).addTo(map);}else{driverMarker.setLatLng(p);driverMarker.setIcon(icon(h,46));}lastDriver=p;};"
                + "window.cgSetPassenger=function(lat,lng){if(failed||!map)return;let p=[lat,lng];if(!passengerMarker)passengerMarker=L.marker(p,{icon:icon(\"<div class='cg-passenger'></div>\",28),zIndexOffset:700}).addTo(map);else passengerMarker.setLatLng(p);};"
                + "boot();})();</script></body></html>";
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
