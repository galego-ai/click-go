create extension if not exists pg_net with schema extensions;

create table if not exists public.device_push_tokens(
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  platform text not null default 'android' check (platform in ('android','ios','web')),
  app_kind text not null check (app_kind in ('driver','passenger','admin','franchise','web')),
  token text not null unique,
  active boolean not null default true,
  last_seen_at timestamptz not null default now(),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists device_push_tokens_user_active_idx on public.device_push_tokens(user_id,active);
alter table public.device_push_tokens enable row level security;
drop policy if exists device_push_tokens_owner_select on public.device_push_tokens;
create policy device_push_tokens_owner_select on public.device_push_tokens for select to authenticated using ((select auth.uid())=user_id);
revoke insert,update,delete on public.device_push_tokens from anon,authenticated;
grant select on public.device_push_tokens to authenticated;

create table if not exists public.push_delivery_queue(
  notification_id bigint primary key references public.user_notifications(id) on delete cascade,
  status text not null default 'queued' check (status in ('queued','sent','partial','failed','no_devices','pending_fcm_configuration')),
  attempts integer not null default 0,
  sent_count integer not null default 0,
  failed_count integer not null default 0,
  last_error text,
  updated_at timestamptz not null default now()
);
alter table public.push_delivery_queue enable row level security;
revoke all on public.push_delivery_queue from anon,authenticated;

create table if not exists public.app_internal_secrets(
  key text primary key,
  value text not null,
  created_at timestamptz not null default now()
);
alter table public.app_internal_secrets enable row level security;
revoke all on public.app_internal_secrets from anon,authenticated;
insert into public.app_internal_secrets(key,value)
values('push_dispatch_secret',encode(gen_random_bytes(32),'hex'))
on conflict(key) do nothing;

create or replace function public.register_device_push_token(p_token text,p_app_kind text,p_platform text default 'android') returns uuid
language plpgsql security definer set search_path to 'public','pg_temp' as $$
declare v_uid uuid:=auth.uid(); v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if length(trim(coalesce(p_token,'')))<20 then raise exception 'Token push inválido'; end if;
  if p_app_kind not in ('driver','passenger','admin','franchise','web') then raise exception 'Aplicativo inválido'; end if;
  if p_platform not in ('android','ios','web') then raise exception 'Plataforma inválida'; end if;
  insert into public.device_push_tokens(user_id,platform,app_kind,token,active,last_seen_at,updated_at)
  values(v_uid,p_platform,p_app_kind,trim(p_token),true,now(),now())
  on conflict(token) do update set user_id=excluded.user_id,platform=excluded.platform,app_kind=excluded.app_kind,active=true,last_seen_at=now(),updated_at=now()
  returning id into v_id;
  return v_id;
end;$$;
revoke all on function public.register_device_push_token(text,text,text) from public,anon;
grant execute on function public.register_device_push_token(text,text,text) to authenticated;

create or replace function public.unregister_device_push_token(p_token text) returns boolean
language plpgsql security definer set search_path to 'public','pg_temp' as $$
declare v_uid uuid:=auth.uid(); v_count integer;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  update public.device_push_tokens set active=false,updated_at=now() where user_id=v_uid and token=p_token and active=true;
  get diagnostics v_count=row_count;
  return v_count>0;
end;$$;
revoke all on function public.unregister_device_push_token(text) from public,anon;
grant execute on function public.unregister_device_push_token(text) to authenticated;

create or replace function public.enqueue_user_notification_push() returns trigger
language plpgsql security definer set search_path to 'public','extensions','pg_temp' as $$
declare v_secret text;
begin
  if not exists(select 1 from public.device_push_tokens t where t.user_id=new.user_id and t.active=true) then return new; end if;
  insert into public.push_delivery_queue(notification_id,status,updated_at) values(new.id,'queued',now()) on conflict(notification_id) do nothing;
  select value into v_secret from public.app_internal_secrets where key='push_dispatch_secret';
  if v_secret is not null then
    perform net.http_post(
      url:='https://kyaewidapnggmhbsrqch.supabase.co/functions/v1/push-notifications',
      headers:=jsonb_build_object('Content-Type','application/json','x-clickgo-internal-secret',v_secret),
      body:=jsonb_build_object('notification_id',new.id),
      timeout_milliseconds:=5000
    );
  end if;
  return new;
end;$$;
revoke all on function public.enqueue_user_notification_push() from public,anon,authenticated;
drop trigger if exists trg_enqueue_user_notification_push on public.user_notifications;
create trigger trg_enqueue_user_notification_push after insert on public.user_notifications for each row execute function public.enqueue_user_notification_push();
