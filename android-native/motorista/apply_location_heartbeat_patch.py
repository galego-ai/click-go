from pathlib import Path
import re

path = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text = path.read_text(encoding='utf-8')

field_anchor = '    private boolean destroyed;\n'
if 'private long lastLocationHeartbeatAt;' not in text:
    if field_anchor not in text:
        raise SystemExit('Campo destroyed não encontrado')
    text = text.replace(field_anchor, field_anchor + '    private long lastLocationHeartbeatAt;\n', 1)

old_watch = 'locationManager.requestLocationUpdates(provider,5000,3f,locationListener,Looper.getMainLooper());'
new_watch = 'locationManager.requestLocationUpdates(provider,10000,0f,locationListener,Looper.getMainLooper());'
if old_watch in text:
    text = text.replace(old_watch, new_watch, 1)
elif new_watch not in text:
    raise SystemExit('requestLocationUpdates do motorista não encontrado')

old_listener = 'locationListener = loc -> { currentLocation=loc; if(online) io.execute(() -> { try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); } catch(Exception ignored){} }); };'
new_listener = 'locationListener = loc -> { currentLocation=loc; if(online) { lastLocationHeartbeatAt=System.currentTimeMillis(); io.execute(() -> { try { DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null); } catch(Exception ignored){} }); } };'
if old_listener in text:
    text = text.replace(old_listener, new_listener, 1)
elif new_listener not in text:
    raise SystemExit('Listener de localização do motorista não encontrado')

poll_anchor = '    private void startPolling(){ stopPolling(); poller=new Runnable(){public void run(){if(!online||destroyed)return;refreshOperation();ui.postDelayed(this,4500);}};ui.post(poller); }\n'
new_poll = '    private void startPolling(){ stopPolling(); poller=new Runnable(){public void run(){if(!online||destroyed)return;heartbeatLocation();refreshOperation();ui.postDelayed(this,4500);}};ui.post(poller); }\n'
if poll_anchor in text:
    text = text.replace(poll_anchor, new_poll, 1)
elif new_poll not in text:
    raise SystemExit('Polling do motorista não encontrado')

method_anchor = '    private void stopPolling(){if(poller!=null)ui.removeCallbacks(poller);poller=null;}\n'
heartbeat_method = '''    private void heartbeatLocation(){
        if(!online||currentLocation==null)return;
        long now=System.currentTimeMillis();
        if(now-lastLocationHeartbeatAt<30000)return;
        lastLocationHeartbeatAt=now;
        Location loc=currentLocation;
        io.execute(()->{try{DriverRepository.updateLocation(token,loc.getLatitude(),loc.getLongitude(),loc.hasBearing()?loc.getBearing():null,loc.hasSpeed()?loc.getSpeed():null);}catch(Exception ignored){}});
    }
'''
if 'private void heartbeatLocation()' not in text:
    if method_anchor not in text:
        raise SystemExit('stopPolling não encontrado')
    text = text.replace(method_anchor, method_anchor + heartbeat_method, 1)

build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '1.2-prime'", build, count=1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Motorista v1.2 PRIME: heartbeat de localização a cada 30s e GPS sem distância mínima.')
