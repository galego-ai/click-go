drop policy if exists super_admin_pricing_all on public.city_pricing_rules;
drop policy if exists franchise_admin_city_pricing_all on public.city_pricing_rules;
create policy super_admin_pricing_all
on public.city_pricing_rules
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_city_pricing_all
on public.city_pricing_rules
for all
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = city_pricing_rules.city_id
  )
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = city_pricing_rules.city_id
  )
);

drop policy if exists super_admin_dynamic_pricing_all on public.dynamic_pricing_rules;
drop policy if exists franchise_admin_dynamic_pricing_all on public.dynamic_pricing_rules;
create policy super_admin_dynamic_pricing_all
on public.dynamic_pricing_rules
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_dynamic_pricing_all
on public.dynamic_pricing_rules
for all
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = dynamic_pricing_rules.city_id
  )
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = dynamic_pricing_rules.city_id
  )
);

drop policy if exists super_admin_categories_all on public.ride_categories;
drop policy if exists franchise_admin_categories_all on public.ride_categories;
drop policy if exists operator_categories_write on public.ride_categories;
create policy super_admin_categories_all
on public.ride_categories
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_categories_all
on public.ride_categories
for all
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and not locked_by_matrix
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = ride_categories.city_id
  )
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and not locked_by_matrix
  and exists (
    select 1 from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = ride_categories.city_id
  )
);
create policy operator_categories_write
on public.ride_categories
for all
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('pricing')
  and not locked_by_matrix
  and public.can_access_city(city_id)
)
with check (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('pricing')
  and not locked_by_matrix
  and public.can_access_city(city_id)
);
