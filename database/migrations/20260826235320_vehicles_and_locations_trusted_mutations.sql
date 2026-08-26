-- CLICK-GO: vehicle + driver location mutations via trusted RPCs only.

-- Browser clients may read according to RLS, but must not write these tables directly.
revoke all on table public.vehicles from anon, authenticated;
grant select on table public.vehicles to authenticated;
grant all on table public.vehicles to service_role;

revoke all on table public.driver_locations from anon, authenticated;
grant select on table public.driver_locations to authenticated;
grant all on table public.driver_locations to service_role;

-- Replace broad policies with scoped read-only policies.
drop policy if exists super_admin_vehicles_all on public.vehicles;
drop policy if exists vehicles_driver_all on public.vehicles;
drop policy if exists franchise_admin_vehicles_select on public.vehicles;
drop policy if exists operator_vehicles_select on public.vehicles;
drop policy if exists super_admin_vehicles_select on public.vehicles;
drop policy if exists vehicles_driver_select on public.vehicles;

create policy vehicles_driver_select on public.vehicles
for select to authenticated
using (driver_id = auth.uid());

create policy super_admin_vehicles_select on public.vehicles
for select to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_vehicles_select on public.vehicles
for select to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and exists (
    select 1 from public.drivers d
    where d.id = vehicles.driver_id
      and d.franchise_id = public.jwt_franchise_id()
      and d.city_id is not null
      and public.can_access_city(d.city_id)
  )
);

create policy operator_vehicles_select on public.vehicles
for select to authenticated
using (
  public.current_active_management_role() = 'operator'
  and exists (
    select 1 from public.drivers d
    where d.id = vehicles.driver_id
      and d.franchise_id = public.staff_franchise_id()
      and d.city_id is not null
      and public.can_access_city(d.city_id)
  )
  and (public.staff_has_permission('drivers') or public.staff_has_permission('support'))
);

drop policy if exists locations_driver_all on public.driver_locations;
drop policy if exists super_admin_locations_all on public.driver_locations;
drop policy if exists locations_driver_select on public.driver_locations;
drop policy if exists super_admin_locations_select on public.driver_locations;

create policy locations_driver_select on public.driver_locations
for select to authenticated
using (driver_id = auth.uid());

create policy super_admin_locations_select on public.driver_locations
for select to authenticated
using (public.current_active_management_role() = 'super_admin');

-- Driver vehicle creation/editing is centralized and validated.
create or replace function public.upsert_my_vehicle(
  p_vehicle_id uuid default null,
  p_make text default null,
  p_model text default null,
  p_year integer default null,
  p_plate text default null,
  p_color text default null,
  p_vehicle_type text default null,
  p_active boolean default true
)
returns uuid
language plpgsql
security definer
set search_path = public, pg_temp
as $function$
declare
  v_uid uuid:=auth.uid();
  v_id uuid;
  v_make text:=nullif(btrim(coalesce(p_make,'')),'');
  v_model text:=nullif(btrim(coalesce(p_model,'')),'');
  v_plate text:=upper(regexp_replace(coalesce(p_plate,''),'[^A-Za-z0-9]','','g'));
  v_type text:=lower(btrim(coalesce(p_vehicle_type,'')));
  v_current_year integer:=extract(year from current_date)::integer;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if not exists(select 1 from public.profiles p where p.id=v_uid and p.role='driver' and p.active=true)
     or not exists(select 1 from public.drivers d where d.id=v_uid) then
    raise exception 'Cadastro de motorista não encontrado ou inativo';
  end if;
  if v_make is null or v_model is null then raise exception 'Informe marca e modelo do veículo'; end if;
  if v_plate !~ '^[A-Z0-9]{7}$' then raise exception 'Placa inválida'; end if;
  if p_year is not null and (p_year<1950 or p_year>v_current_year+1) then raise exception 'Ano do veículo inválido'; end if;
  if v_type not in ('car','motorcycle') then raise exception 'Tipo de veículo inválido'; end if;

  if p_vehicle_id is null then
    insert into public.vehicles(driver_id,make,model,year,plate,color,vehicle_type,active)
    values(v_uid,v_make,v_model,p_year,v_plate,nullif(btrim(coalesce(p_color,'')),''),v_type,coalesce(p_active,true))
    returning id into v_id;
  else
    update public.vehicles
       set make=v_make,
           model=v_model,
           year=p_year,
           plate=v_plate,
           color=nullif(btrim(coalesce(p_color,'')),''),
           vehicle_type=v_type,
           active=coalesce(p_active,true)
     where id=p_vehicle_id and driver_id=v_uid
     returning id into v_id;
    if v_id is null then raise exception 'Veículo não encontrado para este motorista'; end if;
  end if;

  if not coalesce(p_active,true)
     and not exists(select 1 from public.vehicles v where v.driver_id=v_uid and v.active=true) then
    update public.drivers set online=false where id=v_uid;
  end if;

  return v_id;
end;
$function$;

-- Explicit function execute grants. No anonymous execution.
revoke all on function public.upsert_my_vehicle(uuid,text,text,integer,text,text,text,boolean) from public, anon;
grant execute on function public.upsert_my_vehicle(uuid,text,text,integer,text,text,text,boolean) to authenticated, service_role;

revoke all on function public.franchise_set_driver_vehicle_type(uuid,uuid,text) from public, anon;
grant execute on function public.franchise_set_driver_vehicle_type(uuid,uuid,text) to authenticated, service_role;

revoke all on function public.set_driver_online(boolean,double precision,double precision) from public, anon;
grant execute on function public.set_driver_online(boolean,double precision,double precision) to authenticated, service_role;

revoke all on function public.update_driver_location(double precision,double precision,double precision,double precision) from public, anon;
grant execute on function public.update_driver_location(double precision,double precision,double precision,double precision) to authenticated, service_role;
