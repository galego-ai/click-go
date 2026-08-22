package com.clickgo.passageiro;

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

    public static String rpc(String function, JSONObject body, String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/rpc/" + function, "POST", body.toString(), true, token, true);
    }

    public static String restGet(String pathAndQuery, String token) throws Exception {
        return request(BuildConfig.SUPABASE_URL + "/rest/v1/" + pathAndQuery, "GET", null, true, token, true);
    }

    public static String absoluteGet(String url) throws Exception {
        return request(url, "GET", null, false, null, false);
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
            connection.setRequestProperty("User-Agent", "CLICK-GO-Passageiro-Android/0.2");
            if (apiKey) connection.setRequestProperty("apikey", BuildConfig.SUPABASE_KEY);
            if (auth && token != null && !token.isEmpty()) connection.setRequestProperty("Authorization", "Bearer " + token);
            if (body != null) {
                connection.setDoOutput(true);
                connection.setRequestProperty("Content-Type", "application/json; charset=utf-8");
                try (OutputStream os = connection.getOutputStream()) {
                    os.write(body.getBytes(StandardCharsets.UTF_8));
                }
            }
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 300 ? connection.getInputStream() : connection.getErrorStream();
            String text = readAll(stream);
            if (code < 200 || code >= 300) throw new Exception(extractMessage(text, "Erro HTTP " + code));
            return text == null ? "" : text;
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

    private static String readAll(InputStream is) throws Exception {
        if (is == null) return "";
        StringBuilder sb = new StringBuilder();
        try (BufferedReader br = new BufferedReader(new InputStreamReader(is, StandardCharsets.UTF_8))) {
            String line;
            while ((line = br.readLine()) != null) {
                if (Thread.currentThread().isInterrupted()) throw new InterruptedException("Requisição cancelada");
                sb.append(line);
            }
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
