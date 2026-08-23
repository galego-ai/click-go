from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

text=text.replace('type=edit("Tipo do veículo")','type=edit("Tipo do veículo: Carro ou Moto")',1)
old='''            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios.");return;}\n            JSONObject metadata=new JSONObject();JSONObject request=new JSONObject();\n'''
new='''            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()||type.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios, incluindo se o veículo é Carro ou Moto.");return;}\n            String vehicleTypeValue=type.getText().toString().trim().toLowerCase(Locale.ROOT);\n            if(vehicleTypeValue.equals("carro")||vehicleTypeValue.equals("automovel")||vehicleTypeValue.equals("automóvel"))vehicleTypeValue="car";\n            else if(vehicleTypeValue.equals("moto")||vehicleTypeValue.equals("motocicleta"))vehicleTypeValue="motorcycle";\n            else if(!vehicleTypeValue.equals("car")&&!vehicleTypeValue.equals("motorcycle")){toast("No tipo do veículo, informe Carro ou Moto.");return;}\n            JSONObject metadata=new JSONObject();JSONObject request=new JSONObject();\n'''
if old not in text: raise SystemExit('Validação do cadastro do motorista não encontrada')
text=text.replace(old,new,1)
if '.put("vehicle_type",type.getText().toString().trim())' not in text: raise SystemExit('vehicle_type do cadastro não encontrado')
text=text.replace('.put("vehicle_type",type.getText().toString().trim())','.put("vehicle_type",vehicleTypeValue)',1)

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8')
m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '1.1-prime'",build,count=1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Motorista v1.1 PRIME: tipo Carro/Moto obrigatório e normalizado.')
