package com.clickgo.motorista;

import android.Manifest;
import android.app.Activity;
import android.content.pm.PackageManager;
import android.graphics.Bitmap;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.InputType;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.widget.Button;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.ImageView;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;
import org.osmdroid.config.Configuration;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.views.MapView;

import java.text.NumberFormat;
import java.util.Arrays;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int REQ_LOCATION = 51;
    private static final int YELLOW = Color.rgb(255, 212, 0), BLACK = Color.rgb(17,17,17), DARK = Color.rgb(27,27,27), GRAY = Color.rgb(160,160,160), GREEN = Color.rgb(22,163,74);
    private final ExecutorService io = Executors.newFixedThreadPool(3);
    private final Handler ui = new Handler(Looper.getMainLooper());
    private String token, userId, fullName = "Motorista", driverStatus = "pending", billingMode = "wallet_per_ride";
    private boolean online;
    private double rating, balance;
    private Bitmap avatarBitmap;
    private Location currentLocation;
    private MapView map;
    private LinearLayout operationBox;
    private TextView operationTitle, walletText;
    private Runnable poller;
    private LocationManager locationManager;
    private LocationListener locationListener;
    private boolean destroyed;

    @Override protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w = getWindow(); w.setStatusBarColor(BLACK); w.setNavigationBarColor(BLACK);
        Configuration.getInstance().setUserAgentValue(getPackageName());
        token = getPreferences(MODE_PRIVATE).getString("access_token", null);
        userId = getPreferences(MODE_PRIVATE).getString("user_id", null);
        if (token == null || token.isBlank()) showLogin(); else loadSession();
    }

    @Override protected void onDestroy() {
        destroyed = true; stopPolling(); stopLocationWatch(); io.shutdownNow();
        if (map != null) map.onDetach();
        super.onDestroy();
    }

    private void showLogin() {
        LinearLayout body = vertical(BLACK); body.setPadding(dp(24),dp(50),dp(24),dp(30));
        body.addView(text("CLICK-GO",18,YELLOW,true)); body.addView(space(12));
        body.addView(text("App Motorista",32,Color.WHITE,true));
        body.addView(text("Entre para ficar online e receber corridas.",15,GRAY,false)); body.addView(space(26));
        EditText email = edit("E-mail"), pass = edit("Senha");
        pass.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        body.addView(email,match(dp(58))); body.addView(space(10)); body.addView(pass,match(dp(58))); body.addView(space(16));
        Button enter = primary("Entrar"); body.addView(enter,match(dp(58))); body.addView(space(14));
        body.addView(text("O franqueado da cidade precisa aprovar seu cadastro antes de você ficar online.",13,GRAY,false));
        enter.setOnClickListener(v -> login(email.getText().toString().trim(), pass.getText().toString()));
        setContentView(scroll(body,BLACK));
    }

    private void login(String email, String password) {
        if (email.isBlank() || password.isBlank()) { toast("Informe e-mail e senha."); return; }
        io.execute(() -> {
            try {
                JSONObject response = DriverRepository.signIn(email,password);
                token = response.optString("access_token","");
                JSONObject user = response.optJSONObject("user"); userId = user == null ? "" : user.optString("id","");
                if (token.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");
                getPreferences(MODE_PRIVATE).edit().putString("access_token",token).putString("user_id",userId).apply();
                loadSession();
            } catch (Exception e) { ui.post(() -> toast(msg(e))); }
        });
    }

    private void loadSession() {
        io.execute(() -> {
            try {
                if (userId == null || userId.isBlank()) { userId = DriverRepository.userId(token); getPreferences(MODE_PRIVATE).edit().putString("user_id",userId).apply(); }
                JSONObject p = DriverRepository.profile(token), d = DriverRepository.driver(token), w = DriverRepository.wallet(token);
                fullName = p.optString("full_name","Motorista");
                avatarBitmap = ProfileAvatar.download(p.optString("avatar_url",""));
                driverStatus = d.optString("status","pending"); online = d.optBoolean("online",false); rating = d.optDouble("rating",0);
                balance = w.optDouble("operational_balance",0); billingMode = w.optString("billing_mode","wallet_per_ride");
                ui.post(this::showHome);
            } catch (Exception e) { ui.post(() -> { toast(msg(e)); showLogin(); }); }
        });
    }

    private void showHome() {
        LinearLayout root = vertical(BLACK); root.setPadding(dp(16),dp(18),dp(16),dp(20));
        LinearLayout top = horizontal(); top.setGravity(Gravity.CENTER_VERTICAL);
        ImageView avatar = new ImageView(this); avatar.setImageDrawable(ProfileAvatar.circleDrawable(this,avatarBitmap,fullName)); avatar.setScaleType(ImageView.ScaleType.CENTER_CROP);
        top.addView(avatar,new LinearLayout.LayoutParams(dp(54),dp(54)));
        LinearLayout id = vertical(Color.TRANSPARENT); id.setPadding(dp(12),0,0,0); id.addView(text("Olá, "+firstName(fullName),20,Color.WHITE,true)); id.addView(text("Avaliação "+String.format(Locale.getDefault(),"%.1f",rating),13,GRAY,false));
        top.addView(id,new LinearLayout.LayoutParams(0,dp(58),1)); Button logout = darkButton("Sair"); top.addView(logout,new LinearLayout.LayoutParams(dp(72),dp(46))); root.addView(top); root.addView(space(14));

        LinearLayout info = card(DARK,Color.rgb(55,55,55)); info.addView(text(statusLabel(),14,driverStatus.equals("approved")?Color.rgb(74,222,128):YELLOW,true)); walletText = text(walletLabel(),14,GRAY,false); info.addView(walletText); root.addView(info); root.addView(space(12));

        FrameLayout frame = new FrameLayout(this); map = new MapView(this); map.setTileSource(TileSourceFactory.MAPNIK); map.setMultiTouchControls(true); frame.addView(map,new FrameLayout.LayoutParams(-1,-1)); root.addView(frame,new LinearLayout.LayoutParams(-1,dp(340))); root.addView(space(12));
        Button onlineBtn = primary(online?"● ONLINE — ficar offline":"○ OFFLINE — ficar online"); if (online) onlineBtn.setBackground(round(GREEN,16,GREEN)); root.addView(onlineBtn,match(dp(58))); root.addView(space(12));
        operationTitle = text(online?"Aguardando chamadas…":"Fique online para receber corridas.",16,Color.WHITE,true); root.addView(operationTitle); root.addView(space(8)); operationBox = vertical(BLACK); root.addView(operationBox,wrap());
        logout.setOnClickListener(v -> logout()); onlineBtn.setOnClickListener(v -> toggleOnline()); setContentView(scroll(root,BLACK));
        if (online) { startLocationWatch(); startPolling(); } else DriverMapRenderer.render(map,currentLocation,null,dp(5));
    }

    private void toggleOnline() {
        if (!driverStatus.equals("approved")) { toast("Seu cadastro ainda não foi aprovado pelo franqueado."); return; }
        if (online) {
            io.execute(() -> { try { DriverRepository.setOnline(token,false,null,null); online=false; ui.post(this::showHome); } catch(Exception e){ui.post(()->toast(msg(e)));} }); return;
        }
        if (!hasLocation()) { requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},REQ_LOCATION); return; }
        Location loc = bestLocation(); if (loc == null) { startLocationWatch(); toast("Aguardando GPS. Tente novamente em alguns segundos."); return; }
        io.execute(() -> { try { DriverRepository.setOnline(token,true,loc.getLatitude(),loc.getLongitude()); currentLocation=loc; online=true; ui.post(this::showHome); } catch(Exception e){ui.post(()->toast(msg(e)));} });
    }

    private void startLocationWatch() {
        if (!hasLocation()) { requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION,Manifest.permission.ACCESS_COARSE_LOCATION},REQ_LOCATION); return; }
        stopLocationWatch(); locationManager=(LocationManager)getSystemService(LOCATION_SERVICE); Location last=bestLocation(); if(last!=null){currentLocation=last;DriverMapRenderer.render(map,currentLocation,null,dp(5));}
        locationListener = loc -> { currentLocation=loc; if(online) io.execute(() -> { try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); } catch(Exception ignored){} }); };
        try { String provider=locationManager.isProviderEnabled(LocationManager.GPS_PROVIDER)?LocationManager.GPS_PROVIDER:LocationManager.NETWORK_PROVIDER; locationManager.requestLocationUpdates(provider,5000,3f,locationListener,Looper.getMainLooper()); } catch(Exception ignored){}
    }

    private void stopLocationWatch(){ if(locationManager!=null&&locationListener!=null)try{locationManager.removeUpdates(locationListener);}catch(Exception ignored){} locationListener=null; }
    private boolean hasLocation(){ return checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION)==PackageManager.PERMISSION_GRANTED||checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION)==PackageManager.PERMISSION_GRANTED; }
    private Location bestLocation(){ if(!hasLocation())return null; LocationManager m=(LocationManager)getSystemService(LOCATION_SERVICE); Location best=null; for(String p: Arrays.asList(LocationManager.GPS_PROVIDER,LocationManager.NETWORK_PROVIDER))try{Location c=m.getLastKnownLocation(p);if(c!=null&&(best==null||c.getTime()>best.getTime()))best=c;}catch(Exception ignored){} return best; }
    @Override public void onRequestPermissionsResult(int r,String[] p,int[] g){super.onRequestPermissionsResult(r,p,g);if(r==REQ_LOCATION&&g.length>0&&g[0]==PackageManager.PERMISSION_GRANTED)startLocationWatch();else if(r==REQ_LOCATION)toast("O GPS é necessário para receber corridas.");}

    private void startPolling(){ stopPolling(); poller=new Runnable(){public void run(){if(!online||destroyed)return;refreshOperation();ui.postDelayed(this,4500);}};ui.post(poller); }
    private void stopPolling(){if(poller!=null)ui.removeCallbacks(poller);poller=null;}
    private void refreshOperation(){ io.execute(() -> { try { JSONObject ride=DriverRepository.activeRide(token,userId); if(ride!=null){ui.post(()->renderRide(ride));return;} JSONObject offer=DriverRepository.firstOffer(token);ui.post(()->renderOffer(offer)); } catch(Exception e){ui.post(()->{if(operationTitle!=null)operationTitle.setText("Falha ao atualizar chamadas.");});} }); }

    private void renderOffer(JSONObject o){ if(operationBox==null)return;operationBox.removeAllViews();if(o==null){operationTitle.setText("Aguardando chamadas…");DriverMapRenderer.render(map,currentLocation,null,dp(5));return;} operationTitle.setText("Nova corrida"); LinearLayout c=card(DARK,YELLOW); c.addView(text(o.optString("category_name","Corrida CLICK-GO"),20,Color.WHITE,true)); c.addView(text("Embarque: "+o.optString("origin_label",""),14,Color.WHITE,false)); c.addView(text("Destino: "+o.optString("destination_label",""),14,GRAY,false)); c.addView(text("Ganho estimado "+money(o.optDouble("estimated_driver_earning",0)),18,YELLOW,true)); LinearLayout a=horizontal();Button yes=primary("Aceitar"),no=darkButton("Recusar");a.addView(yes,new LinearLayout.LayoutParams(0,dp(54),1));a.addView(spaceH(8));a.addView(no,new LinearLayout.LayoutParams(0,dp(54),1));c.addView(a);operationBox.addView(c,wrap());yes.setOnClickListener(v->respond(o.optString("offer_id"),true));no.setOnClickListener(v->respond(o.optString("offer_id"),false));DriverMapRenderer.render(map,currentLocation,o,dp(5)); }
    private void respond(String id,boolean accept){io.execute(()->{try{DriverRepository.respondOffer(token,id,accept);ui.post(()->toast(accept?"Corrida aceita.":"Chamada recusada."));refreshOperation();}catch(Exception e){ui.post(()->toast(msg(e)));}});}
    private void renderRide(JSONObject r){if(operationBox==null)return;operationBox.removeAllViews();String s=r.optString("status","accepted");operationTitle.setText(s.equals("accepted")?"Corrida aceita":s.equals("driver_arriving")?"A caminho do passageiro":"Corrida em andamento");LinearLayout c=card(DARK,Color.rgb(65,65,65));c.addView(text("Embarque: "+r.optString("origin_label",""),14,Color.WHITE,true));c.addView(text("Destino: "+r.optString("destination_label",""),14,GRAY,false));Button b;String action;if(s.equals("accepted")){b=primary("Estou a caminho");action="arrived";}else if(s.equals("driver_arriving")){b=primary("Iniciar corrida");action="start";}else{b=primary("Finalizar corrida");action="complete";}c.addView(space(8));c.addView(b,match(dp(56)));b.setOnClickListener(v->advance(r.optString("id"),action));operationBox.addView(c,wrap());DriverMapRenderer.render(map,currentLocation,r,dp(5));}
    private void advance(String rideId,String action){io.execute(()->{try{DriverRepository.advanceRide(token,rideId,action);if(action.equals("complete")){JSONObject w=DriverRepository.wallet(token);balance=w.optDouble("operational_balance",balance);}ui.post(()->{if(walletText!=null)walletText.setText(walletLabel());toast(action.equals("complete")?"Corrida concluída.":"Status atualizado.");});refreshOperation();}catch(Exception e){ui.post(()->toast(msg(e)));}});}

    private void logout(){token=null;userId=null;online=false;getPreferences(MODE_PRIVATE).edit().clear().apply();stopPolling();stopLocationWatch();showLogin();}
    private String statusLabel(){return driverStatus.equals("approved")?"Cadastro aprovado":driverStatus.equals("blocked")?"Cadastro bloqueado":"Aguardando aprovação do franqueado";}
    private String walletLabel(){return billingMode.equals("monthly")?"Plano mensal":"Carteira operacional: "+money(balance);}
    private String firstName(String v){v=v==null?"":v.trim();return v.isBlank()?"motorista":v.split("\\s+")[0];}
    private String money(double v){return NumberFormat.getCurrencyInstance(new Locale("pt","BR")).format(v);} private String msg(Exception e){return e.getMessage()==null||e.getMessage().isBlank()?"Não foi possível concluir a operação.":e.getMessage();} private void toast(String s){Toast.makeText(this,s,Toast.LENGTH_LONG).show();}
    private LinearLayout vertical(int c){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setBackgroundColor(c);return l;} private LinearLayout horizontal(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);return l;} private ScrollView scroll(View v,int c){ScrollView s=new ScrollView(this);s.setFillViewport(true);s.setBackgroundColor(c);s.addView(v,new ScrollView.LayoutParams(-1,-2));return s;} private LinearLayout card(int fill,int stroke){LinearLayout l=vertical(fill);l.setPadding(dp(14),dp(14),dp(14),dp(14));l.setBackground(round(fill,18,stroke));return l;} private TextView text(String s,int z,int c,boolean b){TextView v=new TextView(this);v.setText(s);v.setTextSize(z);v.setTextColor(c);if(b)v.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return v;} private EditText edit(String h){EditText e=new EditText(this);e.setHint(h);e.setHintTextColor(Color.rgb(130,130,130));e.setTextColor(Color.WHITE);e.setTextSize(16);e.setPadding(dp(16),0,dp(16),0);e.setSingleLine(true);e.setBackground(round(DARK,14,Color.rgb(55,55,55)));return e;} private Button primary(String s){Button b=new Button(this);b.setText(s);b.setTextSize(15);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setTextColor(BLACK);b.setAllCaps(false);b.setBackground(round(YELLOW,16,YELLOW));return b;} private Button darkButton(String s){Button b=new Button(this);b.setText(s);b.setTextSize(14);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setTextColor(Color.WHITE);b.setAllCaps(false);b.setBackground(round(Color.rgb(38,38,38),14,Color.rgb(65,65,65)));return b;} private GradientDrawable round(int fill,int radius,int stroke){GradientDrawable d=new GradientDrawable();d.setColor(fill);d.setCornerRadius(dp(radius));d.setStroke(dp(1),stroke);return d;} private View space(int h){View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(1,dp(h)));return v;} private View spaceH(int w){View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(dp(w),1));return v;} private LinearLayout.LayoutParams match(int h){return new LinearLayout.LayoutParams(-1,h);} private LinearLayout.LayoutParams wrap(){return new LinearLayout.LayoutParams(-1,-2);} private int dp(int v){return Math.round(v*getResources().getDisplayMetrics().density);}
}
