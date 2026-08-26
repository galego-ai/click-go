create or replace function public.create_franchise_manual_ride(
  p_passenger_id uuid,
  p_city_id uuid,
  p_category_id uuid,
  p_origin_label text,
  p_origin_lat double precision,
  p_origin_lng double precision,
  p_destination_label text,
  p_destination_lat double precision,
  p_destination_lng double precision,
  p_distance_km numeric default null,
  p_duration_min numeric default null,
  p_payment_method text default 'auto',
  p_dispatch_mode text default 'auto',
  p_requested_driver_id uuid default null,
  p_note text default null
)
returns uuid
language plpgsql
security definer
set search_path to public,pg_temp
as $$
declare
  v_user uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_franchise uuid;
  v_staff_franchise uuid;
  v_category public.ride_categories%rowtype;
  v_driver public.drivers%rowtype;
  v_pay record;
  v_method text;
  v_distance numeric;
  v_duration numeric;
  v_ride_id uuid;
begin
  if v_user is null or v_role not in ('super_admin','franchise_admin','operator') then
    raise exception 'Acesso restrito à gestão autenticada';
  end if;

  if nullif(btrim(coalesce(p_origin_label,'')),'') is null
     or nullif(btrim(coalesce(p_destination_label,'')),'') is null then
    raise exception 'Informe origem e destino';
  end if;
  if p_origin_lat not between -90 and 90 or p_destination_lat not between -90 and 90
     or p_origin_lng not between -180 and 180 or p_destination_lng not between -180 and 180 then
    raise exception 'Coordenadas inválidas';
  end if;

  select * into v_category
  from public.ride_categories
  where id=p_category_id and city_id=p_city_id and active=true;
  if not found or v_category.franchise_id is null then
    raise exception 'Categoria ativa da franquia não encontrada para esta cidade';
  end if;
  v_franchise:=v_category.franchise_id;

  if not exists(
    select 1 from public.franchise_cities fc
    where fc.franchise_id=v_franchise and fc.city_id=p_city_id
  ) then
    raise exception 'Cidade não pertence à franquia da categoria';
  end if;

  if v_role='franchise_admin' then
    if v_franchise is distinct from public.current_profile_franchise_id() then
      raise exception 'Franquia fora do seu escopo';
    end if;
    if not public.can_access_city(p_city_id) then raise exception 'Cidade fora do seu escopo'; end if;
  elsif v_role='operator' then
    if not public.staff_has_permission('operation') then raise exception 'Permissão de operação não concedida'; end if;
    v_staff_franchise:=public.staff_franchise_id();
    if v_franchise is distinct from v_staff_franchise then raise exception 'Franquia fora do seu escopo'; end if;
    if not public.can_access_city(p_city_id) then raise exception 'Cidade fora do seu escopo'; end if;
  end if;

  if not exists(
    select 1 from public.profiles p
    where p.id=p_passenger_id and p.role='passenger' and p.active=true
  ) then
    raise exception 'Passageiro ativo não encontrado';
  end if;

  select * into v_pay from public.get_effective_payment_settings(p_city_id);
  v_method:=lower(coalesce(nullif(btrim(p_payment_method),''),'auto'));
  if v_method='auto' then
    if coalesce(v_pay.cash_enabled,false) then v_method:='cash';
    elsif coalesce(v_pay.pix_enabled,false) then v_method:='pix';
    elsif coalesce(v_pay.card_app_enabled,false) then v_method:='card';
    elsif coalesce(v_pay.card_machine_enabled,false) then v_method:='card_machine';
    else raise exception 'Nenhuma forma de pagamento habilitada nesta cidade';
    end if;
  end if;
  if v_method not in ('cash','pix','card','card_machine') then raise exception 'Forma de pagamento inválida'; end if;
  if (v_method='cash' and not coalesce(v_pay.cash_enabled,false))
     or (v_method='pix' and not coalesce(v_pay.pix_enabled,false))
     or (v_method='card' and not coalesce(v_pay.card_app_enabled,false))
     or (v_method='card_machine' and not coalesce(v_pay.card_machine_enabled,false)) then
    raise exception 'Forma de pagamento indisponível nesta cidade';
  end if;

  v_distance:=case when coalesce(p_distance_km,0)>0 then round(p_distance_km,2)
                   else round(greatest(public.haversine_km(p_origin_lat,p_origin_lng,p_destination_lat,p_destination_lng)*1.18,0.5)::numeric,2) end;
  v_duration:=case when coalesce(p_duration_min,0)>0 then round(p_duration_min,1)
                   else round(greatest(v_distance/0.45,2)::numeric,1) end;

  if p_requested_driver_id is not null then
    select * into v_driver from public.drivers where id=p_requested_driver_id;
    if not found
       or v_driver.franchise_id is distinct from v_franchise
       or v_driver.city_id is distinct from p_city_id
       or v_driver.status<>'approved'
       or not v_driver.online
       or not public.driver_can_be_online(v_driver.id)
       or not public.driver_can_accept_payment_method(v_driver.id,v_method) then
      raise exception 'Motorista solicitado não está disponível ou não pertence ao escopo';
    end if;
  end if;

  insert into public.rides(
    passenger_id,franchise_id,city_id,category_id,status,
    origin_label,origin_lat,origin_lng,
    destination_label,destination_lat,destination_lng,
    estimated_distance_km,estimated_duration_min,
    payment_method_preference,dispatch_mode,requested_driver_id,
    created_by_profile_id,dispatch_note
  ) values (
    p_passenger_id,v_franchise,p_city_id,p_category_id,'requested',
    btrim(p_origin_label),p_origin_lat,p_origin_lng,
    btrim(p_destination_label),p_destination_lat,p_destination_lng,
    v_distance,v_duration,
    v_method,
    case when p_requested_driver_id is null then 'auto' else 'manual' end,
    p_requested_driver_id,v_user,
    coalesce(nullif(btrim(coalesce(p_note,'')),''),'Criada pelo painel de gestão')
  ) returning id into v_ride_id;

  if p_requested_driver_id is not null then
    update public.rides
       set driver_id=p_requested_driver_id,status='accepted',accepted_at=now()
     where id=v_ride_id;
    insert into public.ride_events(ride_id,driver_id,event_type)
    values(v_ride_id,p_requested_driver_id,'management_manual_assignment');
  end if;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_user,'management_manual_ride_created','ride',v_ride_id::text,
    jsonb_build_object(
      'actor_role',v_role,'passenger_id',p_passenger_id,'franchise_id',v_franchise,'city_id',p_city_id,
      'category_id',p_category_id,'payment_method',v_method,'requested_driver_id',p_requested_driver_id,
      'distance_km',v_distance,'duration_min',v_duration,'dispatch_mode',case when p_requested_driver_id is null then 'auto' else 'manual' end
    ));

  return v_ride_id;
end;
$$;

revoke all on function public.create_franchise_manual_ride(uuid,uuid,uuid,text,double precision,double precision,text,double precision,double precision,numeric,numeric,text,text,uuid,text) from public,anon;
grant execute on function public.create_franchise_manual_ride(uuid,uuid,uuid,text,double precision,double precision,text,double precision,double precision,numeric,numeric,text,text,uuid,text) to authenticated,service_role;

drop policy if exists franchise_admin_own_rides_insert on public.rides;
drop policy if exists franchise_admin_own_rides_update on public.rides;
drop policy if exists operator_rides_scope_insert on public.rides;
drop policy if exists operator_rides_scope_update on public.rides;
drop policy if exists rides_passenger_insert on public.rides;
drop policy if exists super_admin_rides_all on public.rides;
drop policy if exists super_admin_rides_select on public.rides;
create policy super_admin_rides_select on public.rides for select to authenticated
using (public.current_active_management_role()='super_admin');

revoke all on public.rides from anon;
revoke insert,update,delete,truncate,references,trigger on public.rides from authenticated;
grant select on public.rides to authenticated;
grant all on public.rides to service_role;
