create or replace function public.matrix_assign_franchise_city(p_franchise_id uuid, p_city_id uuid, p_reason text, p_override boolean default false)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_existing uuid;
  v_city_name text;
  v_new_name text;
  v_old_name text;
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if v_reason is null then
    raise exception 'Justificativa obrigatória para alteração territorial';
  end if;

  perform 1 from public.franchises where id=p_franchise_id and deleted_at is null;
  if not found then raise exception 'Franquia não encontrada'; end if;
  select name||'/'||state into v_city_name from public.cities where id=p_city_id;
  if v_city_name is null then raise exception 'Cidade não encontrada'; end if;

  select fc.franchise_id into v_existing
  from public.franchise_cities fc
  where fc.city_id=p_city_id
  limit 1
  for update;

  if v_existing=p_franchise_id then
    return jsonb_build_object('ok',true,'status','already_assigned','franchise_id',p_franchise_id,'city_id',p_city_id);
  end if;

  if v_existing is not null and not p_override then
    select trade_name into v_old_name from public.franchises where id=v_existing;
    return jsonb_build_object(
      'ok',false,'status','conflict','city_id',p_city_id,'city_name',v_city_name,
      'current_franchise_id',v_existing,'current_franchise_name',v_old_name,
      'requested_franchise_id',p_franchise_id
    );
  end if;

  perform set_config('app.audit_reason',v_reason,true);

  if v_existing is not null then
    delete from public.franchise_cities where city_id=p_city_id and franchise_id=v_existing;
  end if;

  insert into public.franchise_cities(franchise_id,city_id)
  values(p_franchise_id,p_city_id)
  on conflict do nothing;

  select trade_name into v_new_name from public.franchises where id=p_franchise_id;
  if v_existing is not null then select trade_name into v_old_name from public.franchises where id=v_existing; end if;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    case when v_existing is null then 'territory_assignment' else 'territory_override' end,
    'franchise_cities',p_city_id::text,
    jsonb_build_object(
      'franchise_id',p_franchise_id,
      'city_id',p_city_id,
      'city_name',v_city_name,
      'old_franchise_id',v_existing,
      'old_franchise_name',v_old_name,
      'new_franchise_id',p_franchise_id,
      'new_franchise_name',v_new_name,
      'reason',v_reason,
      'source','matrix'
    )
  );

  return jsonb_build_object(
    'ok',true,
    'status',case when v_existing is null then 'assigned' else 'overridden' end,
    'city_id',p_city_id,'city_name',v_city_name,
    'old_franchise_id',v_existing,'new_franchise_id',p_franchise_id
  );
end;
$$;

create or replace function public.matrix_remove_franchise_city(p_franchise_id uuid, p_city_id uuid, p_reason text)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_city_name text;
  v_franchise_name text;
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if v_reason is null then raise exception 'Justificativa obrigatória para remover território'; end if;

  select name||'/'||state into v_city_name from public.cities where id=p_city_id;
  select trade_name into v_franchise_name from public.franchises where id=p_franchise_id and deleted_at is null;
  if v_franchise_name is null then raise exception 'Franquia não encontrada'; end if;
  if v_city_name is null then raise exception 'Cidade não encontrada'; end if;

  perform set_config('app.audit_reason',v_reason,true);

  delete from public.franchise_cities where franchise_id=p_franchise_id and city_id=p_city_id;
  if not found then raise exception 'Vínculo territorial não encontrado'; end if;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'territory_removal','franchise_cities',p_city_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'city_id',p_city_id,'city_name',v_city_name,
      'old_franchise_id',p_franchise_id,'old_franchise_name',v_franchise_name,'new_franchise_id',null,
      'reason',v_reason,'source','matrix'));

  return jsonb_build_object('ok',true,'status','removed','city_id',p_city_id,'franchise_id',p_franchise_id);
end;
$$;

revoke all on function public.matrix_assign_franchise_city(uuid,uuid,text,boolean) from public,anon;
grant execute on function public.matrix_assign_franchise_city(uuid,uuid,text,boolean) to authenticated,service_role;
revoke all on function public.matrix_remove_franchise_city(uuid,uuid,text) from public,anon;
grant execute on function public.matrix_remove_franchise_city(uuid,uuid,text) to authenticated,service_role;
