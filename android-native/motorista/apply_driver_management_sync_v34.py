from pathlib import Path
import re

main_path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Motorista v3.4 PRIME
# O app respeita o estado da licença/configuração do CLICK-GO Gestão.
# Uma suspensão impede NOVAS chamadas, mas nunca interrompe uma corrida já aceita.

anchor='    private String driverFranchiseId="",driverCityId="";\n'
fields='''    private String driverFranchiseId="",driverCityId="";\n    private volatile long managementConfigVersion=0L;\n    private volatile boolean managementOperationEnabled=true;\n    private volatile String managementLicenseStatus="active";\n    private volatile long lastManagementConfigCheck=0L;\n'''
if 'managementConfigVersion' not in text:
    if anchor not in text: raise SystemExit('driverFranchiseId não encontrado')
    text=text.replace(anchor,fields,1)

helper_anchor='    private void startPolling(){'
helpers=r'''    private void refreshManagementConfiguration(){
        if(token==null||token.isBlank()||driverFranchiseId==null||driverFranchiseId.isBlank()||destroyed)return;
        long now=System.currentTimeMillis();
        if(now-lastManagementConfigCheck<15000L)return;
        lastManagementConfigCheck=now;
        io.execute(()->{
            try{
                JSONObject args=new JSONObject().put("p_franchise_id",driverFranchiseId);
                if(driverCityId!=null&&!driverCityId.isBlank())args.put("p_city_id",driverCityId);else args.put("p_city_id",JSONObject.NULL);
                String raw=ApiClient.rpc("get_app_configuration_state",args,token);
                String trimmed=raw==null?"":raw.trim();
                JSONObject cfg;
                if(trimmed.startsWith("[")){
                    JSONArray a=new JSONArray(trimmed);
                    cfg=a.length()>0?a.optJSONObject(0):null;
                }else cfg=trimmed.isBlank()?null:new JSONObject(trimmed);
                if(cfg==null)return;
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
                if(BuildConfig.DEBUG)android.util.Log.i("CLICKGO_MANAGEMENT","motorista config v"+version+" license="+license+" enabled="+enabled);
                if(!enabled&&(watchedRideId==null||watchedRideId.isBlank())){
                    ui.post(()->{
                        try{stopRideCallSound(true);}catch(Exception ignored){}
                        try{dismissOfferDialog();}catch(Exception ignored){}
                        if(operationTitle!=null)operationTitle.setText("Operação suspensa pela Matriz");
                        if(operationBox!=null){operationBox.removeAllViews();TextView warning=text("Novas chamadas estão temporariamente bloqueadas. Licença: "+managementLicenseStatus,14,Color.rgb(150,150,150),false);operationBox.addView(warning);}
                    });
                }
            }catch(Exception e){
                if(BuildConfig.DEBUG)android.util.Log.w("CLICKGO_MANAGEMENT","falha ao atualizar configuração: "+e.getMessage());
            }
        });
    }

    private boolean canReceiveNewRidesByManagement(){
        return managementOperationEnabled||(watchedRideId!=null&&!watchedRideId.isBlank());
    }

'''
if 'private void refreshManagementConfiguration()' not in text:
    if helper_anchor not in text: raise SystemExit('startPolling não encontrado')
    text=text.replace(helper_anchor,helpers+helper_anchor,1)

# Atualiza a configuração ao iniciar o polling.
if 'refreshManagementConfiguration();\n        poller.post' not in text:
    old='    private void startPolling(){'
    if old not in text: raise SystemExit('startPolling ausente')
    text=text.replace(old,'    private void startPolling(){\n        refreshManagementConfiguration();',1)

# A cada refresh operacional, no máximo a cada 15s uma nova leitura é disparada.
refresh='    private void refreshOperation(){\n'
if refresh not in text: raise SystemExit('refreshOperation final não encontrado')
if 'canReceiveNewRidesByManagement()' not in text.split(refresh,1)[1][:600]:
    repl='''    private void refreshOperation(){
        refreshManagementConfiguration();
        if(!canReceiveNewRidesByManagement()){
            if(operationTitle!=null)operationTitle.setText("Operação suspensa pela Matriz");
            return;
        }
'''
    text=text.replace(refresh,repl,1)

# Cache local acelera o bloqueio após reinício, sem impedir corrida ativa.
oncreate='        token=getPreferences(MODE_PRIVATE).getString("access_token",null);\n'
cache='''        token=getPreferences(MODE_PRIVATE).getString("access_token",null);
        managementConfigVersion=getPreferences(MODE_PRIVATE).getLong("management_config_version",0L);
        managementOperationEnabled=getPreferences(MODE_PRIVATE).getBoolean("management_operation_enabled",true);
        managementLicenseStatus=getPreferences(MODE_PRIVATE).getString("management_license_status","active");
'''
if oncreate in text and 'managementConfigVersion=getPreferences' not in text:
    text=text.replace(oncreate,cache,1)

build=re.sub(r'versionCode\s+\d+','versionCode 34',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '3.4-prime'",build,count=1)
main_path.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.4 PRIME: sincronização CLICK-GO Gestão aplicada.')
