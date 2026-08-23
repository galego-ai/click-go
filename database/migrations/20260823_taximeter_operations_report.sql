create or replace function public.get_taximeter_operations_report(
  p_from timestamptz default (now() - interval '30 days'),
  p_to timestamptz default now(),
  p_limit integer default 1000
)
returns table(
  session_id uuid,
  driver_id uuid,
  driver_name text,
  franchise_id uuid,
  franchise_name text,
  city_id uuid,
  city_name text,
  status text,
  started_at timestamptz,
  ended_at timestamptz,
  distance_m numeric,
  elapsed_seconds integer,
  final_amount numeric,
  current_amount numeric,
  payment_method text,
  multiplier numeric
)
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid := auth.uid();
  v_role text := public.jwt_app_role();
  v_franchise uuid := public.jwt_franchise_id();
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role not in ('super_admin','franchise_admin') then raise exception 'Acesso restrito à operação'; end if;
  return query
  select s.id,s.driver_id,p.full_name,s.franchise_id,coalesce(f.trade_name,f.legal_name),s.city_id,c.name,
         s.status,s.started_at,s.ended_at,s.distance_m,s.elapsed_seconds,s.final_amount,s.current_amount,s.payment_method,s.multiplier
  from public.driver_taximeter_sessions s
  left join public.profiles p on p.id=s.driver_id
  left join public.franchises f on f.id=s.franchise_id
  left join public.cities c on c.id=s.city_id
  where s.started_at >= coalesce(p_from,now()-interval '30 days')
    and s.started_at <= coalesce(p_to,now())
    and (v_role='super_admin' or s.franchise_id=v_franchise)
  order by s.started_at desc
  limit greatest(1,least(coalesce(p_limit,1000),5000));
end;
$$;
revoke all on function public.get_taximeter_operations_report(timestamptz,timestamptz,integer) from public,anon;
grant execute on function public.get_taximeter_operations_report(timestamptz,timestamptz,integer) to authenticated;
