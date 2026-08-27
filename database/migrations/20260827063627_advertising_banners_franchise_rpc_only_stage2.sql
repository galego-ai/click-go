drop policy if exists franchise_admin_banners_all on public.advertising_banners;
drop policy if exists operator_advertising_banners_write on public.advertising_banners;

drop policy if exists franchise_admin_banners_select on public.advertising_banners;
create policy franchise_admin_banners_select
on public.advertising_banners
for select
to authenticated
using (
  public.current_active_management_role()='franchise_admin'
  and franchise_id=public.current_profile_franchise_id()
  and (
    city_id is null
    or exists(
      select 1 from public.franchise_cities fc
      where fc.franchise_id=public.current_profile_franchise_id()
        and fc.city_id=advertising_banners.city_id
    )
  )
);

revoke insert, update, delete, truncate, references, trigger on table public.advertising_banners from anon;
grant select on table public.advertising_banners to anon;
