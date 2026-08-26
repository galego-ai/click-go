package com.clickgo.motorista;

import org.json.JSONArray;
import org.json.JSONObject;

public final class DriverRepository {
    private DriverRepository() {}

    public static JSONObject signIn(String email, String password) throws Exception {
        return new JSONObject(ApiClient.authPost("/auth/v1/token?grant_type=password", new JSONObject().put("email", email).put("password", password)));
    }

    public static JSONObject signUp(JSONObject body) throws Exception {
        return new JSONObject(ApiClient.authPost("/auth/v1/signup", body));
    }

    public static JSONArray activeCities() throws Exception {
        return new JSONArray(ApiClient.publicRestGet("cities?select=id,name,state&active=eq.true&order=name.asc"));
    }

    public static JSONArray activeSignupFranchises() throws Exception {
        return new JSONArray(ApiClient.publicRpc("list_driver_signup_franchises", new JSONObject()));
    }

    public static String userId(String token) throws Exception {
        return new JSONObject(ApiClient.authGetUser(token)).optString("id", "");
    }

    public static JSONObject profile(String token) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.restGet("profiles?select=full_name,email,phone,avatar_url&limit=1", token));
        if (rows.length() == 0) throw new Exception("Perfil do motorista não encontrado.");
        return rows.getJSONObject(0);
    }

    public static JSONObject driver(String token) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.restGet("drivers?select=status,online,rating,franchise_id,city_id,has_card_machine,card_machine_approved&limit=1", token));
        if (rows.length() == 0) throw new Exception("Cadastro de motorista não encontrado.");
        return rows.getJSONObject(0);
    }

    public static String uploadAvatar(String token, String userId, byte[] jpeg) throws Exception {
        String avatarPath = userId + "/profile.jpg";
        String documentPath = userId + "/profile_photo.jpg";
        ApiClient.storageUpload("driver-avatars", avatarPath, jpeg, "image/jpeg", token);
        ApiClient.storageUpload("driver-documents", documentPath, jpeg, "image/jpeg", token);
        String publicUrl = BuildConfig.SUPABASE_URL + "/storage/v1/object/public/driver-avatars/" + avatarPath + "?v=" + System.currentTimeMillis();
        ApiClient.restPatch("profiles?id=eq." + userId, new JSONObject().put("avatar_url", publicUrl), token);

        ApiClient.rpc("upsert_my_driver_document", new JSONObject()
                .put("p_document_type", "profile_photo")
                .put("p_file_path", documentPath), token);
        return publicUrl;
    }

    public static void uploadDocument(String token, String userId, String documentType, byte[] bytes, String contentType) throws Exception {
        if (documentType == null || !documentType.matches("[a-z0-9_]+")) throw new Exception("Tipo de documento inválido.");
        if (bytes == null || bytes.length == 0) throw new Exception("O arquivo está vazio.");
        if (bytes.length > 12 * 1024 * 1024) throw new Exception("O arquivo deve ter no máximo 12 MB.");
        String mime = contentType == null ? "" : contentType.toLowerCase();
        String ext = mime.contains("pdf") ? "pdf" : mime.contains("png") ? "png" : mime.contains("webp") ? "webp" : "jpg";
        String safeMime = ext.equals("pdf") ? "application/pdf" : ext.equals("png") ? "image/png" : ext.equals("webp") ? "image/webp" : "image/jpeg";
        String objectPath = userId + "/" + documentType + "." + ext;
        ApiClient.storageUpload("driver-documents", objectPath, bytes, safeMime, token);

        ApiClient.rpc("upsert_my_driver_document", new JSONObject()
                .put("p_document_type", documentType)
                .put("p_file_path", objectPath), token);
    }

    public static JSONObject wallet(String token) {
        try {
            JSONArray rows = new JSONArray(ApiClient.rpc("get_my_driver_wallet_summary", new JSONObject(), token));
            return rows.length() > 0 ? rows.getJSONObject(0) : new JSONObject();
        } catch (Exception ignored) { return new JSONObject(); }
    }

    public static JSONObject billing(String token) throws Exception {
        JSONArray rows = new JSONArray(ApiClient.restGet("driver_billing_settings?select=billing_mode,per_ride_fee,monthly_fee,monthly_due_day,monthly_paid_until,active&limit=1", token));
        return rows.length() > 0 ? rows.getJSONObject(0) : new JSONObject();
    }

    public static JSONArray rideHistory(String token, String userId) throws Exception {
        return new JSONArray(ApiClient.restGet("rides?driver_id=eq." + userId + "&status=in.(completed,cancelled)&select=id,status,origin_label,destination_label,estimated_fare,final_fare,requested_at,completed_at,cancelled_at&order=requested_at.desc&limit=50", token));
    }

    public static JSONArray documents(String token, String userId) throws Exception {
        return new JSONArray(ApiClient.restGet("driver_documents?driver_id=eq." + userId + "&select=id,document_type,status,rejection_reason,created_at&order=created_at.desc", token));
    }

    public static JSONArray supportTickets(String token, String userId) throws Exception {
        return new JSONArray(ApiClient.restGet("support_tickets?requester_id=eq." + userId + "&select=id,subject,status,description,created_at&order=created_at.desc&limit=50", token));
    }

    public static void createSupportTicket(String token, String userId, String subject, String description) throws Exception {
        JSONObject d = driver(token);
        String franchiseId = d.optString("franchise_id", "");
        String cityId = d.optString("city_id", "");
        JSONObject body = new JSONObject()
                .put("requester_id", userId)
                .put("franchise_id", franchiseId.isBlank() ? JSONObject.NULL : franchiseId)
                .put("city_id", cityId.isBlank() ? JSONObject.NULL : cityId)
                .put("subject", subject)
                .put("category", "motorista")
                .put("priority", "normal")
                .put("status", "open")
                .put("description", description);
        ApiClient.restPost("support_tickets", body, token);
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
