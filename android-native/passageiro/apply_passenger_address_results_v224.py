from pathlib import Path
import re

main_path = Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path = Path('app/build.gradle')
text = main_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# CLICK-GO Passageiro v2.24 PRIME
# - transforma a busca de destino em uma tela dedicada com área permanente para resultados;
# - mostra sugestões/endereço em cartões clicáveis logo abaixo da caixa de busca;
# - nunca avança para as opções sem toque explícito em um endereço válido;
# - adiciona smoke test visual de autocomplete sem depender da rede.

# Smoke de UI: abre diretamente a busca de destino e injeta resultados conhecidos.
network_smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_home_network_smoke",false)){token="network-smoke-invalid-token";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Localização de teste com serviços ativos";showHome();return;}'
address_smoke = 'if(BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_smoke",false)){token="address-smoke";origin=new GeoPoint(-14.52472,-49.14083);originLabel="Centro, Uruaçu - GO";showDestinationSearch();return;}'
if 'clickgo_address_smoke' not in text:
    if network_smoke not in text:
        raise SystemExit('anchor do smoke de home não encontrado')
    text = text.replace(network_smoke, network_smoke + '\n        ' + address_smoke, 1)

# A tela antiga era um formulário longo dentro de ScrollView e podia deixar a lista abaixo da
# área útil/teclado. Agora os resultados ocupam explicitamente todo o espaço restante da tela.
pattern = r'''    private void showDestinationSearch\(\) \{.*?\n    \}\n\n(?=    private void showOriginPicker\()'''
replacement = r'''    private void showDestinationSearch() {
        homeMapMode=false;
        stopHomeDriverPolling();
        stopPassengerLiveLocation();
        cancelAddressSearch();
        releaseMap();
        homePassengerMarker=null;
        activeDriverMarker=null;
        homeDriverMarkers.clear();
        optionDriverMarkers.clear();

        LinearLayout screen=vertical(LIGHT);
        screen.setPadding(dp(16),dp(14),dp(16),dp(12));
        screen.setContentDescription("clickgo_destination_search_screen");

        LinearLayout top=horizontal();
        top.setGravity(Gravity.CENTER_VERTICAL);
        Button back=circleButton("←",48);
        top.addView(back,new LinearLayout.LayoutParams(dp(50),dp(50)));
        TextView title=text("Para onde vamos?",24,BLACK,true);
        title.setPadding(dp(12),0,0,0);
        top.addView(title,new LinearLayout.LayoutParams(0,dp(50),1));
        screen.addView(top,lpMatch(dp(54)));
        screen.addView(space(12));

        EditText destInput=editLight("Digite rua, avenida, número ou local");
        destInput.setTextSize(17);
        destInput.setSingleLine(true);
        destInput.setContentDescription("clickgo_destination_input");
        screen.addView(destInput,lpMatch(dp(60)));

        TextView helper=text("Digite pelo menos 3 letras. Os endereços encontrados aparecerão abaixo.",13,GRAY,false);
        helper.setPadding(dp(4),dp(9),dp(4),dp(7));
        screen.addView(helper,lpMatchWrap());

        LinearLayout results=vertical(Color.WHITE);
        results.setPadding(dp(2),dp(2),dp(2),dp(12));
        results.setMinimumHeight(dp(300));
        results.setContentDescription("clickgo_destination_results");
        TextView initial=text("Comece digitando o destino para ver os endereços.",14,GRAY,false);
        initial.setPadding(dp(10),dp(16),dp(10),dp(16));
        results.addView(initial,lpMatchWrap());

        ScrollView resultScroll=new ScrollView(this);
        resultScroll.setFillViewport(true);
        resultScroll.setClipToPadding(false);
        resultScroll.addView(results,new ScrollView.LayoutParams(-1,-2));
        screen.addView(resultScroll,new LinearLayout.LayoutParams(-1,0,1));

        back.setOnClickListener(v->showHome());
        destInput.addTextChangedListener(new TextWatcher(){
            @Override public void beforeTextChanged(CharSequence s,int start,int count,int after){}
            @Override public void afterTextChanged(Editable s){}
            @Override public void onTextChanged(CharSequence s,int start,int before,int count){
                scheduleAddressSearch(s==null?"":s.toString(),results,false,null,null);
            }
        });

        setContentView(screen);
        applySafeInsets(screen);

        boolean smoke=BuildConfig.DEBUG&&getIntent()!=null&&getIntent().getBooleanExtra("clickgo_address_smoke",false);
        if(smoke){
            destInput.setText("Avenida Tocantins");
            cancelAddressSearch();
            List<SearchItem> demo=new ArrayList<>();
            demo.add(new SearchItem("Avenida Tocantins, Centro, Uruaçu - GO","Avenida Tocantins","Centro, Uruaçu - GO","address",-14.52390,-49.13910));
            demo.add(new SearchItem("Avenida Tocantins, Setor Central, Uruaçu - GO","Avenida Tocantins","Setor Central, Uruaçu - GO","address",-14.52610,-49.14180));
            demo.add(new SearchItem("Avenida Tocantins, Uruaçu - Goiás","Avenida Tocantins","Uruaçu - Goiás","address",-14.52080,-49.13670));
            renderSearchResults(demo,results,false,null,null);
        }else{
            destInput.requestFocus();
        }
    }

'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('showDestinationSearch final não encontrada')

# Mantém feedback sempre visível enquanto a pessoa digita e evita limpar a lista para uma tela branca.
pattern = r'''    private void scheduleAddressSearch\(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog\) \{.*?\n    \}\n\n(?=    private void startAddressSearch\()'''
replacement = r'''    private void scheduleAddressSearch(String query, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        final int seq=++searchSeq;
        if(pendingAddressSearch!=null){ui.removeCallbacks(pendingAddressSearch);pendingAddressSearch=null;}
        if(addressFuture!=null&&!addressFuture.isDone())addressFuture.cancel(false);
        String normalized=query==null?"":query.trim();
        if(normalized.length()>120)normalized=normalized.substring(0,120);
        target.removeAllViews();
        target.setVisibility(View.VISIBLE);
        if(normalized.length()<3){
            TextView hint=text("Digite pelo menos 3 letras para ver os endereços.",14,GRAY,false);
            hint.setPadding(dp(10),dp(16),dp(10),dp(16));
            target.addView(hint,lpMatchWrap());
            return;
        }
        final String safeQuery=normalized;
        TextView loading=text("Buscando endereços próximos…",14,GRAY,false);
        loading.setPadding(dp(10),dp(14),dp(10),dp(14));
        target.addView(loading,lpMatchWrap());
        pendingAddressSearch=()->{
            if(destroyed||isFinishing()||seq!=searchSeq||!target.isAttachedToWindow())return;
            startAddressSearch(safeQuery,target,forOrigin,originView,dialog,seq);
        };
        ui.postDelayed(pendingAddressSearch,220);
    }

'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('scheduleAddressSearch final não encontrada')

# Resultados claramente visíveis, separados em cartões e selecionados somente por toque explícito.
pattern = r'''    private void renderSearchResults\(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog\) \{.*?\n    \}\n\n(?=    private void )'''
replacement = r'''    private void renderSearchResults(List<SearchItem> items, LinearLayout target, boolean forOrigin, TextView originView, AlertDialog dialog) {
        if(destroyed||isFinishing()||!target.isAttachedToWindow())return;
        target.removeAllViews();
        target.setVisibility(View.VISIBLE);
        if(items==null||items.isEmpty()){
            TextView empty=text("Nenhum endereço encontrado. Tente rua, avenida, número, bairro ou ponto de referência.",14,GRAY,false);
            empty.setPadding(dp(10),dp(16),dp(10),dp(16));
            target.addView(empty,lpMatchWrap());
            return;
        }
        TextView heading=text(items.size()==1?"1 endereço encontrado":items.size()+" endereços encontrados",13,GRAY,true);
        heading.setPadding(dp(6),dp(8),dp(6),dp(8));
        target.addView(heading,lpMatchWrap());
        int index=0;
        for(SearchItem item:items){
            final int itemIndex=++index;
            LinearLayout row=horizontal();
            row.setGravity(Gravity.CENTER_VERTICAL);
            row.setPadding(dp(12),dp(9),dp(12),dp(9));
            row.setMinimumHeight(dp(68));
            row.setBackground(round(Color.WHITE,16,Color.rgb(224,224,224)));
            row.setClickable(true);
            row.setFocusable(true);
            row.setContentDescription("endereco_resultado_"+itemIndex+" "+item.label);
            TextView pin=text("●",18,ORANGE,true);
            pin.setGravity(Gravity.CENTER);
            row.addView(pin,new LinearLayout.LayoutParams(dp(34),dp(48)));
            TextView label=text(item.label,15,BLACK,false);
            label.setMaxLines(3);
            label.setEllipsize(TextUtils.TruncateAt.END);
            label.setGravity(Gravity.CENTER_VERTICAL);
            row.addView(label,new LinearLayout.LayoutParams(0,-2,1));
            row.setOnClickListener(v->{
                if(destroyed||isFinishing())return;
                if(!Double.isFinite(item.lat)||!Double.isFinite(item.lng)){toast("Endereço inválido. Escolha outro resultado.");return;}
                cancelAddressSearch();
                hideKeyboard();
                if(forOrigin){
                    origin=new GeoPoint(item.lat,item.lng);
                    originLabel=item.label;
                    if(originView!=null&&originView.isAttachedToWindow())originView.setText(item.label);
                    if(dialog!=null&&dialog.isShowing())dialog.dismiss();
                }else{
                    destination=new GeoPoint(item.lat,item.lng);
                    destinationLabel=item.label;
                    homePassengerMarker=null;
                    activeDriverMarker=null;
                    homeDriverMarkers.clear();
                    optionDriverMarkers.clear();
                    ui.post(()->{
                        if(destroyed||isFinishing())return;
                        try{showOptions();}
                        catch(RuntimeException ex){
                            releaseMap();
                            toast("Não foi possível abrir a rota agora. Escolha o destino novamente.");
                            ui.postDelayed(this::showDestinationSearch,120);
                        }
                    });
                }
            });
            target.addView(row,lpMatchWrap());
            target.addView(space(8));
        }
    }

'''
text, n = re.subn(pattern, replacement, text, count=1, flags=re.S)
if n != 1:
    raise SystemExit('renderSearchResults final não encontrada')

if 'clickgo_destination_results' not in text or 'endereços encontrados' not in text:
    raise SystemExit('marcadores de visibilidade de endereço não aplicados')

build = re.sub(r'versionCode\s+\d+', 'versionCode 224', build, count=1)
build = re.sub(r"versionName\s+'[^']+'", "versionName '2.24-prime'", build, count=1)
main_path.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Passageiro v2.24 PRIME: resultados de endereço sempre visíveis na tela.')
