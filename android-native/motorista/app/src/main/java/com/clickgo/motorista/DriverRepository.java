package com.clickgo.motorista;

import org.json.JSONArray;
import org.json.JSONObject;

public final class DriverRepository {
    private DriverRepository() {}

    public static JSONObject signIn(String email, String password) throws Exception {
        return new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=password", new JSONObject().put("email", email).put("password", password)));
    }

    public static String userId(String token) throws Exception {
        return new JSONObject(ApiClient.authGetUser(token)).optString("id", "");
    }

    public static JSONObject profile(String token) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.restGet("profiles?select=full_name,email,avatar_url&limit=1", token));
        if (rows.length() == 0) throw new Exception("Perfil do motorista não encontrado.");
        return rows.getJSONObject(0);
    }

    public static JSONObject driver(String token) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.restGet("drivers?select=status,online,rating&limit=1", token));
        if (rows.length() == 0) throw new Exception("Cadastro de motorista não encontrado.");
        return rows.getJSONObject(0);
    }

    public static JSONObject wallet(String token) {
        try {
            JSONArray rows = new JSONArray(ApiClient.rpc("get_my_driver_wallet_summary", new JSONObject(), token));
            return rows.length() > 0 ? rows.getJSONObject(0) : new JSONObject();
        } catch (Exception ignored) { return new JSONObject(); }
    }

    public static void setOnline(String token, boolean online, Double lat, Double lng) throws Exception {
        JSONObject body = new JSONObject().put("p_online", online);
        body.put("p_lat", lat == null ? JSONObject.NULL : lat);
        body.put("p_lng", lng == null ? JSONObject.NULL : lng);
        ApiClient.rpc("set_driver_online", body, token);
    }

    public static void updateLocation(String token, double lat, double lng, Float heading, Float speedMps) throws Exception {
        JSONObject body = new JSONObject().put("p_lat", lat).put("p_lng", lng)
                .put("p_heading", heading == null ? JSONObject.NULL : heading)
                .put("p_speed_kmh", speedMps == null ? JSONObject.NULL : speedMps * 3.6);
        ApiClient.rpc("update_driver_location", body, token);
    }

    public static JSONObject activeRide(String token, String userId) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.restGet("rides?driver_id=eq." + userId + "&status=in.(accepted,driver_arriving,in_progress)&select=id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng&limit=1", token));
        return rows.length() > 0 ? rows.getJSONObject(0) : null;
    }

    public static JSONObject firstOffer(String token) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.rpc("get_driver_pending_offers", new JSONObject(), token));
        return rows.length() > 0 ? rows.getJSONObject(0) : null;
    }

    public static void respondOffer(String token, String offerId, boolean accept) throws Exception {
        ApiClient.rpc("respond_to_ride_offer", new JSONObject().put("p_offer_id", offerId).put("p_accept", accept), token);
    }

    public static void advanceRide(String token, String rideId, String action) throws Exception {
        ApiClient.rpc("advance_driver_ride", new JSONObject().put("p_ride_id", rideId).put("p_action", action), token);
    }
}
