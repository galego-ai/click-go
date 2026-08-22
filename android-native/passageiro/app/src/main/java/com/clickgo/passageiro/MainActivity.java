package com.clickgo.passageiro;

import android.Manifest;
import android.app.Activity;
import android.app.AlertDialog;
import android.content.Context;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.location.Address;
import android.location.Geocoder;
import android.location.Location;
import android.location.LocationListener;
import android.location.LocationManager;
import android.os.Bundle;
import android.os.Handler;
import android.os.Looper;
import android.text.Editable;
import android.text.InputType;
import android.text.TextUtils;
import android.text.TextWatcher;
import android.text.method.PasswordTransformationMethod;
import android.view.Gravity;
import android.view.View;
import android.view.Window;
import android.view.inputmethod.InputMethodManager;
import android.widget.ArrayAdapter;
import android.widget.Button;
import android.widget.CheckBox;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.Spinner;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONArray;
import org.json.JSONObject;
import org.osmdroid.config.Configuration;
import org.osmdroid.tileprovider.tilesource.TileSourceFactory;
import org.osmdroid.util.BoundingBox;
import org.osmdroid.util.GeoPoint;
import org.osmdroid.views.MapView;
import org.osmdroid.views.overlay.Marker;
import org.osmdroid.views.overlay.Polyline;

import java.net.URLEncoder;
import java.nio.charset.StandardCharsets;
import java.text.NumberFormat;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.HashSet;
import java.util.List;
import java.util.Locale;
import java.util.Set;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;

public class MainActivity extends Activity {
    private static final int REQ_LOCATION = 41;
    private static final int YELLOW = Color.rgb(255, 212, 0);
    private static final int BLACK = Color.rgb(17, 17, 17);
    private static final int LIGHT = Color.rgb(247, 247, 247);
    private static final int GRAY = Color.rgb(105, 105, 105);
    private static final int GREEN = Color.rgb(24, 199, 163);
    private static final int ORANGE = Color.rgb(255, 138, 61);

    private final ExecutorService io = Executors.newFixedThreadPool(3);
    private final ExecutorService addressIo = Executors.newFixedThreadPool(2);
    private final Handler ui = new Handler(Looper.getMainLooper());
    private Future<?> addressFuture;
    private Runnable pendingAddressSearch;
    private volatile boolean destroyed = false;
    private int searchSeq = 0;
    private int locationSeq = 0;

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
    private final List<String> paymentValues = new ArrayList<>();
    private RideOption selectedOption;

    private String activeRideId;
    private TextView activeStatus;
    private TextView activeFare;
    private Runnable ridePoll;

    @Override public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        Window w = getWindow();
        w.setStatusBarColor(BLACK);
        w.setNavigationBarColor(BLACK);
        Configuration.getInstance().setUserAgentValue("CLICK-GO-Passageiro-Android/0.2");
        token = getPreferences(MODE_PRIVATE).getString("access_token", null);
        if (token == null || token.isBlank()) showLogin(); else showHome();
    }

    @Override protected void onResume() {
        super.onResume();
        if (map != null) map.onResume();
    }

    @Override protected void onPause() {
        if (map != null) map.onPause();
        super.onPause();
    }

    @Override protected void onDestroy() {
        destroyed = true;
        cancelAddressSearch();
        stopRidePolling();
        io.shutdownNow();
        addressIo.shutdownNow();
        super.onDestroy();
    }

    private void showLogin() {
        cancelAddressSearch();
        stopRidePolling();
        map = null;
        LinearLayout body = vertical(BLACK);
        body.setPadding(dp(24), dp(34), dp(24), dp(30));
        body.addView(text("CLICK-GO", 18, YELLOW, true));
        TextView title = text("Passageiro", 34, Color.WHITE, true);
        title.setPadding(0, dp(4), 0, dp(4));
        body.addView(title);
        TextView sub = text("Entre para pedir sua corrida", 16, Color.rgb(180, 180, 180), false);
        sub.setPadding(0, 0, 0, dp(24));
        body.addView(sub);

        LinearLayout card = card(BLACK, Color.rgb(42, 42, 42), 22, 18);
        EditText email = edit("E-mail");
        email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText pass = edit("Senha");
        pass.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_PASSWORD);
        pass.setTransformationMethod(PasswordTransformationMethod.getInstance());
        CheckBox show = new CheckBox(this);
        show.setText("Mostrar senha");
        show.setTextColor(Color.LTGRAY);
        show.setOnCheckedChangeListener((b, c) -> {
            int pos = pass.getSelectionStart();
            pass.setTransformationMethod(c ? null : PasswordTransformationMethod.getInstance());
            pass.setSelection(Math.max(0, Math.min(pos, pass.length())));
        });
        Button enter = primary("Entrar");
        Button create = secondary("Criar conta");
        TextView forgot = text("Esqueci minha senha", 15, YELLOW, true);
        forgot.setGravity(Gravity.CENTER);
        forgot.setPadding(0, dp(12), 0, dp(6));
        card.addView(email, lpMatch(dp(58)));
        card.addView(space(10));
        card.addView(pass, lpMatch(dp(58)));
        card.addView(show);
        card.addView(space(8));
        card.addView(enter, lpMatch(dp(56)));
        card.addView(space(9));
        card.addView(create, lpMatch(dp(54)));
        card.addView(forgot);
        body.addView(card, lpMatchWrap());

        enter.setOnClickListener(v -> login(email.getText().toString().trim(), pass.getText().toString()));
        create.setOnClickListener(v -> showSignup());
        forgot.setOnClickListener(v -> recover(email.getText().toString().trim()));
        setContentView(scroll(body, BLACK));
    }

    private void showSignup() {
        LinearLayout body = vertical(BLACK);
        body.setPadding(dp(24), dp(30), dp(24), dp(30));
        Button back = secondary("← Voltar");
        back.setOnClickListener(v -> showLogin());
        body.addView(back, new LinearLayout.LayoutParams(dp(110), dp(50)));
        TextView title = text("Criar conta", 30, Color.WHITE, true);
        title.setPadding(0, dp(18), 0, dp(8));
        body.addView(title);
        body.addView(text("Cadastro de passageiro", 16, Color.LTGRAY, false));
        body.addView(space(18));

        EditText name = edit("Nome completo");
        EditText email = edit("E-mail");
        email.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_EMAIL_ADDRESS);
        EditText pass = edit("Senha (mínimo 6 caracteres)");
        pass.setTransformationMethod(PasswordTransformationMethod.getInstance());
        CheckBox show = new CheckBox(this);
        show.setText("Mostrar senha");
        show.setTextColor(Color.LTGRAY);
        show.setOnCheckedChangeListener((b, c) -> pass.setTransformationMethod(c ? null : PasswordTransformationMethod.getInstance()));
        body.addView(name, lpMatch(dp(58)));
        body.addView(space(10));
        body.addView(email, lpMatch(dp(58)));
        body.addView(space(10));
        body.addView(pass, lpMatch(dp(58)));
        body.addView(show);
        body.addView(space(14));
        Button create = primary("Criar minha conta");
        body.addView(create, lpMatch(dp(58)));
        create.setOnClickListener(v -> signup(name.getText().toString().trim(), email.getText().toString().trim(), pass.getText().toString()));
        setContentView(scroll(body, BLACK));
    }

    private void login(String email, String password) {
        if (email.isBlank() || password.isBlank()) {
            toast("Informe e-mail e senha.");
            return;
        }
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("email", email).put("password", password);
                JSONObject response = new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=password", body));
                String accessToken = response.optString("access_token", "");
                if (accessToken.isBlank()) throw new Exception("Não foi possível iniciar a sessão.");
                token = accessToken;
                getPreferences(MODE_PRIVATE).edit().putString("access_token", accessToken).apply();
                ui.post(this::showHome);
            } catch (Exception e) {
                ui.post(() -> toast(message(e)));
            }
        });
    }

    private void signup(String name, String email, String password) {
        if (name.isBlank() || email.isBlank() || password.length() < 6) {
            toast("Preencha nome, e-mail e uma senha com pelo menos 6 caracteres.");
            return;
        }
        io.execute(() -> {
            try {
                JSONObject meta = new JSONObject().put("role", "passenger").put("full_name", name);
                JSONObject body = new JSONObject().put("email", email).put("password", password).put("data", meta);
                JSONObject response = new JSONObject(ApiClient.authPost("/auth/v1/signup", body));
                String accessToken = response.optString("access_token", "");
                if (accessToken.isBlank()) {
                    ui.post(() -> {
                        toast("Conta criada. Confirme seu e-mail e depois entre no aplicativo.");
                        showLogin();
                    });
                } else {
                    token = accessToken;
                    getPreferences(MODE_PRIVATE).edit().putString("access_token", accessToken).apply();
                    ui.post(this::showHome);
                }
            } catch (Exception e) {
                ui.post(() -> toast(message(e)));
            }
        });
    }

    private void recover(String email) {
        if (email.isBlank()) {
            toast("Digite seu e-mail primeiro.");
            return;
        }
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject().put("email", email);
                ApiClient.authPost("/auth/v1/recover?redirect_to=https%3A%2F%2Fclick-go-ten.vercel.app%2Fredefinir-senha", body);
                ui.post(() -> toast("E-mail de recuperação enviado."));
            } catch (Exception e) {
                ui.post(() -> toast(message(e)));
            }
        });
    }

    private void showHome() {
        cancelAddressSearch();
        stopRidePolling();
        activeRideId = null;
        map = null;

        LinearLayout root = vertical(LIGHT);
        root.setPadding(dp(18), dp(18), dp(18), dp(22));

        LinearLayout top = horizontal();
        top.setGravity(Gravity.CENTER_VERTICAL);
        Button menu = circleButton("☰", 48);
        top.addView(menu, new LinearLayout.LayoutParams(dp(50), dp(50)));
        TextView logo = text("CLICK-GO", 18, BLACK, true);
        logo.setPadding(dp(14), 0, 0, 0);
        top.addView(logo, new LinearLayout.LayoutParams(0, dp(50), 1));
        TextView avatar = text("CG", 14, YELLOW, true);
        avatar.setGravity(Gravity.CENTER);
        avatar.setBackground(round(BLACK, 24, BLACK));
        top.addView(avatar, new LinearLayout.LayoutParams(dp(48), dp(48)));
        root.addView(top);
        root.addView(space(18));

        root.addView(text("Para onde vamos?", 30, BLACK, true));
        root.addView(space(14));

        LinearLayout originCard = card(Color.WHITE, Color.rgb(235, 235, 235), 22, 14);
        LinearLayout originRow = horizontal();
        originRow.setGravity(Gravity.CENTER_VERTICAL);
        originRow.addView(text("●", 19, GREEN, true), new LinearLayout.LayoutParams(dp(28), dp(52)));
        LinearLayout originTexts = vertical(Color.TRANSPARENT);
        originTexts.addView(text("EMBARQUE", 11, GRAY, true));
        TextView originView = text(originLabel, 16, BLACK, true);
        originView.setSingleLine(true);
        originView.setEllipsize(TextUtils.TruncateAt.END);
        originTexts.addView(originView);
        originRow.addView(originTexts, new LinearLayout.LayoutParams(0, dp(54), 1));
        Button change = smallButton("Alterar");
        originRow.addView(change, new LinearLayout.LayoutParams(dp(92), dp(46)));
        originCard.addView(originRow);
        root.addView(originCard, lpMatchWrap());
        root.addView(space(12));

        LinearLayout destCard = card(Color.WHITE, Color.rgb(235, 235, 235), 22, 14);
        LinearLayout destRow = horizontal();
        destRow.setGravity(Gravity.CENTER_VERTICAL);
        destRow.addView(text("●", 19, ORANGE, true), new LinearLayout.LayoutParams(dp(28), dp(58)));
        EditText destInput = editLight("Para onde vamos?");
        destInput.setTextSize(18);
        destRow.addView(destInput, new LinearLayout.LayoutParams(0, dp(60), 1));
        destCard.addView(destRow);
        LinearLayout suggestions = vertical(Color.WHITE);
        destCard.addView(suggestions, lpMatchWrap());
        root.addView(destCard, lpMatchWrap());
        root.addView(space(14));

        LinearLayout quick = horizontal();
        quick.addView(quickButton("⌂", "Casa"), new LinearLayout.LayoutParams(0, dp(84), 1));
        quick.addView(spaceH(8));
        quick.addView(quickButton("▣", "Trabalho"), new LinearLayout.LayoutParams(0, dp(84), 1));
        quick.addView(spaceH(8));
        quick.addView(quickButton("★", "Favoritos"), new LinearLayout.LayoutParams(0, dp(84), 1));
        root.addView(quick);
        root.addView(space(18));
        root.addView(text("Digite ao menos 3 letras do destino. A localização atual é usada como origem, mas você pode alterá-la.", 13, GRAY, false));

        menu.setOnClickListener(v -> showMenu());
        change.setOnClickListener(v -> showOriginPicker(originView));
        destInput.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void afterTextChanged(Editable s) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                scheduleAddressSearch(s.toString().trim(), suggestions, false, originView, null);
            }
        });

        setContentView(scroll(root, LIGHT));
        if (origin == null) obtainLocation(originView, false);
    }

    private void showOriginPicker(TextView homeOriginLabel) {
        cancelAddressSearch();
        LinearLayout wrap = vertical(Color.WHITE);
        wrap.setPadding(dp(18), dp(12), dp(18), dp(8));
        wrap.addView(text("Alterar local de embarque", 22, BLACK, true));
        wrap.addView(space(8));
        EditText input = editLight("Digite outro endereço");
        wrap.addView(input, lpMatch(dp(58)));
        LinearLayout results = vertical(Color.WHITE);
        wrap.addView(results, lpMatchWrap());
        wrap.addView(space(8));
        Button gps = secondaryLight("📍 Usar minha localização atual");
        wrap.addView(gps, lpMatch(dp(54)));

        AlertDialog dialog = new AlertDialog.Builder(this)
                .setView(wrap)
                .setNegativeButton("Fechar", null)
                .create();
        input.addTextChangedListener(new TextWatcher() {
            @Override public void beforeTextChanged(CharSequence s, int start, int count, int after) {}
            @Override public void afterTextChanged(Editable s) {}
            @Override public void onTextChanged(CharSequence s, int start, int before, int count) {
                scheduleAddressSearch(s.toString().trim(), results, true, homeOriginLabel, dialog);
            }
        });
        gps.setOnClickListener(v -> {
            dialog.dismiss();
            obtainLocation(homeOriginLabel, true);
        });
        dialog.setOnDismissListener(d -> cancelAddressSearch());
        dialog.show();
    }

    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        final int seq = ++searchSeq;
        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);
        if (addressFuture != null) addressFuture.cancel(true);
        target.removeAllViews();
        if (query.length() < 3) return;

        TextView loading = text("Buscando endereços…", 13, GRAY, false);
        loading.setPadding(dp(8), dp(10), dp(8), dp(6));
        target.addView(loading, lpMatchWrap());

        pendingAddressSearch = () -> {
            if (seq != searchSeq || destroyed) return;
            startAddressSearch(query, target, forOrigin, originView, dialog, seq);
        };
        ui.postDelayed(pendingAddressSearch, 650);
    }

    private void startAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog, int seq) {
        addressFuture = addressIo.submit(() -> {
            try {
                String url = BuildConfig.GEOCODE_URL + "?q=" + URLEncoder.encode(query, StandardCharsets.UTF_8.toString());
                JSONObject root = new JSONObject(ApiClient.absoluteGet(url));
                JSONArray rows = root.optJSONArray("results");
                List<SearchItem> items = new ArrayList<>();
                Set<String> seen = new HashSet<>();
                if (rows != null) {
                    for (int i = 0; i < rows.length() && items.size() < 3; i++) {
                        JSONObject row = rows.getJSONObject(i);
                        String label = cleanLabel(row.optString("label", ""));
                        double lat = row.optDouble("lat", Double.NaN);
                        double lng = row.optDouble("lng", Double.NaN);
                        if (label.isBlank() || !Double.isFinite(lat) || !Double.isFinite(lng)) continue;
                        String key = label.toLowerCase(Locale.ROOT).replaceAll("\\s+", " ");
                        if (seen.add(key)) items.add(new SearchItem(label, lat, lng));
                    }
                }
                if (Thread.currentThread().isInterrupted()) return;
                ui.post(() -> {
                    if (destroyed || seq != searchSeq || !target.isAttachedToWindow()) return;
                    if (dialog != null && !dialog.isShowing()) return;
                    renderSearchResults(items, target, forOrigin, originView, dialog);
                });
            } catch (Exception e) {
                ui.post(() -> {
                    if (destroyed || seq != searchSeq || !target.isAttachedToWindow()) return;
                    target.removeAllViews();
                    TextView error = text("Não foi possível buscar agora. Tente novamente.", 13, Color.rgb(170, 60, 40), false);
                    error.setPadding(dp(8), dp(10), dp(8), dp(8));
                    target.addView(error, lpMatchWrap());
                });
            }
        });
    }

    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        target.removeAllViews();
        if (items.isEmpty()) {
            TextView empty = text("Nenhum endereço encontrado. Tente informar rua, número e cidade.", 13, GRAY, false);
            empty.setPadding(dp(8), dp(10), dp(8), dp(8));
            target.addView(empty, lpMatchWrap());
            return;
        }
        for (SearchItem item : items) {
            TextView row = text(item.label, 14, BLACK, false);
            row.setMaxLines(2);
            row.setEllipsize(TextUtils.TruncateAt.END);
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(14), dp(9), dp(14), dp(9));
            row.setMinHeight(dp(58));
            row.setBackground(round(Color.rgb(250, 250, 250), 14, Color.rgb(228, 228, 228)));
            row.setClickable(true);
            row.setFocusable(true);
            row.setOnClickListener(v -> {
                ++searchSeq;
                cancelAddressSearchOnly();
                hideKeyboard();
                if (forOrigin) {
                    origin = new GeoPoint(item.lat, item.lng);
                    originLabel = item.label;
                    originView.setText(item.label);
                    if (dialog != null && dialog.isShowing()) dialog.dismiss();
                } else {
                    destination = new GeoPoint(item.lat, item.lng);
                    destinationLabel = item.label;
                    showOptions();
                }
            });
            target.addView(row, lpMatchWrap());
            target.addView(space(6));
        }
    }

    private void cancelAddressSearch() {
        ++searchSeq;
        cancelAddressSearchOnly();
    }

    private void cancelAddressSearchOnly() {
        if (pendingAddressSearch != null) {
            ui.removeCallbacks(pendingAddressSearch);
            pendingAddressSearch = null;
        }
        if (addressFuture != null) {
            addressFuture.cancel(true);
            addressFuture = null;
        }
    }

    private void obtainLocation(TextView labelView, boolean userAction) {
        if (checkSelfPermission(Manifest.permission.ACCESS_FINE_LOCATION) != PackageManager.PERMISSION_GRANTED &&
                checkSelfPermission(Manifest.permission.ACCESS_COARSE_LOCATION) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.ACCESS_FINE_LOCATION, Manifest.permission.ACCESS_COARSE_LOCATION}, REQ_LOCATION);
            return;
        }
        final int seq = ++locationSeq;
        if (userAction && labelView != null) labelView.setText("Buscando sua localização…");
        io.execute(() -> {
            try {
                LocationManager manager = (LocationManager) getSystemService(LOCATION_SERVICE);
                Location best = null;
                for (String provider : Arrays.asList(LocationManager.GPS_PROVIDER, LocationManager.NETWORK_PROVIDER)) {
                    try {
                        Location candidate = manager.getLastKnownLocation(provider);
                        if (candidate != null && (best == null || candidate.getTime() > best.getTime())) best = candidate;
                    } catch (Exception ignored) {}
                }
                Location cached = best;
                if (cached != null) ui.post(() -> applyLocation(cached, labelView, seq));
                ui.post(() -> requestFreshLocation(manager, labelView, seq, userAction));
            } catch (Exception e) {
                if (userAction) ui.post(() -> toast("Não foi possível obter a localização. Use 'Alterar' para informar o embarque."));
            }
        });
    }

    private void requestFreshLocation(LocationManager manager, TextView labelView, int seq, boolean userAction) {
        if (destroyed || seq != locationSeq) return;
        try {
            String provider = manager.isProviderEnabled(LocationManager.GPS_PROVIDER)
                    ? LocationManager.GPS_PROVIDER
                    : (manager.isProviderEnabled(LocationManager.NETWORK_PROVIDER) ? LocationManager.NETWORK_PROVIDER : null);
            if (provider == null) {
                if (userAction) toast("Ative a localização do celular ou informe outro endereço.");
                return;
            }
            LocationListener listener = new LocationListener() {
                @Override public void onLocationChanged(Location location) {
                    applyLocation(location, labelView, seq);
                    try { manager.removeUpdates(this); } catch (Exception ignored) {}
                }
                @Override public void onProviderEnabled(String provider) {}
                @Override public void onProviderDisabled(String provider) {}
                @Override public void onStatusChanged(String provider, int status, Bundle extras) {}
            };
            manager.requestSingleUpdate(provider, listener, Looper.getMainLooper());
        } catch (SecurityException ignored) {
        } catch (Exception e) {
            if (userAction) toast("Não foi possível atualizar sua localização agora.");
        }
    }

    private void applyLocation(Location location, TextView labelView, int seq) {
        if (destroyed || seq != locationSeq) return;
        origin = new GeoPoint(location.getLatitude(), location.getLongitude());
        originLabel = "Minha localização atual";
        if (labelView != null) labelView.setText(originLabel);
        reverseGeocodeOrigin(location, labelView, seq);
    }

    private void reverseGeocodeOrigin(Location location, TextView labelView, int seq) {
        io.execute(() -> {
            try {
                if (!Geocoder.isPresent()) return;
                Geocoder geocoder = new Geocoder(this, new Locale("pt", "BR"));
                List<Address> addresses = geocoder.getFromLocation(location.getLatitude(), location.getLongitude(), 1);
                if (addresses == null || addresses.isEmpty()) return;
                String resolved = shortAddress(addresses.get(0));
                if (resolved.isBlank()) return;
                ui.post(() -> {
                    if (destroyed || seq != locationSeq) return;
                    originLabel = resolved;
                    if (labelView != null && labelView.isAttachedToWindow()) labelView.setText(resolved);
                });
            } catch (Exception ignored) {}
        });
    }

    private String shortAddress(Address address) {
        List<String> parts = new ArrayList<>();
        String street = safe(address.getThoroughfare());
        String number = safe(address.getSubThoroughfare());
        if (!street.isBlank()) parts.add(number.isBlank() ? street : street + ", " + number);
        String district = safe(address.getSubLocality());
        if (!district.isBlank()) parts.add(district);
        String city = safe(address.getLocality());
        String state = safe(address.getAdminArea());
        if (!city.isBlank()) parts.add(state.isBlank() ? city : city + " - " + state);
        if (parts.isEmpty() && address.getMaxAddressLineIndex() >= 0) parts.add(address.getAddressLine(0));
        return String.join(" · ", parts);
    }

    @Override public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQ_LOCATION) {
            if (grantResults.length > 0 && grantResults[0] == PackageManager.PERMISSION_GRANTED) showHome();
            else toast("Sem acesso ao GPS. Use 'Alterar' para informar o embarque.");
        }
    }

    private void showOptions() {
        cancelAddressSearch();
        hideKeyboard();
        if (origin == null) {
            toast("Defina primeiro o local de embarque.");
            showHome();
            return;
        }
        LinearLayout root = vertical(Color.WHITE);
        FrameLayout mapFrame = new FrameLayout(this);
        map = new MapView(this);
        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        map.getController().setZoom(14.5);
        mapFrame.addView(map, new FrameLayout.LayoutParams(-1, -1));

        Button back = circleButton("←", 52);
        FrameLayout.LayoutParams backParams = new FrameLayout.LayoutParams(dp(54), dp(54));
        backParams.leftMargin = dp(16);
        backParams.topMargin = dp(16);
        mapFrame.addView(back, backParams);

        TextView destinationPill = text(destinationLabel, 15, BLACK, true);
        destinationPill.setSingleLine(true);
        destinationPill.setEllipsize(TextUtils.TruncateAt.END);
        destinationPill.setPadding(dp(16), 0, dp(16), 0);
        destinationPill.setGravity(Gravity.CENTER_VERTICAL);
        destinationPill.setBackground(round(Color.WHITE, 18, Color.WHITE));
        FrameLayout.LayoutParams pillParams = new FrameLayout.LayoutParams(-1, dp(54));
        pillParams.leftMargin = dp(82);
        pillParams.rightMargin = dp(16);
        pillParams.topMargin = dp(16);
        mapFrame.addView(destinationPill, pillParams);
        root.addView(mapFrame, new LinearLayout.LayoutParams(-1, 0, 1));

        ScrollView scroll = new ScrollView(this);
        LinearLayout bottom = vertical(Color.WHITE);
        bottom.setPadding(dp(16), dp(18), dp(16), dp(22));
        scroll.addView(bottom);
        bottom.addView(text("Escolha sua viagem", 24, BLACK, true));
        optionsSubtitle = text("Buscando categorias disponíveis…", 14, GRAY, false);
        bottom.addView(optionsSubtitle);
        bottom.addView(space(10));
        categoryBox = vertical(Color.WHITE);
        bottom.addView(categoryBox, lpMatchWrap());
        paymentSpinner = new Spinner(this);
        bottom.addView(paymentSpinner, lpMatch(dp(54)));
        bottom.addView(space(10));
        requestRideButton = primary("Aguarde…");
        requestRideButton.setEnabled(false);
        bottom.addView(requestRideButton, lpMatch(dp(58)));
        root.addView(scroll, new LinearLayout.LayoutParams(-1, dp(365)));

        back.setOnClickListener(v -> showHome());
        requestRideButton.setOnClickListener(v -> requestRide());
        setContentView(root);
        drawRoute();
        loadOptions();
    }

    private void drawRoute() {
        if (map == null || origin == null || destination == null) return;
        map.getOverlays().clear();
        Marker start = new Marker(map);
        start.setPosition(origin);
        start.setTitle("Embarque");
        start.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        map.getOverlays().add(start);
        Marker end = new Marker(map);
        end.setPosition(destination);
        end.setTitle("Destino");
        end.setAnchor(Marker.ANCHOR_CENTER, Marker.ANCHOR_BOTTOM);
        map.getOverlays().add(end);
        Polyline line = new Polyline();
        line.setPoints(Arrays.asList(origin, destination));
        line.getOutlinePaint().setStrokeWidth(dp(6));
        line.getOutlinePaint().setColor(Color.rgb(48, 92, 220));
        map.getOverlays().add(line);
        map.post(() -> {
            if (map == null) return;
            try {
                BoundingBox box = BoundingBox.fromGeoPoints(Arrays.asList(origin, destination));
                map.zoomToBoundingBox(box, true, dp(70));
                map.invalidate();
            } catch (Exception ignored) {}
        });
    }

    private void loadOptions() {
        rideOptions.clear();
        selectedOption = null;
        paymentValues.clear();
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject()
                        .put("p_origin_lat", origin.getLatitude())
                        .put("p_origin_lng", origin.getLongitude())
                        .put("p_destination_lat", destination.getLatitude())
                        .put("p_destination_lng", destination.getLongitude());
                JSONArray rows = new JSONArray(ApiClient.rpc("get_passenger_ride_options", body, token));
                List<RideOption> loaded = new ArrayList<>();
                for (int i = 0; i < rows.length(); i++) {
                    JSONObject row = rows.getJSONObject(i);
                    if (row.isNull("category_id")) continue;
                    loaded.add(new RideOption(
                            row.optString("category_id"), row.optString("category_name"), row.optString("required_vehicle_type"),
                            row.optDouble("distance_km"), row.optDouble("duration_min"), row.optDouble("fare"),
                            row.optString("city_id"), row.optString("city_name"), row.optString("state")
                    ));
                }
                if (loaded.isEmpty()) {
                    ui.post(() -> renderOptions(null));
                    return;
                }
                RideOption first = loaded.get(0);
                JSONArray payRows = new JSONArray(ApiClient.rpc("get_effective_payment_settings", new JSONObject().put("p_city_id", first.cityId), token));
                JSONObject settings = payRows.length() > 0 ? payRows.getJSONObject(0) : new JSONObject();
                List<String> payments = new ArrayList<>();
                if (settings.optBoolean("pix_enabled")) payments.add("pix");
                if (settings.optBoolean("card_app_enabled")) payments.add("card");
                if (settings.optBoolean("card_machine_enabled")) payments.add("card_machine");
                if (settings.optBoolean("cash_enabled")) payments.add("cash");
                ui.post(() -> {
                    rideOptions.clear();
                    rideOptions.addAll(loaded);
                    selectedOption = rideOptions.get(0);
                    paymentValues.clear();
                    paymentValues.addAll(payments);
                    renderOptions(settings);
                });
            } catch (Exception e) {
                ui.post(() -> {
                    if (categoryBox == null || optionsSubtitle == null) return;
                    categoryBox.removeAllViews();
                    categoryBox.addView(unavailable("Serviço indisponível", message(e)));
                    optionsSubtitle.setText("");
                    if (requestRideButton != null) requestRideButton.setEnabled(false);
                });
            }
        });
    }

    private void renderOptions(JSONObject settings) {
        if (categoryBox == null) return;
        categoryBox.removeAllViews();
        if (rideOptions.isEmpty()) {
            categoryBox.addView(unavailable("Serviço indisponível", "Ainda não há categorias ativas para esta rota."));
            optionsSubtitle.setText("");
            requestRideButton.setEnabled(false);
            return;
        }
        RideOption first = rideOptions.get(0);
        optionsSubtitle.setText(String.format(Locale.getDefault(), "%.1f km · aprox. %.0f min · %s/%s", first.distance, first.duration, first.city, first.state));
        for (RideOption option : rideOptions) {
            LinearLayout item = horizontal();
            item.setGravity(Gravity.CENTER_VERTICAL);
            item.setPadding(dp(14), dp(12), dp(14), dp(12));
            boolean chosen = option == selectedOption;
            item.setBackground(round(chosen ? Color.rgb(255, 251, 230) : Color.WHITE, 20, chosen ? BLACK : Color.rgb(230, 230, 230)));
            TextView icon = text(vehicleIcon(option.vehicle), 34, BLACK, false);
            icon.setGravity(Gravity.CENTER);
            item.addView(icon, new LinearLayout.LayoutParams(dp(62), dp(62)));
            LinearLayout labels = vertical(Color.TRANSPARENT);
            labels.addView(text(option.name, 18, BLACK, true));
            labels.addView(text((option.vehicle.isBlank() ? "Veículo" : option.vehicle) + " · " + Math.round(option.duration) + " min", 13, GRAY, false));
            item.addView(labels, new LinearLayout.LayoutParams(0, dp(62), 1));
            item.addView(text(money(option.fare), 18, BLACK, true));
            item.setOnClickListener(v -> {
                selectedOption = option;
                renderOptions(settings);
            });
            categoryBox.addView(item, lpMatch(dp(88)));
            categoryBox.addView(space(7));
        }
        List<String> display = new ArrayList<>();
        for (String payment : paymentValues) display.add(paymentLabel(payment));
        if (display.isEmpty()) display.add("Nenhuma forma de pagamento disponível");
        paymentSpinner.setAdapter(new ArrayAdapter<>(this, android.R.layout.simple_spinner_dropdown_item, display));
        requestRideButton.setEnabled(!paymentValues.isEmpty());
        requestRideButton.setText("Solicitar " + selectedOption.name + " · " + money(selectedOption.fare));
    }

    private void requestRide() {
        if (selectedOption == null || paymentValues.isEmpty()) return;
        int index = paymentSpinner.getSelectedItemPosition();
        String payment = paymentValues.get(Math.min(index, paymentValues.size() - 1));
        requestRideButton.setEnabled(false);
        requestRideButton.setText("Procurando motoristas…");
        RideOption option = selectedOption;
        io.execute(() -> {
            try {
                JSONObject body = new JSONObject()
                        .put("p_origin_label", originLabel)
                        .put("p_origin_lat", origin.getLatitude())
                        .put("p_origin_lng", origin.getLongitude())
                        .put("p_destination_label", destinationLabel)
                        .put("p_destination_lat", destination.getLatitude())
                        .put("p_destination_lng", destination.getLongitude())
                        .put("p_category_id", option.id)
                        .put("p_payment_method", payment);
                String raw = ApiClient.rpc("create_passenger_ride", body, token).trim();
                activeRideId = raw.replace("\"", "");
                ui.post(this::showActiveRide);
            } catch (Exception e) {
                ui.post(() -> {
                    toast(message(e));
                    if (requestRideButton != null) {
                        requestRideButton.setEnabled(true);
                        requestRideButton.setText("Solicitar " + option.name + " · " + money(option.fare));
                    }
                });
            }
        });
    }

    private void showActiveRide() {
        stopRidePolling();
        LinearLayout root = vertical(Color.WHITE);
        FrameLayout mapFrame = new FrameLayout(this);
        map = new MapView(this);
        map.setTileSource(TileSourceFactory.MAPNIK);
        map.setMultiTouchControls(true);
        mapFrame.addView(map, new FrameLayout.LayoutParams(-1, -1));
        TextView brand = text("CLICK-GO", 16, BLACK, true);
        brand.setPadding(dp(14), 0, dp(14), 0);
        brand.setGravity(Gravity.CENTER);
        brand.setBackground(round(Color.WHITE, 16, Color.WHITE));
        FrameLayout.LayoutParams brandParams = new FrameLayout.LayoutParams(dp(120), dp(46));
        brandParams.leftMargin = dp(16);
        brandParams.topMargin = dp(16);
        mapFrame.addView(brand, brandParams);
        root.addView(mapFrame, new LinearLayout.LayoutParams(-1, 0, 1));

        LinearLayout bottom = vertical(Color.WHITE);
        bottom.setPadding(dp(18), dp(20), dp(18), dp(24));
        activeStatus = text("Procurando motorista…", 24, BLACK, true);
        activeFare = text(selectedOption == null ? "" : money(selectedOption.fare), 18, BLACK, true);
        bottom.addView(activeStatus);
        TextView route = text(originLabel + " → " + destinationLabel, 14, GRAY, false);
        route.setMaxLines(2);
        route.setEllipsize(TextUtils.TruncateAt.END);
        bottom.addView(route);
        bottom.addView(activeFare);
        bottom.addView(space(8));
        Button cancel = secondaryLight("Cancelar corrida");
        bottom.addView(cancel, lpMatch(dp(54)));
        root.addView(bottom, new LinearLayout.LayoutParams(-1, dp(225)));
        setContentView(root);
        drawRoute();
        cancel.setOnClickListener(v -> previewCancel());
        startRidePolling();
    }

    private void startRidePolling() {
        stopRidePolling();
        ridePoll = new Runnable() {
            @Override public void run() {
                if (activeRideId == null || destroyed) return;
                String rideId = activeRideId;
                io.execute(() -> {
                    try {
                        JSONArray rows = new JSONArray(ApiClient.restGet("rides?id=eq." + rideId + "&select=id,status,estimated_fare,final_fare", token));
                        if (rows.length() == 0) {
                            ui.postDelayed(ridePoll, 3500);
                            return;
                        }
                        JSONObject ride = rows.getJSONObject(0);
                        String status = ride.optString("status");
                        double fare = ride.isNull("final_fare") ? ride.optDouble("estimated_fare") : ride.optDouble("final_fare");
                        ui.post(() -> {
                            if (activeStatus != null) activeStatus.setText(statusLabel(status));
                            if (activeFare != null) activeFare.setText(money(fare));
                            if (status.equals("completed") || status.equals("cancelled")) {
                                activeRideId = null;
                                stopRidePolling();
                                showEndState(status, fare);
                            } else {
                                ui.postDelayed(ridePoll, 3000);
                            }
                        });
                    } catch (Exception e) {
                        ui.postDelayed(ridePoll, 4500);
                    }
                });
            }
        };
        ui.post(ridePoll);
    }

    private void stopRidePolling() {
        if (ridePoll != null) {
            ui.removeCallbacks(ridePoll);
            ridePoll = null;
        }
    }

    private void showEndState(String status, double fare) {
        LinearLayout body = vertical(Color.WHITE);
        body.setGravity(Gravity.CENTER);
        body.setPadding(dp(24), dp(40), dp(24), dp(40));
        body.addView(text(status.equals("completed") ? "Corrida concluída" : "Corrida cancelada", 28, BLACK, true));
        body.addView(text(money(fare), 22, BLACK, true));
        body.addView(space(18));
        Button newRide = primary("Nova corrida");
        body.addView(newRide, lpMatch(dp(58)));
        newRide.setOnClickListener(v -> {
            destination = null;
            destinationLabel = "";
            showHome();
        });
        setContentView(body);
    }

    private void previewCancel() {
        if (activeRideId == null) return;
        String rideId = activeRideId;
        io.execute(() -> {
            try {
                JSONObject preview = new JSONObject(ApiClient.rpc("preview_passenger_ride_cancellation", new JSONObject().put("p_ride_id", rideId), token));
                double fee = preview.optDouble("cancellation_fee_amount", 0);
                boolean charge = preview.optBoolean("requires_confirmation", false);
                ui.post(() -> new AlertDialog.Builder(this)
                        .setTitle(charge ? "Há taxa de cancelamento" : "Cancelamento sem taxa")
                        .setMessage(charge
                                ? "Se cancelar agora, será registrada uma taxa de " + money(fee) + " para a próxima corrida. Deseja realmente cancelar?"
                                : "Você ainda pode cancelar sem taxa. Deseja cancelar esta corrida?")
                        .setNegativeButton("Continuar chamado", null)
                        .setPositiveButton("Cancelar mesmo assim", (d, w) -> confirmCancel())
                        .show());
            } catch (Exception e) {
                ui.post(() -> toast(message(e)));
            }
        });
    }

    private void confirmCancel() {
        if (activeRideId == null) return;
        String rideId = activeRideId;
        io.execute(() -> {
            try {
                ApiClient.rpc("cancel_passenger_ride", new JSONObject().put("p_ride_id", rideId).put("p_confirm_fee", true), token);
                ui.post(() -> toast("Corrida cancelada."));
            } catch (Exception e) {
                ui.post(() -> toast(message(e)));
            }
        });
    }

    private void showMenu() {
        String[] items = {"Histórico", "Pagamentos", "Cupons", "Favoritos", "Ajuda e suporte", "Sair"};
        new AlertDialog.Builder(this)
                .setTitle("CLICK-GO Passageiro")
                .setItems(items, (dialog, which) -> {
                    if (which == 5) {
                        token = null;
                        getPreferences(MODE_PRIVATE).edit().clear().apply();
                        showLogin();
                    } else {
                        toast("Essa área será conectada na próxima etapa do app nativo.");
                    }
                })
                .show();
    }

    private String cleanLabel(String label) {
        String value = label == null ? "" : label.trim().replaceAll("\\s+", " ");
        return value.length() > 150 ? value.substring(0, 147) + "…" : value;
    }

    private String safe(String value) { return value == null ? "" : value.trim(); }
    private String message(Exception e) { return e.getMessage() == null || e.getMessage().isBlank() ? "Não foi possível concluir a operação." : e.getMessage(); }

    private String vehicleIcon(String type) {
        String t = type == null ? "" : type.toLowerCase(Locale.ROOT);
        if (t.contains("moto")) return "🏍";
        if (t.contains("premium") || t.contains("comfort")) return "🚘";
        if (t.contains("tax")) return "🚕";
        return "🚗";
    }

    private String paymentLabel(String payment) {
        switch (payment) {
            case "pix": return "PIX";
            case "card": return "Cartão no app";
            case "card_machine": return "Cartão com motorista";
            default: return "Dinheiro";
        }
    }

    private String statusLabel(String status) {
        switch (status) {
            case "requested":
            case "searching": return "Procurando motorista…";
            case "accepted": return "Motorista aceitou";
            case "driver_arriving": return "Motorista a caminho";
            case "in_progress": return "Corrida em andamento";
            case "completed": return "Corrida concluída";
            case "cancelled": return "Corrida cancelada";
            default: return status;
        }
    }

    private String money(double value) { return NumberFormat.getCurrencyInstance(new Locale("pt", "BR")).format(value); }

    private LinearLayout unavailable(String title, String message) {
        LinearLayout box = card(Color.rgb(250, 250, 250), Color.rgb(230, 230, 230), 20, 18);
        TextView icon = text("⊘", 38, Color.rgb(210, 70, 40), true);
        icon.setGravity(Gravity.CENTER);
        box.addView(icon);
        TextView heading = text(title, 20, BLACK, true);
        heading.setGravity(Gravity.CENTER);
        box.addView(heading);
        TextView detail = text(message == null ? "" : message, 14, GRAY, false);
        detail.setGravity(Gravity.CENTER);
        detail.setPadding(0, dp(6), 0, 0);
        box.addView(detail);
        return box;
    }

    private LinearLayout quickButton(String icon, String label) {
        LinearLayout box = vertical(Color.WHITE);
        box.setGravity(Gravity.CENTER);
        box.setBackground(round(Color.WHITE, 17, Color.WHITE));
        TextView i = text(icon, 22, BLACK, true);
        i.setGravity(Gravity.CENTER);
        TextView l = text(label, 13, BLACK, true);
        l.setGravity(Gravity.CENTER);
        box.addView(i);
        box.addView(l);
        return box;
    }

    private LinearLayout vertical(int color) {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.VERTICAL);
        layout.setBackgroundColor(color);
        return layout;
    }

    private LinearLayout horizontal() {
        LinearLayout layout = new LinearLayout(this);
        layout.setOrientation(LinearLayout.HORIZONTAL);
        return layout;
    }

    private ScrollView scroll(View child, int color) {
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(color);
        scroll.addView(child, new ScrollView.LayoutParams(-1, -2));
        return scroll;
    }

    private LinearLayout card(int fill, int stroke, int radius, int padding) {
        LinearLayout layout = vertical(fill);
        layout.setPadding(dp(padding), dp(padding), dp(padding), dp(padding));
        layout.setBackground(round(fill, radius, stroke));
        return layout;
    }

    private TextView text(String value, int sp, int color, boolean bold) {
        TextView view = new TextView(this);
        view.setText(value);
        view.setTextSize(sp);
        view.setTextColor(color);
        if (bold) view.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return view;
    }

    private EditText edit(String hint) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setHintTextColor(Color.rgb(130, 130, 130));
        edit.setTextColor(Color.WHITE);
        edit.setTextSize(16);
        edit.setPadding(dp(16), 0, dp(16), 0);
        edit.setSingleLine(true);
        edit.setBackground(round(Color.rgb(28, 28, 28), 14, Color.rgb(55, 55, 55)));
        return edit;
    }

    private EditText editLight(String hint) {
        EditText edit = new EditText(this);
        edit.setHint(hint);
        edit.setHintTextColor(Color.rgb(145, 145, 145));
        edit.setTextColor(BLACK);
        edit.setTextSize(16);
        edit.setPadding(dp(12), 0, dp(12), 0);
        edit.setSingleLine(true);
        edit.setBackground(round(Color.rgb(248, 248, 248), 14, Color.rgb(235, 235, 235)));
        return edit;
    }

    private Button primary(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(16);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setTextColor(BLACK);
        button.setAllCaps(false);
        button.setBackground(round(YELLOW, 16, YELLOW));
        return button;
    }

    private Button secondary(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(15);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setTextColor(Color.WHITE);
        button.setAllCaps(false);
        button.setBackground(round(Color.rgb(35, 35, 35), 15, Color.rgb(55, 55, 55)));
        return button;
    }

    private Button secondaryLight(String label) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(14);
        button.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        button.setTextColor(BLACK);
        button.setAllCaps(false);
        button.setBackground(round(Color.rgb(247, 247, 247), 14, Color.rgb(225, 225, 225)));
        return button;
    }

    private Button smallButton(String label) {
        Button button = secondaryLight(label);
        button.setTextSize(13);
        return button;
    }

    private Button circleButton(String label, int size) {
        Button button = new Button(this);
        button.setText(label);
        button.setTextSize(20);
        button.setTextColor(BLACK);
        button.setAllCaps(false);
        button.setPadding(0, 0, 0, 0);
        button.setBackground(round(Color.WHITE, size / 2, Color.rgb(230, 230, 230)));
        return button;
    }

    private GradientDrawable round(int fill, int radius, int stroke) {
        GradientDrawable drawable = new GradientDrawable();
        drawable.setColor(fill);
        drawable.setCornerRadius(dp(radius));
        drawable.setStroke(dp(1), stroke);
        return drawable;
    }

    private View space(int height) {
        View view = new View(this);
        view.setLayoutParams(new LinearLayout.LayoutParams(1, dp(height)));
        return view;
    }

    private View spaceH(int width) {
        View view = new View(this);
        view.setLayoutParams(new LinearLayout.LayoutParams(dp(width), 1));
        return view;
    }

    private LinearLayout.LayoutParams lpMatch(int height) { return new LinearLayout.LayoutParams(-1, height); }
    private LinearLayout.LayoutParams lpMatchWrap() { return new LinearLayout.LayoutParams(-1, -2); }
    private int dp(int value) { return Math.round(value * getResources().getDisplayMetrics().density); }
    private void toast(String message) { Toast.makeText(this, message == null ? "Erro" : message, Toast.LENGTH_LONG).show(); }

    private void hideKeyboard() {
        View view = getCurrentFocus();
        if (view != null) ((InputMethodManager) getSystemService(Context.INPUT_METHOD_SERVICE)).hideSoftInputFromWindow(view.getWindowToken(), 0);
    }

    private static class SearchItem {
        final String label;
        final double lat;
        final double lng;
        SearchItem(String label, double lat, double lng) {
            this.label = label;
            this.lat = lat;
            this.lng = lng;
        }
    }

    private static class RideOption {
        final String id;
        final String name;
        final String vehicle;
        final String cityId;
        final String city;
        final String state;
        final double distance;
        final double duration;
        final double fare;
        RideOption(String id, String name, String vehicle, double distance, double duration, double fare, String cityId, String city, String state) {
            this.id = id;
            this.name = name;
            this.vehicle = vehicle == null ? "" : vehicle;
            this.distance = distance;
            this.duration = duration;
            this.fare = fare;
            this.cityId = cityId;
            this.city = city;
            this.state = state;
        }
    }
}
