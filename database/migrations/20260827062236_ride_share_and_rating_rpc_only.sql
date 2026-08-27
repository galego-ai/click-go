revoke all on table public.ride_shares from anon;
revoke insert, update, delete, truncate on table public.ride_shares from authenticated;
grant select on table public.ride_shares to authenticated;

drop policy if exists ride_shares_own_all on public.ride_shares;
drop policy if exists ride_shares_own_select on public.ride_shares;
create policy ride_shares_own_select
on public.ride_shares
for select
to authenticated
using (passenger_id = auth.uid());

revoke all on table public.ride_ratings from anon;
revoke insert, update, delete, truncate on table public.ride_ratings from authenticated;
grant select on table public.ride_ratings to authenticated;

drop policy if exists ride_ratings_own_all on public.ride_ratings;
drop policy if exists ride_ratings_own_select on public.ride_ratings;
create policy ride_ratings_own_select
on public.ride_ratings
for select
to authenticated
using (passenger_id = auth.uid());

revoke all on function public.create_ride_share(uuid,integer) from public, anon;
revoke all on function public.revoke_ride_share(uuid) from public, anon;
revoke all on function public.submit_passenger_ride_rating(uuid,integer,text) from public, anon;
grant execute on function public.create_ride_share(uuid,integer) to authenticated, service_role;
grant execute on function public.revoke_ride_share(uuid) to authenticated, service_role;
grant execute on function public.submit_passenger_ride_rating(uuid,integer,text) to authenticated, service_role;
