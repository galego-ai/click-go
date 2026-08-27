create or replace function public.set_driver_online(p_online boolean, p_lat double precision default null, p_lng double precision default null)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid := auth.uid();
  v_driver public.drivers%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_driver from public.drivers where id=v_uid for update;
  if not found then raise exception 'Cadastro de motorista não encontrado'; end if;

  if p_online then
    if exists(select 1 from public.driver_taximeter_sessions s where s.driver_id=v_uid and s.status='running') then
      raise exception 'Finalize ou cancele o taxímetro antes de ficar online para chamadas';
    end if;
    if v_driver.status <> 'approved' then raise exception 'Seu cadastro precisa estar aprovado para ficar online'; end if;
    if not public.driver_can_be_online(v_uid) then raise exception 'Seu cadastro ou plano ainda não está liberado para operação'; end if;
    if p_lat is null or p_lng is null or p_lat not between -90 and 90 or p_lng not between -180 and 180 then
      raise exception 'Localização válida é obrigatória para ficar online';
    end if;
    insert into public.driver_locations(driver_id,lat,lng,updated_at)
    values(v_uid,p_lat,p_lng,now())
    on conflict(driver_id) do update set lat=excluded.lat,lng=excluded.lng,updated_at=now();
    update public.drivers set online=true, online_since=coalesce(online_since,now()) where id=v_uid;
  else
    update public.drivers set online=false, online_since=null where id=v_uid;
  end if;

  return jsonb_build_object('ok',true,'online',p_online);
end;
$$;

create or replace function public.start_driver_taximeter(p_category_id uuid, p_lat double precision, p_lng double precision)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_driver public.drivers%rowtype;
  v_cat public.ride_categories%rowtype;
  v_id uuid;
  v_amount numeric;
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
  select * into v_cat from public.ride_categories c
  where c.id=p_category_id and c.active=true
    and c.city_id is not distinct from v_driver.city_id
    and c.franchise_id is not distinct from v_driver.franchise_id;
  if not found then raise exception 'Categoria indisponível para este motorista'; end if;
  if exists(select 1 from public.driver_category_eligibility e0 where e0.driver_id=v_uid)
     and not exists(select 1 from public.driver_category_eligibility e where e.driver_id=v_uid and e.category_id=p_category_id and e.active=true) then
    raise exception 'Categoria não autorizada para este motorista';
  end if;
  v_amount:=round(greatest(coalesce(v_cat.minimum_fare,0),coalesce(v_cat.base_fare,0))*greatest(coalesce(v_cat.dynamic_multiplier,1),1),2);

  update public.drivers set online=false, online_since=null where id=v_uid;

  insert into public.driver_taximeter_sessions(
    driver_id,franchise_id,city_id,category_id,base_fare,price_per_km,price_per_minute,minimum_fare,multiplier,
    start_lat,start_lng,last_lat,last_lng,current_amount
  ) values(
    v_uid,v_driver.franchise_id,v_driver.city_id,v_cat.id,coalesce(v_cat.base_fare,0),coalesce(v_cat.price_per_km,0),coalesce(v_cat.price_per_minute,0),coalesce(v_cat.minimum_fare,0),greatest(coalesce(v_cat.dynamic_multiplier,1),1),
    p_lat,p_lng,p_lat,p_lng,v_amount
  ) returning id into v_id;
  insert into public.driver_taximeter_points(session_id,driver_id,lat,lng,distance_from_prev_m,accepted)
  values(v_id,v_uid,p_lat,p_lng,0,true);
  return jsonb_build_object('ok',true,'session_id',v_id,'status','running','amount',v_amount,'started_at',now(),'driver_online',false);
end;
$$;

revoke execute on function public.set_driver_online(boolean,double precision,double precision) from public, anon;
grant execute on function public.set_driver_online(boolean,double precision,double precision) to authenticated, service_role;
revoke execute on function public.start_driver_taximeter(uuid,double precision,double precision) from public, anon;
grant execute on function public.start_driver_taximeter(uuid,double precision,double precision) to authenticated, service_role;
