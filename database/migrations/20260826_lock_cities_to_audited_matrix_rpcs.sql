drop policy if exists super_admin_cities_all on public.cities;

create policy matrix_cities_select
on public.cities
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

revoke insert, update, delete on table public.cities from authenticated, anon;
grant select on table public.cities to authenticated, anon;
