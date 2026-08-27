alter table public.franchise_settings enable row level security;
alter table public.franchise_business_hours enable row level security;

drop policy if exists franchise_settings_scope on public.franchise_settings;
drop policy if exists operator_franchise_settings_write on public.franchise_settings;
drop policy if exists operator_franchise_settings_select on public.franchise_settings;
drop policy if exists franchise_settings_read on public.franchise_settings;
create policy franchise_settings_read
on public.franchise_settings
for select
to authenticated
using (
  public.current_active_management_role()='super_admin'
  or (public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id())
  or (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id())
);

drop policy if exists business_hours_scope on public.franchise_business_hours;
drop policy if exists franchise_business_hours_read on public.franchise_business_hours;
create policy franchise_business_hours_read
on public.franchise_business_hours
for select
to authenticated
using (
  public.current_active_management_role()='super_admin'
  or (public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id())
  or (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('settings'))
);

revoke all on table public.franchise_settings from anon,authenticated;
revoke all on table public.franchise_business_hours from anon,authenticated;
grant select on table public.franchise_settings to authenticated;
grant select on table public.franchise_business_hours to authenticated;
grant all on table public.franchise_settings to service_role;
grant all on table public.franchise_business_hours to service_role;
