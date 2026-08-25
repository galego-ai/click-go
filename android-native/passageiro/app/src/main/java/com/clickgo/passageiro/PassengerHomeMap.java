package com.clickgo.passageiro;

import android.content.Context;
import android.graphics.Color;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

import org.json.JSONArray;
import org.json.JSONObject;

import java.util.Locale;

/** Lightweight home map that avoids osmdroid MapView during app startup/relaunch. */
public final class PassengerHomeMap extends WebView {
    private boolean pageReady;
    private Double passengerLat;
    private Double passengerLng;
    private JSONArray drivers = new JSONArray();

    public PassengerHomeMap(Context context) {
        super(context);
        setBackgroundColor(Color.rgb(238, 238, 238));
        setOverScrollMode(OVER_SCROLL_NEVER);
        setVerticalScrollBarEnabled(false);
        setHorizontalScrollBarEnabled(false);
        WebSettings s=getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setAllowFileAccess(false);
        s.setAllowContentAccess(false);
        s.setLoadsImagesAutomatically(true);
        s.setMediaPlaybackRequiresUserGesture(true);
        s.setMixedContentMode(WebSettings.MIXED_CONTENT_NEVER_ALLOW);
        setWebViewClient(new WebViewClient(){@Override public void onPageFinished(WebView view,String url){pageReady=true;flush();}});
        loadDataWithBaseURL("https://click-go.local/",html(),"text/html","UTF-8",null);
    }

    public void setPassenger(double lat,double lng){
        if(!Double.isFinite(lat)||!Double.isFinite(lng))return;
        passengerLat=lat;passengerLng=lng;if(pageReady)emitPassenger();
    }

    public void setDrivers(JSONArray rows){
        drivers=rows==null?new JSONArray():rows;if(pageReady)emitDrivers();
    }

    public void destroySafely(){
        pageReady=false;
        try{stopLoading();}catch(Exception ignored){}
        try{setWebViewClient(null);}catch(Exception ignored){}
        try{loadUrl("about:blank");}catch(Exception ignored){}
        try{removeAllViews();}catch(Exception ignored){}
        try{destroy();}catch(Exception ignored){}
    }

    private void flush(){emitPassenger();emitDrivers();}

    private void emitPassenger(){
        if(!pageReady||passengerLat==null||passengerLng==null)return;
        evaluateJavascript(String.format(Locale.US,"window.cgPassenger&&window.cgPassenger(%.7f,%.7f);",passengerLat,passengerLng),null);
    }

    private void emitDrivers(){
        if(!pageReady)return;
        JSONArray safe=new JSONArray();
        for(int i=0;i<drivers.length();i++){
            JSONObject r=drivers.optJSONObject(i);if(r==null)continue;
            double lat=r.optDouble("lat",Double.NaN),lng=r.optDouble("lng",Double.NaN);if(!Double.isFinite(lat)||!Double.isFinite(lng))continue;
            JSONObject p=new JSONObject();
            try{p.put("id",r.optString("driver_id","d"+i));p.put("lat",lat);p.put("lng",lng);p.put("kind",r.optString("category_name","car").toLowerCase(Locale.ROOT).contains("moto")?"moto":"car");}catch(Exception ignored){}
            safe.put(p);
        }
        evaluateJavascript("window.cgDrivers&&window.cgDrivers("+safe.toString()+");",null);
    }

    private String html(){
        return "<!doctype html><html><head><meta name='viewport' content='width=device-width,initial-scale=1,maximum-scale=1,user-scalable=no'>"
                +"<link rel='stylesheet' href='https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'>"
                +"<style>html,body,#map{height:100%;width:100%;margin:0;background:#eee}.me{width:18px;height:18px;border-radius:50%;background:#111;border:5px solid #ffd400;box-shadow:0 2px 8px #0005}.car{width:38px;height:38px;border-radius:50%;background:#ffd400;border:3px solid #111;display:flex;align-items:center;justify-content:center;font-size:19px;box-shadow:0 2px 8px #0004}#loading{position:absolute;z-index:999;left:50%;top:45%;transform:translate(-50%,-50%);background:#fff;padding:8px 12px;border-radius:12px;font:12px Arial;color:#333}</style></head>"
                +"<body><div id='map'></div><div id='loading'>Carregando mapa...</div><script src='https://unpkg.com/leaflet@1.9.4/dist/leaflet.js'></script>"
                +"<script>(function(){let map,me,marks={};function icon(h,s){return L.divIcon({html:h,className:'',iconSize:[s,s],iconAnchor:[s/2,s/2]});}function boot(){if(!window.L){setTimeout(boot,150);return;}map=L.map('map',{zoomControl:false,attributionControl:false,preferCanvas:true}).setView([-14.5247,-49.1408],14);L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png',{maxZoom:19,updateWhenIdle:true,keepBuffer:1}).addTo(map);document.getElementById('loading').style.display='none';}"
                +"window.cgPassenger=function(lat,lng){if(!map){setTimeout(function(){cgPassenger(lat,lng)},120);return;}let p=[lat,lng];if(!me)me=L.marker(p,{icon:icon(\"<div class='me'></div>\",28),zIndexOffset:1000}).addTo(map);else me.setLatLng(p);map.setView(p,15,{animate:false});};"
                +"window.cgDrivers=function(rows){if(!map)return;let seen={};(rows||[]).forEach(function(r){seen[r.id]=1;let e=r.kind==='moto'?'🏍':'🚗',h=\"<div class='car'>\"+e+\"</div>\";if(!marks[r.id])marks[r.id]=L.marker([r.lat,r.lng],{icon:icon(h,44)}).addTo(map);else{marks[r.id].setLatLng([r.lat,r.lng]);marks[r.id].setIcon(icon(h,44));}});Object.keys(marks).forEach(function(k){if(!seen[k]){map.removeLayer(marks[k]);delete marks[k];}});};boot();})();</script></body></html>";
    }
}
