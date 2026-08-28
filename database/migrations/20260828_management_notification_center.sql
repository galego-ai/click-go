-- CLICK-GO: Central de notificações administrativas da Matriz e Franqueado.
-- Permite enviar para Motoristas, Passageiros, ambos os apps ou destinatários específicos.
-- Campanhas administrativas ficam separadas das comunicações privadas de corrida.

create table if not exists public.management_notification_campaigns (
  id uuid primary key default gen_random_uuid(),
  actor_id uuid not null references public.profiles(id) on delete restrict,
  scope text not null check (scope in ('matrix','franchise')),
  franchise_id uuid null references public.franchises(id) on delete set null,
  target_app text not null check (target_app in ('driver','passenger','both')),
  selection_mode text not null check (selection_mode in ('all','selected')),
  title text not null,
  body text not null,
  recipient_count integer not null default 0 check (recipient_count >= 0),
  created_at timestamptz not null default now()
);

alter table public.management_notification_campaigns enable row level security;
revoke all on public.management_notification_campaigns from public, anon, authenticated;

create or replace function public.management_notification_recipients(
  p_target_app text default 'both'
) returns table(
  user_id uuid,
  full_name text,
  app_kind text,
  city_name text,
  city_state text,
  has_active_device boolean
)
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_role text := public.current_active_management_role();
  v_fid uuid;
  v_target text := lower(coalesce(p_target_app,'both'));
begin
  if v_target not in ('driver','passenger','both') then
    raise exception 'Aplicativo de destino inválido';
  end if;

  if v_role='super_admin' then
    v_fid:=null;
  elsif v_role='franchise_admin' then
    v_fid:=public.current_profile_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
  elsif v_role='operator' then
    if not (public.staff_has_permission('marketing') or public.staff_has_permission('support')) then
      raise exception 'Sem permissão para enviar notificações';
    end if;
    v_fid:=public.staff_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
  else
    raise exception 'Acesso não autorizado';
  end if;

  return query
  with driver_rows as (
    select
      p.id as user_id,
      coalesce(nullif(btrim(p.full_name),''),coalesce(p.email,'Motorista CLICK-GO')) as full_name,
      'driver'::text as app_kind,
      c.name as city_name,
      c.state as city_state,
      exists(
        select 1 from public.device_push_tokens t
        where t.user_id=p.id and t.active=true and t.app_kind='driver'
      ) as has_active_device
    from public.profiles p
    join public.drivers d on d.id=p.id
    left join public.cities c on c.id=coalesce(d.city_id,p.city_id)
    where p.active=true
      and p.role='driver'
      and (v_role='super_admin' or d.franchise_id=v_fid)
      and v_target in ('driver','both')
  ), passenger_rows as (
    select
      p.id as user_id,
      coalesce(nullif(btrim(p.full_name),''),coalesce(p.email,'Passageiro CLICK-GO')) as full_name,
      'passenger'::text as app_kind,
      c.name as city_name,
      c.state as city_state,
      exists(
        select 1 from public.device_push_tokens t
        where t.user_id=p.id and t.active=true and t.app_kind='passenger'
      ) as has_active_device
    from public.profiles p
    left join public.cities c on c.id=p.city_id
    where p.active=true
      and p.role='passenger'
      and v_target in ('passenger','both')
      and (
        v_role='super_admin'
        or p.franchise_id=v_fid
        or exists(
          select 1 from public.rides r
          where r.passenger_id=p.id and r.franchise_id=v_fid
        )
      )
  )
  select * from driver_rows
  union all
  select * from passenger_rows
  order by app_kind,full_name;
end;
$$;
revoke all on function public.management_notification_recipients(text) from public,anon;
grant execute on function public.management_notification_recipients(text) to authenticated;

create or replace function public.send_management_notification(
  p_target_app text,
  p_title text,
  p_body text,
  p_recipient_ids uuid[] default null
) returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_actor uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_scope text;
  v_target text:=lower(coalesce(p_target_app,''));
  v_title text:=btrim(coalesce(p_title,''));
  v_body text:=btrim(coalesce(p_body,''));
  v_selected boolean:=coalesce(cardinality(p_recipient_ids),0)>0;
  v_campaign uuid;
  v_count integer:=0;
  r record;
begin
  if v_actor is null then raise exception 'Não autenticado'; end if;
  if v_target not in ('driver','passenger','both') then raise exception 'Aplicativo de destino inválido'; end if;
  if length(v_title)<2 or length(v_title)>120 then raise exception 'Título deve ter entre 2 e 120 caracteres'; end if;
  if length(v_body)<2 or length(v_body)>500 then raise exception 'Mensagem deve ter entre 2 e 500 caracteres'; end if;

  if v_role='super_admin' then
    v_scope:='matrix';
    v_fid:=null;
  elsif v_role='franchise_admin' then
    v_scope:='franchise';
    v_fid:=public.current_profile_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
  elsif v_role='operator' then
    if not (public.staff_has_permission('marketing') or public.staff_has_permission('support')) then
      raise exception 'Sem permissão para enviar notificações';
    end if;
    v_scope:='franchise';
    v_fid:=public.staff_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
  else
    raise exception 'Acesso não autorizado';
  end if;

  insert into public.management_notification_campaigns(
    actor_id,scope,franchise_id,target_app,selection_mode,title,body
  ) values(
    v_actor,v_scope,v_fid,v_target,case when v_selected then 'selected' else 'all' end,v_title,v_body
  ) returning id into v_campaign;

  for r in
    with driver_rows as (
      select p.id as user_id,'driver'::text as app_kind
      from public.profiles p
      join public.drivers d on d.id=p.id
      where p.active=true
        and p.role='driver'
        and (v_role='super_admin' or d.franchise_id=v_fid)
        and v_target in ('driver','both')
        and exists(
          select 1 from public.device_push_tokens t
          where t.user_id=p.id and t.active=true and t.app_kind='driver'
        )
    ), passenger_rows as (
      select p.id as user_id,'passenger'::text as app_kind
      from public.profiles p
      where p.active=true
        and p.role='passenger'
        and v_target in ('passenger','both')
        and (
          v_role='super_admin'
          or p.franchise_id=v_fid
          or exists(
            select 1 from public.rides rr
            where rr.passenger_id=p.id and rr.franchise_id=v_fid
          )
        )
        and exists(
          select 1 from public.device_push_tokens t
          where t.user_id=p.id and t.active=true and t.app_kind='passenger'
        )
    ), recipients as (
      select * from driver_rows
      union all
      select * from passenger_rows
    )
    select distinct user_id,app_kind
    from recipients
    where not v_selected or user_id=any(p_recipient_ids)
  loop
    perform public.enqueue_user_notification(
      r.user_id,
      'management_broadcast',
      v_title,
      v_body,
      null,
      jsonb_build_object(
        'campaign_id',v_campaign,
        'target_app',r.app_kind,
        'scope',v_scope,
        'franchise_id',v_fid
      )
    );
    v_count:=v_count+1;
  end loop;

  if v_count=0 then
    raise exception 'Nenhum destinatário com aplicativo ativo foi encontrado';
  end if;

  update public.management_notification_campaigns
  set recipient_count=v_count
  where id=v_campaign;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    v_actor,
    'send_management_notification',
    'notification_campaign',
    v_campaign::text,
    jsonb_build_object(
      'scope',v_scope,
      'franchise_id',v_fid,
      'target_app',v_target,
      'selection_mode',case when v_selected then 'selected' else 'all' end,
      'recipient_count',v_count
    )
  );

  return jsonb_build_object(
    'ok',true,
    'campaign_id',v_campaign,
    'recipient_count',v_count,
    'target_app',v_target,
    'scope',v_scope
  );
end;
$$;
revoke all on function public.send_management_notification(text,text,text,uuid[]) from public,anon;
grant execute on function public.send_management_notification(text,text,text,uuid[]) to authenticated;

create or replace function public.list_management_notification_campaigns(
  p_limit integer default 20
) returns table(
  id uuid,
  target_app text,
  selection_mode text,
  title text,
  body text,
  recipient_count integer,
  scope text,
  created_at timestamptz
)
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_role text:=public.current_active_management_role();
  v_fid uuid;
begin
  if v_role='super_admin' then
    v_fid:=null;
  elsif v_role='franchise_admin' then
    v_fid:=public.current_profile_franchise_id();
  elsif v_role='operator' then
    if not (public.staff_has_permission('marketing') or public.staff_has_permission('support')) then
      raise exception 'Sem permissão para consultar notificações';
    end if;
    v_fid:=public.staff_franchise_id();
  else
    raise exception 'Acesso não autorizado';
  end if;

  return query
  select c.id,c.target_app,c.selection_mode,c.title,c.body,c.recipient_count,c.scope,c.created_at
  from public.management_notification_campaigns c
  where v_role='super_admin' or c.franchise_id=v_fid
  order by c.created_at desc
  limit greatest(1,least(coalesce(p_limit,20),100));
end;
$$;
revoke all on function public.list_management_notification_campaigns(integer) from public,anon;
grant execute on function public.list_management_notification_campaigns(integer) to authenticated;
