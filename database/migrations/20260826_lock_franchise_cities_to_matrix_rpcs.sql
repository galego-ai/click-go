drop policy if exists super_admin_franchise_cities_all on public.franchise_cities;
drop policy if exists franchise_admin_own_franchise_cities_select on public.franchise_cities;
drop policy if exists operator_franchise_cities_select on public.franchise_cities;

create policy matrix_franchise_cities_select
on public.franchise_cities
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_own_franchise_cities_select
on public.franchise_cities
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

create policy operator_franchise_cities_select
on public.franchise_cities
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
);

revoke insert, update, delete on table public.franchise_cities from authenticated, anon;
grant select on table public.franchise_cities to authenticated;
