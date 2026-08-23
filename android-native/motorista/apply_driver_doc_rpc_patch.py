from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
text=path.read_text(encoding='utf-8')

old_avatar='''        JSONArray existing = new JSONArray(ApiClient.restGet("driver_documents?driver_id=eq." + userId + "&document_type=eq.profile_photo&select=id&order=created_at.desc&limit=1", token));
        if (existing.length() == 0) {
            ApiClient.restPost("driver_documents", new JSONObject()
                    .put("driver_id", userId)
                    .put("document_type", "profile_photo")
                    .put("file_path", documentPath)
                    .put("status", "pending"), token);
        } else {
            String documentId = existing.getJSONObject(0).optString("id", "");
            if (!documentId.isBlank()) {
                ApiClient.restPatch("driver_documents?id=eq." + documentId, new JSONObject()
                        .put("file_path", documentPath)
                        .put("status", "pending")
                        .put("rejection_reason", JSONObject.NULL)
                        .put("reviewed_by", JSONObject.NULL)
                        .put("reviewed_at", JSONObject.NULL), token);
            }
        }
'''
new_avatar='''        ApiClient.rpc("upsert_my_driver_document", new JSONObject()
                .put("p_document_type", "profile_photo")
                .put("p_file_path", documentPath), token);
'''
if old_avatar not in text:
    raise SystemExit('Bloco direto de profile_photo não encontrado')
text=text.replace(old_avatar,new_avatar,1)

old_doc='''        JSONArray existing = new JSONArray(ApiClient.restGet("driver_documents?driver_id=eq." + userId + "&document_type=eq." + documentType + "&select=id&order=created_at.desc&limit=1", token));
        JSONObject payload = new JSONObject()
                .put("file_path", objectPath)
                .put("status", "pending")
                .put("rejection_reason", JSONObject.NULL)
                .put("reviewed_by", JSONObject.NULL)
                .put("reviewed_at", JSONObject.NULL);
        if (existing.length() == 0) {
            payload.put("driver_id", userId).put("document_type", documentType);
            ApiClient.restPost("driver_documents", payload, token);
        } else {
            String id = existing.getJSONObject(0).optString("id", "");
            if (id.isBlank()) throw new Exception("Documento existente inválido.");
            ApiClient.restPatch("driver_documents?id=eq." + id, payload, token);
        }
'''
new_doc='''        ApiClient.rpc("upsert_my_driver_document", new JSONObject()
                .put("p_document_type", documentType)
                .put("p_file_path", objectPath), token);
'''
if old_doc not in text:
    raise SystemExit('Bloco direto de documento não encontrado')
text=text.replace(old_doc,new_doc,1)
path.write_text(text,encoding='utf-8')

build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\\s+(\\d+)',build)
if m:
    build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\\s+'[^']+'","versionName '1.0-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
print('Motorista v1.0 PRIME: documentos registrados via RPC segura.')
