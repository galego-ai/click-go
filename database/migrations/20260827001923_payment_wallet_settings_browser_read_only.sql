-- CLICK-GO: global and local payment/wallet settings mutate only through trusted audited RPCs.

revoke all on table public.platform_payment_settings from anon, authenticated;
grant select on table public.platform_payment_settings to authenticated;
grant all on table public.platform_payment_settings to service_role;

revoke all on table public.platform_operational_wallet_settings from anon, authenticated;
grant select on table public.platform_operational_wallet_settings to authenticated;
grant all on table public.platform_operational_wallet_settings to service_role;

revoke all on table public.franchise_city_payment_settings from anon, authenticated;
grant select on table public.franchise_city_payment_settings to authenticated;
grant all on table public.franchise_city_payment_settings to service_role;

revoke all on table public.franchise_operational_wallet_settings from anon, authenticated;
grant select on table public.franchise_operational_wallet_settings to authenticated;
grant all on table public.franchise_operational_wallet_settings to service_role;

drop policy if exists platform_payment_settings_matrix_update on public.platform_payment_settings;
drop policy if exists platform_operational_settings_matrix_update on public.platform_operational_wallet_settings;

drop policy if exists franchise_city_payment_settings_franchise_insert on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_matrix_insert on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_operator_insert on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_franchise_update on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_matrix_update on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_operator_update on public.franchise_city_payment_settings;

drop policy if exists franchise_operational_settings_franchise_insert on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_matrix_insert on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_operator_insert on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_franchise_update on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_matrix_update on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_operator_update on public.franchise_operational_wallet_settings;

drop policy if exists franchise_city_payment_settings_read on public.franchise_city_payment_settings;
create policy franchise_city_payment_settings_read on public.franchise_city_payment_settings
for select to authenticated
using (
  public.current_active_management_role()='super_admin'
  or (
    public.current_active_management_role()='franchise_admin'
    and franchise_id=public.jwt_franchise_id()
    and public.can_access_city(city_id)
  )
  or (
    public.current_active_management_role()='operator'
    and franchise_id=public.staff_franchise_id()
    and public.staff_has_permission('finance')
    and public.can_access_city(city_id)
  )
);

drop policy if exists franchise_operational_settings_read on public.franchise_operational_wallet_settings;
create policy franchise_operational_settings_read on public.franchise_operational_wallet_settings
for select to authenticated
using (
  public.current_active_management_role()='super_admin'
  or (
    public.current_active_management_role()='franchise_admin'
    and franchise_id=public.jwt_franchise_id()
  )
  or (
    public.current_active_management_role()='operator'
    and franchise_id=public.staff_franchise_id()
    and public.staff_has_permission('finance')
  )
);
