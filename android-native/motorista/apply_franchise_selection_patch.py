from pathlib import Path

path = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text = path.read_text(encoding='utf-8')

def repl(old, new, label):
    global text
    if old not in text:
        raise SystemExit(f'Trecho não encontrado: {label}')
    text = text.replace(old, new, 1)

repl(
'''        Spinner city=new Spinner(this);ArrayAdapter<String> cityAdapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new ArrayList<>());city.setAdapter(cityAdapter);body.addView(city,match(dp(58)));body.addView(space(10));\n        final List<String> cityIds=new ArrayList<>();\n''',
'''        TextView franchiseLabel=text("Franquia / cidade de cadastro",14,YELLOW,true);body.addView(franchiseLabel);body.addView(space(6));\n        Spinner city=new Spinner(this);ArrayAdapter<String> cityAdapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new ArrayList<>());city.setAdapter(cityAdapter);body.addView(city,match(dp(58)));body.addView(text("Seu cadastro será enviado para aprovação do franqueado escolhido.",12,GRAY,false));body.addView(space(10));\n        final List<String> cityIds=new ArrayList<>();\n        final List<String> franchiseIds=new ArrayList<>();\n''',
'campo franquia/cidade'
)

repl(
'''        io.execute(()->{try{JSONArray rows=DriverRepository.activeCities();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);labels.add(c.optString("name")+"/"+c.optString("state"));ids.add(c.optString("id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);submit.setEnabled(!ids.isEmpty());});}catch(Exception e){ui.post(()->toast("Não foi possível carregar as cidades."));}});\n''',
'''        io.execute(()->{try{JSONArray rows=DriverRepository.activeSignupFranchises();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();List<String> fids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);String cityName=c.optString("city_name");String state=c.optString("state");String franchiseName=c.optString("franchise_name","CLICK-GO");labels.add(cityName+"/"+state+" — "+franchiseName);ids.add(c.optString("city_id"));fids.add(c.optString("franchise_id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);franchiseIds.clear();franchiseIds.addAll(fids);submit.setEnabled(!ids.isEmpty()&&ids.size()==fids.size());if(ids.isEmpty())toast("Nenhuma franquia ativa está liberada para novos motoristas.");});}catch(Exception e){ui.post(()->toast("Não foi possível carregar as franquias/cidades."));}});\n''',
'carregamento de franquias'
)

repl(
'''            int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()){toast("Escolha sua cidade de atuação.");return;}\n''',
'''            int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()||pos>=franchiseIds.size()){toast("Escolha a franquia/cidade onde deseja se cadastrar.");return;}\n''',
'validação da seleção'
)

repl(
'''            try{metadata.put("app_role","driver").put("requested_city_id",cityIds.get(pos)).put("full_name",name.getText().toString().trim()).put("phone",phone.getText().toString().trim()).put("cpf",cpf.getText().toString().trim()).put("cnh_number",cnh.getText().toString().trim()).put("cnh_category",cnhCat.getText().toString().trim()).put("vehicle_plate",plate.getText().toString().trim()).put("vehicle_make",make.getText().toString().trim()).put("vehicle_model",model.getText().toString().trim()).put("vehicle_year",year.getText().toString().trim()).put("vehicle_color",color.getText().toString().trim()).put("vehicle_type",type.getText().toString().trim());request.put("email",email.getText().toString().trim()).put("password",pass.getText().toString()).put("data",metadata);}catch(Exception ignored){}\n''',
'''            try{metadata.put("app_role","driver").put("requested_city_id",cityIds.get(pos)).put("requested_franchise_id",franchiseIds.get(pos)).put("full_name",name.getText().toString().trim()).put("phone",phone.getText().toString().trim()).put("cpf",cpf.getText().toString().trim()).put("cnh_number",cnh.getText().toString().trim()).put("cnh_category",cnhCat.getText().toString().trim()).put("vehicle_plate",plate.getText().toString().trim()).put("vehicle_make",make.getText().toString().trim()).put("vehicle_model",model.getText().toString().trim()).put("vehicle_year",year.getText().toString().trim()).put("vehicle_color",color.getText().toString().trim()).put("vehicle_type",type.getText().toString().trim());request.put("email",email.getText().toString().trim()).put("password",pass.getText().toString()).put("data",metadata);}catch(Exception ignored){}\n''',
'metadados da franquia'
)

build_path = Path('app/build.gradle')
build = build_path.read_text(encoding='utf-8')
if 'versionCode 5' in build:
    build = build.replace('versionCode 5', 'versionCode 6', 1)
if "versionName '0.5-native-beta'" in build:
    build = build.replace("versionName '0.5-native-beta'", "versionName '0.6-native-beta'", 1)
build_path.write_text(build, encoding='utf-8')

path.write_text(text, encoding='utf-8')
print('Motorista v0.6: seleção obrigatória da franquia/cidade aplicada.')
