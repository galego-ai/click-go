-- Mantém itens bloqueados pela Matriz visíveis ao Franqueado em modo somente leitura
-- e endurece as políticas SELECT do operador com perfil ativo, permissão e escopo territorial.

-- Categorias: o Franqueado precisa enxergar inclusive categorias locked_by_matrix,
-- enquanto a policy ALL continua sendo a única via de escrita e exige not locked_by_matrix.
drop policy if exists franchise_admin_categories_select on public.ride_categories;
create policy franchise_admin_categories_select
on public.ride_categories
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and exists (
    select 1
    from public.franchise_cities fc
    where fc.franchise_id = public.jwt_franchise_id()
      and fc.city_id = ride_categories.city_id
  )
);

drop policy if exists operator_categories_select on public.ride_categories;
drop policy if exists operator_city_categories_select on public.ride_categories;
create policy operator_categories_select
on public.ride_categories
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and (
    public.staff_has_permission('pricing')
    or public.staff_has_permission('operation')
  )
  and public.can_access_city(city_id)
);

-- Promoções: bloqueadas continuam visíveis, mas a policy ALL impede update/delete.
drop policy if exists franchise_admin_promotions_select on public.promotions;
create policy franchise_admin_promotions_select
on public.promotions
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and (
    city_id is null
    or exists (
      select 1
      from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = promotions.city_id
    )
  )
);

drop policy if exists operator_promotions_select on public.promotions;
create policy operator_promotions_select
on public.promotions
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and (
    public.staff_has_permission('marketing')
    or public.staff_has_permission('operation')
  )
  and (city_id is null or public.can_access_city(city_id))
);

-- Cupons: bloqueados continuam visíveis, mas a policy ALL impede update/delete.
drop policy if exists franchise_admin_coupons_select on public.coupons;
create policy franchise_admin_coupons_select
on public.coupons
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
  and (
    city_id is null
    or exists (
      select 1
      from public.franchise_cities fc
      where fc.franchise_id = public.jwt_franchise_id()
        and fc.city_id = coupons.city_id
    )
  )
);

drop policy if exists operator_coupons_select on public.coupons;
create policy operator_coupons_select
on public.coupons
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and (
    public.staff_has_permission('marketing')
    or public.staff_has_permission('operation')
  )
  and (city_id is null or public.can_access_city(city_id))
);

-- Anúncios não possuem locked_by_matrix; apenas substituímos a leitura antiga do operador.
drop policy if exists operator_advertising_banners_select on public.advertising_banners;
create policy operator_advertising_banners_select
on public.advertising_banners
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and (
    public.staff_has_permission('marketing')
    or public.staff_has_permission('operation')
  )
  and (city_id is null or public.can_access_city(city_id))
);
