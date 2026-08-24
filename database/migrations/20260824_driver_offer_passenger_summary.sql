drop function if exists public.get_driver_pending_offers();

create function public.get_driver_pending_offers()
returns table(
  offer_id uuid,
  ride_id uuid,
  expires_at timestamptz,
  distance_to_pickup_km numeric,
  eta_to_pickup_min integer,
  estimated_driver_earning numeric,
  estimated_fare numeric,
  origin_label text,
  origin_lat double precision,
  origin_lng double precision,
  destination_label text,
  destination_lat double precision,
  destination_lng double precision,
  category_name text,
  passenger_id uuid,
  passenger_name text,
  passenger_avatar_url text,
  passenger_rating numeric,
  passenger_rating_count bigint,
  passenger_completed_rides bigint,
  payment_method text
)
language sql
security definer
set search_path = 'public', 'pg_temp'
as $$
  select
    ro.id,
    ro.ride_id,
    ro.expires_at,
    ro.distance_to_pickup_km,
    ro.eta_to_pickup_min,
    ro.estimated_driver_earning,
    r.estimated_fare,
    r.origin_label,
    r.origin_lat,
    r.origin_lng,
    r.destination_label,
    r.destination_lat,
    r.destination_lng,
    c.name,
    r.passenger_id,
    coalesce(nullif(btrim(p.full_name), ''), 'Passageiro CLICK-GO') as passenger_name,
    p.avatar_url,
    coalesce(pr.rating, 0)::numeric(3,2) as passenger_rating,
    coalesce(pr.rating_count, 0)::bigint as passenger_rating_count,
    coalesce(pc.completed_rides, 0)::bigint as passenger_completed_rides,
    r.payment_method_preference
  from public.ride_offers ro
  join public.rides r on r.id = ro.ride_id
  left join public.ride_categories c on c.id = r.category_id
  left join public.profiles p on p.id = r.passenger_id
  left join lateral (
    select avg(dpr.rating)::numeric(3,2) as rating, count(*)::bigint as rating_count
    from public.driver_passenger_ratings dpr
    where dpr.passenger_id = r.passenger_id
  ) pr on true
  left join lateral (
    select count(*)::bigint as completed_rides
    from public.rides rr
    where rr.passenger_id = r.passenger_id
      and rr.status = 'completed'
  ) pc on true
  where ro.driver_id = auth.uid()
    and ro.status = 'pending'
    and ro.expires_at > now()
  order by ro.expires_at;
$$;

revoke all on function public.get_driver_pending_offers() from public, anon;
grant execute on function public.get_driver_pending_offers() to authenticated;
