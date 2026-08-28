create or replace function public.franchise_live_driver_map(p_city_id uuid default null)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_uid uuid := auth.uid();
  v_role text;
  v_franchise uuid;
  v_result jsonb;
begin
  if v_uid is null then
    raise exception 'Não autenticado';
  end if;

  select p.role::text, p.franchise_id
    into v_role, v_franchise
  from public.profiles p
  where p.id = v_uid
    and p.active is not false;

  if v_role <> 'franchise_admin' or v_franchise is null then
    raise exception 'Acesso exclusivo do franqueado';
  end if;

  if p_city_id is not null and not exists (
    select 1
    from public.franchise_cities fc
    where fc.franchise_id = v_franchise
      and fc.city_id = p_city_id
  ) then
    raise exception 'Cidade fora da franquia';
  end if;

  select coalesce(jsonb_agg(jsonb_build_object(
    'driver_id', d.id,
    'full_name', coalesce(nullif(trim(p.full_name),''), 'Motorista sem nome'),
    'online', coalesce(d.online,false),
    'status', d.status::text,
    'online_since', d.online_since,
    'city_id', d.city_id,
    'city_name', c.name,
    'city_state', c.state,
    'lat', dl.lat,
    'lng', dl.lng,
    'heading', dl.heading,
    'speed_kmh', dl.speed_kmh,
    'updated_at', dl.updated_at
  ) order by coalesce(dl.updated_at,d.online_since,d.created_at) desc), '[]'::jsonb)
    into v_result
  from public.drivers d
  join public.profiles p on p.id = d.id
  left join public.cities c on c.id = d.city_id
  left join public.driver_locations dl on dl.driver_id = d.id
  where d.franchise_id = v_franchise
    and d.status = 'approved'
    and coalesce(d.online,false) = true
    and (p_city_id is null or d.city_id = p_city_id);

  return v_result;
end;
$$;

revoke all on function public.franchise_live_driver_map(uuid) from public, anon;
grant execute on function public.franchise_live_driver_map(uuid) to authenticated, service_role;
