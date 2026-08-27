revoke insert, update, delete, truncate, trigger, references on table public.ride_categories from anon, authenticated;
revoke all on table public.ride_categories from anon;
grant select on table public.ride_categories to authenticated;

drop policy if exists super_admin_categories_all on public.ride_categories;
drop policy if exists franchise_admin_categories_all on public.ride_categories;
drop policy if exists operator_categories_write on public.ride_categories;

drop policy if exists super_admin_categories_select on public.ride_categories;
create policy super_admin_categories_select on public.ride_categories
for select to authenticated
using (public.current_active_management_role() = 'super_admin');

drop policy if exists franchise_admin_categories_select on public.ride_categories;
create policy franchise_admin_categories_select on public.ride_categories
for select to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.current_profile_franchise_id()
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.current_profile_franchise_id()
      and fc.city_id = ride_categories.city_id
  )
);

drop policy if exists operator_categories_select on public.ride_categories;
create policy operator_categories_select on public.ride_categories
for select to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and (public.staff_has_permission('pricing') or public.staff_has_permission('operation'))
  and public.can_access_city(city_id)
);

drop policy if exists ride_categories_read_active on public.ride_categories;
create policy ride_categories_read_active on public.ride_categories
for select to authenticated
using (active = true);