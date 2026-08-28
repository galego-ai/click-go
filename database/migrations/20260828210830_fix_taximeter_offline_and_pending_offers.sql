create or replace function public.start_driver_taximeter(p_category_id uuid, p_lat double precision, p_lng double precision)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_driver public.drivers%rowtype;
  v_cat public.ride_categories%rowtype;
  v_id uuid;
  v_amount numeric;
  v_base numeric;
  v_km numeric;
  v_minute numeric;
  v_minimum numeric;
  v_multiplier numeric;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if p_lat not between -90 and 90 or p_lng not between -180 and 180 then raise exception 'Localização inválida'; end if;

  select * into v_driver from public.drivers where id=v_uid for update;
  if not found or v_driver.status::text<>'approved' then raise exception 'Motorista não aprovado'; end if;
  if exists(select 1 from public.rides r where r.driver_id=v_uid and r.status::text in ('accepted','driver_arriving','in_progress')) then
    raise exception 'Finalize a corrida CLICK-GO ativa antes de usar o taxímetro livre';
  end if;
  if exists(select 1 from public.driver_taximeter_sessions s where s.driver_id=v_uid and s.status='running') then
    raise exception 'Já existe um taxímetro em andamento';
  end if;

  select * into v_cat
  from public.ride_categories c
  where c.id=p_category_id
    and c.active=true
    and c.taximeter_enabled=true
    and c.city_id is not distinct from v_driver.city_id
    and c.franchise_id is not distinct from v_driver.franchise_id;
  if not found then raise exception 'Categoria indisponível para o taxímetro deste motorista'; end if;
  if exists(select 1 from public.driver_category_eligibility e0 where e0.driver_id=v_uid)
     and not exists(select 1 from public.driver_category_eligibility e where e.driver_id=v_uid and e.category_id=p_category_id and e.active=true) then
    raise exception 'Categoria não autorizada para este motorista';
  end if;

  v_base:=coalesce(v_cat.taximeter_base_fare,v_cat.base_fare,0);
  v_km:=coalesce(v_cat.taximeter_price_per_km,v_cat.price_per_km,0);
  v_minute:=coalesce(v_cat.taximeter_price_per_minute,v_cat.price_per_minute,0);
  v_minimum:=coalesce(v_cat.taximeter_minimum_fare,v_cat.minimum_fare,0);
  v_multiplier:=greatest(coalesce(v_cat.taximeter_multiplier,v_cat.dynamic_multiplier,1),1);
  v_amount:=round(greatest(v_minimum,v_base)*v_multiplier,2);

  -- Taxímetro e chamadas normais são mutuamente exclusivos.
  update public.drivers
     set online=false, online_since=null
   where id=v_uid;

  update public.ride_offers
     set status='expired'
   where driver_id=v_uid and status='pending';

  insert into public.driver_taximeter_sessions(
    driver_id,franchise_id,city_id,category_id,base_fare,price_per_km,
    price_per_minute,minimum_fare,multiplier,start_lat,start_lng,last_lat,last_lng,current_amount
  ) values(
    v_uid,v_driver.franchise_id,v_driver.city_id,v_cat.id,v_base,v_km,
    v_minute,v_minimum,v_multiplier,p_lat,p_lng,p_lat,p_lng,v_amount
  ) returning id into v_id;

  insert into public.driver_taximeter_points(session_id,driver_id,lat,lng,distance_from_prev_m,accepted)
  values(v_id,v_uid,p_lat,p_lng,0,true);

  return jsonb_build_object('ok',true,'session_id',v_id,'status','running','amount',v_amount,'started_at',now());
end;
$function$;
