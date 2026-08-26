-- Permissões da equipe: clientes apenas leem; alterações passam por franchise-staff-access.
drop policy if exists franchise_admin_staff_permissions_scope on public.franchise_staff_permissions;
drop policy if exists operator_manager_staff_permissions_all on public.franchise_staff_permissions;
drop policy if exists staff_permissions_self_select on public.franchise_staff_permissions;
drop policy if exists super_admin_staff_permissions_all on public.franchise_staff_permissions;
drop policy if exists super_admin_staff_permissions_select on public.franchise_staff_permissions;
drop policy if exists franchise_admin_staff_permissions_select on public.franchise_staff_permissions;
drop policy if exists operator_staff_permissions_select on public.franchise_staff_permissions;

create policy super_admin_staff_permissions_select
on public.franchise_staff_permissions
for select to authenticated
using (public.current_active_management_role()='super_admin');

create policy franchise_admin_staff_permissions_select
on public.franchise_staff_permissions
for select to authenticated
using (
  public.current_active_management_role()='franchise_admin'
  and franchise_id=public.jwt_franchise_id()
);

create policy operator_staff_permissions_select
on public.franchise_staff_permissions
for select to authenticated
using (
  public.current_active_management_role()='operator'
  and (
    profile_id=auth.uid()
    or (
      franchise_id=public.staff_franchise_id()
      and public.staff_has_permission('settings')
    )
  )
);

revoke all on table public.franchise_staff_permissions from anon;
revoke all on table public.franchise_staff_permissions from authenticated;
grant select on table public.franchise_staff_permissions to authenticated;

-- Escopo por cidade: clientes apenas consultam; Edge Functions sincronizam via service role.
drop policy if exists profile_city_access_self_read on public.profile_city_access;
drop policy if exists super_admin_profile_city_access_all on public.profile_city_access;
drop policy if exists super_admin_profile_city_access_select on public.profile_city_access;
drop policy if exists profile_city_access_self_select on public.profile_city_access;

create policy super_admin_profile_city_access_select
on public.profile_city_access
for select to authenticated
using (public.current_active_management_role()='super_admin');

create policy profile_city_access_self_select
on public.profile_city_access
for select to authenticated
using (profile_id=auth.uid());

revoke all on table public.profile_city_access from anon;
revoke all on table public.profile_city_access from authenticated;
grant select on table public.profile_city_access to authenticated;
