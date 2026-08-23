from pathlib import Path

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text = main_path.read_text(encoding='utf-8')

def require_replace(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'Trecho não encontrado: {label}')
    text = text.replace(old, new, 1)

if 'import android.content.Intent;' not in text:
    text = text.replace('import android.content.Context;\n', 'import android.content.Context;\nimport android.content.Intent;\n', 1)
if 'import android.net.Uri;' not in text:
    text = text.replace('import android.location.LocationManager;\n', 'import android.location.LocationManager;\nimport android.net.Uri;\n', 1)
if 'import java.io.ByteArrayOutputStream;' not in text:
    text = text.replace('import java.net.URLEncoder;\n', 'import java.io.ByteArrayOutputStream;\nimport java.io.InputStream;\nimport java.net.URLEncoder;\n', 1)

if 'REQ_PROFILE_PHOTO' not in text:
    text = text.replace(
        '    private static final int REQ_LOCATION = 41;\n',
        '    private static final int REQ_LOCATION = 41;\n    private static final int REQ_PROFILE_PHOTO = 72;\n',
        1
    )

require_replace(
    'profiles?select=id,full_name,email,phone,cpf,avatar_url&limit=1',
    'profiles?select=id,full_name,email,phone,cpf,cpf_validated_at,avatar_url&limit=1',
    'consulta do perfil'
)

old_avatar_area = '''        PassengerAvatar.preload(this, token, () -> {\n            if (!destroyed && avatar.isAttachedToWindow()) avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));\n        });\n        content.addView(space(8));\n        EditText name = editLight("Nome completo"); name.setText(profile.optString("full_name", ""));\n'''
new_avatar_area = '''        PassengerAvatar.preload(this, token, () -> {\n            if (!destroyed && avatar.isAttachedToWindow()) avatar.setImageDrawable(PassengerAvatar.circleDrawable(this));\n        });\n        Button changePhoto = secondaryLight("📷 Alterar foto de perfil");\n        content.addView(changePhoto, lpMatch(dp(50)));\n        changePhoto.setOnClickListener(v -> pickPassengerProfilePhoto());\n        content.addView(space(10));\n        EditText name = editLight("Nome completo"); name.setText(profile.optString("full_name", ""));\n'''
require_replace(old_avatar_area, new_avatar_area, 'botão de foto')

old_cpf = '''        EditText cpf = editLight("CPF"); cpf.setText(profile.optString("cpf", "")); cpf.setInputType(InputType.TYPE_CLASS_NUMBER);\n        Button save = primary("Salvar alterações");\n'''
new_cpf = '''        EditText cpf = editLight("CPF"); cpf.setText(profile.optString("cpf", "")); cpf.setInputType(InputType.TYPE_CLASS_NUMBER);\n        boolean cpfLocked = !profile.isNull("cpf_validated_at") && !profile.optString("cpf_validated_at", "").isBlank();\n        if (cpfLocked) {\n            cpf.setEnabled(false);\n            cpf.setAlpha(0.68f);\n        }\n        TextView cpfStatus = text(\n                cpfLocked ? "✓ CPF validado — não pode ser alterado." : "CPF ainda não validado. Após validação, ficará bloqueado.",\n                12,\n                cpfLocked ? Color.rgb(30, 140, 80) : GRAY,\n                cpfLocked\n        );\n        Button save = primary("Salvar alterações");\n'''
require_replace(old_cpf, new_cpf, 'bloqueio visual do CPF')

old_fields = '''        content.addView(phone, lpMatch(dp(56))); content.addView(space(8));\n        content.addView(cpf, lpMatch(dp(56))); content.addView(space(14));\n        content.addView(save, lpMatch(dp(56)));\n'''
new_fields = '''        content.addView(phone, lpMatch(dp(56))); content.addView(space(8));\n        content.addView(cpf, lpMatch(dp(56)));\n        content.addView(cpfStatus, lpMatchWrap());\n        content.addView(space(14));\n        content.addView(save, lpMatch(dp(56)));\n'''
require_replace(old_fields, new_fields, 'status do CPF')

old_body = '''                    JSONObject body = new JSONObject()\n                            .put("full_name", fullName)\n                            .put("phone", phone.getText().toString().trim())\n                            .put("cpf", cpf.getText().toString().trim());\n                    ApiClient.restPatch("profiles?id=eq." + uid, body, token);\n'''
new_body = '''                    JSONObject body = new JSONObject()\n                            .put("full_name", fullName)\n                            .put("phone", phone.getText().toString().trim());\n                    if (!cpfLocked) body.put("cpf", cpf.getText().toString().trim());\n                    ApiClient.restPatch("profiles?id=eq." + uid, body, token);\n'''
require_replace(old_body, new_body, 'salvamento protegido do CPF')

insert_before = '''    private TextView drawerItem(String icon, String label) {\n'''
photo_methods = r'''    private void pickPassengerProfilePhoto() {
        Intent intent = new Intent(Intent.ACTION_OPEN_DOCUMENT);
        intent.addCategory(Intent.CATEGORY_OPENABLE);
        intent.setType("image/*");
        startActivityForResult(intent, REQ_PROFILE_PHOTO);
    }

    @Override protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode != REQ_PROFILE_PHOTO || resultCode != RESULT_OK || data == null || data.getData() == null) return;
        Uri uri = data.getData();
        io.execute(() -> {
            try {
                byte[] bytes = readProfilePhotoBytes(uri);
                if (bytes.length == 0) throw new Exception("Não foi possível ler a foto.");
                if (bytes.length > 5 * 1024 * 1024) throw new Exception("A foto deve ter no máximo 5 MB.");

                String uid = ensureUserId();
                String mime = getContentResolver().getType(uri);
                if (mime == null || mime.isBlank() || !mime.startsWith("image/")) mime = "image/jpeg";

                String objectPath = uid + "/profile.jpg";
                ApiClient.storageUpload("passenger-avatars", objectPath, bytes, mime, token);

                String publicUrl = BuildConfig.SUPABASE_URL
                        + "/storage/v1/object/public/passenger-avatars/"
                        + objectPath
                        + "?v=" + System.currentTimeMillis();

                ApiClient.restPatch(
                        "profiles?id=eq." + uid,
                        new JSONObject().put("avatar_url", publicUrl),
                        token
                );

                PassengerAvatar.reset();
                PassengerAvatar.preload(this, token, () -> {});
                ui.post(() -> {
                    toast("Foto de perfil atualizada.");
                    showProfile();
                });
            } catch (Exception e) {
                ui.post(() -> toast(message(e)));
            }
        });
    }

    private byte[] readProfilePhotoBytes(Uri uri) throws Exception {
        try (InputStream in = getContentResolver().openInputStream(uri);
             ByteArrayOutputStream out = new ByteArrayOutputStream()) {
            if (in == null) throw new Exception("Não foi possível abrir a foto.");
            byte[] buffer = new byte[8192];
            int read;
            int total = 0;
            while ((read = in.read(buffer)) != -1) {
                total += read;
                if (total > 5 * 1024 * 1024) throw new Exception("A foto deve ter no máximo 5 MB.");
                out.write(buffer, 0, read);
            }
            return out.toByteArray();
        }
    }

'''
if insert_before not in text:
    raise SystemExit('Ponto de inserção dos métodos de foto não encontrado')
text = text.replace(insert_before, photo_methods + insert_before, 1)
main_path.write_text(text, encoding='utf-8')

api_path = Path('app/src/main/java/com/clickgo/passageiro/ApiClient.java')
api = api_path.read_text(encoding='utf-8')
if 'public static void storageUpload(' not in api:
    marker = '''    private static String request(String urlString, String method, String body, boolean auth, String token, boolean apiKey) throws Exception {\n'''
    method = r'''    public static void storageUpload(String bucket, String objectPath, byte[] bytes, String contentType, String token) throws Exception {
        HttpURLConnection connection = null;
        try {
            String encodedPath = objectPath.replace(" ", "%20");
            connection = (HttpURLConnection) new URL(
                    BuildConfig.SUPABASE_URL + "/storage/v1/object/" + bucket + "/" + encodedPath
            ).openConnection();
            connection.setRequestMethod("POST");
            connection.setConnectTimeout(8000);
            connection.setReadTimeout(12000);
            connection.setUseCaches(false);
            connection.setDoOutput(true);
            connection.setRequestProperty("apikey", BuildConfig.SUPABASE_KEY);
            connection.setRequestProperty("Authorization", "Bearer " + token);
            connection.setRequestProperty("Content-Type",
                    contentType == null || contentType.isBlank() ? "image/jpeg" : contentType);
            connection.setRequestProperty("x-upsert", "true");
            connection.setFixedLengthStreamingMode(bytes.length);
            try (OutputStream os = connection.getOutputStream()) {
                os.write(bytes);
            }
            int code = connection.getResponseCode();
            InputStream stream = code >= 200 && code < 300
                    ? connection.getInputStream()
                    : connection.getErrorStream();
            String response = readAll(stream);
            if (code < 200 || code >= 300) {
                throw new Exception(extractMessage(response, "Erro no envio da foto"));
            }
        } finally {
            if (connection != null) connection.disconnect();
        }
    }

'''
    if marker not in api:
        raise SystemExit('Ponto de inserção do upload no ApiClient não encontrado')
    api = api.replace(marker, method + marker, 1)
api_path.write_text(api, encoding='utf-8')

build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
build = build.replace('versionCode 16', 'versionCode 17', 1)
build = build.replace("versionName '1.6-native-beta'", "versionName '1.7-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

print('Passageiro v1.7: foto de perfil editável e CPF validado bloqueado.')
