-- Quando o Super Admin está em uma sessão ativa da própria franquia alterada,
-- a origem passa a ser matrix_support (Matriz - Suporte) na auditoria e sincronização.

create or replace function public.capture_critical_audit()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_row jsonb;
  v_franchise uuid;
  v_city uuid;
  v_entity_id text;
  v_source text;
  v_reason text;
  v_role text;
begin
  if tg_op='INSERT' then v_old:=null; v_new:=to_jsonb(new);
  elsif tg_op='DELETE' then v_old:=to_jsonb(old); v_new:=null;
  else v_old:=to_jsonb(old); v_new:=to_jsonb(new); end if;

  v_row:=coalesce(v_new,v_old,'{}'::jsonb);
  begin
    if tg_table_name='franchises' then v_franchise:=nullif(v_row->>'id','')::uuid;
    else v_franchise:=nullif(v_row->>'franchise_id','')::uuid; end if;
  exception when others then v_franchise:=null; end;
  begin v_city:=nullif(v_row->>'city_id','')::uuid; exception when others then v_city:=null; end;
  if v_franchise is null and v_city is not null then
    select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=v_city limit 1;
  end if;

  v_entity_id:=coalesce(v_row->>'id',concat_ws(':',v_row->>'franchise_id',v_row->>'city_id'),v_row->>'franchise_id');
  v_role:=public.jwt_app_role();
  if v_role='super_admin' and v_franchise is not null and exists(
    select 1 from public.franchise_support_sessions s
    where s.matrix_user_id=auth.uid() and s.franchise_id=v_franchise and s.active
  ) then v_source:='matrix_support';
  else
    v_source:=case v_role
      when 'super_admin' then 'matrix'
      when 'franchise_admin' then 'franchise'
      when 'operator' then 'staff'
      when 'driver' then 'driver_app'
      when 'passenger' then 'passenger_app'
      else 'system' end;
  end if;
  v_reason:=coalesce(v_row->>'reason',v_row->>'blocked_reason',v_row->>'description',v_row->>'commercial_notes');

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),lower(tg_op),tg_table_name,v_entity_id,
    jsonb_build_object('franchise_id',v_franchise,'city_id',v_city,'source',v_source,'reason',v_reason,'old_value',v_old,'new_value',v_new));
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;
revoke all on function public.capture_critical_audit() from public,anon,authenticated;

create or replace function public.bump_configuration_sync()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_row jsonb;
  v_franchise uuid;
  v_city uuid;
  v_entity_id text;
  v_scope text;
  v_source text;
  v_version bigint;
  v_actor uuid:=auth.uid();
  v_role text;
begin
  if tg_op='INSERT' then v_old:=null; v_new:=to_jsonb(new);
  elsif tg_op='DELETE' then v_old:=to_jsonb(old); v_new:=null;
  else v_old:=to_jsonb(old); v_new:=to_jsonb(new); end if;
  v_row:=coalesce(v_new,v_old,'{}'::jsonb);
  begin v_franchise:=nullif(v_row->>'franchise_id','')::uuid; exception when others then v_franchise:=null; end;
  begin v_city:=nullif(v_row->>'city_id','')::uuid; exception when others then v_city:=null; end;
  v_entity_id:=coalesce(v_row->>'id',v_row->>'setting_key',v_row->>'franchise_id');
  if v_franchise is null and v_city is not null then
    select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=v_city limit 1;
  end if;
  v_scope:=coalesce(v_franchise::text,'global');
  v_role:=public.jwt_app_role();
  if v_role='super_admin' and v_franchise is not null and exists(
    select 1 from public.franchise_support_sessions s
    where s.matrix_user_id=auth.uid() and s.franchise_id=v_franchise and s.active
  ) then v_source:='matrix_support';
  else
    v_source:=case v_role
      when 'super_admin' then 'matrix'
      when 'franchise_admin' then 'franchise'
      when 'operator' then 'staff'
      when 'driver' then 'driver_app'
      when 'passenger' then 'passenger_app'
      else 'system' end;
  end if;

  insert into public.configuration_sync_state(scope_key,franchise_id,version,last_change_at,last_change_source,last_entity,last_actor_id)
  values(v_scope,v_franchise,1,now(),v_source,tg_table_name,v_actor)
  on conflict(scope_key) do update set
    version=public.configuration_sync_state.version+1,
    last_change_at=now(),last_change_source=excluded.last_change_source,
    last_entity=excluded.last_entity,last_actor_id=excluded.last_actor_id
  returning version into v_version;

  insert into public.configuration_events(franchise_id,city_id,version,source,entity,entity_id,action,payload,actor_id)
  values(v_franchise,v_city,v_version,v_source,tg_table_name,v_entity_id,lower(tg_op),
    jsonb_build_object('changed_at',now(),'old_value',v_old,'new_value',v_new),v_actor);

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_actor,'configuration_'||lower(tg_op),tg_table_name,v_entity_id,
    jsonb_build_object('franchise_id',v_franchise,'city_id',v_city,'version',v_version,'source',v_source,'old_value',v_old,'new_value',v_new));

  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;
revoke all on function public.bump_configuration_sync() from public,anon,authenticated;
