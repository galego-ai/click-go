from pathlib import Path
import re

main=Path('app/src/main/java/com/clickgo/passageiro/MainActivity.java')
build_path=Path('app/build.gradle')
text=main.read_text(encoding='utf-8')
build=build_path.read_text(encoding='utf-8')

# Botão de mensagens na tela da corrida ativa.
needle='''        Button share = primary("Compartilhar acompanhamento");\n        Button cancel = secondaryLight("CANCELAR CHAMADO / CORRIDA");\n        body.addView(share,lpMatch(dp(56)));\n        body.addView(space(8));\n        body.addView(cancel,lpMatch(dp(56)));\n        share.setOnClickListener(v -> shareActiveRide());\n        cancel.setOnClickListener(v -> previewCancel());'''
replacement='''        Button share = primary("Compartilhar acompanhamento");\n        Button chat = secondaryLight("💬 MENSAGENS");\n        Button cancel = secondaryLight("CANCELAR CHAMADO / CORRIDA");\n        body.addView(share,lpMatch(dp(56)));\n        body.addView(space(8));\n        body.addView(chat,lpMatch(dp(56)));\n        body.addView(space(8));\n        body.addView(cancel,lpMatch(dp(56)));\n        share.setOnClickListener(v -> shareActiveRide());\n        chat.setOnClickListener(v -> openRideChat(activeRideId));\n        cancel.setOnClickListener(v -> previewCancel());'''
if needle not in text: raise SystemExit('Ações da corrida ativa não encontradas')
text=text.replace(needle,replacement,1)

# Chat modal protegido; banco também rejeita telefone/e-mail/link.
anchor='''    private void previewCancel() {\n'''
chat=r'''    private boolean looksLikeContact(String value){
        if(value==null)return false;String s=value.trim();
        return s.matches("(?is).*[A-Z0-9._%+\\-]+@[A-Z0-9.\\-]+\\.[A-Z]{2,}.*")||s.matches("(?s).*(\\+?[0-9][0-9 ()\\.\\-]{7,}[0-9]).*")||s.matches("(?is).*(https?://|www\\.).*");
    }

    private void openRideChat(String rideId){
        if(rideId==null||rideId.isBlank()){toast("Aguarde a corrida ser criada.");return;}
        LinearLayout root=vertical(Color.WHITE);root.setPadding(dp(16),dp(14),dp(16),dp(12));root.addView(text("Mensagens da corrida",20,BLACK,true));root.addView(text("Por segurança, telefone, e-mail e links de contato não podem ser enviados.",12,Color.DKGRAY,false));root.addView(space(10));
        LinearLayout list=vertical(Color.WHITE);ScrollView sc=new ScrollView(this);sc.addView(list,new ScrollView.LayoutParams(-1,-2));root.addView(sc,new LinearLayout.LayoutParams(-1,dp(280)));root.addView(space(8));
        LinearLayout compose=horizontal();EditText input=editLight("Digite uma mensagem");input.setSingleLine(false);input.setMaxLines(3);Button send=primary("ENVIAR");compose.addView(input,new LinearLayout.LayoutParams(0,dp(58),1));compose.addView(spaceH(8));compose.addView(send,new LinearLayout.LayoutParams(dp(92),dp(58)));root.addView(compose);
        AlertDialog dialog=new AlertDialog.Builder(this).setView(root).setNegativeButton("Fechar",null).create();final Runnable[] poll={null};
        Runnable load=()->io.execute(()->{try{String uid=ensureUserId();JSONArray rows=new JSONArray(ApiClient.restGet("ride_chat_messages?ride_id=eq."+rideId+"&select=id,sender_id,message,created_at&order=created_at.asc&limit=100",token));ui.post(()->{if(!dialog.isShowing())return;list.removeAllViews();if(rows.length()==0)list.addView(text("Nenhuma mensagem ainda.",13,GRAY,false));for(int i=0;i<rows.length();i++){JSONObject m=rows.optJSONObject(i);if(m==null)continue;boolean mine=uid.equals(m.optString("sender_id",""));LinearLayout bubble=vertical(mine?Color.rgb(255,247,204):Color.rgb(242,242,242));bubble.setPadding(dp(10),dp(8),dp(10),dp(8));bubble.setBackground(round(mine?Color.rgb(255,247,204):Color.rgb(242,242,242),14,Color.rgb(225,225,225)));bubble.addView(text(m.optString("message",""),14,BLACK,false));bubble.addView(text(mine?"Você":"Motorista",10,Color.DKGRAY,true));LinearLayout.LayoutParams lp=new LinearLayout.LayoutParams(-1,-2);lp.setMargins(mine?dp(45):0,dp(4),mine?0:dp(45),dp(4));list.addView(bubble,lp);}sc.post(()->sc.fullScroll(View.FOCUS_DOWN));});}catch(Exception e){ui.post(()->{if(dialog.isShowing()&&list.getChildCount()==0)list.addView(text(message(e),12,Color.rgb(190,60,50),false));});}});
        poll[0]=new Runnable(){@Override public void run(){if(!dialog.isShowing())return;load.run();ui.postDelayed(this,1800);}};
        send.setOnClickListener(v->{String msg=input.getText().toString().trim();if(msg.isBlank())return;if(looksLikeContact(msg)){toast("Não é permitido enviar telefone, e-mail ou link de contato.");return;}send.setEnabled(false);io.execute(()->{try{ApiClient.rpc("send_ride_chat_message",new JSONObject().put("p_ride_id",rideId).put("p_message",msg),token);ui.post(()->{input.setText("");send.setEnabled(true);load.run();});}catch(Exception e){ui.post(()->{send.setEnabled(true);toast(message(e));});}});});
        dialog.setOnShowListener(x->ui.post(poll[0]));dialog.setOnDismissListener(x->{if(poll[0]!=null)ui.removeCallbacks(poll[0]);});dialog.show();
    }

'''
if 'private void openRideChat(String rideId)' not in text:
    if anchor not in text: raise SystemExit('previewCancel não encontrado')
    text=text.replace(anchor,chat+anchor,1)

m=re.search(r'versionCode\s+(\d+)',build)
if m:build=build[:m.start(1)]+str(int(m.group(1))+1)+build[m.end(1):]
build=re.sub(r"versionName\s+'[^']+'","versionName '2.15-prime'",build,count=1)
main.write_text(text,encoding='utf-8');build_path.write_text(build,encoding='utf-8')
print('Passageiro v2.15 PRIME: chat protegido motorista-passageiro aplicado.')
