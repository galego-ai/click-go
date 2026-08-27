create or replace function public.matrix_upsert_ride_category(p_category_id uuid,p_city_id uuid,p_payload jsonb,p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid(); v_existing public.ride_categories%rowtype; v_fid uuid; v_city uuid; v_name text;
  v_base numeric; v_km numeric; v_minute numeric; v_minimum numeric; v_cancel numeric; v_dynamic numeric;
  v_vehicle text; v_active boolean; v_wait integer; v_wait_fee numeric; v_deviation integer; v_icon text; v_marker text; v_id uuid;
begin
  if v_uid is null or public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if nullif(btrim(coalesce(p_reason,'')),'') is null then raise exception 'Justificativa obrigatória'; end if;
  if p_payload is null then p_payload:='{}'::jsonb; end if;
  if p_category_id is not null then
    select * into v_existing from public.ride_categories where id=p_category_id for update;
    if not found then raise exception 'Categoria não encontrada'; end if;
    v_fid:=v_existing.franchise_id; v_city:=v_existing.city_id;
    if p_city_id is not null and p_city_id<>v_city then raise exception 'Não é permitido mover uma categoria existente para outra cidade'; end if;
  else
    if p_city_id is null then raise exception 'Cidade obrigatória'; end if;
    select fc.franchise_id into v_fid from public.franchise_cities fc join public.cities c on c.id=fc.city_id where fc.city_id=p_city_id and c.active=true limit 1;
    if v_fid is null then raise exception 'Cidade sem franquia responsável'; end if;
    v_city:=p_city_id;
  end if;
  v_name:=coalesce(nullif(btrim(p_payload->>'name'),''),case when p_category_id is not null then v_existing.name else null end);
  if v_name is null then raise exception 'Nome da categoria é obrigatório'; end if;
  v_base:=coalesce(nullif(p_payload->>'base_fare','')::numeric,case when p_category_id is not null then v_existing.base_fare else 0 end);
  v_km:=coalesce(nullif(p_payload->>'price_per_km','')::numeric,case when p_category_id is not null then v_existing.price_per_km else 0 end);
  v_minute:=coalesce(nullif(p_payload->>'price_per_minute','')::numeric,case when p_category_id is not null then v_existing.price_per_minute else 0 end);
  v_minimum:=coalesce(nullif(p_payload->>'minimum_fare','')::numeric,case when p_category_id is not null then v_existing.minimum_fare else 0 end);
  v_cancel:=coalesce(nullif(p_payload->>'cancellation_fee','')::numeric,case when p_category_id is not null then v_existing.cancellation_fee else 0 end);
  v_dynamic:=coalesce(nullif(p_payload->>'dynamic_multiplier','')::numeric,case when p_category_id is not null then v_existing.dynamic_multiplier else 1 end);
  v_vehicle:=case when p_payload ? 'required_vehicle_type' then nullif(btrim(p_payload->>'required_vehicle_type'),'') when p_category_id is not null then v_existing.required_vehicle_type else null end;
  v_active:=coalesce((p_payload->>'active')::boolean,case when p_category_id is not null then v_existing.active else true end);
  v_wait:=coalesce(nullif(p_payload->>'wait_tolerance_minutes','')::integer,case when p_category_id is not null then v_existing.wait_tolerance_minutes else 5 end);
  v_wait_fee:=coalesce(nullif(p_payload->>'waiting_fee_per_minute','')::numeric,case when p_category_id is not null then v_existing.waiting_fee_per_minute else 0.50 end);
  v_deviation:=coalesce(nullif(p_payload->>'route_deviation_threshold_m','')::integer,case when p_category_id is not null then v_existing.route_deviation_threshold_m else 800 end);
  v_icon:=case when p_payload ? 'icon_url' then nullif(btrim(p_payload->>'icon_url'),'') when p_category_id is not null then v_existing.icon_url else null end;
  v_marker:=case when p_payload ? 'map_marker_url' then nullif(btrim(p_payload->>'map_marker_url'),'') when p_category_id is not null then v_existing.map_marker_url else null end;
  if least(v_base,v_km,v_minute,v_minimum,v_cancel,v_wait_fee)<0 then raise exception 'Valores de tarifa não podem ser negativos'; end if;
  if v_dynamic<1 then raise exception 'Multiplicador dinâmico deve ser maior ou igual a 1'; end if;
  if v_vehicle is not null and v_vehicle not in ('car','motorcycle') then raise exception 'Tipo de veículo inválido'; end if;
  if v_wait<0 or v_wait>120 then raise exception 'Tolerância deve ficar entre 0 e 120 minutos'; end if;
  if v_deviation<100 or v_deviation>5000 then raise exception 'Desvio deve ficar entre 100 e 5.000 metros'; end if;
  if p_category_id is null then
    insert into public.ride_categories(franchise_id,city_id,name,base_fare,price_per_km,price_per_minute,minimum_fare,cancellation_fee,dynamic_multiplier,required_vehicle_type,active,source,locked_by_matrix,wait_tolerance_minutes,waiting_fee_per_minute,route_deviation_threshold_m,icon_url,map_marker_url)
    values(v_fid,v_city,v_name,v_base,v_km,v_minute,v_minimum,v_cancel,v_dynamic,v_vehicle,v_active,'matrix',true,v_wait,v_wait_fee,v_deviation,v_icon,v_marker) returning id into v_id;
  else
    update public.ride_categories set name=v_name,base_fare=v_base,price_per_km=v_km,price_per_minute=v_minute,minimum_fare=v_minimum,cancellation_fee=v_cancel,dynamic_multiplier=v_dynamic,required_vehicle_type=v_vehicle,active=v_active,source='matrix',locked_by_matrix=true,wait_tolerance_minutes=v_wait,waiting_fee_per_minute=v_wait_fee,route_deviation_threshold_m=v_deviation,icon_url=v_icon,map_marker_url=v_marker where id=p_category_id returning id into v_id;
  end if;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,case when p_category_id is null then 'matrix_ride_category_created' else 'matrix_ride_category_updated' end,'ride_categories',v_id::text,jsonb_build_object('franchise_id',v_fid,'city_id',v_city,'reason',btrim(p_reason),'name',v_name,'active',v_active,'locked_by_matrix',true));
  return jsonb_build_object('ok',true,'id',v_id,'franchise_id',v_fid,'city_id',v_city);
end;
$function$;

create or replace function public.franchise_upsert_ride_category(p_category_id uuid,p_city_id uuid,p_payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_fid uuid; v_existing public.ride_categories%rowtype; v_city uuid; v_name text;
  v_base numeric; v_km numeric; v_minute numeric; v_minimum numeric; v_cancel numeric; v_dynamic numeric; v_vehicle text; v_active boolean; v_wait integer; v_wait_fee numeric; v_deviation integer; v_icon text; v_marker text; v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then v_fid:=public.current_profile_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('pricing') then v_fid:=public.staff_franchise_id();
  else raise exception 'Acesso restrito ao franqueado ou operador de tarifas'; end if;
  if v_fid is null then raise exception 'Franquia não identificada'; end if;
  if p_payload is null then p_payload:='{}'::jsonb; end if;
  if p_category_id is not null then
    select * into v_existing from public.ride_categories where id=p_category_id and franchise_id=v_fid for update;
    if not found then raise exception 'Categoria fora da sua franquia'; end if;
    if v_existing.locked_by_matrix then raise exception 'Categoria bloqueada pela Matriz'; end if;
    v_city:=v_existing.city_id;
    if p_city_id is not null and p_city_id<>v_city then raise exception 'Não é permitido mover uma categoria existente para outra cidade'; end if;
  else
    if p_city_id is null then raise exception 'Cidade obrigatória'; end if;
    v_city:=p_city_id;
  end if;
  if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city) then raise exception 'Cidade fora do escopo da franquia'; end if;
  v_name:=coalesce(nullif(btrim(p_payload->>'name'),''),case when p_category_id is not null then v_existing.name else null end);
  if v_name is null then raise exception 'Nome da categoria é obrigatório'; end if;
  v_base:=coalesce(nullif(p_payload->>'base_fare','')::numeric,case when p_category_id is not null then v_existing.base_fare else 0 end);
  v_km:=coalesce(nullif(p_payload->>'price_per_km','')::numeric,case when p_category_id is not null then v_existing.price_per_km else 0 end);
  v_minute:=coalesce(nullif(p_payload->>'price_per_minute','')::numeric,case when p_category_id is not null then v_existing.price_per_minute else 0 end);
  v_minimum:=coalesce(nullif(p_payload->>'minimum_fare','')::numeric,case when p_category_id is not null then v_existing.minimum_fare else 0 end);
  v_cancel:=coalesce(nullif(p_payload->>'cancellation_fee','')::numeric,case when p_category_id is not null then v_existing.cancellation_fee else 0 end);
  v_dynamic:=coalesce(nullif(p_payload->>'dynamic_multiplier','')::numeric,case when p_category_id is not null then v_existing.dynamic_multiplier else 1 end);
  v_vehicle:=case when p_payload ? 'required_vehicle_type' then nullif(btrim(p_payload->>'required_vehicle_type'),'') when p_category_id is not null then v_existing.required_vehicle_type else null end;
  v_active:=coalesce((p_payload->>'active')::boolean,case when p_category_id is not null then v_existing.active else true end);
  v_wait:=coalesce(nullif(p_payload->>'wait_tolerance_minutes','')::integer,case when p_category_id is not null then v_existing.wait_tolerance_minutes else 5 end);
  v_wait_fee:=coalesce(nullif(p_payload->>'waiting_fee_per_minute','')::numeric,case when p_category_id is not null then v_existing.waiting_fee_per_minute else 0.50 end);
  v_deviation:=coalesce(nullif(p_payload->>'route_deviation_threshold_m','')::integer,case when p_category_id is not null then v_existing.route_deviation_threshold_m else 800 end);
  v_icon:=case when p_payload ? 'icon_url' then nullif(btrim(p_payload->>'icon_url'),'') when p_category_id is not null then v_existing.icon_url else null end;
  v_marker:=case when p_payload ? 'map_marker_url' then nullif(btrim(p_payload->>'map_marker_url'),'') when p_category_id is not null then v_existing.map_marker_url else null end;
  if least(v_base,v_km,v_minute,v_minimum,v_cancel,v_wait_fee)<0 then raise exception 'Valores de tarifa não podem ser negativos'; end if;
  if v_dynamic<1 then raise exception 'Multiplicador dinâmico deve ser maior ou igual a 1'; end if;
  if v_vehicle is not null and v_vehicle not in ('car','motorcycle') then raise exception 'Tipo de veículo inválido'; end if;
  if v_wait<0 or v_wait>120 then raise exception 'Tolerância deve ficar entre 0 e 120 minutos'; end if;
  if v_deviation<100 or v_deviation>5000 then raise exception 'Desvio deve ficar entre 100 e 5.000 metros'; end if;
  if v_icon is not null and position('/storage/v1/object/public/category-markers/' in v_icon)=0 then raise exception 'URL de ícone inválida'; end if;
  if v_marker is not null and position('/storage/v1/object/public/category-markers/' in v_marker)=0 then raise exception 'URL de marcador inválida'; end if;
  if p_category_id is null then
    insert into public.ride_categories(franchise_id,city_id,name,base_fare,price_per_km,price_per_minute,minimum_fare,cancellation_fee,dynamic_multiplier,required_vehicle_type,active,source,locked_by_matrix,wait_tolerance_minutes,waiting_fee_per_minute,route_deviation_threshold_m,icon_url,map_marker_url)
    values(v_fid,v_city,v_name,v_base,v_km,v_minute,v_minimum,v_cancel,v_dynamic,v_vehicle,v_active,'franchise',false,v_wait,v_wait_fee,v_deviation,v_icon,v_marker) returning id into v_id;
  else
    update public.ride_categories set name=v_name,base_fare=v_base,price_per_km=v_km,price_per_minute=v_minute,minimum_fare=v_minimum,cancellation_fee=v_cancel,dynamic_multiplier=v_dynamic,required_vehicle_type=v_vehicle,active=v_active,source='franchise',wait_tolerance_minutes=v_wait,waiting_fee_per_minute=v_wait_fee,route_deviation_threshold_m=v_deviation,icon_url=v_icon,map_marker_url=v_marker where id=p_category_id returning id into v_id;
  end if;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,case when p_category_id is null then 'franchise_ride_category_created' else 'franchise_ride_category_updated' end,'ride_categories',v_id::text,jsonb_build_object('franchise_id',v_fid,'city_id',v_city,'name',v_name,'active',v_active,'source_role',v_role));
  return jsonb_build_object('ok',true,'id',v_id,'franchise_id',v_fid,'city_id',v_city);
end;
$function$;

create or replace function public.matrix_archive_ride_category(p_category_id uuid,p_reason text)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare v_uid uuid:=auth.uid(); v_row public.ride_categories%rowtype;
begin
  if v_uid is null or public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if nullif(btrim(coalesce(p_reason,'')),'') is null then raise exception 'Justificativa obrigatória'; end if;
  select * into v_row from public.ride_categories where id=p_category_id for update;
  if not found then raise exception 'Categoria não encontrada'; end if;
  update public.ride_categories set active=false,source='matrix',locked_by_matrix=true where id=p_category_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'matrix_ride_category_archived','ride_categories',p_category_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'name',v_row.name,'reason',btrim(p_reason)));
  return jsonb_build_object('ok',true,'id',p_category_id,'active',false);
end;
$function$;

revoke all on function public.matrix_upsert_ride_category(uuid,uuid,jsonb,text) from public,anon;
grant execute on function public.matrix_upsert_ride_category(uuid,uuid,jsonb,text) to authenticated,service_role;
revoke all on function public.franchise_upsert_ride_category(uuid,uuid,jsonb) from public,anon;
grant execute on function public.franchise_upsert_ride_category(uuid,uuid,jsonb) to authenticated,service_role;
revoke all on function public.matrix_archive_ride_category(uuid,text) from public,anon;
grant execute on function public.matrix_archive_ride_category(uuid,text) to authenticated,service_role;