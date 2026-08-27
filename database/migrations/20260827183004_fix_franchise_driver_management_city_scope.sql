create or replace function public.franchise_list_driver_management()
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid := auth.uid();
  v_role text;
  v_franchise uuid;
  v_result jsonb;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;

  select p.role::text, p.franchise_id
    into v_role, v_franchise
  from public.profiles p
  where p.id=v_uid and p.active is not false;

  if v_role <> 'franchise_admin' or v_franchise is null then
    raise exception 'Acesso exclusivo do franqueado';
  end if;

  select coalesce(jsonb_agg(x.item order by x.created_at desc),'[]'::jsonb)
    into v_result
  from (
    select d.created_at,
      jsonb_build_object(
        'id',d.id,'status',d.status::text,'online',coalesce(d.online,false),'rating',coalesce(d.rating,0),
        'city_id',d.city_id,'city_name',c.name,'city_state',c.state,'created_at',d.created_at,
        'has_card_machine',coalesce(d.has_card_machine,false),'card_machine_approved',coalesce(d.card_machine_approved,false),
        'full_name',p.full_name,'email',p.email,'phone',p.phone,'cpf',p.cpf,'avatar_url',p.avatar_url,
        'cnh_number',dp.cnh_number,'cnh_category',dp.cnh_category,'pix_key',dp.pix_key,
        'vehicle_id',v.id,'vehicle_make',v.make,'vehicle_model',v.model,'vehicle_year',v.year,
        'vehicle_plate',v.plate,'vehicle_color',v.color,'vehicle_type',v.vehicle_type,
        'balance',coalesce(w.balance,0),
        'billing_mode',coalesce(eb.billing_mode,'wallet_per_ride'),'ride_fee_mode',coalesce(eb.ride_fee_mode,'fixed'),
        'per_ride_fee',coalesce(eb.per_ride_fee,0),'ride_fee_percentage',coalesce(eb.ride_fee_percentage,0),
        'monthly_fee',coalesce(eb.monthly_fee,0),'monthly_due_day',coalesce(eb.monthly_due_day,10),
        'monthly_paid_until',eb.monthly_paid_until,'minimum_balance',coalesce(eb.minimum_balance,0),
        'low_balance_threshold',coalesce(eb.low_balance_threshold,0),'operational_enabled',coalesce(eb.operational_enabled,true)
      ) item
    from public.drivers d
    join public.profiles p on p.id=d.id
    left join public.driver_profiles dp on dp.driver_id=d.id
    left join public.cities c on c.id=d.city_id
    left join lateral (
      select vv.* from public.vehicles vv
      where vv.driver_id=d.id and vv.active
      order by vv.created_at desc limit 1
    ) v on true
    left join public.driver_operational_wallets w on w.driver_id=d.id
    left join lateral public.get_effective_driver_billing_v2(d.id) eb on true
    where d.franchise_id=v_franchise
  ) x;

  return v_result;
end;
$$;

create or replace function public.franchise_update_driver_management(p_driver_id uuid, p_payload jsonb)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid := auth.uid();
  v_role text;
  v_franchise uuid;
  v_driver public.drivers%rowtype;
  v_status text;
  v_vehicle_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if p_driver_id is null then raise exception 'Motorista inválido'; end if;
  if p_payload is null or jsonb_typeof(p_payload) <> 'object' then raise exception 'Dados inválidos'; end if;

  select p.role::text,p.franchise_id into v_role,v_franchise
  from public.profiles p where p.id=v_uid and p.active is not false;
  if v_role <> 'franchise_admin' or v_franchise is null then raise exception 'Acesso exclusivo do franqueado'; end if;

  select * into v_driver from public.drivers d where d.id=p_driver_id;
  if not found then raise exception 'Motorista não encontrado'; end if;
  if v_driver.franchise_id is distinct from v_franchise then raise exception 'Motorista fora da sua franquia'; end if;

  if p_payload ? 'status' then
    v_status:=lower(trim(coalesce(p_payload->>'status','')));
    if v_status not in ('pending','approved','rejected','blocked') then raise exception 'Status inválido'; end if;
  end if;

  update public.profiles p set
    full_name=case when p_payload ? 'full_name' then nullif(trim(p_payload->>'full_name'),'') else p.full_name end,
    phone=case when p_payload ? 'phone' then nullif(trim(p_payload->>'phone'),'') else p.phone end,
    cpf=case when p_payload ? 'cpf' then nullif(regexp_replace(coalesce(p_payload->>'cpf',''),'[^0-9]','','g'),'') else p.cpf end,
    updated_at=now()
  where p.id=p_driver_id;

  if p_payload ? 'cnh_number' or p_payload ? 'cnh_category' or p_payload ? 'pix_key' then
    insert into public.driver_profiles(driver_id,cnh_number,cnh_category,pix_key,updated_at)
    values(p_driver_id,nullif(trim(p_payload->>'cnh_number'),''),nullif(upper(trim(p_payload->>'cnh_category')),''),nullif(trim(p_payload->>'pix_key'),''),now())
    on conflict(driver_id) do update set
      cnh_number=case when p_payload ? 'cnh_number' then excluded.cnh_number else driver_profiles.cnh_number end,
      cnh_category=case when p_payload ? 'cnh_category' then excluded.cnh_category else driver_profiles.cnh_category end,
      pix_key=case when p_payload ? 'pix_key' then excluded.pix_key else driver_profiles.pix_key end,
      updated_at=now();
  end if;

  update public.drivers d set
    status=case when v_status is not null then v_status::public.driver_status else d.status end,
    online=case when v_status in ('pending','rejected','blocked') then false else d.online end,
    approved_at=case when v_status='approved' then coalesce(d.approved_at,now()) else d.approved_at end,
    approved_by=case when v_status='approved' then v_uid else d.approved_by end,
    rejection_reason=case when v_status='rejected' then nullif(trim(p_payload->>'rejection_reason'),'') when v_status in ('approved','pending') then null else d.rejection_reason end,
    has_card_machine=case when p_payload ? 'has_card_machine' then coalesce((p_payload->>'has_card_machine')::boolean,false) else d.has_card_machine end,
    card_machine_approved=case when p_payload ? 'has_card_machine' and coalesce((p_payload->>'has_card_machine')::boolean,false)=false then false else d.card_machine_approved end
  where d.id=p_driver_id;

  select vv.id into v_vehicle_id from public.vehicles vv where vv.driver_id=p_driver_id and vv.active order by vv.created_at desc limit 1;
  if v_vehicle_id is not null then
    update public.vehicles vv set
      make=case when p_payload ? 'vehicle_make' then nullif(trim(p_payload->>'vehicle_make'),'') else vv.make end,
      model=case when p_payload ? 'vehicle_model' then nullif(trim(p_payload->>'vehicle_model'),'') else vv.model end,
      year=case when p_payload ? 'vehicle_year' then nullif(p_payload->>'vehicle_year','')::integer else vv.year end,
      plate=case when p_payload ? 'vehicle_plate' then upper(nullif(regexp_replace(coalesce(p_payload->>'vehicle_plate',''),'[^A-Za-z0-9]','','g'),'')) else vv.plate end,
      color=case when p_payload ? 'vehicle_color' then nullif(trim(p_payload->>'vehicle_color'),'') else vv.color end,
      vehicle_type=case when p_payload ? 'vehicle_type' then nullif(trim(p_payload->>'vehicle_type'),'') else vv.vehicle_type end
    where vv.id=v_vehicle_id;
  elsif nullif(trim(coalesce(p_payload->>'vehicle_plate','')),'') is not null then
    insert into public.vehicles(driver_id,make,model,year,plate,color,active,vehicle_type)
    values(p_driver_id,nullif(trim(p_payload->>'vehicle_make'),''),nullif(trim(p_payload->>'vehicle_model'),''),nullif(p_payload->>'vehicle_year','')::integer,upper(regexp_replace(p_payload->>'vehicle_plate','[^A-Za-z0-9]','','g')),nullif(trim(p_payload->>'vehicle_color'),''),true,coalesce(nullif(trim(p_payload->>'vehicle_type'),''),'car'));
  end if;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_update_driver_management','driver',p_driver_id::text,jsonb_build_object('franchise_id',v_franchise,'city_id',v_driver.city_id,'changed_fields',(select coalesce(jsonb_agg(k),'[]'::jsonb) from jsonb_object_keys(p_payload) k)));

  return jsonb_build_object('ok',true,'driver_id',p_driver_id);
end;
$$;

revoke all on function public.franchise_list_driver_management() from public, anon;
revoke all on function public.franchise_update_driver_management(uuid,jsonb) from public, anon;
grant execute on function public.franchise_list_driver_management() to authenticated, service_role;
grant execute on function public.franchise_update_driver_management(uuid,jsonb) to authenticated, service_role;
