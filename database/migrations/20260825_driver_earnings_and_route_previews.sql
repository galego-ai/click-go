-- CLICK-GO: lightweight ride-history route previews and real driver earnings.
-- Both functions run with caller privileges so the existing RLS policies remain authoritative.

create or replace function public.get_my_ride_route_previews(
  p_limit integer default 20,
  p_max_points integer default 36
)
returns table(
  ride_id uuid,
  points jsonb
)
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
  with params as (
    select
      least(greatest(coalesce(p_limit, 20), 1), 50) as ride_limit,
      least(greatest(coalesce(p_max_points, 36), 8), 80) as max_points
  ),
  mine as (
    select r.id, r.completed_at, r.requested_at
    from public.rides r
    where r.status::text = 'completed'
      and (r.passenger_id = auth.uid() or r.driver_id = auth.uid())
    order by r.completed_at desc nulls last, r.requested_at desc
    limit (select ride_limit from params)
  ),
  numbered as (
    select lp.ride_id,lp.lat,lp.lng,lp.recorded_at,lp.id,
      row_number() over (partition by lp.ride_id order by lp.recorded_at, lp.id) as rn,
      count(*) over (partition by lp.ride_id) as cnt
    from public.ride_location_points lp
    join mine m on m.id = lp.ride_id
  ),
  sampled as (
    select n.* from numbered n cross join params p
    where n.cnt <= p.max_points
       or n.rn = 1
       or n.rn = n.cnt
       or mod(n.rn - 1,greatest(1, ceil(n.cnt::numeric / p.max_points)::integer)) = 0
  ),
  aggregated as (
    select s.ride_id,
      jsonb_agg(jsonb_build_object('lat', s.lat, 'lng', s.lng) order by s.recorded_at, s.id) as points
    from sampled s group by s.ride_id
  )
  select m.id as ride_id, coalesce(a.points, '[]'::jsonb) as points
  from mine m left join aggregated a on a.ride_id = m.id
  order by m.completed_at desc nulls last, m.requested_at desc;
$$;

revoke all on function public.get_my_ride_route_previews(integer, integer) from public;
revoke all on function public.get_my_ride_route_previews(integer, integer) from anon;
grant execute on function public.get_my_ride_route_previews(integer, integer) to authenticated;

create or replace function public.get_my_driver_earnings_history(p_limit integer default 50)
returns table(
  ride_id uuid,
  completed_at timestamptz,
  origin_label text,
  destination_label text,
  payment_method text,
  gross_fare numeric,
  wallet_discount numeric,
  net_earning numeric
)
language sql
stable
security invoker
set search_path = public, pg_temp
as $$
  with debits as (
    select t.ride_id,
      coalesce(sum(t.amount) filter (
        where t.transaction_type = 'debit'
          and t.status = 'settled'
      ),0)::numeric as wallet_discount
    from public.driver_operational_transactions t
    where t.driver_id = auth.uid() and t.ride_id is not null
    group by t.ride_id
  )
  select r.id,r.completed_at,r.origin_label,r.destination_label,
    coalesce(r.payment_method_preference,'cash') as payment_method,
    coalesce(r.final_fare,r.estimated_fare,0)::numeric as gross_fare,
    coalesce(d.wallet_discount,0)::numeric as wallet_discount,
    greatest(coalesce(r.final_fare,r.estimated_fare,0)::numeric-coalesce(d.wallet_discount,0)::numeric,0::numeric) as net_earning
  from public.rides r
  left join debits d on d.ride_id=r.id
  where r.driver_id=auth.uid() and r.status::text='completed'
  order by r.completed_at desc nulls last,r.requested_at desc
  limit least(greatest(coalesce(p_limit,50),1),100);
$$;

revoke all on function public.get_my_driver_earnings_history(integer) from public;
revoke all on function public.get_my_driver_earnings_history(integer) from anon;
grant execute on function public.get_my_driver_earnings_history(integer) to authenticated;
