create or replace function public.normalize_service_area_polygon(p_polygon jsonb, p_allow_empty boolean default false)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_item jsonb;
  v_lat numeric;
  v_lng numeric;
  v_result jsonb:='[]'::jsonb;
  v_count integer:=0;
begin
  if p_polygon is null or jsonb_typeof(p_polygon)<>'array' then
    raise exception 'Polígono deve ser uma lista de pontos';
  end if;
  v_count:=jsonb_array_length(p_polygon);
  if v_count=0 and p_allow_empty then return '[]'::jsonb; end if;
  if v_count<3 or v_count>500 then raise exception 'A região deve ter entre 3 e 500 pontos'; end if;

  for v_item in select value from jsonb_array_elements(p_polygon)
  loop
    if jsonb_typeof(v_item)='object' then
      v_lat:=nullif(v_item->>'lat','')::numeric;
      v_lng:=nullif(v_item->>'lng','')::numeric;
    elsif jsonb_typeof(v_item)='array' and jsonb_array_length(v_item)=2 then
      v_lat:=(v_item->>0)::numeric;
      v_lng:=(v_item->>1)::numeric;
    else
      raise exception 'Cada ponto deve conter latitude e longitude';
    end if;
    if v_lat is null or v_lng is null or v_lat not between -90 and 90 or v_lng not between -180 and 180 then
      raise exception 'Coordenada fora dos limites válidos';
    end if;
    v_result:=v_result || jsonb_build_array(jsonb_build_object('lat',v_lat,'lng',v_lng));
  end loop;
  return v_result;
end;
$$;

create or replace function public.create_service_area(p_area jsonb)
returns uuid
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_city uuid:=nullif(p_area->>'city_id','')::uuid;
  v_name text:=btrim(coalesce(p_area->>'name',''));
  v_polygon jsonb;
  v_source text;
  v_locked boolean:=false;
  v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if char_length(v_name)<2 or char_length(v_name)>100 then raise exception 'Nome da região deve ter 2 a 100 caracteres'; end if;
  if v_city is null then raise exception 'Cidade obrigatória'; end if;

  if v_role='super_admin' then
    v_fid:=nullif(p_area->>'franchise_id','')::uuid;
    if v_fid is null then raise exception 'Franquia obrigatória para a região'; end if;
    if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) then raise exception 'Cidade não pertence à franquia indicada'; end if;
    v_polygon:=public.normalize_service_area_polygon(coalesce(p_area->'polygon','[]'::jsonb),true);
    v_source:='matrix';
    v_locked:=coalesce((p_area->>'locked_by_matrix')::boolean,true);
  elsif v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id();
    if v_fid is null or not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city) then raise exception 'Cidade fora do escopo da franquia'; end if;
    v_polygon:=public.normalize_service_area_polygon(coalesce(p_area->'polygon','[]'::jsonb),false);
    v_source:='franchise'; v_locked:=false;
  elsif v_role='operator' and (public.staff_has_permission('operation') or public.staff_has_permission('settings')) then
    v_fid:=public.staff_franchise_id();
    if v_fid is null or not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city) then raise exception 'Cidade fora do escopo da equipe'; end if;
    v_polygon:=public.normalize_service_area_polygon(coalesce(p_area->'polygon','[]'::jsonb),false);
    v_source:='franchise'; v_locked:=false;
  else
    raise exception 'Sem permissão para criar regiões';
  end if;

  insert into public.service_areas(franchise_id,city_id,name,polygon,active,source,locked_by_matrix,updated_at)
  values(v_fid,v_city,v_name,v_polygon,true,v_source,v_locked,now()) returning id into v_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'service_area_created','service_areas',v_id::text,jsonb_build_object('franchise_id',v_fid,'city_id',v_city,'source',v_source,'locked_by_matrix',v_locked,'points',jsonb_array_length(v_polygon)));
  return v_id;
end;
$$;

create or replace function public.save_service_area_polygon(p_area_id uuid,p_polygon jsonb)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_row public.service_areas%rowtype;
  v_polygon jsonb;
  v_source text;
  v_lock boolean;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.service_areas where id=p_area_id for update;
  if not found then raise exception 'Região não encontrada'; end if;
  v_polygon:=public.normalize_service_area_polygon(p_polygon,false);

  if v_role='super_admin' then
    v_source:='matrix'; v_lock:=true;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and public.can_access_city(v_row.city_id) then
    v_source:='franchise'; v_lock:=false;
  elsif v_role='operator' and (public.staff_has_permission('operation') or public.staff_has_permission('settings')) and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and public.can_access_city(v_row.city_id) then
    v_source:='franchise'; v_lock:=false;
  else
    raise exception 'Sem permissão para alterar esta região';
  end if;

  update public.service_areas set polygon=v_polygon,source=v_source,locked_by_matrix=v_lock,updated_at=now() where id=p_area_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'service_area_polygon_saved','service_areas',p_area_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'source',v_source,'locked_by_matrix',v_lock,'points',jsonb_array_length(v_polygon)));
  return jsonb_build_object('ok',true,'points',jsonb_array_length(v_polygon),'locked_by_matrix',v_lock);
end;
$$;

create or replace function public.set_service_area_active(p_area_id uuid,p_active boolean)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_row public.service_areas%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.service_areas where id=p_area_id for update;
  if not found then raise exception 'Região não encontrada'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and public.can_access_city(v_row.city_id) then null;
  elsif v_role='operator' and (public.staff_has_permission('operation') or public.staff_has_permission('settings')) and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and public.can_access_city(v_row.city_id) then null;
  else raise exception 'Sem permissão para alterar esta região'; end if;
  update public.service_areas set active=coalesce(p_active,false),updated_at=now() where id=p_area_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'service_area_status_changed','service_areas',p_area_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'active',coalesce(p_active,false)));
  return jsonb_build_object('ok',true,'active',coalesce(p_active,false));
end;
$$;

create or replace function public.delete_service_area(p_area_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_row public.service_areas%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.service_areas where id=p_area_id for update;
  if not found then raise exception 'Região não encontrada'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and public.can_access_city(v_row.city_id) then null;
  elsif v_role='operator' and (public.staff_has_permission('operation') or public.staff_has_permission('settings')) and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and public.can_access_city(v_row.city_id) then null;
  else raise exception 'Sem permissão para excluir esta região'; end if;
  delete from public.service_areas where id=p_area_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'service_area_deleted','service_areas',p_area_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'name',v_row.name));
  return jsonb_build_object('ok',true);
end;
$$;

revoke all on function public.normalize_service_area_polygon(jsonb,boolean) from public,anon,authenticated;
grant execute on function public.normalize_service_area_polygon(jsonb,boolean) to service_role;
revoke all on function public.create_service_area(jsonb) from public,anon;
revoke all on function public.save_service_area_polygon(uuid,jsonb) from public,anon;
revoke all on function public.set_service_area_active(uuid,boolean) from public,anon;
revoke all on function public.delete_service_area(uuid) from public,anon;
grant execute on function public.create_service_area(jsonb) to authenticated,service_role;
grant execute on function public.save_service_area_polygon(uuid,jsonb) to authenticated,service_role;
grant execute on function public.set_service_area_active(uuid,boolean) to authenticated,service_role;
grant execute on function public.delete_service_area(uuid) to authenticated,service_role;
