from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Repositório autenticado: categorias da operação do próprio motorista.
if 'myCategories(String token)' not in repo:
    marker='    public static String userId(String token) throws Exception {'
    method='''    public static JSONArray myCategories(String token) throws Exception {\n        return new JSONArray(ApiClient.rpc("driver_my_categories", new JSONObject(), token));\n    }\n\n'''
    if marker not in repo: raise SystemExit('Ponto de inserção myCategories não encontrado')
    repo=repo.replace(marker,method+marker,1)

# Menu do motorista: categoria vira item próprio do painel.
old='        body.addView(menuLink("Perfil e veículo",()->showDriverProfile()));\n'
new='        body.addView(menuLink("Perfil e veículo",()->showDriverProfile()));\n        body.addView(menuLink("Categorias do veículo",()->showDriverCategories()));\n'
if old not in text: raise SystemExit('Item Perfil e veículo não encontrado no menu final')
text=text.replace(old,new,1)

# Tela somente leitura: quem cria/edita/atribui é o franqueado.
anchor='    private void showRideHistory(){\n'
method=r'''    private void showDriverCategories(){
        LinearLayout body=pageShell("Categorias do veículo","Categorias criadas pela sua franquia. A franquia define quais categorias você está autorizado a atender.");
        TextView loading=text("Carregando categorias…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,Color.WHITE));
        io.execute(()->{try{JSONArray rows=DriverRepository.myCategories(token);ui.post(()->{body.removeView(loading);if(rows.length()==0){body.addView(text("Nenhuma categoria configurada para sua cidade.",14,Color.DKGRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);if(c==null)continue;boolean assigned=c.optBoolean("assigned",false),active=c.optBoolean("category_active",false);LinearLayout card=card(Color.rgb(248,248,248),assigned?YELLOW:Color.rgb(225,225,225));card.addView(text(c.optString("category_name","Categoria CLICK-GO"),18,BLACK,true));String status=assigned&&active?"✓ LIBERADA PARA VOCÊ":active?"Disponível na operação · aguardando liberação da franquia":"Desativada pela franquia";card.addView(text(status,13,assigned&&active?Color.rgb(24,120,65):Color.DKGRAY,true));if(active){card.addView(space(6));card.addView(text("Base "+money(c.optDouble("base_fare",0))+" · "+money(c.optDouble("price_per_km",0))+"/km · "+money(c.optDouble("price_per_minute",0))+"/min",12,Color.DKGRAY,false));card.addView(text("Tarifa mínima "+money(c.optDouble("minimum_fare",0)),12,Color.DKGRAY,false));}body.addView(card);body.addView(space(9));}body.addView(text("Criação, edição e liberação de categorias são feitas pelo seu franqueado.",12,Color.DKGRAY,false));});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

'''
if anchor not in text: raise SystemExit('Âncora showRideHistory não encontrada')
if 'private void showDriverCategories()' not in text:text=text.replace(anchor,method+anchor,1)

if 'Categorias do veículo' not in text or 'driver_my_categories' not in repo:
    raise SystemExit('Painel de categorias não aplicado por completo')

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.7-prime'",build,count=1)
main.write_text(text,encoding='utf-8');repo_path.write_text(repo,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v3.7 PRIME: painel exibe categorias dinâmicas controladas pelo franqueado.')
