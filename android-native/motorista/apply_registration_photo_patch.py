from pathlib import Path

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

def imp(after,value):
 global text
 if value not in text:text=text.replace(after,after+value,1)

imp('import android.app.Activity;\n','import android.app.AlertDialog;\n')
imp('import android.content.pm.PackageManager;\n','import android.content.Intent;\n')
imp('import android.graphics.Bitmap;\n','import android.graphics.BitmapFactory;\n')
imp('import android.os.Looper;\n','import android.provider.MediaStore;\n')
imp('import android.widget.ImageView;\n','import android.widget.ArrayAdapter;\n')
imp('import android.widget.ScrollView;\n','import android.widget.Spinner;\n')
imp('import org.json.JSONObject;\n','import org.json.JSONArray;\n')
imp('import java.text.NumberFormat;\n','import java.io.ByteArrayOutputStream;\nimport java.io.File;\nimport java.io.FileOutputStream;\n')

text=text.replace('''    private static final int REQ_LOCATION = 51;\n''','''    private static final int REQ_LOCATION = 51;\n    private static final int REQ_PROFILE_CAMERA = 52;\n''',1)
text=text.replace('''    private boolean destroyed;\n    private final AtomicBoolean refreshingOperation''','''    private boolean destroyed;\n    private Bitmap registrationPhoto;\n    private ImageView registrationPreview;\n    private boolean cameraForExistingProfile;\n    private final AtomicBoolean refreshingOperation''',1)

# Acrescenta Criar cadastro no login final já corrigido.
anchor='''        TextView forgot = text("Esqueci minha senha?",15,YELLOW,true); forgot.setGravity(Gravity.CENTER); forgot.setPadding(0,dp(8),0,dp(8)); body.addView(forgot,match(dp(48)));\n        body.addView(space(8));\n        body.addView(text("O franqueado da cidade precisa aprovar seu cadastro antes de você ficar online.",13,GRAY,false));\n        enter.setOnClickListener(v -> login(email.getText().toString().trim(), pass.getText().toString()));\n        forgot.setOnClickListener(v -> showRecovery(email.getText().toString().trim()));\n'''
new='''        TextView forgot = text("Esqueci minha senha?",15,YELLOW,true); forgot.setGravity(Gravity.CENTER); forgot.setPadding(0,dp(8),0,dp(8)); body.addView(forgot,match(dp(48)));\n        Button createAccount = darkButton("Criar cadastro de motorista"); body.addView(createAccount,match(dp(54)));\n        body.addView(space(8));\n        body.addView(text("O franqueado da cidade precisa aprovar seu cadastro antes de você ficar online.",13,GRAY,false));\n        enter.setOnClickListener(v -> login(email.getText().toString().trim(), pass.getText().toString()));\n        forgot.setOnClickListener(v -> showRecovery(email.getText().toString().trim()));\n        createAccount.setOnClickListener(v -> showRegistration());\n'''
if anchor not in text:raise SystemExit('Login final do motorista não encontrado')
text=text.replace(anchor,new,1)

# Antes de carregar perfil, envia foto pendente do cadastro assim que houver sessão autenticada.
anchor='''                if (userId == null || userId.isBlank()) { userId = DriverRepository.userId(token); getPreferences(MODE_PRIVATE).edit().putString("user_id",userId).apply(); }\n                JSONObject p = DriverRepository.profile(token), d = DriverRepository.driver(token), w = DriverRepository.wallet(token);\n                fullName = p.optString("full_name","Motorista");\n                avatarBitmap = ProfileAvatar.download(p.optString("avatar_url",""));\n'''
new='''                if (userId == null || userId.isBlank()) { userId = DriverRepository.userId(token); getPreferences(MODE_PRIVATE).edit().putString("user_id",userId).apply(); }\n                uploadPendingRegistrationPhoto();\n                JSONObject p = DriverRepository.profile(token), d = DriverRepository.driver(token), w = DriverRepository.wallet(token);\n                fullName = p.optString("full_name","Motorista");\n                String avatarUrl = p.optString("avatar_url","");\n                if (avatarUrl.isBlank()) { ui.post(this::showMandatoryProfilePhoto); return; }\n                avatarBitmap = ProfileAvatar.download(avatarUrl);\n'''
if anchor not in text:raise SystemExit('loadSession não encontrado')
text=text.replace(anchor,new,1)

# Métodos de cadastro antes do loadSession.
marker='''    private void loadSession() {\n'''
methods=r'''    private void showRegistration() {
        stopPolling(); stopLocationWatch(); releaseMap(); registrationPhoto = null; cameraForExistingProfile = false;
        LinearLayout body = vertical(BLACK); body.setPadding(dp(20),dp(30),dp(20),dp(30));
        Button back=darkButton("← Voltar");back.setOnClickListener(v->showLogin());body.addView(back,new LinearLayout.LayoutParams(dp(110),dp(50)));body.addView(space(16));
        body.addView(text("Cadastro do motorista",28,Color.WHITE,true));body.addView(text("A foto de perfil é obrigatória e deve ser tirada agora pela câmera.",14,YELLOW,true));body.addView(space(16));
        registrationPreview=new ImageView(this);registrationPreview.setScaleType(ImageView.ScaleType.CENTER_CROP);registrationPreview.setBackground(round(DARK,18,Color.rgb(60,60,60)));body.addView(registrationPreview,new LinearLayout.LayoutParams(-1,dp(190)));
        body.addView(space(8));Button camera=primary("📷 Tirar foto de perfil obrigatória");body.addView(camera,match(dp(56)));body.addView(space(14));
        Spinner city=new Spinner(this);ArrayAdapter<String> cityAdapter=new ArrayAdapter<>(this,android.R.layout.simple_spinner_dropdown_item,new ArrayList<>());city.setAdapter(cityAdapter);body.addView(city,match(dp(58)));body.addView(space(10));
        final List<String> cityIds=new ArrayList<>();
        EditText name=edit("Nome completo"),phone=edit("Telefone / WhatsApp"),cpf=edit("CPF"),cnh=edit("Número da CNH"),cnhCat=edit("Categoria CNH"),plate=edit("Placa"),make=edit("Marca do veículo"),model=edit("Modelo"),year=edit("Ano"),color=edit("Cor"),type=edit("Tipo do veículo"),email=edit("E-mail"),pass=edit("Senha (mínimo 6 caracteres)");
        pass.setInputType(InputType.TYPE_CLASS_TEXT|InputType.TYPE_TEXT_VARIATION_PASSWORD);pass.setTransformationMethod(PasswordTransformationMethod.getInstance());
        for(EditText e:new EditText[]{name,phone,cpf,cnh,cnhCat,plate,make,model,year,color,type,email,pass}){body.addView(e,match(dp(58)));body.addView(space(8));}
        Button submit=primary("Enviar cadastro para aprovação");submit.setEnabled(false);body.addView(space(8));body.addView(submit,match(dp(60)));
        camera.setOnClickListener(v->openProfileCamera(false));
        io.execute(()->{try{JSONArray rows=DriverRepository.activeCities();List<String> labels=new ArrayList<>();List<String> ids=new ArrayList<>();for(int i=0;i<rows.length();i++){JSONObject c=rows.getJSONObject(i);labels.add(c.optString("name")+"/"+c.optString("state"));ids.add(c.optString("id"));}ui.post(()->{cityAdapter.clear();cityAdapter.addAll(labels);cityIds.clear();cityIds.addAll(ids);submit.setEnabled(!ids.isEmpty());});}catch(Exception e){ui.post(()->toast("Não foi possível carregar as cidades."));}});
        submit.setOnClickListener(v->{
            if(registrationPhoto==null){toast("Tire sua foto de perfil pela câmera antes de continuar.");return;}
            int pos=city.getSelectedItemPosition();if(pos<0||pos>=cityIds.size()){toast("Escolha sua cidade de atuação.");return;}
            if(name.getText().toString().trim().isBlank()||email.getText().toString().trim().isBlank()||pass.getText().length()<6||cnh.getText().toString().trim().isBlank()||plate.getText().toString().trim().isBlank()){toast("Preencha os dados obrigatórios.");return;}
            JSONObject metadata=new JSONObject();JSONObject request=new JSONObject();
            try{metadata.put("app_role","driver").put("requested_city_id",cityIds.get(pos)).put("full_name",name.getText().toString().trim()).put("phone",phone.getText().toString().trim()).put("cpf",cpf.getText().toString().trim()).put("cnh_number",cnh.getText().toString().trim()).put("cnh_category",cnhCat.getText().toString().trim()).put("vehicle_plate",plate.getText().toString().trim()).put("vehicle_make",make.getText().toString().trim()).put("vehicle_model",model.getText().toString().trim()).put("vehicle_year",year.getText().toString().trim()).put("vehicle_color",color.getText().toString().trim()).put("vehicle_type",type.getText().toString().trim());request.put("email",email.getText().toString().trim()).put("password",pass.getText().toString()).put("data",metadata);}catch(Exception ignored){}
            savePendingRegistrationPhoto();submit.setEnabled(false);
            io.execute(()->{try{JSONObject response=DriverRepository.signUp(request);String access=response.optString("access_token","");JSONObject u=response.optJSONObject("user");String id=u==null?"":u.optString("id","");if(!access.isBlank()){token=access;userId=id;getPreferences(MODE_PRIVATE).edit().putString("access_token",token).putString("user_id",userId).apply();uploadPendingRegistrationPhoto();ui.post(this::loadSession);}else{ui.post(()->new AlertDialog.Builder(this).setTitle("Cadastro recebido").setMessage("Confirme seu e-mail. Depois entre no App Motorista. A foto tirada agora será enviada automaticamente no primeiro acesso e o franqueado só poderá aprovar seu cadastro depois disso.").setPositiveButton("Ir para o login",(d,w)->showLogin()).show());}}catch(Exception e){ui.post(()->{submit.setEnabled(true);toast(msg(e));});}});
        });
        setContentView(scroll(body,BLACK));
    }

    private void openProfileCamera(boolean existingProfile) {
        cameraForExistingProfile=existingProfile;
        Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
        if(intent.resolveActivity(getPackageManager())==null){toast("Nenhum aplicativo de câmera disponível.");return;}
        startActivityForResult(intent,REQ_PROFILE_CAMERA);
    }

    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode==REQ_PROFILE_CAMERA&&resultCode==RESULT_OK&&data!=null&&data.getExtras()!=null){Object obj=data.getExtras().get("data");if(obj instanceof Bitmap){registrationPhoto=(Bitmap)obj;if(registrationPreview!=null)registrationPreview.setImageBitmap(registrationPhoto);}}
    }

    private byte[] photoJpeg(Bitmap photo) throws Exception {ByteArrayOutputStream out=new ByteArrayOutputStream();if(!photo.compress(Bitmap.CompressFormat.JPEG,88,out))throw new Exception("Não foi possível processar a foto.");return out.toByteArray();}
    private File pendingPhotoFile(){return new File(getFilesDir(),"pending_driver_profile.jpg");}
    private void savePendingRegistrationPhoto(){if(registrationPhoto==null)return;try(FileOutputStream out=new FileOutputStream(pendingPhotoFile())){out.write(photoJpeg(registrationPhoto));}catch(Exception ignored){}}
    private void uploadPendingRegistrationPhoto() throws Exception {File f=pendingPhotoFile();if(!f.exists()||token==null||userId==null||userId.isBlank())return;Bitmap b=BitmapFactory.decodeFile(f.getAbsolutePath());if(b==null)throw new Exception("A foto obrigatória não pôde ser recuperada.");DriverRepository.uploadAvatar(token,userId,photoJpeg(b));f.delete();}

    private void showMandatoryProfilePhoto(){
        registrationPhoto=null;cameraForExistingProfile=true;LinearLayout body=vertical(BLACK);body.setPadding(dp(24),dp(45),dp(24),dp(30));body.addView(text("Foto obrigatória",30,Color.WHITE,true));body.addView(space(8));body.addView(text("Antes de continuar, tire uma foto real do seu rosto pela câmera. O franqueado verá essa foto ao analisar seu cadastro.",15,GRAY,false));body.addView(space(18));registrationPreview=new ImageView(this);registrationPreview.setScaleType(ImageView.ScaleType.CENTER_CROP);registrationPreview.setBackground(round(DARK,18,Color.rgb(60,60,60)));body.addView(registrationPreview,new LinearLayout.LayoutParams(-1,dp(260)));body.addView(space(12));Button take=primary("📷 Tirar foto agora");Button save=darkButton("Salvar foto e continuar");body.addView(take,match(dp(58)));body.addView(space(10));body.addView(save,match(dp(58)));take.setOnClickListener(v->openProfileCamera(true));save.setOnClickListener(v->{if(registrationPhoto==null){toast("Tire a foto pela câmera.");return;}save.setEnabled(false);io.execute(()->{try{String url=DriverRepository.uploadAvatar(token,userId,photoJpeg(registrationPhoto));avatarBitmap=registrationPhoto;ui.post(this::loadSession);}catch(Exception e){ui.post(()->{save.setEnabled(true);toast(msg(e));});}});});setContentView(scroll(body,BLACK));
    }

'''
if marker not in text:raise SystemExit('loadSession marker não encontrado')
text=text.replace(marker,methods+marker,1)

# Versão motorista v0.4.
build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8');build=build.replace('versionCode 3','versionCode 4',1).replace("versionName '0.3-native-beta'","versionName '0.4-native-beta'",1);build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Motorista v0.4: cadastro nativo com foto obrigatória via câmera.')
