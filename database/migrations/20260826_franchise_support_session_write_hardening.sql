revoke insert, update, delete on table public.franchise_support_sessions from anon, authenticated;
grant select on table public.franchise_support_sessions to authenticated;

drop policy if exists super_admin_support_sessions_all on public.franchise_support_sessions;
drop policy if exists franchise_admin_support_sessions_select on public.franchise_support_sessions;
drop policy if exists matrix_support_sessions_select on public.franchise_support_sessions;

create policy matrix_support_sessions_select
on public.franchise_support_sessions
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_support_sessions_select
on public.franchise_support_sessions
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);
