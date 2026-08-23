from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

# Cada MapView recebe markers novos. Um Marker do osmdroid não deve ser reaproveitado
# depois que o MapView anterior passou por onDetach().
old='''        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n\n        FrameLayout root = new FrameLayout(this);\n'''
new='''        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n        homePassengerMarker = null;\n        activeDriverMarker = null;\n\n        FrameLayout root = new FrameLayout(this);\n'''
if old not in text: raise SystemExit('home map state não encontrado')
text=text.replace(old,new,1)

# Ao sair da home para pesquisar endereço, solta referências de overlays do mapa anterior.
old='''    private void showDestinationSearch() {\n        homeMapMode=false;\n        stopHomeDriverPolling();\n'''
new='''    private void showDestinationSearch() {\n        homeMapMode=false;\n        stopHomeDriverPolling();\n        homePassengerMarker=null;\n        activeDriverMarker=null;\n        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n'''
if old not in text: raise SystemExit('showDestinationSearch não encontrado')
text=text.replace(old,new,1)

# Ao criar o mapa de categorias/rota, não carrega nenhum marker preso ao mapa anterior.
old='''    private void showOptions() {\n        cancelAddressSearch();\n        hideKeyboard();\n        releaseMap();\n'''
new='''    private void showOptions() {\n        cancelAddressSearch();\n        hideKeyboard();\n        releaseMap();\n        homePassengerMarker=null;\n        activeDriverMarker=null;\n        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n'''
if old not in text: raise SystemExit('showOptions não encontrado')
text=text.replace(old,new,1)

# A busca existente já possui debounce, searchSeq, lat/lng/contexto regional e proteção
# de View anexada. Apenas endurecemos a transição ao tocar em um destino.
old='''                } else {\n                    destination = new GeoPoint(item.lat, item.lng);\n                    destinationLabel = item.label;\n                    showOptions();\n                }\n'''
new='''                } else {\n                    destination = new GeoPoint(item.lat, item.lng);\n                    destinationLabel = item.label;\n                    homePassengerMarker=null;\n                    activeDriverMarker=null;\n                    homeDriverMarkers.clear();\n                    optionDriverMarkers.clear();\n                    ui.post(() -> {\n                        if (destroyed || isFinishing()) return;\n                        try {\n                            showOptions();\n                        } catch (RuntimeException ex) {\n                            releaseMap();\n                            toast("Não foi possível abrir a rota agora. Tente escolher o destino novamente.");\n                            ui.postDelayed(this::showDestinationSearch, 120);\n                        }\n                    });\n                }\n'''
if old not in text: raise SystemExit('clique no resultado não encontrado')
text=text.replace(old,new,1)

# Limita o texto pesquisado para evitar payloads extremos e mantém o debounce existente.
old='''    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {\n        final int seq = ++searchSeq;\n        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);\n        if (query.length() < 3) {\n'''
new='''    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {\n        query = query == null ? "" : query.trim();\n        if (query.length() > 120) query = query.substring(0, 120);\n        final String safeQuery = query;\n        final int seq = ++searchSeq;\n        if (pendingAddressSearch != null) ui.removeCallbacks(pendingAddressSearch);\n        if (safeQuery.length() < 3) {\n'''
if old not in text: raise SystemExit('scheduleAddressSearch não encontrado')
text=text.replace(old,new,1)
# Dentro do runnable usa a cópia final, necessária para lambda e para impedir alteração.
needle='''            startAddressSearch(query, target, forOrigin, originView, dialog, seq);\n'''
if needle not in text: raise SystemExit('startAddressSearch do debounce não encontrado')
text=text.replace(needle,'''            startAddressSearch(safeQuery, target, forOrigin, originView, dialog, seq);\n''',1)

# Versão da correção.
build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.1-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.1 PRIME: ciclo de mapa e transição de endereço estabilizados.')
