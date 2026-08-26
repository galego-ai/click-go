drop policy if exists super_admin_promotions_all on public.promotions;
drop policy if exists franchise_admin_own_promotions_all on public.promotions;
drop policy if exists operator_promotions_write on public.promotions;
create policy super_admin_promotions_all
on public.promotions
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_own_promotions_all
on public.promotions
for all
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and not locked_by_matrix
  and (
    city_id is null or exists (
      select 1 from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = promotions.city_id
    )
  )
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and not locked_by_matrix
  and (
    city_id is null or exists (
      select 1 from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = promotions.city_id
    )
  )
);
create policy operator_promotions_write
on public.promotions
for all
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('marketing')
  and not locked_by_matrix
  and (city_id is null or public.can_access_city(city_id))
)
with check (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('marketing')
  and not locked_by_matrix
  and (city_id is null or public.can_access_city(city_id))
);

drop policy if exists super_admin_coupons_all on public.coupons;
drop policy if exists franchise_admin_own_coupons_all on public.coupons;
drop policy if exists operator_coupons_write on public.coupons;
create policy super_admin_coupons_all
on public.coupons
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_own_coupons_all
on public.coupons
for all
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and not locked_by_matrix
  and (
    city_id is null or exists (
      select 1 from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = coupons.city_id
    )
  )
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and not locked_by_matrix
  and (
    city_id is null or exists (
      select 1 from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = coupons.city_id
    )
  )
);
create policy operator_coupons_write
on public.coupons
for all
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('marketing')
  and not locked_by_matrix
  and (city_id is null or public.can_access_city(city_id))
)
with check (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('marketing')
  and not locked_by_matrix
  and (city_id is null or public.can_access_city(city_id))
);

drop policy if exists super_admin_banners_all on public.advertising_banners;
drop policy if exists franchise_admin_banners_all on public.advertising_banners;
drop policy if exists operator_advertising_banners_write on public.advertising_banners;
create policy super_admin_banners_all
on public.advertising_banners
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_banners_all
on public.advertising_banners
for all
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and (
    city_id is null or exists (
      select 1 from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = advertising_banners.city_id
    )
  )
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and (
    city_id is null or exists (
      select 1 from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = advertising_banners.city_id
    )
  )
);
create policy operator_advertising_banners_write
on public.advertising_banners
for all
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('marketing')
  and (city_id is null or public.can_access_city(city_id))
)
with check (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('marketing')
  and (city_id is null or public.can_access_city(city_id))
);
