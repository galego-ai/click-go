create or replace function public.franchise_set_passenger_cancellation_policy(p_free_seconds integer)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_locked boolean:=false;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('settings') then
    v_fid:=public.staff_franchise_id();
  else
    raise exception 'Acesso restrito ao franqueado ou operador autorizado';
  end if;
  if v_fid is null then raise exception 'Franquia não identificada'; end if;
  if p_free_seconds is null or p_free_seconds<0 or p_free_seconds>86400 then
    raise exception 'Tempo grátis deve ficar entre 0 e 86400 segundos';
  end if;

  select fs.locked_by_matrix into v_locked
  from public.franchise_settings fs
  where fs.franchise_id=v_fid and fs.setting_key='passenger_cancellation_policy'
  for update;
  if coalesce(v_locked,false) then raise exception 'Esta configuração está bloqueada pela Matriz'; end if;

  insert into public.franchise_settings(franchise_id,setting_key,setting_value,source,locked_by_matrix,updated_at)
  values(v_fid,'passenger_cancellation_policy',jsonb_build_object('free_seconds',p_free_seconds),'franchise',false,now())
  on conflict(franchise_id,setting_key) do update set
    setting_value=excluded.setting_value,
    source='franchise',
    updated_at=now();

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_set_passenger_cancellation_policy','franchise_settings',v_fid::text,
    jsonb_build_object('franchise_id',v_fid,'free_seconds',p_free_seconds,'source_role',v_role));
  return jsonb_build_object('ok',true,'free_seconds',p_free_seconds);
end;
$$;

create or replace function public.matrix_set_passenger_cancellation_policy(
  p_franchise_id uuid,
  p_free_seconds integer,
  p_locked_by_matrix boolean,
  p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare v_uid uuid:=auth.uid();
begin
  if v_uid is null or public.current_active_management_role()<>'super_admin' then
    raise exception 'Acesso restrito ao Super Admin ativo';
  end if;
  if p_franchise_id is null or not exists(select 1 from public.franchises f where f.id=p_franchise_id and f.deleted_at is null) then
    raise exception 'Franquia inválida';
  end if;
  if p_free_seconds is null or p_free_seconds<0 or p_free_seconds>86400 then raise exception 'Tempo grátis inválido'; end if;
  if nullif(btrim(coalesce(p_reason,'')),'') is null then raise exception 'Justificativa obrigatória'; end if;

  insert into public.franchise_settings(franchise_id,setting_key,setting_value,source,locked_by_matrix,updated_at)
  values(p_franchise_id,'passenger_cancellation_policy',jsonb_build_object('free_seconds',p_free_seconds),'matrix',coalesce(p_locked_by_matrix,false),now())
  on conflict(franchise_id,setting_key) do update set
    setting_value=excluded.setting_value,
    source='matrix',
    locked_by_matrix=excluded.locked_by_matrix,
    updated_at=now();

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'matrix_set_passenger_cancellation_policy','franchise_settings',p_franchise_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'free_seconds',p_free_seconds,'locked_by_matrix',coalesce(p_locked_by_matrix,false),'reason',btrim(p_reason)));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'free_seconds',p_free_seconds,'locked_by_matrix',coalesce(p_locked_by_matrix,false));
end;
$$;

create or replace function public.franchise_save_business_hours(p_city_id uuid,p_hours jsonb)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_item jsonb;
  v_weekday integer;
  v_closed boolean;
  v_open time;
  v_close time;
  v_total integer;
  v_distinct integer;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('settings') then
    v_fid:=public.staff_franchise_id();
  else
    raise exception 'Acesso restrito ao franqueado ou operador autorizado';
  end if;
  if v_fid is null or p_city_id is null then raise exception 'Franquia/cidade inválida'; end if;
  if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=p_city_id) or not public.can_access_city(p_city_id) then
    raise exception 'Cidade fora do escopo da franquia';
  end if;
  if jsonb_typeof(p_hours)<>'array' or jsonb_array_length(p_hours)<1 or jsonb_array_length(p_hours)>7 then
    raise exception 'Informe de 1 a 7 horários';
  end if;
  select count(*),count(distinct (x->>'weekday')::integer) into v_total,v_distinct from jsonb_array_elements(p_hours) x;
  if v_total<>v_distinct then raise exception 'Dia da semana duplicado'; end if;

  for v_item in select value from jsonb_array_elements(p_hours)
  loop
    v_weekday:=(v_item->>'weekday')::integer;
    v_closed:=coalesce((v_item->>'closed')::boolean,false);
    if v_weekday<0 or v_weekday>6 then raise exception 'Dia da semana inválido'; end if;
    if exists(select 1 from public.franchise_business_hours h where h.franchise_id=v_fid and h.city_id=p_city_id and h.weekday=v_weekday and h.locked_by_matrix) then
      raise exception 'Horário do dia % está bloqueado pela Matriz',v_weekday;
    end if;
    if v_closed then
      v_open:=null; v_close:=null;
    else
      v_open:=nullif(v_item->>'opens_at','')::time;
      v_close:=nullif(v_item->>'closes_at','')::time;
      if v_open is null or v_close is null then raise exception 'Abertura e fechamento são obrigatórios para dia aberto'; end if;
    end if;

    insert into public.franchise_business_hours(franchise_id,city_id,weekday,opens_at,closes_at,closed,source,locked_by_matrix)
    values(v_fid,p_city_id,v_weekday,v_open,v_close,v_closed,'franchise',false)
    on conflict(franchise_id,city_id,weekday) do update set
      opens_at=excluded.opens_at,
      closes_at=excluded.closes_at,
      closed=excluded.closed,
      source='franchise';
  end loop;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_save_business_hours','franchise_business_hours',v_fid::text,
    jsonb_build_object('franchise_id',v_fid,'city_id',p_city_id,'days_changed',v_total,'source_role',v_role));
  return jsonb_build_object('ok',true,'franchise_id',v_fid,'city_id',p_city_id,'days_changed',v_total);
end;
$$;

create or replace function public.matrix_save_franchise_business_hours(
  p_franchise_id uuid,
  p_city_id uuid,
  p_hours jsonb,
  p_locked_by_matrix boolean,
  p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_item jsonb;
  v_weekday integer;
  v_closed boolean;
  v_open time;
  v_close time;
  v_total integer;
  v_distinct integer;
begin
  if v_uid is null or public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_franchise_id is null or p_city_id is null or not exists(select 1 from public.franchise_cities fc where fc.franchise_id=p_franchise_id and fc.city_id=p_city_id) then
    raise exception 'Franquia/cidade não vinculada';
  end if;
  if nullif(btrim(coalesce(p_reason,'')),'') is null then raise exception 'Justificativa obrigatória'; end if;
  if jsonb_typeof(p_hours)<>'array' or jsonb_array_length(p_hours)<1 or jsonb_array_length(p_hours)>7 then raise exception 'Informe de 1 a 7 horários'; end if;
  select count(*),count(distinct (x->>'weekday')::integer) into v_total,v_distinct from jsonb_array_elements(p_hours) x;
  if v_total<>v_distinct then raise exception 'Dia da semana duplicado'; end if;

  for v_item in select value from jsonb_array_elements(p_hours)
  loop
    v_weekday:=(v_item->>'weekday')::integer;
    v_closed:=coalesce((v_item->>'closed')::boolean,false);
    if v_weekday<0 or v_weekday>6 then raise exception 'Dia da semana inválido'; end if;
    if v_closed then v_open:=null; v_close:=null;
    else
      v_open:=nullif(v_item->>'opens_at','')::time;
      v_close:=nullif(v_item->>'closes_at','')::time;
      if v_open is null or v_close is null then raise exception 'Abertura e fechamento são obrigatórios para dia aberto'; end if;
    end if;
    insert into public.franchise_business_hours(franchise_id,city_id,weekday,opens_at,closes_at,closed,source,locked_by_matrix)
    values(p_franchise_id,p_city_id,v_weekday,v_open,v_close,v_closed,'matrix',coalesce(p_locked_by_matrix,false))
    on conflict(franchise_id,city_id,weekday) do update set
      opens_at=excluded.opens_at,closes_at=excluded.closes_at,closed=excluded.closed,source='matrix',locked_by_matrix=excluded.locked_by_matrix;
  end loop;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'matrix_save_franchise_business_hours','franchise_business_hours',p_franchise_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'city_id',p_city_id,'days_changed',v_total,'locked_by_matrix',coalesce(p_locked_by_matrix,false),'reason',btrim(p_reason)));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'city_id',p_city_id,'days_changed',v_total,'locked_by_matrix',coalesce(p_locked_by_matrix,false));
end;
$$;

revoke all on function public.franchise_set_passenger_cancellation_policy(integer) from public,anon;
revoke all on function public.matrix_set_passenger_cancellation_policy(uuid,integer,boolean,text) from public,anon;
revoke all on function public.franchise_save_business_hours(uuid,jsonb) from public,anon;
revoke all on function public.matrix_save_franchise_business_hours(uuid,uuid,jsonb,boolean,text) from public,anon;
grant execute on function public.franchise_set_passenger_cancellation_policy(integer) to authenticated,service_role;
grant execute on function public.matrix_set_passenger_cancellation_policy(uuid,integer,boolean,text) to authenticated,service_role;
grant execute on function public.franchise_save_business_hours(uuid,jsonb) to authenticated,service_role;
grant execute on function public.matrix_save_franchise_business_hours(uuid,uuid,jsonb,boolean,text) to authenticated,service_role;
