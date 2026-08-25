-- CLICK-GO first-party app banner feed.
-- Uses existing advertising_banners and resolves city by current GPS when needed.

create or replace function public.get_active_app_banners(
  p_audience text,
  p_placement text default 'home',
  p_lat double precision default null,
  p_lng double precision default null,
  p_city_id uuid default null,
  p_franchise_id uuid default null,
  p_limit integer default 3
)
returns table(
  id uuid,
  title text,
  image_url text,
  target_url text,
  advertiser_name text,
  city_id uuid,
  franchise_id uuid,
  placement text,
  audience text,
  sort_order integer
)
language sql
stable
security invoker
set search_path=public,pg_temp
as $$
  with nearest_city as (
    select coalesce(
      p_city_id,
      (
        select x.id
        from (
          select c.id,c.detection_radius_km,
            6371.0 * acos(
              least(1.0,greatest(-1.0,
                cos(radians(p_lat)) * cos(radians(c.center_lat)) * cos(radians(c.center_lng)-radians(p_lng)) +
                sin(radians(p_lat)) * sin(radians(c.center_lat))
              ))
            ) as distance_km
          from public.cities c
          where c.active=true
            and c.center_lat is not null and c.center_lng is not null
            and p_lat is not null and p_lng is not null
        ) x
        where x.distance_km <= coalesce(x.detection_radius_km,25)::double precision
        order by x.distance_km
        limit 1
      )
    ) as id
  )
  select b.id,b.title,b.image_url,b.target_url,b.advertiser_name,b.city_id,b.franchise_id,b.placement,b.audience,b.sort_order
  from public.advertising_banners b
  cross join nearest_city n
  where b.active=true
    and (b.starts_at is null or b.starts_at <= now())
    and (b.ends_at is null or b.ends_at >= now())
    and b.audience in (p_audience,'both')
    and b.placement in (p_placement,'home')
    and (b.city_id is null or b.city_id=n.id)
    and (
      b.franchise_id is null
      or b.franchise_id=p_franchise_id
      or (p_audience='passenger' and b.city_id is not null and b.city_id=n.id)
    )
  order by
    case when p_franchise_id is not null and b.franchise_id=p_franchise_id then 0
         when n.id is not null and b.city_id=n.id then 1
         else 2 end,
    b.sort_order asc,b.created_at desc
  limit least(greatest(coalesce(p_limit,3),1),10);
$$;

revoke all on function public.get_active_app_banners(text,text,double precision,double precision,uuid,uuid,integer) from public;
revoke all on function public.get_active_app_banners(text,text,double precision,double precision,uuid,uuid,integer) from anon;
grant execute on function public.get_active_app_banners(text,text,double precision,double precision,uuid,uuid,integer) to authenticated;
