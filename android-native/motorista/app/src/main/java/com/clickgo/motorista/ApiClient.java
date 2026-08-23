package com.clickgo.motorista;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStream;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.HttpURLConnection;
import java.net.URL;
import java.nio.charset.StandardCharsets;

public final class ApiClient {
    private ApiClient() {}

    public static String authPost(String path, JSONObject body) throws Exception {
        return request(BuildConfig.SUPABASE_URL + path, "POST", body.toString(), false, null, true);
    }

    public static String authGetUser(String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/auth/v1/user", "GET", null, true, token, true);
    }

    public static String rpc(String function, JSONObject body, String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/rpc/" + function, "POST", body.toString(), true, token, true);
    }

    public static String restGet(String pathAndQuery, String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "GET", null, true, token, true);
    }

    public static String publicRestGet(String pathAndQuery) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "GET", null, false, null, true);
    }

    public static String restPost(String path, JSONObject body, String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + path, "POST", body.toString(), true, token, true);
    }

    public static String restPatch(String pathAndQuery, JSONObject body, String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "PATCH", body.toString(), true, token, true);
    }

    public static void storageUpload(String bucket, String objectPath, byte[] bytes, String contentType, String token) throws Exception {
        HttpURLConnection connection = null;
        try {
            String encodedPath = objectPath.replace(" ", "%20");
            connection = (HttpURLConnection) new URL(BuildConfig.SUPABASE_URL + "/storage/v1/object/" + bucket + "/" + encodedPath).openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(12000);
            connection.setUseCaches(false);
            connection.setDoOutput(true);
            connection.setRequestProperty("apikey", BuildConfig.SUPABASE_KEY);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type", contentType == null || contentType.isBlank() ? "image/jpeg" : contentType);
            connection.setRequestProperty("x-upsert", "true");
            connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream os = connection.getOutputStream()) { os.write(bytes); }
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream();
            String text = readAll(stream);
            if (code < 200 || code >= 300) throw new Exception(extractMessage(text, "Erro no envio da foto"));
        } finally { if (connection != null) connection.disconnect(); }
    }

    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {
        HttpURLConnection connection = null;
        try {
            connection = (HttpURLConnection) new URL(urlString).openConnection();
            connection.setRequestMethod(method);
            connection.setConnectTimeout(7000);
            connection.setReadTimeout(10000);
            connection.setUseCaches(false);
            connection.setRequestProperty("Accept", "application/json");
            connection.setRequestProperty("User-Agent", "CLICK-GO-Motorista-Android/0.4");
            if (apiKey) connection.setRequestProperty("apikey", BuildConfig.SUPABASE_KEY);
            if (auth && token != null && !token.isBlank()) connection.setRequestProperty("Authorization", "Bearer " + token);
            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                connection.setRequestProperty("Prefer", "return=minimal");
                try (OutputStream os = connection.getOutputStream()) { os.write(body.getBytes(StandardCharsets.UTF_8)); }
            }
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream();
            String text = readAll(stream);
            if (code < 200 || code >= 300) throw new Exception(extractMessage(text, "Erro HTTP " + code));
            return text == null ? "" : text;
        } finally { if (connection != null) connection.disconnect(); }
    }

    private static String readAll(InputStream is) throws Exception {
        if (is == null) return "";
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String line; while ((line = br.readLine()) != null) sb.append(line);
        }
        return sb.toString();
    }

    private static String extractMessage(String text, String fallback) {
        try {
            JSONObject o = new JSONObject(text);
            if (o.has("message")) return o.optString("message", fallback);
            if (o.has("error_description")) return o.optString("error_description", fallback);
            if (o.has("error")) return o.optString("error", fallback);
            if (o.has("msg")) return o.optString("msg", fallback);
        } catch (Exception ignored) {}
        return text != null && !text.isBlank() ? text : fallback;
    }
}
