from pathlib import Path
import re

main = Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
build_path = Path('app/build.gradle')
text = main.read_text(encoding='utf-8')
build = build_path.read_text(encoding='utf-8')

# Deixa claro que o motorista escolhe somente a cidade.
spinner = '        Spinner city=new Spinner(this);'
if spinner not in text:
    raise SystemExit('Spinner de cidade não encontrado no cadastro final')
if 'Cidade de cadastro' not in text:
    text = text.replace(
        spinner,
        '        body.addView(text("Cidade de cadastro",14,YELLOW,true));body.addView(space(6));\n' + spinner,
        1,
    )

# Não permite que a primeira cidade seja escolhida automaticamente.
loader_marker = 'List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();for(int i=0;i<rows.length();i++)'
if loader_marker not in text:
    raise SystemExit('Carregamento final de cidades não encontrado')
text = text.replace(
    loader_marker,
    'List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();labels.add("Selecione sua cidade");ids.add("");for(int i=0;i<rows.length();i++)',
    1,
)

# A cidade precisa ter sido escolhida de forma explícita.
old_validation = 'int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()){toast("Escolha sua cidade de atuação.");return;}'
new_validation = 'int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()||cityIds.get(pos).isBlank()){toast("Selecione sua cidade para continuar.");return;}'
if old_validation not in text:
    raise SystemExit('Validação final da cidade não encontrada')
text = text.replace(old_validation, new_validation, 1)

# O app não escolhe nem envia franquia. O backend resolve a franquia pela cidade.
old_category = 'String vehicleTypeValue=categoryTypes.get(categoryPos),requestedFranchiseId=categoryFranchises.get(categoryPos);if(requestedFranchiseId.isBlank()){toast("Categoria sem franquia responsável.");return;}'
if old_category in text:
    text = text.replace(old_category, 'String vehicleTypeValue=categoryTypes.get(categoryPos);', 1)

old_meta = '.put("requested_city_id",cityIds.get(pos)).put("requested_franchise_id",requestedFranchiseId).put("requested_category_id",categoryIds.get(categoryPos))'
new_meta = '.put("requested_city_id",cityIds.get(pos)).put("requested_category_id",categoryIds.get(categoryPos))'
if old_meta in text:
    text = text.replace(old_meta, new_meta, 1)

if 'requested_franchise_id",requestedFranchiseId' in text:
    raise SystemExit('Cadastro ainda envia franquia escolhida pelo app')
if 'Selecione sua cidade' not in text or 'Cidade de cadastro' not in text:
    raise SystemExit('Seleção explícita de cidade não aplicada')

m = re.search(r'versionCode\s+(\d+)', build)
if m:
    build = build[:m.start(1)] + str(int(m.group(1)) + 1) + build[m.end(1):]
build = re.sub(r"versionName\s+'[^']+'", "versionName '3.10-prime'", build, count=1)

main.write_text(text, encoding='utf-8')
build_path.write_text(build, encoding='utf-8')
print('Motorista v3.10 PRIME: cadastro exige escolha explicita somente da cidade.')
