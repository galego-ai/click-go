-- Cadastro do motorista: o usuário escolhe somente a cidade.
-- A franquia responsável é resolvida exclusivamente no backend.

create or replace function public.available_driver_registration_cities()
returns table(city_id uuid, city_name text, state text)
language sql
stable
security definer
set search_path to 'public','pg_temp'
as $$
  select c.id, c.name, c.state
  from public.cities c
  where c.active = true
    and 1 = (
      select count(distinct fc.franchise_id)
      from public.franchise_cities fc
      join public.franchises f on f.id = fc.franchise_id
      where fc.city_id = c.id
        and f.active = true
        and f.deleted_at is null
        and f.blocked_at is null
    )
  order by c.name, c.state;
$$;

create or replace function public.handle_new_passenger_user()
returns trigger
language plpgsql
security definer
set search_path to 'public'
as $$
declare
  v_role text;
  v_cpf text;
  v_city uuid;
  v_franchise uuid;
  v_franchise_count integer;
  v_requested_category uuid;
  v_required_vehicle_type text;
  v_vehicle_id uuid;
  v_machine boolean;
begin
  v_role := coalesce(nullif(new.raw_user_meta_data->>'app_role',''), nullif(new.raw_user_meta_data->>'role',''), '');
  v_cpf := regexp_replace(coalesce(new.raw_user_meta_data->>'cpf',''),'[^0-9]','','g');

  if v_role = 'passenger' then
    insert into public.profiles(id,full_name,phone,email,cpf,role,franchise_id,city_id,active)
    values(
      new.id,
      nullif(trim(new.raw_user_meta_data->>'full_name'),''),
      nullif(trim(new.raw_user_meta_data->>'phone'),''),
      lower(new.email),
      nullif(v_cpf,''),
      'passenger',
      null,
      null,
      true
    )
    on conflict(id) do update set
      full_name = excluded.full_name,
      phone = excluded.phone,
      email = excluded.email,
      cpf = excluded.cpf,
      role = 'passenger',
      franchise_id = null,
      city_id = null,
      active = true,
      updated_at = now();

  elsif v_role = 'driver' then
    v_city := nullif(new.raw_user_meta_data->>'requested_city_id','')::uuid;
    v_requested_category := nullif(new.raw_user_meta_data->>'requested_category_id','')::uuid;

    if v_city is null then
      raise exception 'Escolha a cidade para cadastro';
    end if;

    select count(distinct fc.franchise_id), min(fc.franchise_id)
      into v_franchise_count, v_franchise
    from public.franchise_cities fc
    join public.franchises f on f.id = fc.franchise_id
    join public.cities c on c.id = fc.city_id
    where fc.city_id = v_city
      and f.active = true
      and f.deleted_at is null
      and f.blocked_at is null
      and c.active = true;

    if coalesce(v_franchise_count,0) = 0 or v_franchise is null then
      raise exception 'Esta cidade não possui franquia ativa disponível para cadastro';
    end if;
    if v_franchise_count <> 1 then
      raise exception 'Cidade com configuração de franquia inválida. Contate a CLICK-GO';
    end if;

    if v_requested_category is not null then
      select rc.required_vehicle_type into v_required_vehicle_type
      from public.ride_categories rc
      where rc.id = v_requested_category
        and rc.city_id = v_city
        and rc.franchise_id = v_franchise
        and rc.active = true;
      if not found then
        raise exception 'Categoria de veículo indisponível para esta cidade';
      end if;
    end if;

    if nullif(v_cpf,'') is not null and not public.is_valid_cpf(v_cpf) then
      raise exception 'CPF invalido';
    end if;

    v_machine := lower(coalesce(new.raw_user_meta_data->>'has_card_machine','false')) in ('true','1','yes','sim');

    insert into public.profiles(id,full_name,phone,email,role,franchise_id,city_id,active)
    values(new.id,nullif(trim(new.raw_user_meta_data->>'full_name'),''),nullif(trim(new.raw_user_meta_data->>'phone'),''),lower(new.email),'driver',v_franchise,v_city,true)
    on conflict(id) do update set
      full_name = excluded.full_name,
      phone = excluded.phone,
      email = excluded.email,
      role = 'driver',
      franchise_id = v_franchise,
      city_id = v_city,
      active = true,
      updated_at = now();

    insert into public.drivers(id,status,franchise_id,city_id,online,has_card_machine,card_machine_approved)
    values(new.id,'pending',v_franchise,v_city,false,v_machine,false)
    on conflict(id) do update set
      status='pending',franchise_id=v_franchise,city_id=v_city,online=false,has_card_machine=v_machine,card_machine_approved=false;

    insert into public.driver_operational_wallets(driver_id)
    values(new.id)
    on conflict(driver_id) do nothing;

    insert into public.driver_profiles(driver_id,cpf,cnh_number,cnh_category)
    values(new.id,nullif(v_cpf,''),nullif(trim(new.raw_user_meta_data->>'cnh_number'),''),nullif(trim(new.raw_user_meta_data->>'cnh_category'),''))
    on conflict(driver_id) do update set
      cpf=excluded.cpf,cnh_number=excluded.cnh_number,cnh_category=excluded.cnh_category,updated_at=now();

    if nullif(trim(new.raw_user_meta_data->>'vehicle_plate'),'') is not null then
      insert into public.vehicles(driver_id,plate,make,model,year,color,vehicle_type)
      values(
        new.id,
        upper(trim(new.raw_user_meta_data->>'vehicle_plate')),
        coalesce(nullif(trim(new.raw_user_meta_data->>'vehicle_make'),''),'Não informado'),
        coalesce(nullif(trim(new.raw_user_meta_data->>'vehicle_model'),''),'Não informado'),
        nullif(new.raw_user_meta_data->>'vehicle_year','')::int,
        nullif(trim(new.raw_user_meta_data->>'vehicle_color'),''),
        coalesce(v_required_vehicle_type, nullif(trim(new.raw_user_meta_data->>'vehicle_type'),''))
      )
      returning id into v_vehicle_id;
    end if;

    if v_requested_category is not null then
      insert into public.driver_category_eligibility(driver_id,category_id,vehicle_id,active,approved_at)
      values(new.id,v_requested_category,v_vehicle_id,true,now())
      on conflict(driver_id,category_id) do update set
        vehicle_id=excluded.vehicle_id,
        active=true,
        approved_at=now();
    end if;

    insert into public.admin_notifications(type,title,body,profile_id,driver_id,city_id,franchise_id)
    values('new_driver','Novo motorista aguardando aprovação',coalesce(new.raw_user_meta_data->>'full_name','Novo motorista'),new.id,new.id,v_city,v_franchise);
  end if;

  return new;
end;
$$;
