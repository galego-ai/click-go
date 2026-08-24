create or replace function private.guard_ride_chat_message()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_message text := btrim(coalesce(new.message, ''));
begin
  if v_message = '' then raise exception 'Mensagem vazia.' using errcode = '22023'; end if;
  if char_length(v_message) > 800 then raise exception 'Mensagem muito longa.' using errcode = '22023'; end if;
  if v_message ~* '[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}' then raise exception 'Não é permitido compartilhar e-mail pelo chat.' using errcode = '22023'; end if;
  if v_message ~ '(\+?[0-9][0-9 ()\.\-]{7,}[0-9])' then raise exception 'Não é permitido compartilhar telefone pelo chat.' using errcode = '22023'; end if;
  if v_message ~* '(https?://|www\.)' then raise exception 'Não é permitido compartilhar links de contato pelo chat.' using errcode = '22023'; end if;
  new.message := v_message;
  new.message_type := 'text';
  return new;
end;
$$;

revoke all on function private.guard_ride_chat_message() from public, anon, authenticated;

drop trigger if exists trg_guard_ride_chat_message on public.ride_chat_messages;
create trigger trg_guard_ride_chat_message before insert or update of message on public.ride_chat_messages for each row execute function private.guard_ride_chat_message();

create or replace function public.send_ride_chat_message(p_ride_id uuid,p_message text)
returns public.ride_chat_messages
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_uid uuid := auth.uid();
  v_ride public.rides%rowtype;
  v_row public.ride_chat_messages%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado.' using errcode = '42501'; end if;
  select * into v_ride from public.rides r where r.id = p_ride_id;
  if not found then raise exception 'Corrida não encontrada.' using errcode = 'P0002'; end if;
  if v_uid <> v_ride.passenger_id and v_uid is distinct from v_ride.driver_id then raise exception 'Você não participa desta corrida.' using errcode = '42501'; end if;
  if v_ride.driver_id is null then raise exception 'Aguarde um motorista aceitar a corrida.' using errcode = '22023'; end if;
  if v_ride.status not in ('accepted','driver_arriving','in_progress') then raise exception 'O chat fica disponível apenas durante a corrida.' using errcode = '22023'; end if;
  insert into public.ride_chat_messages(ride_id,sender_id,message,message_type)
  values(p_ride_id,v_uid,p_message,'text') returning * into v_row;
  return v_row;
end;
$$;

revoke all on function public.send_ride_chat_message(uuid,text) from public, anon;
grant execute on function public.send_ride_chat_message(uuid,text) to authenticated;
revoke insert, update, delete on public.ride_chat_messages from anon, authenticated;
grant select on public.ride_chat_messages to authenticated;
create index if not exists ride_chat_messages_ride_created_idx on public.ride_chat_messages(ride_id,created_at);

create or replace function private.notify_ride_chat_message()
returns trigger
language plpgsql
security definer
set search_path = ''
as $$
declare
  v_ride public.rides%rowtype;
  v_recipient uuid;
begin
  select * into v_ride from public.rides where id = new.ride_id;
  if not found then return new; end if;
  if new.sender_id = v_ride.passenger_id then v_recipient := v_ride.driver_id;
  elsif new.sender_id = v_ride.driver_id then v_recipient := v_ride.passenger_id; end if;
  if v_recipient is not null then
    perform public.enqueue_user_notification(v_recipient,'ride_chat','Nova mensagem da corrida',left(new.message,140),new.ride_id,jsonb_build_object('message_id',new.id,'ride_id',new.ride_id));
  end if;
  return new;
end;
$$;

revoke all on function private.notify_ride_chat_message() from public, anon, authenticated;
drop trigger if exists trg_notify_ride_chat_message on public.ride_chat_messages;
create trigger trg_notify_ride_chat_message after insert on public.ride_chat_messages for each row execute function private.notify_ride_chat_message();
