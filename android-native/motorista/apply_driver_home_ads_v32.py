from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

if 'private String driverFranchiseId=' not in text:
    anchor='''    private boolean showEarningsMoney = true;\n'''
    if anchor not in text: raise SystemExit('showEarningsMoney field not found')
    text=text.replace(anchor,anchor+'''    private String driverFranchiseId="",driverCityId="";\n''',1)

# Keep franchise/city from the already loaded driver row; no extra request on every home draw.
if 'driverFranchiseId=d.optString("franchise_id","")' not in text:
    pattern=r'(driverStatus\s*=\s*d\.optString\("status","pending"\);)'
    text,n=re.subn(pattern,r'\1 driverFranchiseId=d.optString("franchise_id",""); driverCityId=d.optString("city_id","");',text,count=1)
    if n!=1: raise SystemExit('driverStatus assignment not found')

map_anchor='''        root.addView(map,new FrameLayout.LayoutParams(-1,-1));\n'''
ad_insert='''        root.addView(map,new FrameLayout.LayoutParams(-1,-1));\n        FirstPartyAdBannerView adSlot=new FirstPartyAdBannerView(this);\n        FrameLayout.LayoutParams adLp=new FrameLayout.LayoutParams(-1,dp(86));adLp.gravity=Gravity.TOP;adLp.leftMargin=dp(12);adLp.rightMargin=dp(12);adLp.topMargin=dp(94);root.addView(adSlot,adLp);\n'''
if map_anchor not in text: raise SystemExit('driver home map anchor not found')
text=text.replace(map_anchor,ad_insert,1)

set_anchor='''        setContentView(root);\n        if(online){startLocationWatch();startPolling();}else DriverMapRenderer.render(map,currentLocation,null,dp(5));\n'''
set_replacement='''        setContentView(root);\n        loadDriverHomeAd(adSlot);\n        if(online){startLocationWatch();startPolling();}else DriverMapRenderer.render(map,currentLocation,null,dp(5));\n'''
if set_anchor not in text: raise SystemExit('driver home setContentView anchor not found')
text=text.replace(set_anchor,set_replacement,1)

helper_anchor='''    private void toggleOnline() {\n'''
helper=r'''    private void loadDriverHomeAd(FirstPartyAdBannerView slot){
        if(slot==null||token==null||token.isBlank()||destroyed||io.isShutdown()){if(slot!=null)slot.setBanner(null);return;}
        final Double lat=currentLocation==null?null:currentLocation.getLatitude(),lng=currentLocation==null?null:currentLocation.getLongitude();
        try{io.execute(()->{try{
            JSONObject body=new JSONObject().put("p_audience","driver").put("p_placement","driver_home").put("p_lat",lat==null?JSONObject.NULL:lat).put("p_lng",lng==null?JSONObject.NULL:lng).put("p_city_id",driverCityId==null||driverCityId.isBlank()?JSONObject.NULL:driverCityId).put("p_franchise_id",driverFranchiseId==null||driverFranchiseId.isBlank()?JSONObject.NULL:driverFranchiseId).put("p_limit",1);
            JSONArray rows=new JSONArray(ApiClient.rpc("get_active_app_banners",body,token));JSONObject banner=rows.length()>0?rows.optJSONObject(0):null;
            ui.post(()->{if(!destroyed&&slot.isAttachedToWindow())slot.setBanner(banner);});
        }catch(Exception ignored){ui.post(()->{if(!destroyed&&slot.isAttachedToWindow())slot.setBanner(null);});}});}catch(java.util.concurrent.RejectedExecutionException ignored){}
    }

'''
if 'private void loadDriverHomeAd(' not in text:
    if helper_anchor not in text: raise SystemExit('toggleOnline anchor not found')
    text=text.replace(helper_anchor,helper+helper_anchor,1)

build=re.sub(r'versionCode\s+\d+','versionCode 32',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '3.2-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v3.2 PRIME: slot de anúncio próprio e leve aplicado na tela inicial.')
