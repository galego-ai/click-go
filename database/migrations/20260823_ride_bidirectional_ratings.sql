create table if not exists public.driver_passenger_ratings (
  id uuid primary key default gen_random_uuid(),
  ride_id uuid not null unique references public.rides(id) on delete cascade,
  driver_id uuid not null references public.drivers(id) on delete cascade,
  passenger_id uuid not null references public.profiles(id) on delete cascade,
  rating integer not null check (rating between 1 and 5),
  comment text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.driver_passenger_ratings enable row level security;

create index if not exists driver_passenger_ratings_driver_idx on public.driver_passenger_ratings(driver_id, created_at desc);
create index if not exists driver_passenger_ratings_passenger_idx on public.driver_passenger_ratings(passenger_id, created_at desc);

drop policy if exists driver_passenger_ratings_driver_read on public.driver_passenger_ratings;
create policy driver_passenger_ratings_driver_read on public.driver_passenger_ratings for select to authenticated using ((select auth.uid()) = driver_id);

drop policy if exists driver_passenger_ratings_passenger_read on public.driver_passenger_ratings;
create policy driver_passenger_ratings_passenger_read on public.driver_passenger_ratings for select to authenticated using ((select auth.uid()) = passenger_id);

create or replace function public.submit_passenger_ride_rating(p_ride_id uuid, p_rating integer, p_comment text default null)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_actor uuid := auth.uid();
  v_ride public.rides%rowtype;
  v_avg numeric;
begin
  if v_actor is null then raise exception 'Autenticação obrigatória'; end if;
  if p_rating < 1 or p_rating > 5 then raise exception 'Avaliação deve ficar entre 1 e 5'; end if;
  select * into v_ride from public.rides where id = p_ride_id;
  if not found then raise exception 'Corrida não encontrada'; end if;
  if v_ride.passenger_id <> v_actor then raise exception 'Corrida não pertence a este passageiro'; end if;
  if v_ride.status <> 'completed' then raise exception 'A corrida precisa estar concluída'; end if;
  if v_ride.driver_id is null then raise exception 'Motorista não encontrado na corrida'; end if;
  insert into public.ride_ratings(id, ride_id, passenger_id, driver_id, rating, comment, created_at)
  values (gen_random_uuid(), p_ride_id, v_actor, v_ride.driver_id, p_rating, nullif(btrim(p_comment), ''), now())
  on conflict (ride_id) do update set rating = excluded.rating, comment = excluded.comment;
  select round(avg(rating)::numeric, 2) into v_avg from public.ride_ratings where driver_id = v_ride.driver_id;
  update public.drivers set rating = coalesce(v_avg, rating) where id = v_ride.driver_id;
  return jsonb_build_object('ok', true, 'driver_id', v_ride.driver_id, 'rating', p_rating, 'driver_average', v_avg);
end;
$$;

create or replace function public.submit_driver_passenger_rating(p_ride_id uuid, p_rating integer, p_comment text default null)
returns jsonb language plpgsql security definer set search_path = public, pg_temp as $$
declare
  v_actor uuid := auth.uid();
  v_ride public.rides%rowtype;
begin
  if v_actor is null then raise exception 'Autenticação obrigatória'; end if;
  if p_rating < 1 or p_rating > 5 then raise exception 'Avaliação deve ficar entre 1 e 5'; end if;
  select * into v_ride from public.rides where id = p_ride_id;
  if not found then raise exception 'Corrida não encontrada'; end if;
  if v_ride.driver_id <> v_actor then raise exception 'Corrida não pertence a este motorista'; end if;
  if v_ride.status <> 'completed' then raise exception 'A corrida precisa estar concluída'; end if;
  insert into public.driver_passenger_ratings(ride_id, driver_id, passenger_id, rating, comment, created_at, updated_at)
  values (p_ride_id, v_actor, v_ride.passenger_id, p_rating, nullif(btrim(p_comment), ''), now(), now())
  on conflict (ride_id) do update set rating = excluded.rating, comment = excluded.comment, updated_at = now();
  return jsonb_build_object('ok', true, 'passenger_id', v_ride.passenger_id, 'rating', p_rating);
end;
$$;

revoke all on function public.submit_passenger_ride_rating(uuid, integer, text) from public, anon;
revoke all on function public.submit_driver_passenger_rating(uuid, integer, text) from public, anon;
grant execute on function public.submit_passenger_ride_rating(uuid, integer, text) to authenticated, service_role;
grant execute on function public.submit_driver_passenger_rating(uuid, integer, text) to authenticated, service_role;

grant select on public.driver_passenger_ratings to authenticated;
revoke insert, update, delete on public.driver_passenger_ratings from anon, authenticated;
