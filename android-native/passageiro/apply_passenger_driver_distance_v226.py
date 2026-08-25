from pathlib import Path
import re

home_path=Path('app/src/main/java/com/clickgo/passageiro/PassengerHomeMap.java')
live_path=Path('app/src/main/java/com/clickgo/passageiro/PassengerLiveMap.java')
build_path=Path('app/build.gradle')
home=home_path.read_text(encoding='utf-8')
live=live_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.26 PRIME
# - tocar em qualquer carro/moto online da Home mostra a distância até o passageiro;
# - durante a corrida, tocar no veículo do motorista mostra a distância até o passageiro;
# - cálculo é local (Haversine), sem nova chamada de API e sem sair do app.

old_home="""<script>(function(){let map,me,marks={},failed=false,attempts=0;function icon(h,s){return L.divIcon({html:h,className:'',iconSize:[s,s],iconAnchor:[s/2,s/2]});}function boot(){"""
new_home="""<script>(function(){let map,me,mePos=null,marks={},failed=false,attempts=0;function icon(h,s){return L.divIcon({html:h,className:'',iconSize:[s,s],iconAnchor:[s/2,s/2]});}function km(a,b){if(!a||!b)return null;let R=6371,dlat=(b.lat-a.lat)*Math.PI/180,dlng=(b.lng-a.lng)*Math.PI/180,la1=a.lat*Math.PI/180,la2=b.lat*Math.PI/180;let h=Math.sin(dlat/2)*Math.sin(dlat/2)+Math.cos(la1)*Math.cos(la2)*Math.sin(dlng/2)*Math.sin(dlng/2);return 2*R*Math.asin(Math.min(1,Math.sqrt(h)));}function distText(p){if(!mePos)return 'Distância indisponível';let d=km({lat:mePos[0],lng:mePos[1]},{lat:p.lat,lng:p.lng});if(d==null)return 'Distância indisponível';return d<1?Math.max(1,Math.round(d*1000))+' m':d.toFixed(1).replace('.',',')+' km';}function boot(){"""
if old_home not in home: raise SystemExit('JS Home anchor não encontrado')
home=home.replace(old_home,new_home,1)

old_passenger="""window.cgPassenger=function(lat,lng){if(failed)return;if(!map){setTimeout(function(){cgPassenger(lat,lng)},120);return;}let p=[lat,lng];if(!me)me=L.marker(p,{icon:icon(\"<div class='me'></div>\",28),zIndexOffset:1000}).addTo(map);else me.setLatLng(p);map.setView(p,15,{animate:false});};"""
new_passenger="""window.cgPassenger=function(lat,lng){if(failed)return;if(!map){setTimeout(function(){cgPassenger(lat,lng)},120);return;}let p=[lat,lng];mePos=p;if(!me)me=L.marker(p,{icon:icon(\"<div class='me'></div>\",28),zIndexOffset:1000}).addTo(map);else me.setLatLng(p);map.setView(p,15,{animate:false});};"""
if old_passenger not in home: raise SystemExit('cgPassenger Home não encontrado')
home=home.replace(old_passenger,new_passenger,1)

old_drivers="""window.cgDrivers=function(rows){if(failed||!map)return;let seen={};(rows||[]).forEach(function(r){seen[r.id]=1;let e=r.kind==='moto'?'🏍':'🚗',h=\"<div class='car'>\"+e+\"</div>\";if(!marks[r.id])marks[r.id]=L.marker([r.lat,r.lng],{icon:icon(h,44)}).addTo(map);else{marks[r.id].setLatLng([r.lat,r.lng]);marks[r.id].setIcon(icon(h,44));}});Object.keys(marks).forEach(function(k){if(!seen[k]){map.removeLayer(marks[k]);delete marks[k];}});};"""
new_drivers="""window.cgDrivers=function(rows){if(failed||!map)return;let seen={};(rows||[]).forEach(function(r){seen[r.id]=1;let e=r.kind==='moto'?'🏍':'🚗',h=\"<div class='car'>\"+e+\"</div>\";if(!marks[r.id]){let m=L.marker([r.lat,r.lng],{icon:icon(h,44)}).addTo(map);m.on('click',function(){let d=distText(m.getLatLng());m.bindPopup(\"<b>Motorista CLICK-GO</b><br>\"+(d==='Distância indisponível'?d:d+\" de você\")).openPopup();});marks[r.id]=m;}else{marks[r.id].setLatLng([r.lat,r.lng]);marks[r.id].setIcon(icon(h,44));}});Object.keys(marks).forEach(function(k){if(!seen[k]){map.removeLayer(marks[k]);delete marks[k];}});};"""
if old_drivers not in home: raise SystemExit('cgDrivers Home não encontrado')
home=home.replace(old_drivers,new_drivers,1)

# Live tracking: distância usa a localização atual do passageiro; se ainda não chegou,
# usa o ponto de embarque como fallback.
old_live_head="""<script>(function(){'use strict';let map,routeLayer,originMarker,destMarker,driverMarker,passengerMarker,lastDriver=null,failed=false,attempts=0;"""
new_live_head="""<script>(function(){'use strict';let map,routeLayer,originMarker,destMarker,driverMarker,passengerMarker,lastDriver=null,failed=false,attempts=0;function km(a,b){if(!a||!b)return null;let R=6371,dlat=(b.lat-a.lat)*Math.PI/180,dlng=(b.lng-a.lng)*Math.PI/180,la1=a.lat*Math.PI/180,la2=b.lat*Math.PI/180;let h=Math.sin(dlat/2)*Math.sin(dlat/2)+Math.cos(la1)*Math.cos(la2)*Math.sin(dlng/2)*Math.sin(dlng/2);return 2*R*Math.asin(Math.min(1,Math.sqrt(h)));}function driverDist(){let base=passengerMarker?passengerMarker.getLatLng():(originMarker?originMarker.getLatLng():null);if(!base||!driverMarker)return null;return km(base,driverMarker.getLatLng());}function driverDistText(){let d=driverDist();if(d==null)return 'Distância indisponível';return d<1?Math.max(1,Math.round(d*1000))+' m':d.toFixed(1).replace('.',',')+' km';}"""
if old_live_head not in live: raise SystemExit('JS Live anchor não encontrado')
live=live.replace(old_live_head,new_live_head,1)

old_live_driver="""let p=[lat,lng];if(!driverMarker){driverMarker=L.marker(p,{icon:icon(h,46),zIndexOffset:900}).addTo(map);}else{driverMarker.setLatLng(p);driverMarker.setIcon(icon(h,46));}lastDriver=p;};"""
new_live_driver="""let p=[lat,lng];if(!driverMarker){driverMarker=L.marker(p,{icon:icon(h,46),zIndexOffset:900}).addTo(map);driverMarker.on('click',function(){let d=driverDistText();driverMarker.bindPopup(\"<b>Seu motorista</b><br>\"+(d==='Distância indisponível'?d:d+\" de você\")).openPopup();});}else{driverMarker.setLatLng(p);driverMarker.setIcon(icon(h,46));}lastDriver=p;};"""
if old_live_driver not in live: raise SystemExit('cgSetDriver Live não encontrado')
live=live.replace(old_live_driver,new_live_driver,1)

build=re.sub(r'versionCode\s+\d+','versionCode 226',build,count=1)
build=re.sub(r"versionName\s+'[^']+'","versionName '2.26-prime'",build,count=1)
home_path.write_text(home,encoding='utf-8')
live_path.write_text(live,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.26 PRIME: distância ao tocar nos veículos aplicada.')
