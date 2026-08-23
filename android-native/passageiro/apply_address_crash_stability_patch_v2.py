from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
text=path.read_text(encoding='utf-8')

def sub(pattern,replacement,label):
    global text
    text,n=re.subn(pattern,replacement,text,count=1,flags=re.S)
    if n!=1: raise SystemExit(f'Patch não encontrou: {label}')

# Não reutiliza Marker entre MapViews diferentes.
old='''        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n\n        FrameLayout root = new FrameLayout(this);\n'''
new='''        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n        homePassengerMarker = null;\n        activeDriverMarker = null;\n\n        FrameLayout root = new FrameLayout(this);\n'''
if old not in text: raise SystemExit('Estado do mapa inicial não encontrado')
text=text.replace(old,new,1)

old='''    private void showDestinationSearch() {\n        homeMapMode=false;\n        stopHomeDriverPolling();\n'''
new='''    private void showDestinationSearch() {\n        homeMapMode=false;\n        stopHomeDriverPolling();\n        homePassengerMarker=null;\n        activeDriverMarker=null;\n        homeDriverMarkers.clear();\n        optionDriverMarkers.clear();\n'''
if old not in text: raise SystemExit('Entrada da busca de destino não encontrada')
text=text.replace(old,new,1)

old='''    private void showOptions() {\n        cancelAddressSearch();\n        hideKeyboard();\n        releaseMap();\n'''
new='''    private void showOptions() {\n        cancelAddressSearch();\n        hideKeyboard();\n        releaseMap();\n        optionDriverMarkers.clear();\n        activeDriverMarker=null;\n'''
if old not in text: raise SystemExit('showOptions seguro não encontrado')
text=text.replace(old,new,1)

# Busca com debounce curto e sem tocar em Views que já saíram da tela.
pattern=r'''    private void scheduleAddressSearch\(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog\) \{.*?\n    \}\n\n    private void startAddressSearch'''
replacement=r'''    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        final int seq=++searchSeq;
        if(pendingAddressSearch!=null){ui.removeCallbacks(pendingAddressSearch);pendingAddressSearch=null;}
        String normalized=query==null?"":query.trim();
        if(normalized.length()<3){if(target.isAttachedToWindow())target.removeAllViews();return;}
        if(normalized.length()>120)normalized=normalized.substring(0,120);
        final String safeQuery=normalized;
        pendingAddressSearch=()->{
            if(destroyed||isFinishing()||seq!=searchSeq||!target.isAttachedToWindow())return;
            target.removeAllViews();
            TextView loading=text("Buscando endereços próximos…",13,GRAY,false);
            loading.setPadding(dp(8),dp(10),dp(8),dp(6));
            target.addView(loading,lpMatchWrap());
            startAddressSearch(safeQuery,target,forOrigin,originView,dialog,seq);
        };
        ui.postDelayed(pendingAddressSearch,550);
    }

    private void startAddressSearch'''
sub(pattern,replacement,'debounce endereço')

# Envia a posição atual para regionalizar os resultados e descarta respostas antigas.
pattern=r'''    private void startAddressSearch\(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog, int seq\) \{.*?\n    \}\n\n    private void renderSearchResults'''
replacement=r'''    private void startAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog, int seq) {
        final double biasLat=origin==null?Double.NaN:origin.getLatitude();
        final double biasLng=origin==null?Double.NaN:origin.getLongitude();
        addressFuture=addressIo.submit(()->{
            try{
                if(destroyed||seq!=searchSeq)return;
                StringBuilder url=new StringBuilder(BuildConfig.GEOCODE_URL)
                        .append("?q=").append(URLEncoder.encode(query,StandardCharsets.UTF_8.toString()));
                if(Double.isFinite(biasLat)&&Double.isFinite(biasLng)){
                    url.append("&lat=").append(biasLat).append("&lng=").append(biasLng);
                }
                JSONObject root=new JSONObject(ApiClient.absoluteGet(url.toString()));
                JSONArray rows=root.optJSONArray("results");
                List<SearchItem> items=new ArrayList<>();
                Set<String> seen=new HashSet<>();
                if(rows!=null){
                    for(int i=0;i<rows.length()&&items.size()<6;i++){
                        JSONObject row=rows.optJSONObject(i);if(row==null)continue;
                        String label=cleanLabel(row.optString("label",""));
                        double lat=row.optDouble("lat",Double.NaN),lng=row.optDouble("lng",Double.NaN);
                        if(label.isBlank()||!Double.isFinite(lat)||!Double.isFinite(lng))continue;
                        String key=label.toLowerCase(Locale.ROOT).replaceAll("\\s+"," ");
                        if(seen.add(key))items.add(new SearchItem(label,lat,lng));
                    }
                }
                ui.post(()->{
                    if(destroyed||isFinishing()||seq!=searchSeq||!target.isAttachedToWindow())return;
                    if(dialog!=null&&!dialog.isShowing())return;
                    renderSearchResults(items,target,forOrigin,originView,dialog);
                });
            }catch(Exception e){
                ui.post(()->{
                    if(destroyed||isFinishing()||seq!=searchSeq||!target.isAttachedToWindow())return;
                    target.removeAllViews();
                    TextView error=text("Não foi possível buscar agora. Verifique a internet e tente novamente.",13,GRAY,false);
                    error.setPadding(dp(8),dp(10),dp(8),dp(8));
                    target.addView(error,lpMatchWrap());
                });
            }
        });
    }

    private void renderSearchResults'''
sub(pattern,replacement,'busca regionalizada')

# Seleção de endereço e troca para opções protegidas contra tela/mapa já descartados.
pattern=r'''    private void renderSearchResults\(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog\) \{.*?\n    \}\n\n    private String cleanLabel'''
replacement=r'''    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        if(destroyed||isFinishing()||!target.isAttachedToWindow())return;
        target.removeAllViews();
        if(items==null||items.isEmpty()){
            TextView empty=text("Nenhum endereço próximo encontrado. Digite rua, número ou ponto de referência.",13,GRAY,false);
            empty.setPadding(dp(8),dp(10),dp(8),dp(8));target.addView(empty,lpMatchWrap());return;
        }
        for(SearchItem item:items){
            TextView row=text(item.label,14,BLACK,false);row.setMaxLines(2);row.setEllipsize(TextUtils.TruncateAt.END);row.setGravity(Gravity.CENTER_VERTICAL);row.setPadding(dp(14),dp(10),dp(14),dp(10));row.setBackground(round(Color.WHITE,12,Color.rgb(230,230,230)));
            row.setOnClickListener(v->{
                if(destroyed||isFinishing())return;
                if(!Double.isFinite(item.lat)||!Double.isFinite(item.lng)){toast("Endereço inválido. Escolha outro resultado.");return;}
                cancelAddressSearch();hideKeyboard();
                if(forOrigin){
                    origin=new GeoPoint(item.lat,item.lng);originLabel=item.label;if(originView!=null&&originView.isAttachedToWindow())originView.setText(item.label);if(dialog!=null&&dialog.isShowing())dialog.dismiss();
                }else{
                    destination=new GeoPoint(item.lat,item.lng);destinationLabel=item.label;
                    ui.post(this::openRideOptionsSafely);
                }
            });
            target.addView(row,lpMatchWrap());target.addView(space(6));
        }
    }

    private void openRideOptionsSafely(){
        if(destroyed||isFinishing())return;
        if(origin==null){toast("Não foi possível identificar o local de embarque.");showDestinationSearch();return;}
        if(destination==null){toast("Escolha um destino válido.");return;}
        try{showOptions();}
        catch(RuntimeException e){
            releaseMap();
            toast("Não foi possível abrir a rota. Tente escolher o destino novamente.");
            ui.postDelayed(this::showDestinationSearch,120);
        }
    }

    private String cleanLabel'''
sub(pattern,replacement,'resultado de endereço seguro')

# O patch de estabilidade anterior já implementa cancelamento cancel(false) e searchSeq.
# Mantemos esse código para evitar conflito entre patches.

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.1-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Passageiro v2.1 PRIME: busca regionalizada e transições estabilizadas.')
