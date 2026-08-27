create or replace function public.driver_my_categories()
returns table(
  category_id uuid,
  category_name text,
  required_vehicle_type text,
  category_active boolean,
  assigned boolean,
  locked_by_matrix boolean,
  base_fare numeric,
  price_per_km numeric,
  price_per_minute numeric,
  minimum_fare numeric
)
language plpgsql
stable
security definer
set search_path = 'public', 'pg_temp'
as $$
declare
  v_uid uuid := auth.uid();
  v_fid uuid;
  v_city uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;

  select d.franchise_id, d.city_id
    into v_fid, v_city
  from public.drivers d
  join public.profiles p on p.id = d.id
  where d.id = v_uid
    and p.role = 'driver'
    and p.active = true;

  if v_fid is null or v_city is null then
    raise exception 'Motorista sem operação vinculada';
  end if;

  return query
  select rc.id,
         rc.name,
         rc.required_vehicle_type,
         rc.active,
         exists(
           select 1
           from public.driver_category_eligibility e
           where e.driver_id = v_uid
             and e.category_id = rc.id
             and e.active = true
         ),
         rc.locked_by_matrix,
         rc.base_fare,
         rc.price_per_km,
         rc.price_per_minute,
         rc.minimum_fare
  from public.ride_categories rc
  where rc.franchise_id = v_fid
    and rc.city_id = v_city
  order by rc.active desc, rc.name;
end;
$$;

revoke all on function public.driver_my_categories() from public, anon;
grant execute on function public.driver_my_categories() to authenticated, service_role;