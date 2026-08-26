drop policy if exists super_admin_notifications_all on public.admin_notifications;
drop policy if exists franchise_notifications_read on public.admin_notifications;
drop policy if exists super_admin_notifications_select on public.admin_notifications;
drop policy if exists super_admin_notifications_mark_read on public.admin_notifications;
drop policy if exists franchise_notifications_mark_read on public.admin_notifications;

create policy super_admin_notifications_select
on public.admin_notifications
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_notifications_read
on public.admin_notifications
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

create policy super_admin_notifications_mark_read
on public.admin_notifications
for update
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');

create policy franchise_notifications_mark_read
on public.admin_notifications
for update
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
)
with check (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

revoke all on table public.admin_notifications from anon;
revoke all on table public.admin_notifications from authenticated;
grant select on table public.admin_notifications to authenticated;
grant update (read_at) on table public.admin_notifications to authenticated;
