from pathlib import Path
import re

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

def add_import(anchor,value):
    global text
    if value.strip() not in text:
        if anchor not in text: raise SystemExit('Import anchor não encontrado: '+anchor.strip())
        text=text.replace(anchor,anchor+value,1)

add_import('import android.content.Intent;\n','import android.net.Uri;\n')
add_import('import android.widget.Spinner;\n','import androidx.core.content.FileProvider;\n')
add_import('import java.io.FileOutputStream;\n','import java.io.FileInputStream;\nimport java.io.InputStream;\n')
add_import('import java.util.List;\n','import java.util.HashMap;\nimport java.util.Map;\n')

text=text.replace('''    private static final int REQ_PROFILE_CAMERA = 52;\n''','''    private static final int REQ_PROFILE_CAMERA = 52;\n    private static final int REQ_DRIVER_DOC_CAMERA = 53;\n    private static final int REQ_DRIVER_DOC_FILE = 54;\n''',1)

field_anchor='''    private Bitmap registrationPhoto;\n    private ImageView registrationPreview;\n    private boolean cameraForExistingProfile;\n'''
if field_anchor not in text: raise SystemExit('Campos de foto não encontrados')
text=text.replace(field_anchor,field_anchor+'''    private String pendingDocumentType;\n    private File pendingDocumentCameraFile;\n    private Uri pendingDocumentCameraUri;\n''',1)

old_result='''    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){\n        super.onActivityResult(requestCode,resultCode,data);\n        if(requestCode==REQ_PROFILE_CAMERA&&resultCode==RESULT_OK&&data!=null&&data.getExtras()!=null){Object obj=data.getExtras().get("data");if(obj instanceof Bitmap){registrationPhoto=(Bitmap)obj;if(registrationPreview!=null)registrationPreview.setImageBitmap(registrationPhoto);}}\n    }\n'''
new_result=r'''    @Override protected void onActivityResult(int requestCode,int resultCode,Intent data){
        super.onActivityResult(requestCode,resultCode,data);
        if(requestCode==REQ_PROFILE_CAMERA&&resultCode==RESULT_OK&&data!=null&&data.getExtras()!=null){Object obj=data.getExtras().get("data");if(obj instanceof Bitmap){registrationPhoto=(Bitmap)obj;if(registrationPreview!=null)registrationPreview.setImageBitmap(registrationPhoto);}return;}
        if(requestCode==REQ_DRIVER_DOC_CAMERA){
            if(resultCode==RESULT_OK&&pendingDocumentType!=null&&pendingDocumentCameraFile!=null&&pendingDocumentCameraFile.exists()){
                String type=pendingDocumentType;File file=pendingDocumentCameraFile;clearPendingDocumentCapture();
                io.execute(()->{try{byte[] bytes=cameraDocumentBytes(file);file.delete();DriverRepository.uploadDocument(token,userId,type,bytes,"image/jpeg");ui.post(()->{toast("Documento enviado para análise.");showDocuments();});}catch(Exception e){file.delete();ui.post(()->toast(msg(e)));}});
            }else clearPendingDocumentCapture();
            return;
        }
        if(requestCode==REQ_DRIVER_DOC_FILE&&resultCode==RESULT_OK&&data!=null&&data.getData()!=null&&pendingDocumentType!=null){
            String type=pendingDocumentType;Uri uri=data.getData();pendingDocumentType=null;
            io.execute(()->{try{String mime=getContentResolver().getType(uri);byte[] bytes=readDocumentUri(uri);DriverRepository.uploadDocument(token,userId,type,bytes,mime);ui.post(()->{toast("Documento enviado para análise.");showDocuments();});}catch(Exception e){ui.post(()->toast(msg(e)));}});
        }
    }
'''
if old_result not in text: raise SystemExit('onActivityResult do motorista não encontrado')
text=text.replace(old_result,new_result,1)

old_docs='''    private void showDocuments(){\n        LinearLayout body=pageShell("Meus documentos","A foto real de perfil e os documentos precisam ser aprovados pelo franqueado.");TextView loading=text("Carregando documentos…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));\n        io.execute(()->{try{JSONArray rows=DriverRepository.documents(token,userId);ui.post(()->{body.removeView(loading);if(rows.length()==0){body.addView(text("Nenhum documento enviado.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject d=rows.optJSONObject(i);if(d==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));String type=d.optString("document_type","Documento"),status=d.optString("status","pending");c.addView(text(type.equals("profile_photo")?"📷 Foto real de perfil":type,16,Color.WHITE,true));c.addView(text(statusLabelForDocument(status),14,status.equals("approved")?Color.rgb(74,222,128):status.equals("rejected")?Color.rgb(248,113,113):YELLOW,true));String reason=d.optString("rejection_reason","");if(!reason.isBlank())c.addView(text("Motivo: "+reason,12,Color.rgb(248,113,113),false));body.addView(c);body.addView(space(8));}});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});\n    }\n'''
new_docs=r'''    private void showDocuments(){
        LinearLayout body=pageShell("Meus documentos","Envie todos os documentos obrigatórios. Você pode tirar uma foto agora ou escolher uma foto/PDF do aparelho.");
        TextView loading=text("Carregando documentos…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONArray rows=DriverRepository.documents(token,userId);Map<String,JSONObject> latest=new HashMap<>();for(int i=0;i<rows.length();i++){JSONObject d=rows.optJSONObject(i);if(d==null)continue;String type=d.optString("document_type","");if(!type.isBlank()&&!latest.containsKey(type))latest.put(type,d);}ui.post(()->{
            body.removeView(loading);
            String[][] required={{"profile_photo","📷 Foto real de perfil"},{"cnh_frente","🪪 CNH - frente"},{"cnh_verso","🪪 CNH - verso"},{"selfie_cnh","🤳 Selfie segurando a CNH"},{"crlv","🚘 CRLV do veículo"},{"comprovante_residencia","🏠 Comprovante de residência"}};
            int missing=0;for(String[] item:required)if(!latest.containsKey(item[0]))missing++;
            if(missing>0){LinearLayout notice=card(Color.rgb(41,31,5),Color.rgb(113,84,8));notice.addView(text("Faltam "+missing+" documento(s) obrigatório(s)",15,YELLOW,true));notice.addView(text("Envie todos para que o franqueado possa concluir sua aprovação.",13,Color.WHITE,false));body.addView(notice);body.addView(space(10));}
            for(String[] item:required){body.addView(driverDocumentCard(item[0],item[1],latest.get(item[0])));body.addView(space(9));}
        });}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private View driverDocumentCard(String type,String label,JSONObject d){
        LinearLayout c=card(DARK,Color.rgb(55,55,55));String status=d==null?"missing":d.optString("status","pending");
        c.addView(text(label,17,Color.WHITE,true));
        String statusText=status.equals("approved")?"✅ Aprovado":status.equals("rejected")?"❌ Rejeitado":status.equals("pending")?"⏳ Aguardando análise":"⚠ Não enviado";
        int statusColor=status.equals("approved")?Color.rgb(74,222,128):status.equals("rejected")?Color.rgb(248,113,113):status.equals("pending")?YELLOW:GRAY;
        c.addView(text(statusText,14,statusColor,true));
        String reason="";if(d!=null&&!d.isNull("rejection_reason"))reason=d.optString("rejection_reason","");if("null".equalsIgnoreCase(reason))reason="";
        if(!reason.isBlank())c.addView(text("Motivo: "+reason,13,Color.rgb(248,113,113),false));
        c.addView(space(10));
        if(type.equals("profile_photo")){
            Button photo=primary(status.equals("missing")?"📷 Tirar foto real":"📷 Atualizar foto real");photo.setOnClickListener(v->showMandatoryProfilePhoto());c.addView(photo,match(dp(52)));
        }else{
            LinearLayout actions=horizontal();Button camera=primary("📷 Tirar foto");Button file=darkButton("📁 Arquivo / PDF");actions.addView(camera,new LinearLayout.LayoutParams(0,dp(52),1));actions.addView(spaceH(8));actions.addView(file,new LinearLayout.LayoutParams(0,dp(52),1));c.addView(actions);
            camera.setOnClickListener(v->openDocumentCamera(type));file.setOnClickListener(v->openDocumentFile(type));
        }
        return c;
    }

    private void openDocumentCamera(String type){
        try{
            File dir=new File(getCacheDir(),"document-camera");if(!dir.exists()&&!dir.mkdirs())throw new Exception("Não foi possível preparar a câmera.");
            pendingDocumentType=type;pendingDocumentCameraFile=new File(dir,type+"-"+System.currentTimeMillis()+".jpg");pendingDocumentCameraUri=FileProvider.getUriForFile(this,getPackageName()+".fileprovider",pendingDocumentCameraFile);
            Intent intent=new Intent(MediaStore.ACTION_IMAGE_CAPTURE);intent.putExtra(MediaStore.EXTRA_OUTPUT,pendingDocumentCameraUri);intent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION|Intent.FLAG_GRANT_READ_URI_PERMISSION);
            if(intent.resolveActivity(getPackageManager())==null)throw new Exception("Nenhum aplicativo de câmera disponível.");startActivityForResult(intent,REQ_DRIVER_DOC_CAMERA);
        }catch(Exception e){clearPendingDocumentCapture();toast(msg(e));}
    }

    private void openDocumentFile(String type){
        pendingDocumentType=type;Intent intent=new Intent(Intent.ACTION_OPEN_DOCUMENT);intent.addCategory(Intent.CATEGORY_OPENABLE);intent.setType("*/*");intent.putExtra(Intent.EXTRA_MIME_TYPES,new String[]{"image/jpeg","image/png","image/webp","application/pdf"});startActivityForResult(intent,REQ_DRIVER_DOC_FILE);
    }

    private void clearPendingDocumentCapture(){pendingDocumentType=null;pendingDocumentCameraUri=null;pendingDocumentCameraFile=null;}

    private byte[] readDocumentUri(Uri uri) throws Exception{
        try(InputStream in=getContentResolver().openInputStream(uri)){if(in==null)throw new Exception("Não foi possível abrir o arquivo.");ByteArrayOutputStream out=new ByteArrayOutputStream();byte[] buffer=new byte[8192];int n,total=0;while((n=in.read(buffer))!=-1){total+=n;if(total>12*1024*1024)throw new Exception("O arquivo deve ter no máximo 12 MB.");out.write(buffer,0,n);}return out.toByteArray();}
    }

    private byte[] cameraDocumentBytes(File file) throws Exception{
        BitmapFactory.Options bounds=new BitmapFactory.Options();bounds.inJustDecodeBounds=true;BitmapFactory.decodeFile(file.getAbsolutePath(),bounds);int sample=1;while(bounds.outWidth/sample>2600||bounds.outHeight/sample>2600)sample*=2;BitmapFactory.Options opts=new BitmapFactory.Options();opts.inSampleSize=sample;Bitmap photo=BitmapFactory.decodeFile(file.getAbsolutePath(),opts);if(photo==null)throw new Exception("Não foi possível processar a foto.");ByteArrayOutputStream out=new ByteArrayOutputStream();if(!photo.compress(Bitmap.CompressFormat.JPEG,88,out))throw new Exception("Não foi possível salvar a foto.");photo.recycle();return out.toByteArray();
    }
'''
if old_docs not in text: raise SystemExit('showDocuments original não encontrado')
text=text.replace(old_docs,new_docs,1)

build_path=Path('app/build.gradle');build=build_path.read_text(encoding='utf-8');m=re.search(r'versionCode\s+(\d+)',build)
if m: build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '0.9-prime'",build,count=1);build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Motorista v0.9 PRIME: documentos com câmera, arquivo/PDF e status completos.')
