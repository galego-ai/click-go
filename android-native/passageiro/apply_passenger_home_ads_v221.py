from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Lightweight first-party ad slot. No advertising SDK is added.
if 'private FirstPartyAdBannerView homeAdView;' not in text:
    anchor='''    private PassengerHomeMap homeLiveMap;\n'''
    if anchor not in text: raise SystemExit('homeLiveMap field not found')
    text=text.replace(anchor,anchor+'''    private FirstPartyAdBannerView homeAdView;\n    private boolean homeAdRequested;\n''',1)

# Old home views must not receive an async banner after navigation/relaunch.
release_anchor='''        PassengerHomeMap home=homeLiveMap;homeLiveMap=null;\n'''
if release_anchor in text and 'homeAdView=null;homeAdRequested=false;' not in text[text.find(release_anchor)-120:text.find(release_anchor)+220]:
    text=text.replace(release_anchor,'''        homeAdView=null;homeAdRequested=false;\n'''+release_anchor,1)

home_map_anchor='''        PassengerHomeMap home=new PassengerHomeMap(this);homeLiveMap=home;root.addView(home,new FrameLayout.LayoutParams(-1,-1));\n'''
ad_insert='''        PassengerHomeMap home=new PassengerHomeMap(this);homeLiveMap=home;root.addView(home,new FrameLayout.LayoutParams(-1,-1));\n        homeAdRequested=false;FirstPartyAdBannerView adSlot=new FirstPartyAdBannerView(this);homeAdView=adSlot;\n        FrameLayout.LayoutParams adLp=new FrameLayout.LayoutParams(-1,dp(86));adLp.gravity=Gravity.BOTTOM;adLp.leftMargin=dp(12);adLp.rightMargin=dp(12);adLp.bottomMargin=dp(164);root.addView(adSlot,adLp);\n'''
if home_map_anchor not in text: raise SystemExit('v2.20 home map anchor not found')
text=text.replace(home_map_anchor,ad_insert,1)

# Keep location control above the banner slot.
text=text.replace('''locateLp.bottomMargin=dp(164);''','''locateLp.bottomMargin=dp(258);''',1)

# Load the most relevant banner after the passenger location is available.
center_pattern=r'''    private void centerHomeMap\(\)\{\n        if\(!homeMapMode\|\|homeLiveMap==null\|\|origin==null\)return;\n        renderHomePassengerMarker\(\);homeCentered=true;\n    \}\n'''
center_replacement='''    private void centerHomeMap(){\n        if(!homeMapMode||homeLiveMap==null||origin==null)return;\n        renderHomePassengerMarker();\n        if(!homeAdRequested){homeAdRequested=true;loadPassengerHomeAd(homeAdView);}\n        homeCentered=true;\n    }\n'''
text,n=re.subn(center_pattern,center_replacement,text,count=1)
if n!=1: raise SystemExit('v2.20 centerHomeMap not found')

helper_anchor='''    private void renderHomePassengerMarker(){\n'''
helper=r'''    private void loadPassengerHomeAd(FirstPartyAdBannerView slot){
        if(slot==null||homeSmokeMode||token==null||token.isBlank()){if(slot!=null)slot.setBanner(null);return;}
        final double lat=origin==null?Double.NaN:origin.getLatitude(),lng=origin==null?Double.NaN:origin.getLongitude();
        runIo(()->{try{
            JSONObject body=new JSONObject().put("p_audience","passenger").put("p_placement","passenger_home").put("p_lat",Double.isFinite(lat)?lat:JSONObject.NULL).put("p_lng",Double.isFinite(lng)?lng:JSONObject.NULL).put("p_city_id",JSONObject.NULL).put("p_franchise_id",JSONObject.NULL).put("p_limit",1);
            JSONArray rows=new JSONArray(ApiClient.rpc("get_active_app_banners",body,token));JSONObject banner=rows.length()>0?rows.optJSONObject(0):null;
            ui.post(()->{if(!destroyed&&homeMapMode&&homeAdView==slot&&slot.isAttachedToWindow())slot.setBanner(banner);});
        }catch(Exception ignored){ui.post(()->{if(!destroyed&&homeAdView==slot&&slot.isAttachedToWindow())slot.setBanner(null);});}});
    }

'''
if 'private void loadPassengerHomeAd(' not in text:
    if helper_anchor not in text: raise SystemExit('renderHomePassengerMarker anchor not found')
    text=text.replace(helper_anchor,helper+helper_anchor,1)

build=re.sub(r'versionCode\s+\d+','versionCode 221',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.21-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.21 PRIME: slot de anúncio próprio e leve aplicado na tela inicial.')
