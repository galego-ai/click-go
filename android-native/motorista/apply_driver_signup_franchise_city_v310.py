from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

old='        final List<String> cityIds=new ArrayList<>();\n'
new='        final List<String> cityIds=new ArrayList<>();\n        final List<String> signupFranchiseIds=new ArrayList<>();\n'
if old not in text:
    raise SystemExit('Lista de cidades do cadastro não encontrada')
text=text.replace(old,new,1)

old='''        final Runnable refreshCategories=()->{categoryAdapter.clear();categoryIds.clear();categoryTypes.clear();categoryFranchises.clear();int selected=city.getSelectedItemPosition();if(selected<0||selected>=cityIds.size()){submit.setEnabled(false);return;}String selectedCity=cityIds.get(selected);JSONArray rows=categoryRows[0];for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);if(c==null||!selectedCity.equals(c.optString("city_id")))continue;categoryAdapter.add(c.optString("category_name","Categoria CLICK-GO"));categoryIds.add(c.optString("category_id"));categoryTypes.add(c.optString("required_vehicle_type",""));categoryFranchises.add(c.optString("franchise_id",""));}submit.setEnabled(!categoryIds.isEmpty());};
'''
new='''        final Runnable refreshCategories=()->{categoryAdapter.clear();categoryIds.clear();categoryTypes.clear();categoryFranchises.clear();int selected=city.getSelectedItemPosition();if(selected<=0||selected>=cityIds.size()||selected>=signupFranchiseIds.size()){submit.setEnabled(false);return;}String selectedCity=cityIds.get(selected),selectedFranchise=signupFranchiseIds.get(selected);if(selectedCity.isBlank()||selectedFranchise.isBlank()){submit.setEnabled(false);return;}JSONArray rows=categoryRows[0];for(int i=0;i<rows.length();i++){JSONObject c=rows.optJSONObject(i);if(c==null||!selectedCity.equals(c.optString("city_id"))||!selectedFranchise.equals(c.optString("franchise_id")))continue;categoryAdapter.add(c.optString("category_name","Categoria CLICK-GO"));categoryIds.add(c.optString("category_id"));categoryTypes.add(c.optString("required_vehicle_type",""));categoryFranchises.add(c.optString("franchise_id",""));}submit.setEnabled(!categoryIds.isEmpty());};
'''
if old not in text:
    raise SystemExit('Filtro de categorias do cadastro não encontrado')
text=text.replace(old,new,1)

old='''        io.execute(()->{try{JSONArray rows=DriverRepository.activeCities();JSONArray cats=DriverRepository.activeSignupCategories();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);labels.add(c.optString("name")+"/"+c.optString("state"));ids.add(c.optString("id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);categoryRows[0]=cats;submit.setEnabled(false);if(ids.isEmpty())toast("Nenhuma cidade ativa disponível.");else refreshCategories.run();});}catch(Exception e){ui.post(()->toast("Não foi possível carregar cidades e categorias."));}});
'''
new='''        io.execute(()->{try{JSONArray rows=DriverRepository.activeSignupFranchises();JSONArray cats=DriverRepository.activeSignupCategories();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();List<String> fids=new ArrayList<>();labels.add("Selecione a franquia / cidade");ids.add("");fids.add("");for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);String cityName=c.optString("city_name"),state=c.optString("state"),franchiseName=c.optString("franchise_name","CLICK-GO");labels.add(franchiseName+" — "+cityName+"/"+state);ids.add(c.optString("city_id"));fids.add(c.optString("franchise_id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);signupFranchiseIds.clear();signupFranchiseIds.addAll(fids);categoryRows[0]=cats;city.setSelection(0);submit.setEnabled(false);if(rows.length()==0)toast("Nenhuma franquia/cidade está liberada para novos motoristas.");});}catch(Exception e){ui.post(()->toast("Não foi possível carregar franquias, cidades e categorias."));}});
'''
if old not in text:
    raise SystemExit('Carregamento final de cidades do cadastro não encontrado')
text=text.replace(old,new,1)

old='''            int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()){toast("Escolha sua cidade de atuação.");return;}
            int categoryPos=category.getSelectedItemPosition();if(categoryPos<0||categoryPos>=categoryIds.size()){toast("Escolha uma categoria disponível para esta cidade.");return;}
            String vehicleTypeValue=categoryTypes.get(categoryPos),requestedFranchiseId=categoryFranchises.get(categoryPos);if(requestedFranchiseId.isBlank()){toast("Categoria sem franquia responsável.");return;}
'''
new='''            int pos=city.getSelectedItemPosition();if(pos<=0||pos>=cityIds.size()||pos>=signupFranchiseIds.size()||cityIds.get(pos).isBlank()||signupFranchiseIds.get(pos).isBlank()){toast("Escolha a franquia e a cidade onde deseja se cadastrar.");return;}
            int categoryPos=category.getSelectedItemPosition();if(categoryPos<0||categoryPos>=categoryIds.size()){toast("Escolha uma categoria disponível para esta franquia/cidade.");return;}
            String vehicleTypeValue=categoryTypes.get(categoryPos),requestedFranchiseId=signupFranchiseIds.get(pos),categoryFranchiseId=categoryFranchises.get(categoryPos);if(!requestedFranchiseId.equals(categoryFranchiseId)){toast("A categoria escolhida não pertence à franquia/cidade selecionada.");return;}
'''
if old not in text:
    raise SystemExit('Validação final do cadastro não encontrada')
text=text.replace(old,new,1)

if 'Selecione a franquia / cidade' not in text or 'signupFranchiseIds' not in text or 'activeSignupFranchises()' not in text:
    raise SystemExit('Seleção explícita de franquia/cidade não foi aplicada por completo')

m=re.search(r'versionCode\s+(\d+)',build)
if m:
    build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.10-prime'",build,count=1)

main.write_text(text,encoding='utf-8')
build_path.write_text(build,encoding='utf-8')
print('Motorista v3.10 PRIME: franquia/cidade obrigatórias e escolhidas explicitamente no cadastro.')
