from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
repo_path=Path('app/src/main/java/com/clickgo/motorista/DriverRepository.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
repo=repo_path.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Endpoint seguro que informa se a Matriz liberou o taxímetro para a franquia do motorista.
anchor='''    public static JSONArray taximeterCategories(String token) throws Exception {\n        return new JSONArray(ApiClient.rpc("get_my_taximeter_categories", new JSONObject(), token));\n    }\n'''
addition='''    public static JSONObject taximeterAccess(String token) throws Exception {\n        return new JSONObject(ApiClient.rpc("get_my_taximeter_access", new JSONObject(), token));\n    }\n\n'''+anchor
if 'public static JSONObject taximeterAccess(' not in repo:
    if anchor not in repo: raise SystemExit('taximeterCategories não encontrado no DriverRepository')
    repo=repo.replace(anchor,addition,1)

# Na home o bloco nasce oculto e só aparece após confirmação do backend.
home_head='''        LinearLayout homeTaximeter=card(Color.rgb(250,250,250),Color.rgb(225,225,225));\n        homeTaximeter.setPadding(dp(12),dp(10),dp(12),dp(10));\n'''
if 'homeTaximeter.setVisibility(android.view.View.GONE);' not in text:
    if home_head not in text: raise SystemExit('bloco homeTaximeter não encontrado')
    text=text.replace(home_head,home_head+'        homeTaximeter.setVisibility(android.view.View.GONE);\n',1)

old='''            JSONObject running=DriverRepository.runningTaximeter(token,userId);\n            JSONArray categories=DriverRepository.taximeterCategories(token);\n            ui.post(()->renderHomeTaximeter(box,running,categories));\n'''
new='''            JSONObject access=DriverRepository.taximeterAccess(token);\n            boolean taximeterAllowed=access.optBoolean("enabled",true);\n            getPreferences(MODE_PRIVATE).edit().putBoolean("taximeter_enabled_by_matrix",taximeterAllowed).apply();\n            if(!taximeterAllowed){ui.post(()->box.setVisibility(android.view.View.GONE));return;}\n            JSONObject running=DriverRepository.runningTaximeter(token,userId);\n            JSONArray categories=DriverRepository.taximeterCategories(token);\n            ui.post(()->{box.setVisibility(android.view.View.VISIBLE);renderHomeTaximeter(box,running,categories);});\n'''
if 'boolean taximeterAllowed=access.optBoolean("enabled",true);' not in text:
    if old not in text: raise SystemExit('carregamento do taxímetro da home não encontrado')
    text=text.replace(old,new,1)

# O item do menu desaparece quando a regra da Matriz estiver desligada.
menu_line='''        body.addView(menuCard("🚕", "Taxímetro / Maçaneta", "Corrida livre com bandeirada, km e minuto", () -> showTaximeter())); body.addView(space(9));\n'''
menu_guard='''        if(getPreferences(MODE_PRIVATE).getBoolean("taximeter_enabled_by_matrix",true)){body.addView(menuCard("🚕", "Taxímetro / Maçaneta", "Corrida livre com bandeirada, km e minuto", () -> showTaximeter())); body.addView(space(9));}\n'''
if menu_guard not in text:
    if menu_line in text:
        text=text.replace(menu_line,menu_guard,1)
    else:
        menu_pat=r'(?m)^\s*body\.addView\(menuCard\("🚕",\s*"Taxímetro / Maçaneta"[^\n]*\n'
        m=re.search(menu_pat,text)
        if not m: raise SystemExit('item Taxímetro / Maçaneta não encontrado')
        line=m.group(0)
        indent=re.match(r'\s*',line).group(0)
        text=text[:m.start()]+indent+'if(getPreferences(MODE_PRIVATE).getBoolean("taximeter_enabled_by_matrix",true)){'+line.strip()+'}\n'+text[m.end():]

# Proteção local imediata na abertura da tela completa. O backend continua sendo a autoridade final.
guard='''        if(!getPreferences(MODE_PRIVATE).getBoolean("taximeter_enabled_by_matrix",true)){\n            toast("Taxímetro não disponível nesta franquia.");\n            showHome();\n            return;\n        }\n'''
if 'Taxímetro não disponível nesta franquia.' not in text:
    text,n=re.subn(r'(    private void showTaximeter\(\)\s*\{\s*\n)',r'\1'+guard,text,count=1)
    if n!=1: raise SystemExit('showTaximeter não encontrado')

for required in ['get_my_taximeter_access','taximeter_enabled_by_matrix','Taxímetro não disponível nesta franquia.','boolean taximeterAllowed']:
    if required not in text+repo: raise SystemExit('Motorista v3.13 incompleto: '+required)

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(max(int(m.group(1))+1,313))+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '3.13-prime'",build,count=1)
main.write_text(text,encoding='utf-8');repo_path.write_text(repo,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Motorista v3.13 PRIME: Matriz pode ocultar/liberar o taxímetro por franquia.')
