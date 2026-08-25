from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.25 PRIME
# - mantém a busca digitada dentro do app e adiciona fallback nativo do Android;
# - restaura "Buscar no mapa" na tela de destino, sem abrir navegador/app externo;
# - reduz guardas frágeis de View que podiam descartar uma resposta HTTP 200 válida;
# - adiciona smoke real de endereço para o CI.

# 1) Smoke de rede real: abre a tela de destino e digita automaticamente um endereço conhecido.
address_smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_smoke",false)){token="address-smoke";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Centro, Uruaçu - GO";showDestinationSearch();return;}'
network_address_smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_network_smoke",false)){token="address-network-smoke";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Centro, Uruaçu - GO";showDestinationSearch();return;}'
if 'clickgo_address_network_smoke' not in text:
    if address_smoke not in text:
        raise SystemExit('anchor do smoke de endereço não encontrado')
    text = text.replace(address_smoke, address_smoke + '\n        ' + network_address_smoke, 1)

# 2) Botão Buscar no mapa permanece no próprio app.
anchor = '''        TextView helper=text("Digite pelo menos 3 letras. Os endereços encontrados aparecerão abaixo.",13,GRAY,false);\n        helper.setPadding(dp(4),dp(9),dp(4),dp(7));\n        screen.addView(helper,lpMatchWrap());\n\n        LinearLayout results=vertical(Color.WHITE);\n'''
replacement = '''        TextView helper=text("Digite pelo menos 3 letras. Os endereços encontrados aparecerão abaixo.",13,GRAY,false);\n        helper.setPadding(dp(4),dp(9),dp(4),dp(7));\n        screen.addView(helper,lpMatchWrap());\n\n        Button mapSearch=secondaryLight("🗺 Buscar no mapa");\n        mapSearch.setContentDescription("clickgo_search_on_map");\n        screen.addView(mapSearch,lpMatch(dp(54)));\n        screen.addView(space(8));\n\n        LinearLayout results=vertical(Color.WHITE);\n'''
if anchor not in text:
    raise SystemExit('ponto do botão Buscar no mapa não encontrado')
text = text.replace(anchor, replacement, 1)

click_anchor = '''        back.setOnClickListener(v->showHome());\n        destInput.addTextChangedListener(new TextWatcher(){\n'''
click_replacement = '''        back.setOnClickListener(v->showHome());\n        mapSearch.setOnClickListener(v->{\n            cancelAddressSearch();\n            hideKeyboard();\n            showMapPicker(false,null);\n        });\n        destInput.addTextChangedListener(new TextWatcher(){\n'''
if click_anchor not in text:
    raise SystemExit('clique da tela de destino não encontrado')
text = text.replace(click_anchor, click_replacement, 1)

# 3) O smoke antigo continua visual; o novo smoke usa a API real.
smoke_block = '''        boolean smoke=BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_smoke",false);\n        if(smoke){\n            destInput.setText("Avenida Tocantins");\n            cancelAddressSearch();\n            List<SearchItem> demo=new ArrayList<>();\n            demo.add(new SearchItem("Avenida Tocantins, Centro, Uruaçu - GO","Avenida Tocantins","Centro, Uruaçu - GO","address",-14.52390,-49.13910));\n            demo.add(new SearchItem("Avenida Tocantins, Setor Central, Uruaçu - GO","Avenida Tocantins","Setor Central, Uruaçu - GO","address",-14.52610,-49.14180));\n            demo.add(new SearchItem("Avenida Tocantins, Uruaçu - Goiás","Avenida Tocantins","Uruaçu - Goiás","address",-14.52080,-49.13670));\n            renderSearchResults(demo,results,false,null,null);\n        }else{\n            destInput.requestFocus();\n        }\n'''
smoke_replacement = '''        boolean smoke=BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_smoke",false);\n        boolean networkSmoke=BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_network_smoke",false);\n        if(smoke){\n            destInput.setText("Avenida Tocantins");\n            cancelAddressSearch();\n            List<SearchItem> demo=new ArrayList<>();\n            demo.add(new SearchItem("Avenida Tocantins, Centro, Uruaçu - GO","Avenida Tocantins","Centro, Uruaçu - GO","address",-14.52390,-49.13910));\n            demo.add(new SearchItem("Avenida Tocantins, Setor Central, Uruaçu - GO","Avenida Tocantins","Setor Central, Uruaçu - GO","address",-14.52610,-49.14180));\n            demo.add(new SearchItem("Avenida Tocantins, Uruaçu - Goiás","Avenida Tocantins","Uruaçu - Goiás","address",-14.52080,-49.13670));\n            renderSearchResults(demo,results,false,null,null);\n        }else if(networkSmoke){\n            destInput.setText("Avenida Tocantins");\n            destInput.setSelection(destInput.length());\n        }else{\n            destInput.requestFocus();\n        }\n'''
if smoke_block not in text:
    raise SystemExit('smoke da tela de endereço não encontrado')
text = text.replace(smoke_block, smoke_replacement, 1)

# 4) Busca real: endpoint CLICK-GO primeiro; se houver qualquer falha ou resposta vazia,
# usa Geocoder nativo do Android. A UI recebe a resposta enquanto a tela ainda pertence ao fluxo.
pattern = r'''    private void startAddressSearch\(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog, int seq\) \{.*?\n    \}\n\n(?=    private void renderSearchResults)'''
new_method = r'''    private void startAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog, int seq) {
        final double biasLat=origin==null?Double.NaN:origin.getLatitude();
        final double biasLng=origin==null?Double.NaN:origin.getLongitude();
        addressFuture=addressIo.submit(()->{
            List<SearchItem> items=new ArrayList<>();
            String failure="";
            try{
                StringBuilder url=new StringBuilder(BuildConfig.GEOCODE_URL)
                        .append("?q=").append(URLEncoder.encode(query,StandardCharsets.UTF_8.toString()));
                if(Double.isFinite(biasLat)&&Double.isFinite(biasLng)){
                    url.append("&lat=").append(biasLat).append("&lng=").append(biasLng);
                }
                JSONObject root=new JSONObject(ApiClient.absoluteGet(url.toString()));
                JSONArray rows=root.optJSONArray("results");
                Set<String> seen=new HashSet<>();
                if(rows!=null){
                    for(int i=0;i<rows.length()&&items.size()<7;i++){
                        JSONObject row=rows.optJSONObject(i);
                        if(row==null)continue;
                        String label=cleanLabel(row.optString("label",""));
                        String name=cleanLabel(row.optString("name",""));
                        String subtitle=cleanLabel(row.optString("subtitle",""));
                        String kind=row.optString("kind","address");
                        double lat=row.optDouble("lat",Double.NaN);
                        double lng=row.optDouble("lng",Double.NaN);
                        if(label.isBlank()||!Double.isFinite(lat)||!Double.isFinite(lng))continue;
                        String key=label.toLowerCase(Locale.ROOT).replaceAll("\\s+"," ");
                        if(seen.add(key))items.add(new SearchItem(label,name,subtitle,kind,lat,lng));
                    }
                }
            }catch(Exception e){
                failure=message(e);
            }

            if(items.isEmpty()){
                items.addAll(nativeAddressFallback(query,biasLat,biasLng));
            }

            final List<SearchItem> finalItems=new ArrayList<>(items);
            final String finalFailure=failure;
            ui.post(()->{
                if(destroyed||isFinishing()||seq!=searchSeq||target.getParent()==null)return;
                if(dialog!=null&&!dialog.isShowing())return;
                renderSearchResults(finalItems,target,forOrigin,originView,dialog);
                if(finalItems.isEmpty()&&!finalFailure.isBlank()){
                    TextView error=text("A busca online não respondeu. Você pode tentar novamente ou usar Buscar no mapa.",13,Color.rgb(170,60,40),false);
                    error.setPadding(dp(10),dp(6),dp(10),dp(10));
                    target.addView(error,lpMatchWrap());
                }
            });
        });
    }

    private List<SearchItem> nativeAddressFallback(String query,double biasLat,double biasLng){
        List<SearchItem> items=new ArrayList<>();
        try{
            if(!Geocoder.isPresent())return items;
            Geocoder geocoder=new Geocoder(this,new Locale("pt","BR"));
            String nativeQuery=query==null?"":query.trim();
            if(originSearchContext!=null&&!originSearchContext.isBlank()){
                String low=nativeQuery.toLowerCase(Locale.ROOT);
                String ctxLow=originSearchContext.toLowerCase(Locale.ROOT);
                if(!low.contains(ctxLow))nativeQuery=nativeQuery+", "+originSearchContext;
            }
            List<Address> addresses;
            if(Double.isFinite(biasLat)&&Double.isFinite(biasLng)){
                addresses=geocoder.getFromLocationName(nativeQuery,7,biasLat-0.40,biasLng-0.40,biasLat+0.40,biasLng+0.40);
            }else{
                addresses=geocoder.getFromLocationName(nativeQuery,7);
            }
            if(addresses==null)return items;
            Set<String> seen=new HashSet<>();
            for(Address address:addresses){
                if(address==null||!address.hasLatitude()||!address.hasLongitude())continue;
                String label="";
                try{if(address.getMaxAddressLineIndex()>=0)label=cleanLabel(address.getAddressLine(0));}catch(Exception ignored){}
                if(label.isBlank())label=cleanLabel(shortAddress(address));
                if(label.isBlank())continue;
                String key=label.toLowerCase(Locale.ROOT).replaceAll("\\s+"," ");
                if(!seen.add(key))continue;
                String name=safe(address.getThoroughfare());
                if(name.isBlank())name=label;
                String subtitle=shortAddress(address);
                items.add(new SearchItem(label,name,subtitle,"address",address.getLatitude(),address.getLongitude()));
                if(items.size()>=7)break;
            }
        }catch(Exception ignored){}
        return items;
    }

'''
text, n = re.subn(pattern, new_method, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('startAddressSearch final não encontrado')

# 5) Não descarta a resposta apenas porque isAttachedToWindow oscilou durante teclado/insets.
text = text.replace(
    'if(destroyed||isFinishing()||!target.isAttachedToWindow())return;\n        target.removeAllViews();',
    'if(destroyed||isFinishing()||target.getParent()==null)return;\n        target.removeAllViews();',
    1
)

# 6) Ao sair do seletor de mapa de destino, volta para a busca dentro do app.
old_back = 'back.setOnClickListener(v -> { picker.onDetach(); showHome(); });'
new_back = 'back.setOnClickListener(v -> { picker.onDetach(); if(forOrigin)showHome(); else showDestinationSearch(); });'
if old_back not in text:
    raise SystemExit('voltar do seletor de mapa não encontrado')
text = text.replace(old_back, new_back, 1)

if 'clickgo_search_on_map' not in text or 'nativeAddressFallback' not in text or 'clickgo_address_network_smoke' not in text:
    raise SystemExit('marcadores v2.25 não aplicados')

build = re.sub(r'versionCode\s+\d+', 'versionCode 225', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.25-prime'", build, count=1)
main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.25 PRIME: busca real + fallback nativo + Buscar no mapa interno aplicados.')
