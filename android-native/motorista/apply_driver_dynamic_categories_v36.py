from pathlib import Path
import re

root = Path('app')
main_path = root / 'src/main/java/com/clickgo/motorista/MainActivity.java'
repo_path = root / 'src/main/java/com/clickgo/motorista/DriverRepository.java'
build_path = root / 'build.gradle'

text = main_path.read_text(encoding='utf-8')
repo = repo_path.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# Repositório: categorias públicas e ativas disponíveis para cadastro, filtradas
# posteriormente pela franquia/cidade escolhida no app.
if 'activeSignupCategories()' not in repo:
    marker = '''    public static String userId(String token) throws Exception {\n'''
    method = '''    public static JSONArray activeSignupCategories() throws Exception {\n        return new JSONArray(ApiClient.publicRpc("list_driver_signup_categories", new JSONObject()));\n    }\n\n'''
    if marker not in repo:
        raise SystemExit('Ponto de inserção para activeSignupCategories não encontrado')
    repo = repo.replace(marker, method + marker, 1)

# Troca o campo livre Carro/Moto por uma lista de categorias reais da operação.
old_fields = '''        EditText name=edit("Nome completo"),phone=edit("Telefone / WhatsApp"),cpf=edit("CPF"),cnh=edit("Número da CNH"),cnhCat=edit("Categoria CNH"),plate=edit("Placa"),make=edit("Marca do veículo"),model=edit("Modelo"),year=edit("Ano"),color=edit("Cor"),type=edit("Tipo do veículo: Carro ou Moto"),email=edit("E-mail"),pass=edit("Senha (mínimo 6 caracteres)");\n        pass.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);pass.setTransformationMethod(PasswordTransformationMethod.getInstance());\n        for(EditText e:new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,type,email,pass}){body.addView(e,match(dp(58)));body.addView(space(8));}\n'''
new_fields = '''        body.addView(text("Categoria do veículo",14,YELLOW,true));body.addView(space(6));\n        Spinner category=new Spinner(this);ArrayAdapter<String> categoryAdapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new ArrayList<>());category.setAdapter(categoryAdapter);body.addView(category,match(dp(58)));body.addView(text("A lista acompanha as categorias ativas configuradas pela franquia para a cidade escolhida.",12,GRAY,false));body.addView(space(10));\n        final List<String> categoryIds=new ArrayList<>();final List<String> categoryVehicleTypes=new ArrayList<>();final JSONArray[] categoryRowsRef=new JSONArray[]{new JSONArray()};\n        EditText name=edit("Nome completo"),phone=edit("Telefone / WhatsApp"),cpf=edit("CPF"),cnh=edit("Número da CNH"),cnhCat=edit("Categoria CNH"),plate=edit("Placa"),make=edit("Marca do veículo"),model=edit("Modelo"),year=edit("Ano"),color=edit("Cor"),email=edit("E-mail"),pass=edit("Senha (mínimo 6 caracteres)");\n        pass.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);pass.setTransformationMethod(PasswordTransformationMethod.getInstance());\n        for(EditText e:new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,email,pass}){body.addView(e,match(dp(58)));body.addView(space(8));}\n'''
if old_fields not in text:
    raise SystemExit('Campos finais de cadastro Carro/Moto não encontrados')
text = text.replace(old_fields, new_fields, 1)

old_loader = '''        camera.setOnClickListener(v->openProfileCamera(false));\n        io.execute(()->{try{JSONArray rows=DriverRepository.activeSignupFranchises();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();List<String> fids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);String cityName=c.optString("city_name");String state=c.optString("state");String franchiseName=c.optString("franchise_name","CLICK-GO");labels.add(cityName+"/"+state+" — "+franchiseName);ids.add(c.optString("city_id"));fids.add(c.optString("franchise_id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);franchiseIds.clear();franchiseIds.addAll(fids);submit.setEnabled(!ids.isEmpty()&&ids.size()==fids.size());if(ids.isEmpty())toast("Nenhuma franquia ativa está liberada para novos motoristas.");});}catch(Exception e){ui.post(()->toast("Não foi possível carregar as franquias/cidades."));}});\n'''
new_loader = '''        camera.setOnClickListener(v->openProfileCamera(false));\n        final Runnable refreshCategories=()->{\n            categoryAdapter.clear();categoryIds.clear();categoryVehicleTypes.clear();\n            int selected=city.getSelectedItemPosition();\n            if(selected<0||selected>=cityIds.size()||selected>=franchiseIds.size()){submit.setEnabled(false);return;}\n            String selectedCity=cityIds.get(selected),selectedFranchise=franchiseIds.get(selected);JSONArray rows=categoryRowsRef[0];\n            for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);if(c==null)continue;if(!selectedCity.equals(c.optString("city_id"))||!selectedFranchise.equals(c.optString("franchise_id")))continue;categoryAdapter.add(c.optString("category_name","Categoria CLICK-GO"));categoryIds.add(c.optString("category_id"));categoryVehicleTypes.add(c.optString("required_vehicle_type",""));}\n            submit.setEnabled(!categoryIds.isEmpty());if(categoryIds.isEmpty())toast("Esta franquia ainda não possui categoria ativa para novos motoristas.");\n        };\n        city.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onItemSelected(android.widget.AdapterView<?> p,View v,int position,long id){refreshCategories.run();}public void onNothingSelected(android.widget.AdapterView<?> p){submit.setEnabled(false);}});\n        io.execute(()->{try{JSONArray rows=DriverRepository.activeSignupFranchises();JSONArray cats=DriverRepository.activeSignupCategories();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();List<String> fids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);String cityName=c.optString("city_name");String state=c.optString("state");String franchiseName=c.optString("franchise_name","CLICK-GO");labels.add(cityName+"/"+state+" — "+franchiseName);ids.add(c.optString("city_id"));fids.add(c.optString("franchise_id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);franchiseIds.clear();franchiseIds.addAll(fids);categoryRowsRef[0]=cats;submit.setEnabled(false);if(ids.isEmpty())toast("Nenhuma franquia ativa está liberada para novos motoristas.");else refreshCategories.run();});}catch(Exception e){ui.post(()->toast("Não foi possível carregar franquias e categorias."));}});\n'''
if old_loader not in text:
    raise SystemExit('Carregamento final de franquias não encontrado')
text = text.replace(old_loader, new_loader, 1)

old_validation = '''            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()||type.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios, incluindo se o veículo é Carro ou Moto.");return;}\n            String vehicleTypeValue=type.getText().toString().trim().toLowerCase(Locale.ROOT);\n            if(vehicleTypeValue.equals("carro")||vehicleTypeValue.equals("automovel")||vehicleTypeValue.equals("automóvel"))vehicleTypeValue="car";\n            else if(vehicleTypeValue.equals("moto")||vehicleTypeValue.equals("motocicleta"))vehicleTypeValue="motorcycle";\n            else if(!vehicleTypeValue.equals("car")&&!vehicleTypeValue.equals("motorcycle")){toast("No tipo do veículo, informe Carro ou Moto.");return;}\n'''
new_validation = '''            int categoryPos=category.getSelectedItemPosition();if(categoryPos<0||categoryPos>=categoryIds.size()||categoryPos>=categoryVehicleTypes.size()){toast("Escolha uma categoria de veículo disponível para esta franquia.");return;}\n            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios.");return;}\n            String vehicleTypeValue=categoryVehicleTypes.get(categoryPos);\n'''
if old_validation not in text:
    raise SystemExit('Validação final Carro/Moto não encontrada')
text = text.replace(old_validation, new_validation, 1)

old_meta = '.put("vehicle_color",color.getText().toString().trim()).put("vehicle_type",vehicleTypeValue);request.put("email",email.getText().toString().trim())'
new_meta = '.put("vehicle_color",color.getText().toString().trim()).put("requested_category_id",categoryIds.get(categoryPos)).put("vehicle_type",vehicleTypeValue);request.put("email",email.getText().toString().trim())'
if old_meta not in text:
    raise SystemExit('Metadado final vehicle_type não encontrado')
text = text.replace(old_meta, new_meta, 1)

# Garante que o app final não peça mais Carro/Moto como única categoria.
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
