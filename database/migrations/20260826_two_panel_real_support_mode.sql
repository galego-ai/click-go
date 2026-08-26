-- CLICK-GO: Modo Suporte real da Matriz, sem impersonação de conta do franqueado.

create unique index if not exists franchise_support_sessions_one_active_per_matrix_user
  on public.franchise_support_sessions(matrix_user_id)
  where active;

create or replace function public.matrix_start_support_session(
  p_franchise_id uuid,
  p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_name text;
  v_enabled boolean;
  v_session public.franchise_support_sessions%rowtype;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Informe o motivo do atendimento de suporte'; end if;

  select trade_name,support_mode_enabled
    into v_name,v_enabled
  from public.franchises
  where id=p_franchise_id and deleted_at is null;
  if not found then raise exception 'Franquia não encontrada'; end if;
  if not coalesce(v_enabled,false) then raise exception 'Modo Suporte não está habilitado para esta franquia'; end if;

  update public.franchise_support_sessions
     set active=false,ended_at=coalesce(ended_at,now())
   where matrix_user_id=auth.uid() and active;

  insert into public.franchise_support_sessions(franchise_id,matrix_user_id,reason,active,metadata)
  values(p_franchise_id,auth.uid(),v_reason,true,jsonb_build_object('source','matrix_support'))
  returning * into v_session;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'support_session_start','franchise_support_sessions',v_session.id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'franchise_name',v_name,'session_id',v_session.id,
      'reason',v_reason,'source','matrix_support','new_value',jsonb_build_object('active',true,'started_at',v_session.started_at)));

  return jsonb_build_object('id',v_session.id,'franchise_id',p_franchise_id,'franchise_name',v_name,
    'reason',v_reason,'started_at',v_session.started_at,'active',true);
end;
$$;
revoke all on function public.matrix_start_support_session(uuid,text) from public,anon;
grant execute on function public.matrix_start_support_session(uuid,text) to authenticated;

create or replace function public.matrix_end_support_session(p_session_id uuid default null)
returns jsonb
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_session public.franchise_support_sessions%rowtype;
  v_name text;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;

  select * into v_session
  from public.franchise_support_sessions
  where matrix_user_id=auth.uid() and active
    and (p_session_id is null or id=p_session_id)
  order by started_at desc
  limit 1
  for update;

  if not found then return jsonb_build_object('ok',true,'ended',false); end if;

  update public.franchise_support_sessions
     set active=false,ended_at=now()
   where id=v_session.id;

  select trade_name into v_name from public.franchises where id=v_session.franchise_id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'support_session_end','franchise_support_sessions',v_session.id::text,
    jsonb_build_object('franchise_id',v_session.franchise_id,'franchise_name',v_name,'session_id',v_session.id,
      'reason',v_session.reason,'source','matrix_support','old_value',jsonb_build_object('active',true,'started_at',v_session.started_at),
      'new_value',jsonb_build_object('active',false,'ended_at',now())));

  return jsonb_build_object('ok',true,'ended',true,'id',v_session.id,'franchise_id',v_session.franchise_id,'franchise_name',v_name);
end;
$$;
revoke all on function public.matrix_end_support_session(uuid) from public,anon;
grant execute on function public.matrix_end_support_session(uuid) to authenticated;

create or replace function public.matrix_active_support_session()
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
  v_result jsonb;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if public.jwt_app_role()<>'super_admin' then return null; end if;

  select jsonb_build_object(
    'id',s.id,'franchise_id',s.franchise_id,'franchise_name',f.trade_name,'reason',s.reason,
    'started_at',s.started_at,'active',s.active,'cities',coalesce((
      select jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'state',c.state) order by c.name)
      from public.franchise_cities fc join public.cities c on c.id=fc.city_id
      where fc.franchise_id=s.franchise_id
    ),'[]'::jsonb)
  ) into v_result
  from public.franchise_support_sessions s
  join public.franchises f on f.id=s.franchise_id
  where s.matrix_user_id=auth.uid() and s.active
  order by s.started_at desc
  limit 1;

  return v_result;
end;
$$;
revoke all on function public.matrix_active_support_session() from public,anon;
grant execute on function public.matrix_active_support_session() to authenticated;
