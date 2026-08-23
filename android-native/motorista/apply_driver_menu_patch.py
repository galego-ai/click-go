from pathlib import Path

path=Path('app/src/main/java/com/clickgo/motorista/MainActivity.java')
text=path.read_text(encoding='utf-8')

def repl(old,new,name):
    global text
    if old not in text:
        raise SystemExit(f'Trecho não encontrado: {name}')
    text=text.replace(old,new,1)

# Troca o botão Sair do cabeçalho por menu completo.
repl('''        top.addView(id,new LinearLayout.LayoutParams(0,dp(58),1)); Button logout = darkButton("Sair"); top.addView(logout,new LinearLayout.LayoutParams(dp(72),dp(46))); root.addView(top); root.addView(space(14));\n''','''        top.addView(id,new LinearLayout.LayoutParams(0,dp(58),1)); Button menuBtn = darkButton("☰ Menu"); top.addView(menuBtn,new LinearLayout.LayoutParams(dp(96),dp(46))); root.addView(top); root.addView(space(14));\n''','botão menu')

repl('''        logout.setOnClickListener(v -> logout()); onlineBtn.setOnClickListener(v -> toggleOnline()); setContentView(scroll(root,BLACK));\n''','''        menuBtn.setOnClickListener(v -> showDriverMenu()); onlineBtn.setOnClickListener(v -> toggleOnline()); setContentView(scroll(root,BLACK));\n''','clique menu')

marker='''    private void releaseMap(){MapView old=map;map=null;if(old!=null){try{old.onPause();}catch(Exception ignored){}try{old.onDetach();}catch(Exception ignored){}}}\n'''
if marker not in text:
    raise SystemExit('Ponto de inserção do menu não encontrado')

methods=r'''    private void showDriverMenu(){
        stopPolling(); releaseMap();
        LinearLayout body=vertical(BLACK); body.setPadding(dp(18),dp(24),dp(18),dp(26));
        LinearLayout top=horizontal(); top.setGravity(Gravity.CENTER_VERTICAL);
        Button back=darkButton("← Início"); top.addView(back,new LinearLayout.LayoutParams(dp(110),dp(50)));
        TextView title=text("Menu do motorista",24,Color.WHITE,true); title.setPadding(dp(14),0,0,0); top.addView(title,new LinearLayout.LayoutParams(0,dp(50),1)); body.addView(top); body.addView(space(16));
        body.addView(menuCard("🚘", "Corridas", "Corrida atual e tela principal", () -> showHome())); body.addView(space(9));
        body.addView(menuCard("👤", "Meu perfil", "Foto, dados, avaliação e situação cadastral", () -> showDriverProfile())); body.addView(space(9));
        body.addView(menuCard("🕘", "Histórico de corridas", "Corridas concluídas e canceladas", () -> showRideHistory())); body.addView(space(9));
        body.addView(menuCard("💰", "Ganhos e carteira", "Saldo operacional e forma de cobrança", () -> showEarnings())); body.addView(space(9));
        body.addView(menuCard("💳", "Pagamentos", "Mensalidade, taxa por corrida e maquininha", () -> showPaymentSettings())); body.addView(space(9));
        body.addView(menuCard("📄", "Documentos", "Foto real, CNH e documentos enviados", () -> showDocuments())); body.addView(space(9));
        body.addView(menuCard("🛟", "Suporte", "Chamados e contato com a operação", () -> showSupport())); body.addView(space(9));
        body.addView(menuCard("⚙", "Configurações", "Senha, conta e segurança", () -> showDriverSettings())); body.addView(space(14));
        Button exit=darkButton("Sair da conta"); exit.setTextColor(Color.rgb(248,113,113)); body.addView(exit,match(dp(56)));
        back.setOnClickListener(v->showHome()); exit.setOnClickListener(v->logout());
        setContentView(scroll(body,BLACK));
    }

    private View menuCard(String icon,String title,String subtitle,Runnable action){
        LinearLayout card=card(DARK,Color.rgb(55,55,55)); card.setOrientation(LinearLayout.HORIZONTAL); card.setGravity(Gravity.CENTER_VERTICAL);
        TextView ico=text(icon,25,Color.WHITE,false); ico.setGravity(Gravity.CENTER); card.addView(ico,new LinearLayout.LayoutParams(dp(48),dp(56)));
        LinearLayout copy=vertical(Color.TRANSPARENT); copy.setPadding(dp(8),0,0,0); copy.addView(text(title,17,Color.WHITE,true)); copy.addView(text(subtitle,12,GRAY,false)); card.addView(copy,new LinearLayout.LayoutParams(0,dp(60),1));
        TextView arrow=text("›",28,YELLOW,true); arrow.setGravity(Gravity.CENTER); card.addView(arrow,new LinearLayout.LayoutParams(dp(36),dp(56))); card.setOnClickListener(v->action.run()); return card;
    }

    private LinearLayout pageShell(String title,String subtitle){
        stopPolling(); releaseMap();
        LinearLayout body=vertical(BLACK); body.setPadding(dp(18),dp(24),dp(18),dp(26));
        Button back=darkButton("← Menu"); back.setOnClickListener(v->showDriverMenu()); body.addView(back,new LinearLayout.LayoutParams(dp(110),dp(50))); body.addView(space(16));
        body.addView(text(title,28,Color.WHITE,true)); if(subtitle!=null&&!subtitle.isBlank())body.addView(text(subtitle,14,GRAY,false)); body.addView(space(16)); return body;
    }

    private void showDriverProfile(){
        LinearLayout body=pageShell("Meu perfil","Dados visíveis no app e situação junto à franquia."); TextView loading=text("Carregando perfil…",14,GRAY,false); body.addView(loading); setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONObject p=DriverRepository.profile(token),d=DriverRepository.driver(token);String name=p.optString("full_name",fullName),email=p.optString("email",""),phone=p.optString("phone","");String status=d.optString("status",driverStatus);double r=d.optDouble("rating",rating);Bitmap av=ProfileAvatar.download(p.optString("avatar_url",""));ui.post(()->{body.removeView(loading);LinearLayout card=card(DARK,Color.rgb(55,55,55));ImageView photo=new ImageView(this);photo.setImageDrawable(ProfileAvatar.circleDrawable(this,av,name));photo.setScaleType(ImageView.ScaleType.CENTER_CROP);LinearLayout row=horizontal();row.setGravity(Gravity.CENTER_VERTICAL);row.addView(photo,new LinearLayout.LayoutParams(dp(86),dp(86)));LinearLayout info=vertical(Color.TRANSPARENT);info.setPadding(dp(14),0,0,0);info.addView(text(name,21,Color.WHITE,true));info.addView(text(email.isBlank()?"E-mail não informado":email,13,GRAY,false));info.addView(text(phone.isBlank()?"Telefone não informado":phone,13,GRAY,false));row.addView(info,new LinearLayout.LayoutParams(0,dp(90),1));card.addView(row);card.addView(space(12));card.addView(text("Avaliação: "+String.format(Locale.getDefault(),"%.1f",r),15,YELLOW,true));card.addView(text("Situação: "+statusLabelFor(status),14,status.equals("approved")?Color.rgb(74,222,128):YELLOW,true));body.addView(card);});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void showRideHistory(){
        LinearLayout body=pageShell("Histórico de corridas","Últimas corridas vinculadas ao seu cadastro."); TextView loading=text("Carregando histórico…",14,GRAY,false); body.addView(loading); setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONArray rows=DriverRepository.rideHistory(token,userId);ui.post(()->{body.removeView(loading);if(rows.length()==0){body.addView(text("Nenhuma corrida no histórico.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject r=rows.optJSONObject(i);if(r==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));String status=r.optString("status","");String date=r.optString("completed_at",r.optString("cancelled_at",r.optString("requested_at","")));double fare=r.optDouble("final_fare",r.optDouble("estimated_fare",0));c.addView(text(status.equals("completed")?"Corrida concluída":"Corrida "+status,15,status.equals("completed")?Color.rgb(74,222,128):YELLOW,true));c.addView(text(shortDate(date),12,GRAY,false));c.addView(space(6));c.addView(text("De: "+r.optString("origin_label",""),14,Color.WHITE,false));c.addView(text("Para: "+r.optString("destination_label",""),14,GRAY,false));if(fare>0)c.addView(text("Valor: "+money(fare),15,YELLOW,true));body.addView(c);body.addView(space(9));}});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void showEarnings(){
        LinearLayout body=pageShell("Ganhos e carteira","Resumo operacional do motorista.");TextView loading=text("Carregando carteira…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONObject w=DriverRepository.wallet(token);JSONArray history=DriverRepository.rideHistory(token,userId);double total=0;int completed=0;for(int i=0;i<history.length();i++){JSONObject r=history.optJSONObject(i);if(r!=null&&"completed".equals(r.optString("status"))){completed++;total+=r.optDouble("final_fare",0);}}double bal=w.optDouble("operational_balance",balance);String mode=w.optString("billing_mode",billingMode);double finalTotal=total;int finalCompleted=completed;ui.post(()->{body.removeView(loading);LinearLayout c=card(DARK,Color.rgb(55,55,55));c.addView(text("Saldo operacional",13,GRAY,false));c.addView(text(money(bal),30,YELLOW,true));c.addView(space(10));c.addView(text(mode.equals("monthly")?"Cobrança: mensalidade":"Cobrança: taxa por corrida",14,Color.WHITE,true));body.addView(c);body.addView(space(10));LinearLayout stats=card(DARK,Color.rgb(55,55,55));stats.addView(text("Últimas corridas concluídas: "+finalCompleted,15,Color.WHITE,true));stats.addView(text("Valor bruto somado no histórico: "+money(finalTotal),14,GRAY,false));body.addView(stats);});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void showPaymentSettings(){
        LinearLayout body=pageShell("Pagamentos","Regras aplicadas ao seu cadastro pela franquia.");TextView loading=text("Carregando configurações…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONObject d=DriverRepository.driver(token);JSONObject b=DriverRepository.billing(token);ui.post(()->{body.removeView(loading);LinearLayout c=card(DARK,Color.rgb(55,55,55));String mode=b.optString("billing_mode","wallet_per_ride");c.addView(text(mode.equals("monthly")?"Plano mensal":"Taxa por corrida",19,YELLOW,true));if(mode.equals("monthly")){c.addView(text("Mensalidade: "+money(b.optDouble("monthly_fee",0)),14,Color.WHITE,false));c.addView(text("Dia de vencimento: "+b.optInt("monthly_due_day",1),14,GRAY,false));String paid=b.optString("monthly_paid_until","");if(!paid.isBlank())c.addView(text("Pago até: "+paid,14,GRAY,false));}else c.addView(text("Taxa por corrida: "+money(b.optDouble("per_ride_fee",0)),14,Color.WHITE,false));body.addView(c);body.addView(space(10));LinearLayout machine=card(DARK,Color.rgb(55,55,55));boolean has=d.optBoolean("has_card_machine",false),approved=d.optBoolean("card_machine_approved",false);machine.addView(text("Maquininha de cartão",17,Color.WHITE,true));machine.addView(text(has?(approved?"✓ Cadastrada e aprovada":"Cadastrada, aguardando aprovação"):"Não cadastrada",14,has&&approved?Color.rgb(74,222,128):GRAY,true));body.addView(machine);});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void showDocuments(){
        LinearLayout body=pageShell("Meus documentos","A foto real de perfil e os documentos precisam ser aprovados pelo franqueado.");TextView loading=text("Carregando documentos…",14,GRAY,false);body.addView(loading);setContentView(scroll(body,BLACK));
        io.execute(()->{try{JSONArray rows=DriverRepository.documents(token,userId);ui.post(()->{body.removeView(loading);if(rows.length()==0){body.addView(text("Nenhum documento enviado.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject d=rows.optJSONObject(i);if(d==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));String type=d.optString("document_type","Documento"),status=d.optString("status","pending");c.addView(text(type.equals("profile_photo")?"📷 Foto real de perfil":type,16,Color.WHITE,true));c.addView(text(statusLabelForDocument(status),14,status.equals("approved")?Color.rgb(74,222,128):status.equals("rejected")?Color.rgb(248,113,113):YELLOW,true));String reason=d.optString("rejection_reason","");if(!reason.isBlank())c.addView(text("Motivo: "+reason,12,Color.rgb(248,113,113),false));body.addView(c);body.addView(space(8));}});}catch(Exception e){ui.post(()->loading.setText(msg(e)));}});
    }

    private void showSupport(){
        LinearLayout body=pageShell("Suporte","Abra chamados para a operação da sua franquia.");Button create=primary("+ Abrir novo chamado");body.addView(create,match(dp(56)));body.addView(space(14));LinearLayout list=vertical(BLACK);body.addView(list);create.setOnClickListener(v->openSupportDialog());setContentView(scroll(body,BLACK));loadSupportTickets(list);
    }

    private void loadSupportTickets(LinearLayout list){
        list.removeAllViews();TextView loading=text("Carregando chamados…",14,GRAY,false);list.addView(loading);io.execute(()->{try{JSONArray rows=DriverRepository.supportTickets(token,userId);ui.post(()->{list.removeAllViews();if(rows.length()==0){list.addView(text("Nenhum chamado aberto.",14,GRAY,false));return;}for(int i=0;i<rows.length();i++){JSONObject t=rows.optJSONObject(i);if(t==null)continue;LinearLayout c=card(DARK,Color.rgb(55,55,55));c.addView(text(t.optString("subject","Chamado"),16,Color.WHITE,true));c.addView(text("Status: "+t.optString("status","open"),13,YELLOW,true));c.addView(text(shortDate(t.optString("created_at","")),12,GRAY,false));c.addView(text(t.optString("description",""),13,GRAY,false));list.addView(c);list.addView(space(8));}});}catch(Exception e){ui.post(()->{list.removeAllViews();list.addView(text(msg(e),13,Color.rgb(248,113,113),false));});}});
    }

    private void openSupportDialog(){
        LinearLayout wrap=vertical(Color.WHITE);wrap.setPadding(dp(18),dp(16),dp(18),dp(10));wrap.addView(text("Novo chamado",22,BLACK,true));wrap.addView(space(10));EditText subject=new EditText(this);subject.setHint("Assunto");subject.setTextColor(BLACK);subject.setHintTextColor(Color.GRAY);subject.setSingleLine(true);subject.setBackground(round(Color.rgb(245,245,245),12,Color.rgb(220,220,220)));subject.setPadding(dp(12),0,dp(12),0);wrap.addView(subject,match(dp(54)));wrap.addView(space(8));EditText description=new EditText(this);description.setHint("Descreva o que aconteceu");description.setTextColor(BLACK);description.setHintTextColor(Color.GRAY);description.setMinLines(4);description.setGravity(Gravity.TOP);description.setPadding(dp(12),dp(10),dp(12),dp(10));description.setBackground(round(Color.rgb(245,245,245),12,Color.rgb(220,220,220)));wrap.addView(description,new LinearLayout.LayoutParams(-1,dp(130)));new AlertDialog.Builder(this).setView(wrap).setNegativeButton("Cancelar",null).setPositiveButton("Enviar",(dialog,which)->{String s=subject.getText().toString().trim(),d=description.getText().toString().trim();if(s.isBlank()||d.isBlank()){toast("Informe assunto e descrição.");return;}io.execute(()->{try{DriverRepository.createSupportTicket(token,userId,s,d);ui.post(()->{toast("Chamado aberto.");showSupport();});}catch(Exception e){ui.post(()->toast(msg(e)));}});}).show();
    }

    private void showDriverSettings(){
        LinearLayout body=pageShell("Configurações","Segurança e acesso à sua conta.");Button password=primary("Redefinir minha senha por e-mail");body.addView(password,match(dp(56)));body.addView(space(10));Button home=darkButton("Voltar ao início");body.addView(home,match(dp(56)));body.addView(space(10));Button exit=darkButton("Sair da conta");exit.setTextColor(Color.rgb(248,113,113));body.addView(exit,match(dp(56)));password.setOnClickListener(v->io.execute(()->{try{JSONObject p=DriverRepository.profile(token);String email=p.optString("email","");ui.post(()->{if(email.isBlank())toast("Seu perfil não possui e-mail cadastrado.");else recover(email);});}catch(Exception e){ui.post(()->toast(msg(e)));}}));home.setOnClickListener(v->showHome());exit.setOnClickListener(v->logout());setContentView(scroll(body,BLACK));
    }

    private String shortDate(String iso){if(iso==null||iso.isBlank())return "";String s=iso.replace('T',' ');return s.length()>16?s.substring(0,16):s;}
    private String statusLabelFor(String s){return "approved".equals(s)?"Aprovado":"rejected".equals(s)?"Reprovado":"blocked".equals(s)?"Bloqueado":"Aguardando aprovação";}
    private String statusLabelForDocument(String s){return "approved".equals(s)?"✓ Aprovado":"rejected".equals(s)?"✕ Reprovado":"⏳ Aguardando análise";}

'''
text=text.replace(marker,methods+marker,1)

build_path=Path('app/build.gradle')
build=build_path.read_text(encoding='utf-8')
build=build.replace('versionCode 4','versionCode 5',1).replace("versionName '0.4-native-beta'","versionName '0.5-native-beta'",1)
build_path.write_text(build,encoding='utf-8')
path.write_text(text,encoding='utf-8')
print('Motorista v0.5: menu completo aplicado.')
