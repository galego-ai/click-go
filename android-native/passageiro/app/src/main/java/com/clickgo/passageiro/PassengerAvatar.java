package com.clickgo.passageiro;

import android.content.Context;
import android.graphics.Bitmap;
import android.graphics.BitmapFactory;
import android.graphics.Canvas;
import android.graphics.Color;
import android.graphics.Paint;
import android.graphics.Path;
import android.graphics.Rect;
import android.graphics.RectF;
import android.graphics.Typeface;
import android.graphics.drawable.BitmapDrawable;
import android.graphics.drawable.Drawable;
import android.os.Handler;
import android.os.Looper;

import org.json.JSONArray;
import org.json.JSONObject;

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;
import java.util.concurrent.atomic.AtomicBoolean;

public final class PassengerAvatar {
    private static volatile String fullName = "Passageiro";
    private static volatile Bitmap photo;
    private static final AtomicBoolean loading = new AtomicBoolean(false);
    private static volatile boolean loaded = false;

    private PassengerAvatar() {}

    public static void preload(Context context, String token, Runnable onLoaded) {
        if (token == null || token.isBlank()) {
            notifyLoaded(onLoaded);
            return;
        }
        if (loaded) {
            notifyLoaded(onLoaded);
            return;
        }
        if (!loading.compareAndSet(false, true)) return;

        Thread worker = new Thread(() -> {
            try {
                JSONArray rows = new JSONArray(ApiClient.restGet("profiles?select=full_name,avatar_url&limit=1", token));
                if (rows.length() > 0) {
                    JSONObject profile = rows.getJSONObject(0);
                    String name = profile.optString("full_name", "").trim();
                    if (!name.isBlank()) fullName = name;
                    String avatarUrl = profile.optString("avatar_url", "").trim();
                    if (!avatarUrl.isBlank()) photo = downloadBitmap(avatarUrl);
                }
            } catch (Exception ignored) {
                // O fallback por iniciais continua funcionando sem rede/foto.
            } finally {
                loaded = true;
                loading.set(false);
                notifyLoaded(onLoaded);
            }
        }, "clickgo-passenger-avatar");
        worker.setDaemon(true);
        worker.start();
    }

    public static Drawable markerDrawable(Context context) {
        float density = context.getResources().getDisplayMetrics().density;
        int width = Math.max(68, Math.round(68 * density));
        int circle = Math.max(58, Math.round(58 * density));
        int pointer = Math.max(12, Math.round(12 * density));
        int height = circle + pointer;

        Bitmap output = Bitmap.createBitmap(width, height, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(output);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);

        float cx = width / 2f;
        float cy = circle / 2f;
        float outerRadius = circle / 2f - Math.max(1f, 1.5f * density);

        // Pequeno ponteiro para indicar o ponto exato do embarque.
        paint.setColor(Color.rgb(255, 212, 0));
        paint.setStyle(Paint.Style.FILL);
        Path pointerPath = new Path();
        pointerPath.moveTo(cx - 8f * density, circle - 5f * density);
        pointerPath.lineTo(cx + 8f * density, circle - 5f * density);
        pointerPath.lineTo(cx, height - 1f * density);
        pointerPath.close();
        canvas.drawPath(pointerPath, paint);

        // Borda amarela CLICK-GO.
        canvas.drawCircle(cx, cy, outerRadius, paint);
        float innerRadius = outerRadius - Math.max(3f, 3f * density);

        Bitmap currentPhoto = photo;
        if (currentPhoto != null && !currentPhoto.isRecycled()) {
            int save = canvas.save();
            Path clip = new Path();
            clip.addCircle(cx, cy, innerRadius, Path.Direction.CW);
            canvas.clipPath(clip);

            Rect src = centerCrop(currentPhoto);
            RectF dst = new RectF(cx - innerRadius, cy - innerRadius, cx + innerRadius, cy + innerRadius);
            canvas.drawBitmap(currentPhoto, src, dst, paint);
            canvas.restoreToCount(save);
        } else {
            paint.setColor(Color.rgb(17, 17, 17));
            canvas.drawCircle(cx, cy, innerRadius, paint);
            paint.setColor(Color.rgb(255, 212, 0));
            paint.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTextSize(Math.max(16f, 18f * density));
            Paint.FontMetrics fm = paint.getFontMetrics();
            float baseline = cy - (fm.ascent + fm.descent) / 2f;
            canvas.drawText(initials(fullName), cx, baseline, paint);
        }

        return new BitmapDrawable(context.getResources(), output);
    }

    public static String initials() {
        return initials(fullName);
    }

    private static Bitmap downloadBitmap(String urlValue) {
        HttpURLConnection connection = null;
        try {
            URL url = new URL(urlValue);
            connection = (HttpURLConnection) url.openConnection();
            connection.setConnectTimeout(7000);
            connection.setReadTimeout(9000);
            connection.setRequestProperty("User-Agent", "CLICK-GO-Passageiro-Android/0.3");
            connection.setRequestProperty("Accept", "image/*");
            connection.connect();
            if (connection.getResponseCode() < 200 || connection.getResponseCode() >= 300) return null;
            try (InputStream input = connection.getInputStream()) {
                return BitmapFactory.decodeStream(input);
            }
        } catch (Exception ignored) {
            return null;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static Rect centerCrop(Bitmap bitmap) {
        int width = bitmap.getWidth();
        int height = bitmap.getHeight();
        int side = Math.min(width, height);
        int left = (width - side) / 2;
        int top = (height - side) / 2;
        return new Rect(left, top, left + side, top + side);
    }

    private static String initials(String value) {
        String text = value == null ? "" : value.trim();
        if (text.isBlank()) return "P";
        String[] parts = text.split("\\s+");
        String first = parts[0].substring(0, 1);
        String second = parts.length > 1 ? parts[parts.length - 1].substring(0, 1) : "";
        return (first + second).toUpperCase(Locale.ROOT);
    }

    private static void notifyLoaded(Runnable callback) {
        if (callback == null) return;
        new Handler(Looper.getMainLooper()).post(callback);
    }
}
