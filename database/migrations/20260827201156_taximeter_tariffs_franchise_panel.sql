alter table public.ride_categories
  add column if not exists taximeter_enabled boolean not null default true,
  add column if not exists taximeter_base_fare numeric(12,2),
  add column if not exists taximeter_price_per_km numeric(12,4),
  add column if not exists taximeter_price_per_minute numeric(12,4),
  add column if not exists taximeter_minimum_fare numeric(12,2),
  add column if not exists taximeter_multiplier numeric(8,3);

do $$ begin
  if not exists(select 1 from pg_constraint where conname='ride_categories_taximeter_base_nonnegative') then
    alter table public.ride_categories add constraint ride_categories_taximeter_base_nonnegative check (taximeter_base_fare is null or taximeter_base_fare >= 0);
  end if;
  if not exists(select 1 from pg_constraint where conname='ride_categories_taximeter_km_nonnegative') then
    alter table public.ride_categories add constraint ride_categories_taximeter_km_nonnegative check (taximeter_price_per_km is null or taximeter_price_per_km >= 0);
  end if;
  if not exists(select 1 from pg_constraint where conname='ride_categories_taximeter_minute_nonnegative') then
    alter table public.ride_categories add constraint ride_categories_taximeter_minute_nonnegative check (taximeter_price_per_minute is null or taximeter_price_per_minute >= 0);
  end if;
  if not exists(select 1 from pg_constraint where conname='ride_categories_taximeter_minimum_nonnegative') then
    alter table public.ride_categories add constraint ride_categories_taximeter_minimum_nonnegative check (taximeter_minimum_fare is null or taximeter_minimum_fare >= 0);
  end if;
  if not exists(select 1 from pg_constraint where conname='ride_categories_taximeter_multiplier_range') then
    alter table public.ride_categories add constraint ride_categories_taximeter_multiplier_range check (taximeter_multiplier is null or taximeter_multiplier between 1 and 10);
  end if;
end $$;

create or replace function public.franchise_save_taximeter_tariff(p_category_id uuid,p_payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_cat public.ride_categories%rowtype;
  v_enabled boolean;
  v_base numeric;
  v_km numeric;
  v_minute numeric;
  v_minimum numeric;
  v_multiplier numeric;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then v_fid:=public.current_profile_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('pricing') then v_fid:=public.staff_franchise_id();
  else raise exception 'Acesso restrito ao franqueado ou operador de tarifas'; end if;
  if v_fid is null then raise exception 'Franquia não identificada'; end if;
  if p_category_id is null then raise exception 'Categoria obrigatória'; end if;
  select * into v_cat from public.ride_categories where id=p_category_id and franchise_id=v_fid for update;
  if not found then raise exception 'Categoria fora da sua franquia'; end if;
  if v_cat.locked_by_matrix then raise exception 'Categoria bloqueada pela Matriz'; end if;
  if not public.can_access_city(v_cat.city_id) then raise exception 'Cidade fora do escopo da franquia'; end if;
  if p_payload is null then p_payload:='{}'::jsonb; end if;

  v_enabled:=coalesce((p_payload->>'enabled')::boolean,v_cat.taximeter_enabled,true);
  v_base:=coalesce(nullif(p_payload->>'base_fare','')::numeric,v_cat.taximeter_base_fare,v_cat.base_fare,0);
  v_km:=coalesce(nullif(p_payload->>'price_per_km','')::numeric,v_cat.taximeter_price_per_km,v_cat.price_per_km,0);
  v_minute:=coalesce(nullif(p_payload->>'price_per_minute','')::numeric,v_cat.taximeter_price_per_minute,v_cat.price_per_minute,0);
  v_minimum:=coalesce(nullif(p_payload->>'minimum_fare','')::numeric,v_cat.taximeter_minimum_fare,v_cat.minimum_fare,0);
  v_multiplier:=coalesce(nullif(p_payload->>'multiplier','')::numeric,v_cat.taximeter_multiplier,v_cat.dynamic_multiplier,1);

  if least(v_base,v_km,v_minute,v_minimum)<0 then raise exception 'Tarifas do taxímetro não podem ser negativas'; end if;
  if v_multiplier<1 or v_multiplier>10 then raise exception 'Multiplicador do taxímetro deve ficar entre 1 e 10'; end if;

  update public.ride_categories
     set taximeter_enabled=v_enabled,
         taximeter_base_fare=v_base,
         taximeter_price_per_km=v_km,
         taximeter_price_per_minute=v_minute,
         taximeter_minimum_fare=v_minimum,
         taximeter_multiplier=v_multiplier
   where id=v_cat.id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_taximeter_tariff_updated','ride_categories',v_cat.id::text,
    jsonb_build_object('franchise_id',v_fid,'city_id',v_cat.city_id,'category_name',v_cat.name,'enabled',v_enabled,'base_fare',v_base,'price_per_km',v_km,'price_per_minute',v_minute,'minimum_fare',v_minimum,'multiplier',v_multiplier,'source_role',v_role));

  return jsonb_build_object('ok',true,'category_id',v_cat.id,'enabled',v_enabled,'base_fare',v_base,'price_per_km',v_km,'price_per_minute',v_minute,'minimum_fare',v_minimum,'multiplier',v_multiplier);
end;
$function$;

revoke all on function public.franchise_save_taximeter_tariff(uuid,jsonb) from public,anon;
grant execute on function public.franchise_save_taximeter_tariff(uuid,jsonb) to authenticated,service_role;

create or replace function public.get_my_taximeter_categories()
returns table(category_id uuid,category_name text,base_fare numeric,price_per_km numeric,price_per_minute numeric,minimum_fare numeric,multiplier numeric)
language plpgsql security definer set search_path to 'public','pg_temp' as $$
declare v_uid uuid:=auth.uid(); v_driver public.drivers%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_driver from public.drivers where id=v_uid;
  if not found or v_driver.status::text<>'approved' then raise exception 'Motorista ainda não está aprovado'; end if;
  return query
  select c.id,c.name,
         coalesce(c.taximeter_base_fare,c.base_fare,0),
         coalesce(c.taximeter_price_per_km,c.price_per_km,0),
         coalesce(c.taximeter_price_per_minute,c.price_per_minute,0),
         coalesce(c.taximeter_minimum_fare,c.minimum_fare,0),
         greatest(coalesce(c.taximeter_multiplier,c.dynamic_multiplier,1),1)
  from public.ride_categories c
  where c.active=true and c.taximeter_enabled=true
    and c.city_id is not distinct from v_driver.city_id and c.franchise_id is not distinct from v_driver.franchise_id
    and (not exists(select 1 from public.driver_category_eligibility e0 where e0.driver_id=v_uid) or exists(select 1 from public.driver_category_eligibility e where e.driver_id=v_uid and e.category_id=c.id and e.active=true))
  order by c.name;
end;
$$;
revoke all on function public.get_my_taximeter_categories() from public,anon;
grant execute on function public.get_my_taximeter_categories() to authenticated;

create or replace function public.start_driver_taximeter(p_category_id uuid,p_lat double precision,p_lng double precision)
returns jsonb language plpgsql security definer set search_path to 'public','pg_temp' as $$
declare
  v_uid uuid:=auth.uid(); v_driver public.drivers%rowtype; v_cat public.ride_categories%rowtype; v_id uuid; v_amount numeric;
  v_base numeric; v_km numeric; v_minute numeric; v_minimum numeric; v_multiplier numeric;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if p_lat not between -90 and 90 or p_lng not between -180 and 180 then raise exception 'Localização inválida'; end if;
  select * into v_driver from public.drivers where id=v_uid for update;
  if not found or v_driver.status::text<>'approved' then raise exception 'Motorista não aprovado'; end if;
  if exists(select 1 from public.rides r where r.driver_id=v_uid and r.status::text in ('accepted','driver_arriving','in_progress')) then raise exception 'Finalize a corrida CLICK-GO ativa antes de usar o taxímetro livre'; end if;
  if exists(select 1 from public.driver_taximeter_sessions s where s.driver_id=v_uid and s.status='running') then raise exception 'Já existe um taxímetro em andamento'; end if;
  select * into v_cat from public.ride_categories c where c.id=p_category_id and c.active=true and c.taximeter_enabled=true and c.city_id is not distinct from v_driver.city_id and c.franchise_id is not distinct from v_driver.franchise_id;
  if not found then raise exception 'Categoria indisponível para o taxímetro deste motorista'; end if;
  if exists(select 1 from public.driver_category_eligibility e0 where e0.driver_id=v_uid) and not exists(select 1 from public.driver_category_eligibility e where e.driver_id=v_uid and e.category_id=p_category_id and e.active=true) then raise exception 'Categoria não autorizada para este motorista'; end if;

  v_base:=coalesce(v_cat.taximeter_base_fare,v_cat.base_fare,0);
  v_km:=coalesce(v_cat.taximeter_price_per_km,v_cat.price_per_km,0);
  v_minute:=coalesce(v_cat.taximeter_price_per_minute,v_cat.price_per_minute,0);
  v_minimum:=coalesce(v_cat.taximeter_minimum_fare,v_cat.minimum_fare,0);
  v_multiplier:=greatest(coalesce(v_cat.taximeter_multiplier,v_cat.dynamic_multiplier,1),1);
  v_amount:=round(greatest(v_minimum,v_base)*v_multiplier,2);

  insert into public.driver_taximeter_sessions(driver_id,franchise_id,city_id,category_id,base_fare,price_per_km,price_per_minute,minimum_fare,multiplier,start_lat,start_lng,last_lat,last_lng,current_amount)
  values(v_uid,v_driver.franchise_id,v_driver.city_id,v_cat.id,v_base,v_km,v_minute,v_minimum,v_multiplier,p_lat,p_lng,p_lat,p_lng,v_amount) returning id into v_id;
  insert into public.driver_taximeter_points(session_id,driver_id,lat,lng,distance_from_prev_m,accepted) values(v_id,v_uid,p_lat,p_lng,0,true);
  return jsonb_build_object('ok',true,'session_id',v_id,'status','running','amount',v_amount,'started_at',now());
end;
$$;
revoke all on function public.start_driver_taximeter(uuid,double precision,double precision) from public,anon;
grant execute on function public.start_driver_taximeter(uuid,double precision,double precision) to authenticated;
