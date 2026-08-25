from pathlib import Path
import re

home_path=Path('app/src/main/java/com/clickgo/passageiro/PassengerHomeMap.java')
live_path=Path('app/src/main/java/com/clickgo/passageiro/PassengerLiveMap.java')
build_path=Path('app/build.gradle')
home=home_path.read_text(encoding='utf-8')
live=live_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.26 PRIME
# Tocar no carro/moto mostra a distância do motorista até o passageiro.

# HOME: adiciona posição do passageiro + cálculo Haversine.
old_head="<script>(function(){let map,me,marks={},failed=false,attempts=0;function icon(h,s){return L.divIcon({html:h,className:'',iconSize:[s,s],iconAnchor:[s/2,s/2]});}function boot(){"
new_head="<script>(function(){let map,me,mePos=null,marks={},failed=false,attempts=0;function icon(h,s){return L.divIcon({html:h,className:'',iconSize:[s,s],iconAnchor:[s/2,s/2]});}function km(a,b){if(!a||!b)return null;let R=6371,dlat=(b.lat-a.lat)*Math.PI/180,dlng=(b.lng-a.lng)*Math.PI/180,la1=a.lat*Math.PI/180,la2=b.lat*Math.PI/180;let h=Math.sin(dlat/2)*Math.sin(dlat/2)+Math.cos(la1)*Math.cos(la2)*Math.sin(dlng/2)*Math.sin(dlng/2);return 2*R*Math.asin(Math.min(1,Math.sqrt(h)));}function distText(p){if(!mePos)return 'Distância indisponível';let d=km({lat:mePos[0],lng:mePos[1]},{lat:p.lat,lng:p.lng});if(d==null)return 'Distância indisponível';return d<1?Math.max(1,Math.round(d*1000))+' m':d.toFixed(1).replace('.',',')+' km';}function boot(){"
if 'mePos=null' not in home:
    if old_head not in home: raise SystemExit('JS Home anchor não encontrado')
    home=home.replace(old_head,new_head,1)

if 'mePos=p;' not in home:
    needle='let p=[lat,lng];if(!me)me=L.marker'
    if needle not in home: raise SystemExit('posição do passageiro Home não encontrada')
    home=home.replace(needle,'let p=[lat,lng];mePos=p;if(!me)me=L.marker',1)

if 'Motorista CLICK-GO' not in home:
    needle='if(!marks[r.id])marks[r.id]=L.marker([r.lat,r.lng],{icon:icon(h,44)}).addTo(map);else{'
    repl='if(!marks[r.id]){let m=L.marker([r.lat,r.lng],{icon:icon(h,44)}).addTo(map);m.on(\'click\',function(){let d=distText(m.getLatLng());m.bindPopup(\\\"<b>Motorista CLICK-GO</b><br>\\\"+(d===\'Distância indisponível\'?d:d+\\\" de você\\\")).openPopup();});marks[r.id]=m;}else{'
    if needle not in home: raise SystemExit('marker de motorista Home não encontrado')
    home=home.replace(needle,repl,1)

# ACOMPANHAMENTO: distância usa localização atual do passageiro e, antes dela,
# o ponto de embarque como fallback.
old_live="<script>(function(){'use strict';let map,routeLayer,originMarker,destMarker,driverMarker,passengerMarker,lastDriver=null,failed=false,attempts=0;"
new_live="<script>(function(){'use strict';let map,routeLayer,originMarker,destMarker,driverMarker,passengerMarker,lastDriver=null,failed=false,attempts=0;function km(a,b){if(!a||!b)return null;let R=6371,dlat=(b.lat-a.lat)*Math.PI/180,dlng=(b.lng-a.lng)*Math.PI/180,la1=a.lat*Math.PI/180,la2=b.lat*Math.PI/180;let h=Math.sin(dlat/2)*Math.sin(dlat/2)+Math.cos(la1)*Math.cos(la2)*Math.sin(dlng/2)*Math.sin(dlng/2);return 2*R*Math.asin(Math.min(1,Math.sqrt(h)));}function driverDist(){let base=passengerMarker?passengerMarker.getLatLng():(originMarker?originMarker.getLatLng():null);if(!base||!driverMarker)return null;return km(base,driverMarker.getLatLng());}function driverDistText(){let d=driverDist();if(d==null)return 'Distância indisponível';return d<1?Math.max(1,Math.round(d*1000))+' m':d.toFixed(1).replace('.',',')+' km';}"
if 'driverDistText' not in live:
    if old_live not in live: raise SystemExit('JS Live anchor não encontrado')
    live=live.replace(old_live,new_live,1)

if '<b>Seu motorista</b>' not in live:
    needle='if(!driverMarker){driverMarker=L.marker(p,{icon:icon(h,46),zIndexOffset:900}).addTo(map);}else{'
    repl='if(!driverMarker){driverMarker=L.marker(p,{icon:icon(h,46),zIndexOffset:900}).addTo(map);driverMarker.on(\'click\',function(){let d=driverDistText();driverMarker.bindPopup(\\\"<b>Seu motorista</b><br>\\\"+(d===\'Distância indisponível\'?d:d+\\\" de você\\\")).openPopup();});}else{'
    if needle not in live: raise SystemExit('marker do motorista Live não encontrado')
    live=live.replace(needle,repl,1)

build=re.sub(r'versionCode\s+\d+','versionCode 226',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.26-prime'",build,count=1)
home_path.write_text(home,encoding='utf-8')
live_path.write_text(live,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.26 PRIME: distância ao tocar nos veículos aplicada.')
