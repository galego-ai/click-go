package com.clickgo.motorista;

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

import java.io.InputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.util.Locale;

public final class ProfileAvatar {
    private ProfileAvatar() {}

    public static Bitmap download(String urlValue) {
        if (urlValue == null || urlValue.isBlank()) return null;
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(urlValue).openConnection();
            connection.setConnectTimeout(7000);
            connection.setReadTimeout(9000);
            connection.setRequestProperty("Accept", "image/*");
            connection.setRequestProperty("User-Agent", "CLICK-GO-Motorista-Android/0.1");
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

    public static Drawable circleDrawable(Context context, Bitmap photo, String fullName) {
        float density = context.getResources().getDisplayMetrics().density;
        int size = Math.max(52, Math.round(52 * density));
        Bitmap output = Bitmap.createBitmap(size, size, Bitmap.Config.ARGB_8888);
        Canvas canvas = new Canvas(output);
        Paint paint = new Paint(Paint.ANTI_ALIAS_FLAG);
        float c = size / 2f;
        float outer = c - Math.max(1f, density);
        paint.setColor(Color.rgb(255, 212, 0));
        canvas.drawCircle(c, c, outer, paint);
        float inner = outer - Math.max(3f, 3f * density);
        if (photo != null && !photo.isRecycled()) {
            int save = canvas.save();
            Path clip = new Path();
            clip.addCircle(c, c, inner, Path.Direction.CW);
            canvas.clipPath(clip);
            Rect src = centerCrop(photo);
            RectF dst = new RectF(c - inner, c - inner, c + inner, c + inner);
            canvas.drawBitmap(photo, src, dst, paint);
            canvas.restoreToCount(save);
        } else {
            paint.setColor(Color.rgb(17, 17, 17));
            canvas.drawCircle(c, c, inner, paint);
            paint.setColor(Color.rgb(255, 212, 0));
            paint.setTypeface(Typeface.create(Typeface.DEFAULT, Typeface.BOLD));
            paint.setTextAlign(Paint.Align.CENTER);
            paint.setTextSize(Math.max(15f, 17f * density));
            Paint.FontMetrics fm = paint.getFontMetrics();
            float baseline = c - (fm.ascent + fm.descent) / 2f;
            canvas.drawText(initials(fullName), c, baseline, paint);
        }
        return new BitmapDrawable(context.getResources(), output);
    }

    private static Rect centerCrop(Bitmap bitmap) {
        int side = Math.min(bitmap.getWidth(), bitmap.getHeight());
        int left = (bitmap.getWidth() - side) / 2;
        int top = (bitmap.getHeight() - side) / 2;
        return new Rect(left, top, left + side, top + side);
    }

    private static String initials(String value) {
        String text = value == null ? "" : value.trim();
        if (text.isBlank()) return "M";
        String[] parts = text.split("\\s+");
        String first = parts[0].substring(0, 1);
        String second = parts.length > 1 ? parts[parts.length - 1].substring(0, 1) : "";
        return (first + second).toUpperCase(Locale.ROOT);
    }
}
