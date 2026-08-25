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

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;

/**
 * Lightweight home map isolated behind a crash-safe container.
 *
 * Some Android/HyperOS builds may kill the WebView renderer independently from
 * the app process. A raw WebView with the default client can take the Activity
 * down when that happens. This container handles renderer loss, disposes the
 * broken WebView and keeps the passenger UI alive with a lightweight fallback.
 */
public final class PassengerHomeMap extends FrameLayout {
    private WebView web;
    private final TextView fallback;
    private boolean pageReady;
    private boolean disposed;
    private Double passengerLat;
    private Double passengerLng;
    private JSONArray drivers = new JSONArray();

    public PassengerHomeMap(Context context) {
        super(context);
        setBackgroundColor(Color.rgb(238, 238, 238));

        fallback = new TextView(context);
        fallback.setText("Mapa temporariamente indisponível\nVocê ainda pode pedir sua corrida normalmente.");
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

            WebSettings s = candidate.getSettings();
            s.setJavaScriptEnabled(true);
            s.setDomStorageEnabled(true);
            s.setAllowFileAccess(false);
            s.setAllowContentAccess(false);
            s.setLoadsImagesAutomatically(true);
            s.setMediaPlaybackRequiresUserGesture(true);
            s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);

            candidate.setWebViewClient(new WebViewClient() {
                @Override public void onPageFinished(WebView view, String url) {
                    if (disposed || view != web) return;
                    pageReady = true;
                    flush();
                }

                @Override public boolean onRenderProcessGone(WebView view, RenderProcessGoneDetail detail) {
                    if (view == web) {
                        pageReady = false;
                        web = null;
                        PassengerHomeMap.this.post(() -> disposeBrokenRenderer(view));
                    }
                    // We handled the dead renderer. Returning true keeps the Activity alive.
                    return true;
                }
            });

            FrameLayout.LayoutParams lp = new FrameLayout.LayoutParams(-1, -1);
            addView(candidate, 0, lp);
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

    public void setPassenger(double lat, double lng) {
        if (disposed || !Double.isFinite(lat) || !Double.isFinite(lng)) return;
        passengerLat = lat;
        passengerLng = lng;
        if (pageReady) emitPassenger();
    }

    public void setDrivers(JSONArray rows) {
        if (disposed) return;
        drivers = rows == null ? new JSONArray() : rows;
        if (pageReady) emitDrivers();
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

    private void flush() {
        emitPassenger();
        emitDrivers();
    }

    private void emitPassenger() {
        if (!pageReady || disposed || passengerLat == null || passengerLng == null) return;
        safeEval(String.format(Locale.US,
                "window.cgPassenger&&window.cgPassenger(%.7f,%.7f);",
                passengerLat, passengerLng));
    }

    private void emitDrivers() {
        if (!pageReady || disposed) return;
        JSONArray safe = new JSONArray();
        for (int i = 0; i < drivers.length(); i++) {
            JSONObject r = drivers.optJSONObject(i);
            if (r == null) continue;
            double lat = r.optDouble("lat", Double.NaN);
            double lng = r.optDouble("lng", Double.NaN);
            if (!Double.isFinite(lat) || !Double.isFinite(lng)) continue;
            JSONObject p = new JSONObject();
            try {
                p.put("id", r.optString("driver_id", "d" + i));
                p.put("lat", lat);
                p.put("lng", lng);
                p.put("kind", r.optString("category_name", "car").toLowerCase(Locale.ROOT).contains("moto") ? "moto" : "car");
            } catch (Exception ignored) {}
            safe.put(p);
        }
        safeEval("window.cgDrivers&&window.cgDrivers(" + safe.toString() + ");");
    }

    private void safeEval(String script) {
        WebView current = web;
        if (!pageReady || disposed || current == null || script == null) return;
        try { current.evaluateJavascript(script, null); } catch (Throwable ignored) {
            pageReady = false;
        }
    }

    private String html() {
        return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no'>"
                + "<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>"
                + "<style>html,body,#map{height:100%;width:100%;margin:0;background:#eee}.me{width:18px;height:18px;border-radius:50%;background:#111;border:5px solid #ffd400;box-shadow:0 2px 8px #0005}.car{width:38px;height:38px;border-radius:50%;background:#ffd400;border:3px solid #111;display:flex;align-items:center;justify-content:center;font-size:19px;box-shadow:0 2px 8px #0004}#loading{position:absolute;z-index:999;left:50%;top:45%;transform:translate(-50%,-50%);background:#fff;padding:8px 12px;border-radius:12px;font:12px Arial;color:#333}</style></head>"
                + "<body><div id='map'></div><div id='loading'>Carregando mapa...</div><script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>"
                + "<script>(function(){let map,me,marks={},failed=false,attempts=0;function icon(h,s){return L.divIcon({html:h,className:'',iconSize:[s,s],iconAnchor:[s/2,s/2]});}function boot(){if(!window.L){if(++attempts>40){failed=true;document.getElementById('loading').innerText='Mapa indisponível. Tente novamente depois.';return;}setTimeout(boot,150);return;}map=L.map('map',{zoomControl:false,attributionControl:false,preferCanvas:true}).setView([-14.5247,-49.1408],14);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,updateWhenIdle:true,keepBuffer:1}).addTo(map);document.getElementById('loading').style.display='none';}"
                + "window.cgPassenger=function(lat,lng){if(failed)return;if(!map){setTimeout(function(){cgPassenger(lat,lng)},120);return;}let p=[lat,lng];if(!me)me=L.marker(p,{icon:icon(\"<div class='me'></div>\",28),zIndexOffset:1000}).addTo(map);else me.setLatLng(p);map.setView(p,15,{animate:false});};"
                + "window.cgDrivers=function(rows){if(failed||!map)return;let seen={};(rows||[]).forEach(function(r){seen[r.id]=1;let e=r.kind==='moto'?'🏍':'🚗',h=\"<div class='car'>\"+e+\"</div>\";if(!marks[r.id])marks[r.id]=L.marker([r.lat,r.lng],{icon:icon(h,44)}).addTo(map);else{marks[r.id].setLatLng([r.lat,r.lng]);marks[r.id].setIcon(icon(h,44));}});Object.keys(marks).forEach(function(k){if(!seen[k]){map.removeLayer(marks[k]);delete marks[k];}});};boot();})();</script></body></html>";
    }

    private int dp(int value) {
        return (int) (value * getResources().getDisplayMetrics().density + 0.5f);
    }
}
