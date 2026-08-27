from pathlib import Path
import re

root = Path('app')
main_path = root / 'src/main/java/com/clickgo/motorista/MainActivity.java'
repo_path = root / 'src/main/java/com/clickgo/motorista/DriverRepository.java'
build_path = root / 'build.gradle'

text = main_path.read_text(encoding='utf-8')
repo = repo_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

def replace_once(old, new, label):
    global text
    if old not in text:
        nearby = '\n'.join(line for line in text.splitlines() if any(k in line for k in ('Tipo do veículo','activeSignupFranchises','vehicleTypeValue','franchiseIds')))
        raise SystemExit(f'{label} não encontrado. Trechos relacionados:\n{nearby[:5000]}')
    text = text.replace(old, new, 1)

# Repositório: categorias públicas/ativas disponíveis para cadastro. O app filtra
# por franquia/cidade selecionada antes de mostrar ao motorista.
if 'activeSignupCategories()' not in repo:
    marker = '    public static String userId(String token) throws Exception {'
    method = '''    public static JSONArray activeSignupCategories() throws Exception {\n        return new JSONArray(ApiClient.publicRpc("list_driver_signup_categories", new JSONObject()));\n    }\n\n'''
    if marker not in repo:
        raise SystemExit('Ponto de inserção para activeSignupCategories não encontrado')
    repo = repo.replace(marker, method + marker, 1)

# O cadastro final já contém seleção de franquia/cidade. Logo abaixo dela,
# adiciona a categoria real da operação (Econômico, Conforto, Moto, Premium etc.).
category_anchor = '        final List<String> franchiseIds=new ArrayList<>();\n'
category_ui = '''        final List<String> franchiseIds=new ArrayList<>();\n        body.addView(text("Categoria do veículo",14,YELLOW,true));body.addView(space(6));\n        Spinner category=new Spinner(this);ArrayAdapter<String> categoryAdapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new ArrayList<>());category.setAdapter(categoryAdapter);body.addView(category,match(dp(58)));body.addView(text("A lista acompanha as categorias ativas configuradas pela franquia para a cidade escolhida.",12,GRAY,false));body.addView(space(10));\n        final List<String> categoryIds=new ArrayList<>();final List<String> categoryVehicleTypes=new ArrayList<>();final JSONArray[] categoryRowsRef=new JSONArray[]{new JSONArray()};\n'''
if category_anchor not in text:
    raise SystemExit('Âncora franchiseIds do cadastro final não encontrada')
text = text.replace(category_anchor, category_ui, 1)

# Remove somente o campo livre antigo; fazemos em partes para resistir a mudanças
# de formatação introduzidas pelos patches anteriores.
replace_once(',type=edit("Tipo do veículo: Carro ou Moto")', '', 'Campo livre Carro/Moto')
replace_once('new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,type,email,pass}', 'new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,email,pass}', 'Lista de campos com tipo antigo')

old_loader = '        camera.setOnClickListener(v->openProfileCamera(false));\n        io.execute(()->{try{JSONArray rows=DriverRepository.activeSignupFranchises();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();List<String> fids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);String cityName=c.optString("city_name");String state=c.optString("state");String franchiseName=c.optString("franchise_name","CLICK-GO");labels.add(cityName+"/"+state+" — "+franchiseName);ids.add(c.optString("city_id"));fids.add(c.optString("franchise_id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);franchiseIds.clear();franchiseIds.addAll(fids);submit.setEnabled(!ids.isEmpty()&&ids.size()==fids.size());if(ids.isEmpty())toast("Nenhuma franquia ativa está liberada para novos motoristas.");});}catch(Exception e){ui.post(()->toast("Não foi possível carregar as franquias/cidades."));}});\n'
new_loader = '''        camera.setOnClickListener(v->openProfileCamera(false));\n        final Runnable refreshCategories=()->{\n            categoryAdapter.clear();categoryIds.clear();categoryVehicleTypes.clear();\n            int selected=city.getSelectedItemPosition();\n            if(selected<0||selected>=cityIds.size()||selected>=franchiseIds.size()){submit.setEnabled(false);return;}\n            String selectedCity=cityIds.get(selected),selectedFranchise=franchiseIds.get(selected);JSONArray rows=categoryRowsRef[0];\n            for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);if(c==null)continue;if(!selectedCity.equals(c.optString("city_id"))||!selectedFranchise.equals(c.optString("franchise_id")))continue;categoryAdapter.add(c.optString("category_name","Categoria CLICK-GO"));categoryIds.add(c.optString("category_id"));categoryVehicleTypes.add(c.optString("required_vehicle_type",""));}\n            submit.setEnabled(!categoryIds.isEmpty());\n        };\n        city.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onItemSelected(android.widget.AdapterView<?> p,View v,int position,long id){refreshCategories.run();}public void onNothingSelected(android.widget.AdapterView<?> p){submit.setEnabled(false);}});\n        io.execute(()->{try{JSONArray rows=DriverRepository.activeSignupFranchises();JSONArray cats=DriverRepository.activeSignupCategories();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();List<String> fids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);String cityName=c.optString("city_name");String state=c.optString("state");String franchiseName=c.optString("franchise_name","CLICK-GO");labels.add(cityName+"/"+state+" — "+franchiseName);ids.add(c.optString("city_id"));fids.add(c.optString("franchise_id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);franchiseIds.clear();franchiseIds.addAll(fids);categoryRowsRef[0]=cats;submit.setEnabled(false);if(ids.isEmpty())toast("Nenhuma franquia ativa está liberada para novos motoristas.");else refreshCategories.run();});}catch(Exception e){ui.post(()->toast("Não foi possível carregar franquias e categorias."));}});\n'''
replace_once(old_loader, new_loader, 'Carregamento final de franquias')

old_validation = '''            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()||type.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios, incluindo se o veículo é Carro ou Moto.");return;}\n            String vehicleTypeValue=type.getText().toString().trim().toLowerCase(Locale.ROOT);\n            if(vehicleTypeValue.equals("carro")||vehicleTypeValue.equals("automovel")||vehicleTypeValue.equals("automóvel"))vehicleTypeValue="car";\n            else if(vehicleTypeValue.equals("moto")||vehicleTypeValue.equals("motocicleta"))vehicleTypeValue="motorcycle";\n            else if(!vehicleTypeValue.equals("car")&&!vehicleTypeValue.equals("motorcycle")){toast("No tipo do veículo, informe Carro ou Moto.");return;}\n'''
new_validation = '''            int categoryPos=category.getSelectedItemPosition();if(categoryPos<0||categoryPos>=categoryIds.size()||categoryPos>=categoryVehicleTypes.size()){toast("Escolha uma categoria de veículo disponível para esta franquia.");return;}\n            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios.");return;}\n            String vehicleTypeValue=categoryVehicleTypes.get(categoryPos);\n'''
replace_once(old_validation, new_validation, 'Validação Carro/Moto final')

old_meta = '.put("vehicle_color",color.getText().toString().trim()).put("vehicle_type",vehicleTypeValue);request.put("email",email.getText().toString().trim())'
new_meta = '.put("vehicle_color",color.getText().toString().trim()).put("requested_category_id",categoryIds.get(categoryPos)).put("vehicle_type",vehicleTypeValue);request.put("email",email.getText().toString().trim())'
replace_once(old_meta, new_meta, 'Metadado vehicle_type final')

if 'Tipo do veículo: Carro ou Moto' in text or 'No tipo do veículo, informe Carro ou Moto.' in text:
    raise SystemExit('Texto residual Carro/Moto encontrado após v3.6')
if 'list_driver_signup_categories' not in repo or 'requested_category_id' not in text or 'Categoria do veículo' not in text:
    raise SystemExit('Categorias dinâmicas não foram aplicadas por completo')

m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '3.6-prime'", build, count=1)

main_path.write_text(text, encoding='utf-8')
repo_path.write_text(repo, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Driver v3.6: cadastro usa categorias dinâmicas da franquia/cidade.')
