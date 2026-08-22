package com.clickgo.passageiro;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.InputType;
import android.text.TextWatcher;
import android.text.method.PasswordTransformationMethod;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.inputmethod.InputMethodManager;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ProgressBar;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.ArrayAdapter;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;
import org.osmdroid.config.Configuration;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.Marker;
import org.osmdroid.views.overlay.Polyline;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final int REQ_LOCATION = 41;
    private static final int YELLOW = Color.rgb(255, 212, 0);
    private static final int BLACK = Color.rgb(17, 17, 17);
    private static final int LIGHT = Color.rgb(247, 247, 247);
    private static final int GRAY = Color.rgb(110, 110, 110);

    private final ExecutorService io = Executors.newCachedThreadPool();
    private final Handler ui = new Handler(Looper.getMainLooper());
    private String token;
    private GeoPoint origin;
    private GeoPoint destination;
    private String originLabel = "Obtendo sua localização...";
    private String destinationLabel = "";
    private MapView map;
    private LinearLayout categoryBox;
    private TextView optionsSubtitle;
    private Spinner paymentSpinner;
    private Button requestRideButton;
    private final List<RideOption> rideOptions = new ArrayList<>();
    private RideOption selectedOption;
    private final List<String> paymentValues = new ArrayList<>();
    private String activeRideId;
    private TextView activeStatus;
    private TextView activeFare;
    private Runnable ridePoll;
    private int searchSeq = 0;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w = getWindow();
        w.setStatusBarColor(BLACK);
        w.setNavigationBarColor(BLACK);
        Configuration.getInstance().setUserAgentValue(getPackageName());
        token = getPreferences(MODE_PRIVATE).getString("access_token", null);
        if (token == null || token.isBlank()) showLogin(); else showHome();
    }

    @Override protected void onResume() { super.onResume(); if (map != null) map.onResume(); }
    @Override protected void onPause() { if (map != null) map.onPause(); super.onPause(); }
    @Override protected void onDestroy() { ui.removeCallbacksAndMessages(null); io.shutdownNow(); super.onDestroy(); }

    private void showLogin() {
        map = null;
        LinearLayout body = vertical(BLACK, 20);
        body.setPadding(dp(24), dp(34), dp(24), dp(30));
        body.addView(text("CLICK-GO", 18, YELLOW, true));
        TextView title = text("Passageiro", 34, Color.WHITE, true);
        title.setPadding(0, dp(4), 0, dp(4)); body.addView(title);
        TextView sub = text("Entre para pedir sua corrida", 16, Color.rgb(180,180,180), false);
        sub.setPadding(0, 0, 0, dp(24)); body.addView(sub);

        LinearLayout card = card(BLACK, Color.rgb(42,42,42), 22, 18);
        EditText email = edit("E-mail"); email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText pass = edit("Senha"); pass.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD); pass.setTransformationMethod(PasswordTransformationMethod.getInstance());
        CheckBox show = new CheckBox(this); show.setText("Mostrar senha"); show.setTextColor(Color.LTGRAY); show.setOnCheckedChangeListener((b,c)->pass.setTransformationMethod(c?null:PasswordTransformationMethod.getInstance()));
        Button enter = primary("Entrar");
        Button create = secondary("Criar conta");
        TextView forgot = text("Esqueci minha senha", 15, YELLOW, true); forgot.setGravity(Gravity.CENTER); forgot.setPadding(0, dp(12), 0, dp(6));
        card.addView(email, lpMatch(dp(58))); card.addView(space(10)); card.addView(pass, lpMatch(dp(58))); card.addView(show); card.addView(space(8)); card.addView(enter, lpMatch(dp(56))); card.addView(space(9)); card.addView(create, lpMatch(dp(54))); card.addView(forgot);
        body.addView(card, lpMatchWrap());
        enter.setOnClickListener(v -> login(email.getText().toString().trim(), pass.getText().toString()));
        create.setOnClickListener(v -> showSignup());
        forgot.setOnClickListener(v -> recover(email.getText().toString().trim()));
        setContentView(scroll(body, BLACK));
    }

    private void showSignup() {
        LinearLayout body = vertical(BLACK, 16); body.setPadding(dp(24), dp(30), dp(24), dp(30));
        Button back = secondary("← Voltar"); back.setOnClickListener(v->showLogin()); body.addView(back, new LinearLayout.LayoutParams(dp(110), dp(50)));
        TextView t = text("Criar conta", 30, Color.WHITE, true); t.setPadding(0, dp(18), 0, dp(8)); body.addView(t);
        body.addView(text("Cadastro de passageiro", 16, Color.LTGRAY, false)); body.addView(space(18));
        EditText name = edit("Nome completo"); EditText email = edit("E-mail"); EditText pass = edit("Senha (mínimo 6 caracteres)"); pass.setTransformationMethod(PasswordTransformationMethod.getInstance());
        body.addView(name, lpMatch(dp(58))); body.addView(space(10)); body.addView(email, lpMatch(dp(58))); body.addView(space(10)); body.addView(pass, lpMatch(dp(58))); body.addView(space(14));
        Button b = primary("Criar minha conta"); body.addView(b, lpMatch(dp(58)));
        b.setOnClickListener(v->signup(name.getText().toString().trim(), email.getText().toString().trim(), pass.getText().toString()));
        setContentView(scroll(body, BLACK));
    }

    private void login(String email, String password) {
        if (email.isBlank() || password.isBlank()) { toast("Informe e-mail e senha."); return; }
        blocking(true);
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("email", email).put("password", password);
                JSONObject r = new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=password", body));
                String tk = r.optString("access_token", "");
                if (tk.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");
                token = tk; getPreferences(MODE_PRIVATE).edit().putString("access_token", tk).apply();
                ui.post(this::showHome);
            } catch (Exception e) { ui.post(() -> toast(e.getMessage())); }
            finally { ui.post(() -> blocking(false)); }
        });
    }

    private void signup(String name, String email, String password) {
        if (name.isBlank() || email.isBlank() || password.length() < 6) { toast("Preencha nome, e-mail e uma senha com pelo menos 6 caracteres."); return; }
        blocking(true);
        io.execute(() -> {
            try {
                JSONObject meta = new JSONObject().put("role", "passenger").put("full_name", name);
                JSONObject body = new JSONObject().put("email", email).put("password", password).put("data", meta);
                JSONObject r = new JSONObject(ApiClient.authPost("/auth/v1/signup", body));
                String tk = r.optString("access_token", "");
                if (tk.isBlank()) { ui.post(() -> { toast("Conta criada. Confirme seu e-mail e depois entre no aplicativo."); showLogin(); }); }
                else { token = tk; getPreferences(MODE_PRIVATE).edit().putString("access_token", tk).apply(); ui.post(this::showHome); }
            } catch (Exception e) { ui.post(() -> toast(e.getMessage())); }
            finally { ui.post(() -> blocking(false)); }
        });
    }

    private void recover(String email) {
        if (email.isBlank()) { toast("Digite seu e-mail primeiro."); return; }
        blocking(true);
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("email", email);
                ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha", body);
                ui.post(() -> toast("E-mail de recuperação enviado."));
            } catch (Exception e) { ui.post(() -> toast(e.getMessage())); }
            finally { ui.post(() -> blocking(false)); }
        });
    }

    private void showHome() {
        activeRideId = null; ui.removeCallbacksAndMessages(null); map = null;
        LinearLayout root = vertical(LIGHT, 0); root.setPadding(dp(18), dp(18), dp(18), dp(20));
        LinearLayout top = horizontal(); top.setGravity(Gravity.CENTER_VERTICAL);
        Button menu = circleButton("☰", 48); top.addView(menu, new LinearLayout.LayoutParams(dp(50), dp(50)));
        TextView logo = text("CLICK-GO", 18, BLACK, true); logo.setPadding(dp(14),0,0,0); top.addView(logo, new LinearLayout.LayoutParams(0, dp(50), 1));
        TextView avatar = text("CG", 14, YELLOW, true); avatar.setGravity(Gravity.CENTER); avatar.setBackground(round(BLACK, 24, BLACK)); top.addView(avatar, new LinearLayout.LayoutParams(dp(48),dp(48)));
        root.addView(top); root.addView(space(18));
        TextView title = text("Para onde vamos?", 30, BLACK, true); root.addView(title); root.addView(space(14));

        LinearLayout originCard = card(Color.WHITE, Color.rgb(235,235,235), 22, 14);
        LinearLayout row = horizontal(); row.setGravity(Gravity.CENTER_VERTICAL);
        TextView dot = text("●", 19, Color.rgb(24,199,163), true); row.addView(dot, new LinearLayout.LayoutParams(dp(28), dp(48)));
        LinearLayout ol = vertical(Color.TRANSPARENT, 0); TextView cap = text("EMBARQUE", 11, GRAY, true); TextView ov = text(originLabel, 16, BLACK, true); ov.setSingleLine(true); ol.addView(cap); ol.addView(ov); row.addView(ol, new LinearLayout.LayoutParams(0, dp(50), 1));
        Button change = smallButton("Alterar"); row.addView(change, new LinearLayout.LayoutParams(dp(90), dp(44))); originCard.addView(row);
        root.addView(originCard, lpMatchWrap()); root.addView(space(12));

        LinearLayout destCard = card(Color.WHITE, Color.rgb(235,235,235), 22, 14);
        LinearLayout destRow = horizontal(); destRow.setGravity(Gravity.CENTER_VERTICAL);
        TextView orangeDot = text("●", 19, Color.rgb(255,138,61), true); destRow.addView(orangeDot, new LinearLayout.LayoutParams(dp(28), dp(56)));
        EditText dest = editLight("Para onde vamos?"); dest.setTextSize(18); destRow.addView(dest, new LinearLayout.LayoutParams(0, dp(58), 1)); destCard.addView(destRow);
        LinearLayout suggestions = vertical(Color.WHITE, 6); destCard.addView(suggestions, lpMatchWrap()); root.addView(destCard, lpMatchWrap()); root.addView(space(14));

        LinearLayout quick = horizontal();
        quick.addView(quickButton("⌂", "Casa"), new LinearLayout.LayoutParams(0, dp(82), 1)); quick.addView(spaceH(8));
        quick.addView(quickButton("▣", "Trabalho"), new LinearLayout.LayoutParams(0, dp(82), 1)); quick.addView(spaceH(8));
        quick.addView(quickButton("★", "Favoritos"), new LinearLayout.LayoutParams(0, dp(82), 1)); root.addView(quick);
        root.addView(space(18));
        TextView hint = text("Digite ao menos 3 letras do destino. A localização atual é usada como origem, mas você pode alterá-la.", 13, GRAY, false); root.addView(hint);

        menu.setOnClickListener(v -> showMenu()); change.setOnClickListener(v -> showOriginPicker(ov));
        dest.addTextChangedListener(new TextWatcher() {
            public void beforeTextChanged(CharSequence s,int st,int c,int a){}
            public void onTextChanged(CharSequence s,int st,int b,int c){ int seq=++searchSeq; String q=s.toString().trim(); suggestions.removeAllViews(); if(q.length()<3)return; ui.postDelayed(()->{ if(seq==searchSeq) searchAddress(q,suggestions,false,ov); },450); }
            public void afterTextChanged(Editable e){}
        });
        setContentView(scroll(root, LIGHT));
        if (origin == null) obtainLocation(ov, false);
    }

    private void showOriginPicker(TextView homeOriginLabel) {
        LinearLayout wrap = vertical(Color.WHITE, 10); wrap.setPadding(dp(18),dp(12),dp(18),dp(8));
        TextView t = text("Alterar local de embarque", 22, BLACK, true); wrap.addView(t); wrap.addView(space(8));
        EditText input = editLight("Digite outro endereço"); wrap.addView(input, lpMatch(dp(58)));
        LinearLayout results = vertical(Color.WHITE, 6); wrap.addView(results, lpMatchWrap());
        Button gps = secondaryLight("📍 Usar minha localização atual"); wrap.addView(gps, lpMatch(dp(52)));
        AlertDialog dlg = new AlertDialog.Builder(this).setView(wrap).setNegativeButton("Fechar", null).create();
        input.addTextChangedListener(new TextWatcher(){ public void beforeTextChanged(CharSequence s,int a,int b,int c){} public void afterTextChanged(Editable e){} public void onTextChanged(CharSequence s,int a,int b,int c){ int seq=++searchSeq;String q=s.toString().trim();results.removeAllViews();if(q.length()<3)return;ui.postDelayed(()->{if(seq==searchSeq)searchAddress(q,results,true,homeOriginLabel,dlg);},450);} });
        gps.setOnClickListener(v->{ dlg.dismiss(); obtainLocation(homeOriginLabel,true); });
        dlg.show();
    }

    private void searchAddress(String q, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog... dialog) {
        io.execute(() -> {
            try {
                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(q, StandardCharsets.UTF_8.toString());
                JSONObject root = new JSONObject(ApiClient.absoluteGet(url)); JSONArray arr = root.optJSONArray("results");
                List<SearchItem> items = new ArrayList<>(); if(arr!=null) for(int i=0;i<arr.length();i++){JSONObject o=arr.getJSONObject(i);items.add(new SearchItem(o.optString("label"),o.optDouble("lat"),o.optDouble("lng")));}
                ui.post(() -> { target.removeAllViews(); if(items.isEmpty()){target.addView(text("Nenhum endereço encontrado.",13,GRAY,false));return;} for(SearchItem item:items){Button b=secondaryLight(item.label);b.setGravity(Gravity.START|Gravity.CENTER_VERTICAL);target.addView(b,lpMatch(dp(58)));target.addView(space(5));b.setOnClickListener(v->{hideKeyboard();if(forOrigin){origin=new GeoPoint(item.lat,item.lng);originLabel=item.label;originView.setText(item.label);if(dialog.length>0)dialog[0].dismiss();}else{destination=new GeoPoint(item.lat,item.lng);destinationLabel=item.label;showOptions();}}); } });
            } catch(Exception e){ ui.post(()->{target.removeAllViews();target.addView(text(e.getMessage(),13,Color.rgb(170,60,40),false));}); }
        });
    }

    private void obtainLocation(TextView labelView, boolean userAction) {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED && checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_LOCATION); return;
        }
        try {
            LocationManager lm=(LocationManager)getSystemService(LOCATION_SERVICE); Location best=null;
            for(String p: Arrays.asList(LocationManager.GPS_PROVIDER,LocationManager.NETWORK_PROVIDER)){try{Location x=lm.getLastKnownLocation(p);if(x!=null&&(best==null||x.getTime()>best.getTime()))best=x;}catch(Exception ignored){}}
            if(best!=null){setOriginFromLocation(best,labelView);}
            LocationListener listener = new LocationListener(){public void onLocationChanged(Location l){setOriginFromLocation(l,labelView);try{lm.removeUpdates(this);}catch(Exception ignored){}} public void onProviderEnabled(String p){} public void onProviderDisabled(String p){} public void onStatusChanged(String p,int s,Bundle b){}};
            if(lm.isProviderEnabled(LocationManager.GPS_PROVIDER)) lm.requestSingleUpdate(LocationManager.GPS_PROVIDER,listener,Looper.getMainLooper()); else if(lm.isProviderEnabled(LocationManager.NETWORK_PROVIDER)) lm.requestSingleUpdate(LocationManager.NETWORK_PROVIDER,listener,Looper.getMainLooper());
            if(best==null&&userAction)toast("Buscando sua localização...");
        } catch(Exception e){ if(userAction)toast("Não foi possível obter a localização. Você pode digitar outro endereço."); }
    }

    private void setOriginFromLocation(Location l, TextView labelView){ origin=new GeoPoint(l.getLatitude(),l.getLongitude());originLabel="Minha localização atual";if(labelView!=null)labelView.setText(originLabel); }
    @Override public void onRequestPermissionsResult(int requestCode,String[] permissions,int[] grantResults){super.onRequestPermissionsResult(requestCode,permissions,grantResults);if(requestCode==REQ_LOCATION){if(grantResults.length>0&&grantResults[0]==PackageManager.PERMISSION_GRANTED)showHome();else toast("Sem acesso ao GPS. Use 'Alterar' para informar o embarque.");}}

    private void showOptions() {
        if(origin==null){toast("Defina primeiro o local de embarque.");showHome();return;}
        LinearLayout root = vertical(Color.WHITE,0);
        FrameLayout mapFrame=new FrameLayout(this); map=new MapView(this); map.setTileSource(TileSourceFactory.MAPNIK);map.setMultiTouchControls(true);map.getController().setZoom(14.5);mapFrame.addView(map,new FrameLayout.LayoutParams(-1,-1));
        Button back=circleButton("←",52);FrameLayout.LayoutParams bp=new FrameLayout.LayoutParams(dp(54),dp(54));bp.leftMargin=dp(16);bp.topMargin=dp(16);mapFrame.addView(back,bp);
        TextView pill=text(destinationLabel,15,BLACK,true);pill.setSingleLine(true);pill.setPadding(dp(16),0,dp(16),0);pill.setGravity(Gravity.CENTER_VERTICAL);pill.setBackground(round(Color.WHITE,18,Color.WHITE));FrameLayout.LayoutParams pp=new FrameLayout.LayoutParams(-1,dp(54));pp.leftMargin=dp(82);pp.rightMargin=dp(16);pp.topMargin=dp(16);mapFrame.addView(pill,pp);
        root.addView(mapFrame,new LinearLayout.LayoutParams(-1,0,1));
        ScrollView sv=new ScrollView(this);LinearLayout bottom=vertical(Color.WHITE,10);bottom.setPadding(dp(16),dp(18),dp(16),dp(22));sv.addView(bottom);
        TextView h=text("Escolha sua viagem",24,BLACK,true);bottom.addView(h);optionsSubtitle=text("Buscando categorias disponíveis...",14,GRAY,false);bottom.addView(optionsSubtitle);bottom.addView(space(10));categoryBox=vertical(Color.WHITE,8);bottom.addView(categoryBox,lpMatchWrap());
        paymentSpinner=new Spinner(this);bottom.addView(paymentSpinner,lpMatch(dp(54)));bottom.addView(space(10));requestRideButton=primary("Aguarde...");requestRideButton.setEnabled(false);bottom.addView(requestRideButton,lpMatch(dp(58)));root.addView(sv,new LinearLayout.LayoutParams(-1,dp(360)));
        back.setOnClickListener(v->showHome());requestRideButton.setOnClickListener(v->requestRide());setContentView(root);drawRoute();loadOptions();
    }

    private void drawRoute(){ if(map==null||origin==null||destination==null)return;map.getOverlays().clear();Marker a=new Marker(map);a.setPosition(origin);a.setTitle("Embarque");a.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_BOTTOM);map.getOverlays().add(a);Marker b=new Marker(map);b.setPosition(destination);b.setTitle("Destino");b.setAnchor(Marker.ANCHOR_CENTER,Marker.ANCHOR_BOTTOM);map.getOverlays().add(b);Polyline line=new Polyline();line.setPoints(Arrays.asList(origin,destination));line.getOutlinePaint().setStrokeWidth(dp(6));line.getOutlinePaint().setColor(Color.rgb(48,92,220));map.getOverlays().add(line);map.zoomToBoundingBox(org.osmdroid.util.BoundingBox.fromGeoPoints(Arrays.asList(origin,destination)),true,dp(70));map.invalidate(); }

    private void loadOptions(){
        rideOptions.clear();selectedOption=null;paymentValues.clear();
        io.execute(()->{try{
            JSONObject body=new JSONObject().put("p_origin_lat",origin.getLatitude()).put("p_origin_lng",origin.getLongitude()).put("p_destination_lat",destination.getLatitude()).put("p_destination_lng",destination.getLongitude());
            JSONArray arr=new JSONArray(ApiClient.rpc("get_passenger_ride_options",body,token));
            for(int i=0;i<arr.length();i++){JSONObject o=arr.getJSONObject(i);if(o.isNull("category_id"))continue;rideOptions.add(new RideOption(o.optString("category_id"),o.optString("category_name"),o.optString("required_vehicle_type"),o.optDouble("distance_km"),o.optDouble("duration_min"),o.optDouble("fare"),o.optString("city_id"),o.optString("city_name"),o.optString("state")));}
            if(rideOptions.isEmpty()){ui.post(()->renderOptions(null));return;}
            selectedOption=rideOptions.get(0);String ps=ApiClient.rpc("get_effective_payment_settings",new JSONObject().put("p_city_id",selectedOption.cityId),token);JSONArray pArr=new JSONArray(ps);JSONObject settings=pArr.length()>0?pArr.getJSONObject(0):new JSONObject();
            if(settings.optBoolean("pix_enabled"))paymentValues.add("pix");if(settings.optBoolean("card_app_enabled"))paymentValues.add("card");if(settings.optBoolean("card_machine_enabled"))paymentValues.add("card_machine");if(settings.optBoolean("cash_enabled"))paymentValues.add("cash");
            ui.post(()->renderOptions(settings));
        }catch(Exception e){ui.post(()->{categoryBox.removeAllViews();categoryBox.addView(unavailable("Serviço indisponível",e.getMessage()));optionsSubtitle.setText("");});}});
    }

    private void renderOptions(JSONObject settings){
        categoryBox.removeAllViews();
        if(rideOptions.isEmpty()){categoryBox.addView(unavailable("Serviço indisponível","Ainda não há categorias ativas para esta rota."));optionsSubtitle.setText("");requestRideButton.setEnabled(false);return;}
        RideOption first=rideOptions.get(0);optionsSubtitle.setText(String.format(Locale.getDefault(),"%.1f km · aprox. %.0f min · %s/%s",first.distance,first.duration,first.city,first.state));
        for(RideOption o:rideOptions){LinearLayout item=horizontal();item.setGravity(Gravity.CENTER_VERTICAL);item.setPadding(dp(14),dp(12),dp(14),dp(12));item.setBackground(round(o==selectedOption?Color.rgb(255,251,230):Color.WHITE,20,o==selectedOption?BLACK:Color.rgb(230,230,230)));TextView icon=text(vehicleIcon(o.vehicle),34,BLACK,false);icon.setGravity(Gravity.CENTER);item.addView(icon,new LinearLayout.LayoutParams(dp(62),dp(62)));LinearLayout labels=vertical(Color.TRANSPARENT,0);TextView n=text(o.name,18,BLACK,true);labels.addView(n);labels.addView(text((o.vehicle.isBlank()?"Veículo":o.vehicle)+" · "+Math.round(o.duration)+" min",13,GRAY,false));item.addView(labels,new LinearLayout.LayoutParams(0,dp(62),1));TextView price=text(money(o.fare),18,BLACK,true);item.addView(price);categoryBox.addView(item,lpMatch(dp(88)));categoryBox.addView(space(7));item.setOnClickListener(v->{selectedOption=o;renderOptions(settings);});}
        List<String> display=new ArrayList<>();for(String p:paymentValues)display.add(paymentLabel(p));if(display.isEmpty())display.add("Nenhuma forma de pagamento disponível");ArrayAdapter<String> adapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,display);paymentSpinner.setAdapter(adapter);requestRideButton.setEnabled(!paymentValues.isEmpty());requestRideButton.setText("Solicitar "+selectedOption.name+" · "+money(selectedOption.fare));
    }

    private void requestRide(){
        if(selectedOption==null||paymentValues.isEmpty())return;int idx=paymentSpinner.getSelectedItemPosition();String payment=paymentValues.get(Math.min(idx,paymentValues.size()-1));requestRideButton.setEnabled(false);requestRideButton.setText("Procurando motoristas...");
        io.execute(()->{try{JSONObject body=new JSONObject().put("p_origin_label",originLabel).put("p_origin_lat",origin.getLatitude()).put("p_origin_lng",origin.getLongitude()).put("p_destination_label",destinationLabel).put("p_destination_lat",destination.getLatitude()).put("p_destination_lng",destination.getLongitude()).put("p_category_id",selectedOption.id).put("p_payment_method",payment);String raw=ApiClient.rpc("create_passenger_ride",body,token).trim();activeRideId=raw.replace("\"","");ui.post(()->showActiveRide());}catch(Exception e){ui.post(()->{toast(e.getMessage());requestRideButton.setEnabled(true);requestRideButton.setText("Solicitar "+selectedOption.name+" · "+money(selectedOption.fare));});}});
    }

    private void showActiveRide(){
        LinearLayout root=vertical(Color.WHITE,0);FrameLayout mf=new FrameLayout(this);map=new MapView(this);map.setTileSource(TileSourceFactory.MAPNIK);map.setMultiTouchControls(true);mf.addView(map,new FrameLayout.LayoutParams(-1,-1));TextView brand=text("CLICK-GO",16,BLACK,true);brand.setPadding(dp(14),0,dp(14),0);brand.setGravity(Gravity.CENTER);brand.setBackground(round(Color.WHITE,16,Color.WHITE));FrameLayout.LayoutParams br=new FrameLayout.LayoutParams(dp(120),dp(46));br.leftMargin=dp(16);br.topMargin=dp(16);mf.addView(brand,br);root.addView(mf,new LinearLayout.LayoutParams(-1,0,1));LinearLayout bottom=vertical(Color.WHITE,10);bottom.setPadding(dp(18),dp(20),dp(18),dp(24));activeStatus=text("Procurando motorista...",24,BLACK,true);activeFare=text(selectedOption==null?"":money(selectedOption.fare),18,BLACK,true);bottom.addView(activeStatus);bottom.addView(text(originLabel+" → "+destinationLabel,14,GRAY,false));bottom.addView(activeFare);bottom.addView(space(8));Button cancel=secondaryLight("Cancelar corrida");bottom.addView(cancel,lpMatch(dp(54)));root.addView(bottom,new LinearLayout.LayoutParams(-1,dp(220)));setContentView(root);drawRoute();cancel.setOnClickListener(v->previewCancel());startRidePolling();
    }

    private void startRidePolling(){ if(ridePoll!=null)ui.removeCallbacks(ridePoll);ridePoll=new Runnable(){public void run(){if(activeRideId==null)return;io.execute(()->{try{JSONArray arr=new JSONArray(ApiClient.restGet("rides?id=eq."+activeRideId+"&select=id,status,estimated_fare,final_fare",token));if(arr.length()>0){JSONObject r=arr.getJSONObject(0);String status=r.optString("status");double fare=r.isNull("final_fare")?r.optDouble("estimated_fare"):r.optDouble("final_fare");ui.post(()->{if(activeStatus!=null)activeStatus.setText(statusLabel(status));if(activeFare!=null)activeFare.setText(money(fare));if(status.equals("completed")||status.equals("cancelled")){activeRideId=null;showEndState(status,fare);return;}ui.postDelayed(ridePoll,3000);});}else ui.postDelayed(ridePoll,3000);}catch(Exception e){ui.postDelayed(ridePoll,4500);}});}};ui.post(ridePoll); }

    private void showEndState(String status,double fare){LinearLayout body=vertical(Color.WHITE,16);body.setGravity(Gravity.CENTER);body.setPadding(dp(24),dp(40),dp(24),dp(40));body.addView(text(status.equals("completed")?"Corrida concluída":"Corrida cancelada",28,BLACK,true));body.addView(text(money(fare),22,BLACK,true));Button n=primary("Nova corrida");body.addView(space(18));body.addView(n,lpMatch(dp(58)));n.setOnClickListener(v->{destination=null;destinationLabel="";showHome();});setContentView(body);}

    private void previewCancel(){if(activeRideId==null)return;io.execute(()->{try{JSONObject x=new JSONObject(ApiClient.rpc("preview_passenger_ride_cancellation",new JSONObject().put("p_ride_id",activeRideId),token));double fee=x.optDouble("cancellation_fee_amount",0);boolean charge=x.optBoolean("requires_confirmation",false);ui.post(()->new AlertDialog.Builder(this).setTitle(charge?"Há taxa de cancelamento":"Cancelamento sem taxa").setMessage(charge?"Se cancelar agora, será registrada uma taxa de "+money(fee)+" para a próxima corrida. Deseja realmente cancelar?":"Você ainda pode cancelar sem taxa. Deseja cancelar esta corrida?").setNegativeButton("Continuar chamado",null).setPositiveButton("Cancelar mesmo assim",(d,w)->confirmCancel()).show());}catch(Exception e){ui.post(()->toast(e.getMessage()));}});}
    private void confirmCancel(){if(activeRideId==null)return;io.execute(()->{try{ApiClient.rpc("cancel_passenger_ride",new JSONObject().put("p_ride_id",activeRideId).put("p_confirm_fee",true),token);ui.post(()->toast("Corrida cancelada."));}catch(Exception e){ui.post(()->toast(e.getMessage()));}});}

    private void showMenu(){String[] items={"Histórico","Pagamentos","Cupons","Favoritos","Ajuda e suporte","Sair"};new AlertDialog.Builder(this).setTitle("CLICK-GO Passageiro").setItems(items,(d,which)->{if(which==5){token=null;getPreferences(MODE_PRIVATE).edit().clear().apply();showLogin();}else toast("Essa área será conectada na próxima etapa do app nativo.");}).show();}

    private String vehicleIcon(String type){String t=type==null?"":type.toLowerCase(Locale.ROOT);if(t.contains("moto"))return "🏍";if(t.contains("premium")||t.contains("comfort"))return "🚘";if(t.contains("tax"))return "🚕";return "🚗";}
    private String paymentLabel(String p){switch(p){case"pix":return"PIX";case"card":return"Cartão no app";case"card_machine":return"Cartão com motorista";default:return"Dinheiro";}}
    private String statusLabel(String s){switch(s){case"requested":case"searching":return"Procurando motorista...";case"accepted":return"Motorista aceitou";case"driver_arriving":return"Motorista a caminho";case"in_progress":return"Corrida em andamento";case"completed":return"Corrida concluída";case"cancelled":return"Corrida cancelada";default:return s;}}
    private String money(double v){return NumberFormat.getCurrencyInstance(new Locale("pt","BR")).format(v);}

    private LinearLayout unavailable(String title,String message){LinearLayout b=card(Color.rgb(250,250,250),Color.rgb(230,230,230),20,18);TextView icon=text("⊘",38,Color.rgb(210,70,40),true);icon.setGravity(Gravity.CENTER);b.addView(icon);TextView t=text(title,20,BLACK,true);t.setGravity(Gravity.CENTER);b.addView(t);TextView m=text(message==null?"":message,14,GRAY,false);m.setGravity(Gravity.CENTER);b.addView(m);return b;}
    private LinearLayout quickButton(String icon,String label){LinearLayout b=vertical(Color.WHITE,2);b.setGravity(Gravity.CENTER);b.setBackground(round(Color.WHITE,17,Color.WHITE));TextView i=text(icon,22,BLACK,true);i.setGravity(Gravity.CENTER);TextView l=text(label,13,BLACK,true);l.setGravity(Gravity.CENTER);b.addView(i);b.addView(l);return b;}
    private LinearLayout vertical(int color,int gap){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.VERTICAL);l.setBackgroundColor(color);return l;}
    private LinearLayout horizontal(){LinearLayout l=new LinearLayout(this);l.setOrientation(LinearLayout.HORIZONTAL);return l;}
    private ScrollView scroll(View child,int color){ScrollView s=new ScrollView(this);s.setFillViewport(true);s.setBackgroundColor(color);s.addView(child,new ScrollView.LayoutParams(-1,-2));return s;}
    private LinearLayout card(int fill,int stroke,int radius,int padding){LinearLayout l=vertical(fill,0);l.setPadding(dp(padding),dp(padding),dp(padding),dp(padding));l.setBackground(round(fill,radius,stroke));return l;}
    private TextView text(String value,int sp,int color,boolean bold){TextView t=new TextView(this);t.setText(value);t.setTextSize(sp);t.setTextColor(color);if(bold)t.setTypeface(Typeface.DEFAULT,Typeface.BOLD);return t;}
    private EditText edit(String hint){EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.rgb(130,130,130));e.setTextColor(Color.WHITE);e.setTextSize(16);e.setPadding(dp(16),0,dp(16),0);e.setSingleLine(true);e.setBackground(round(Color.rgb(28,28,28),14,Color.rgb(55,55,55)));return e;}
    private EditText editLight(String hint){EditText e=new EditText(this);e.setHint(hint);e.setHintTextColor(Color.rgb(145,145,145));e.setTextColor(BLACK);e.setTextSize(16);e.setPadding(dp(12),0,dp(12),0);e.setSingleLine(true);e.setBackground(round(Color.rgb(248,248,248),14,Color.rgb(235,235,235)));return e;}
    private Button primary(String label){Button b=new Button(this);b.setText(label);b.setTextSize(16);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setTextColor(BLACK);b.setAllCaps(false);b.setBackground(round(YELLOW,16,YELLOW));return b;}
    private Button secondary(String label){Button b=new Button(this);b.setText(label);b.setTextSize(15);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setTextColor(Color.WHITE);b.setAllCaps(false);b.setBackground(round(Color.rgb(35,35,35),15,Color.rgb(55,55,55)));return b;}
    private Button secondaryLight(String label){Button b=new Button(this);b.setText(label);b.setTextSize(14);b.setTypeface(Typeface.DEFAULT,Typeface.BOLD);b.setTextColor(BLACK);b.setAllCaps(false);b.setBackground(round(Color.rgb(247,247,247),14,Color.rgb(225,225,225)));return b;}
    private Button smallButton(String label){Button b=secondaryLight(label);b.setTextSize(13);return b;}
    private Button circleButton(String label,int size){Button b=new Button(this);b.setText(label);b.setTextSize(20);b.setTextColor(BLACK);b.setAllCaps(false);b.setPadding(0,0,0,0);b.setBackground(round(Color.WHITE,size/2,Color.rgb(230,230,230)));return b;}
    private GradientDrawable round(int fill,int radius,int stroke){GradientDrawable d=new GradientDrawable();d.setColor(fill);d.setCornerRadius(dp(radius));d.setStroke(dp(1),stroke);return d;}
    private View space(int h){View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(1,dp(h)));return v;}
    private View spaceH(int w){View v=new View(this);v.setLayoutParams(new LinearLayout.LayoutParams(dp(w),1));return v;}
    private LinearLayout.LayoutParams lpMatch(int h){return new LinearLayout.LayoutParams(-1,h);}
    private LinearLayout.LayoutParams lpMatchWrap(){return new LinearLayout.LayoutParams(-1,-2);}
    private int dp(int n){return Math.round(n*getResources().getDisplayMetrics().density);}
    private void toast(String m){Toast.makeText(this,m==null?"Erro":m,Toast.LENGTH_LONG).show();}
    private void hideKeyboard(){View v=getCurrentFocus();if(v!=null)((InputMethodManager)getSystemService(Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(v.getWindowToken(),0);}
    private void blocking(boolean on){/* Ações já exibem estado nos próprios botões; mantido simples para a prévia nativa. */}

    private static class SearchItem {final String label;final double lat,lng;SearchItem(String l,double a,double b){label=l;lat=a;lng=b;}}
    private static class RideOption {final String id,name,vehicle,cityId,city,state;final double distance,duration,fare;RideOption(String i,String n,String v,double d,double du,double f,String ci,String c,String s){id=i;name=n;vehicle=v==null?"":v;distance=d;duration=du;fare=f;cityId=ci;city=c;state=s;}}
}
