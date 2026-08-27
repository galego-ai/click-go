from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

def rep(a,b,label):
    global text
    if a not in text: raise SystemExit(label+' não encontrado')
    text=text.replace(a,b,1)

if 'activeSignupCategories()' not in repo:
    marker='    public static String userId(String token) throws Exception {'
    if marker not in repo: raise SystemExit('marker repository não encontrado')
    repo=repo.replace(marker,'    public static JSONArray activeSignupCategories() throws Exception {\n        return new JSONArray(ApiClient.publicRpc("list_driver_signup_categories", new JSONObject()));\n    }\n\n'+marker,1)

rep('        final List<String> cityIds=new ArrayList<>();\n','''        final List<String> cityIds=new ArrayList<>();
        body.addView(text("Categoria do veículo",14,YELLOW,true));body.addView(space(6));
        Spinner category=new Spinner(this);ArrayAdapter<String> categoryAdapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new ArrayList<>());category.setAdapter(categoryAdapter);body.addView(category,match(dp(58)));body.addView(text("Escolha uma categoria disponível na cidade.",12,GRAY,false));body.addView(space(10));
        final List<String> categoryIds=new ArrayList<>(),categoryTypes=new ArrayList<>(),categoryFranchises=new ArrayList<>();final JSONArray[] categoryRows=new JSONArray[]{new JSONArray()};
''','cityIds')

if ',type=edit("Tipo do veículo")' in text:text=text.replace(',type=edit("Tipo do veículo")','',1)
elif ',type=edit("Tipo do veículo: Carro ou Moto")' in text:text=text.replace(',type=edit("Tipo do veículo: Carro ou Moto")','',1)
else:raise SystemExit('campo Tipo do veículo não encontrado')
rep('new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,type,email,pass}','new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,email,pass}','array tipo')

old='        camera.setOnClickListener(v->openProfileCamera(false));\n        io.execute(()->{try{JSONArray rows=DriverRepository.activeCities();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);labels.add(c.optString("name")+"/"+c.optString("state"));ids.add(c.optString("id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);submit.setEnabled(!ids.isEmpty());});}catch(Exception e){ui.post(()->toast("Não foi possível carregar as cidades."));}});\n'
new='''        camera.setOnClickListener(v->openProfileCamera(false));
        final Runnable refreshCategories=()->{categoryAdapter.clear();categoryIds.clear();categoryTypes.clear();categoryFranchises.clear();int selected=city.getSelectedItemPosition();if(selected<0||selected>=cityIds.size()){submit.setEnabled(false);return;}String selectedCity=cityIds.get(selected);JSONArray rows=categoryRows[0];for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);if(c==null||!selectedCity.equals(c.optString("city_id")))continue;categoryAdapter.add(c.optString("category_name","Categoria CLICK-GO"));categoryIds.add(c.optString("category_id"));categoryTypes.add(c.optString("required_vehicle_type",""));categoryFranchises.add(c.optString("franchise_id",""));}submit.setEnabled(!categoryIds.isEmpty());};
        city.setOnItemSelectedListener(new android.widget.AdapterView.OnItemSelectedListener(){public void onItemSelected(android.widget.AdapterView<?> p,View v,int position,long id){refreshCategories.run();}public void onNothingSelected(android.widget.AdapterView<?> p){submit.setEnabled(false);}});
        io.execute(()->{try{JSONArray rows=DriverRepository.activeCities();JSONArray cats=DriverRepository.activeSignupCategories();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);labels.add(c.optString("name")+"/"+c.optString("state"));ids.add(c.optString("id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);categoryRows[0]=cats;submit.setEnabled(false);if(ids.isEmpty())toast("Nenhuma cidade ativa disponível.");else refreshCategories.run();});}catch(Exception e){ui.post(()->toast("Não foi possível carregar cidades e categorias."));}});
'''
rep(old,new,'loader cidades')

rep('            int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()){toast("Escolha sua cidade de atuação.");return;}\n','''            int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()){toast("Escolha sua cidade de atuação.");return;}
            int categoryPos=category.getSelectedItemPosition();if(categoryPos<0||categoryPos>=categoryIds.size()){toast("Escolha uma categoria disponível para esta cidade.");return;}
            String vehicleTypeValue=categoryTypes.get(categoryPos),requestedFranchiseId=categoryFranchises.get(categoryPos);if(requestedFranchiseId.isBlank()){toast("Categoria sem franquia responsável.");return;}
''','validação cidade')

text=text.replace('||type.getText().toString().trim().isBlank()','',1).replace('Preencha os dados obrigatórios, incluindo se o veículo é Carro ou Moto.','Preencha os dados obrigatórios.',1)
text=re.sub(r'            String vehicleTypeValue=type\.getText\(\).*?\n            else if\(!vehicleTypeValue\.equals\("car"\).*?\n','',text,count=1,flags=re.S)
rep('.put("requested_city_id",cityIds.get(pos)).put("full_name",name.getText().toString().trim())','.put("requested_city_id",cityIds.get(pos)).put("requested_franchise_id",requestedFranchiseId).put("requested_category_id",categoryIds.get(categoryPos)).put("full_name",name.getText().toString().trim())','metadata ids')
if '.put("vehicle_type",type.getText().toString().trim())' in text:text=text.replace('.put("vehicle_type",type.getText().toString().trim())','.put("vehicle_type",vehicleTypeValue)',1)
elif '.put("vehicle_type",vehicleTypeValue)' not in text:raise SystemExit('metadata vehicle_type não encontrado')

if 'type.getText()' in text or 'Tipo do veículo: Carro ou Moto' in text:raise SystemExit('referência antiga ainda presente')
if 'requested_category_id' not in text or 'requested_franchise_id' not in text:raise SystemExit('ids dinâmicos ausentes')

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.6-prime'",build,count=1)
main.write_text(text,encoding='utf-8');repo_path.write_text(repo,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Driver v3.6: categorias dinâmicas aplicadas ao formulário final.')
