drop policy if exists operator_manager_staff_permissions_all on public.franchise_staff_permissions;
create policy operator_manager_staff_permissions_all
on public.franchise_staff_permissions
for all
using (
  public.jwt_app_role()='operator'
  and franchise_id=public.staff_franchise_id()
  and public.staff_has_permission('settings')
)
with check (
  public.jwt_app_role()='operator'
  and franchise_id=public.staff_franchise_id()
  and public.staff_has_permission('settings')
);
