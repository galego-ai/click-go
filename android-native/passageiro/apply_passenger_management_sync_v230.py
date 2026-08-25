from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.30 PRIME
# Lê a versão/configuração efetiva da operação publicada pelo CLICK-GO Gestão.
# A suspensão da licença bloqueia somente NOVAS solicitações; uma corrida já ativa
# continua acessível para acompanhamento, segurança e cancelamento.

field_anchor='    private String currentUserId;\n'
fields='''    private String currentUserId;\n    private volatile long managementConfigVersion=0L;\n    private volatile boolean managementOperationEnabled=true;\n    private volatile String managementLicenseStatus="active";\n    private volatile long lastManagementConfigCheck=0L;\n'''
if 'managementConfigVersion' not in text:
    if field_anchor not in text: raise SystemExit('currentUserId não encontrado para sync da gestão')
    text=text.replace(field_anchor,fields,1)

show_home_match=re.search(r'\n    private void showHome\(\)\s*\{',text)
if not show_home_match: raise SystemExit('showHome não encontrado')
helper=r'''
    private void refreshManagementConfiguration(){
        if(token==null||token.isBlank()||destroyed)return;
        long now=System.currentTimeMillis();
        if(now-lastManagementConfigCheck<15000L)return;
        lastManagementConfigCheck=now;
        io.execute(()->{
            try{
                String franchiseId="",cityId="";
                JSONArray recent=new JSONArray(ApiClient.restGet("rides?select=franchise_id,city_id&order=requested_at.desc&limit=1",token));
                if(recent.length()>0){
                    JSONObject row=recent.optJSONObject(0);
                    if(row!=null){franchiseId=row.optString("franchise_id","");cityId=row.optString("city_id","");}
                }
                if(franchiseId.isBlank()&&cityId.isBlank())return;
                JSONObject args=new JSONObject();
                if(!franchiseId.isBlank())args.put("p_franchise_id",franchiseId);else args.put("p_franchise_id",JSONObject.NULL);
                if(!cityId.isBlank())args.put("p_city_id",cityId);else args.put("p_city_id",JSONObject.NULL);
                String raw=ApiClient.rpc("get_app_configuration_state",args,token);
                JSONObject cfg;
                String trimmed=raw==null?"":raw.trim();
                if(trimmed.startsWith("[")){
                    JSONArray array=new JSONArray(trimmed);
                    cfg=array.length()>0?array.optJSONObject(0):null;
                }else cfg=trimmed.isBlank()?null:new JSONObject(trimmed);
                if(cfg==null)return;
                long previous=managementConfigVersion;
                long version=cfg.optLong("version",0L);
                boolean enabled=cfg.optBoolean("operation_enabled",true);
                String license=cfg.optString("license_status","active");
                managementConfigVersion=version;
                managementOperationEnabled=enabled;
                managementLicenseStatus=license;
                getPreferences(MODE_PRIVATE).edit()
                        .putLong("management_config_version",version)
                        .putBoolean("management_operation_enabled",enabled)
                        .putString("management_license_status",license)
                        .apply();
                if(BuildConfig.DEBUG)android.util.Log.i("CLICKGO_MANAGEMENT","passageiro config v"+version+" license="+license+" enabled="+enabled);
                if(previous!=0L&&previous!=version){
                    ui.post(()->{
                        if(requestRideButton!=null&&activeRideId==null)requestRideButton.setEnabled(managementOperationEnabled);
                    });
                }
            }catch(Exception e){
                if(BuildConfig.DEBUG)android.util.Log.w("CLICKGO_MANAGEMENT","falha ao atualizar configuração: "+e.getMessage());
            }
        });
    }

    private boolean canRequestRideByManagement(){
        if(managementOperationEnabled)return true;
        toast("Operação temporariamente indisponível nesta região (licença "+managementLicenseStatus+").");
        return false;
    }
'''
if 'private void refreshManagementConfiguration()' not in text:
    pos=show_home_match.start()+1
    text=text[:pos]+helper+text[pos:]

# Atualiza a configuração sempre que a Home é aberta, com limitador interno.
text,n=re.subn(r'(    private void showHome\(\)\s*\{\n)',r'\1        refreshManagementConfiguration();\n',text,count=1)
if n!=1: raise SystemExit('não foi possível ligar sync à Home')

# Bloqueia apenas o início de uma nova corrida se a Matriz suspendeu a operação.
if 'canRequestRideByManagement();' not in text:
    pat=re.compile(r'(    private void requestRide\(\)\s*\{\n)')
    text,n=pat.subn(r'\1        refreshManagementConfiguration();\n        if(!canRequestRideByManagement())return;\n',text,count=1)
    if n!=1: raise SystemExit('requestRide não encontrado para bloqueio de licença')

# Restaura último estado conhecido imediatamente; uma consulta fresca vem logo depois.
if 'management_config_version' not in text.split('private void refreshManagementConfiguration()',1)[0]:
    pass
# onCreate já carrega a sessão; injeta cache antes da primeira tela.
oncreate_anchor='        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n'
cache='''        token = getPreferences(MODE_PRIVATE).getString("access_token", null);\n        managementConfigVersion=getPreferences(MODE_PRIVATE).getLong("management_config_version",0L);\n        managementOperationEnabled=getPreferences(MODE_PRIVATE).getBoolean("management_operation_enabled",true);\n        managementLicenseStatus=getPreferences(MODE_PRIVATE).getString("management_license_status","active");\n'''
if oncreate_anchor in text and 'managementConfigVersion=getPreferences' not in text:
    text=text.replace(oncreate_anchor,cache,1)

build=re.sub(r'versionCode\s+\d+','versionCode 230',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.30-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.30 PRIME: sincronização CLICK-GO Gestão aplicada.')
