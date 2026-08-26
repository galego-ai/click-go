revoke insert, update, delete on table public.franchise_subscriptions from anon, authenticated;
grant select on table public.franchise_subscriptions to authenticated;

drop policy if exists super_admin_subscriptions_all on public.franchise_subscriptions;
drop policy if exists matrix_subscriptions_select on public.franchise_subscriptions;
drop policy if exists franchise_admin_own_subscriptions_select on public.franchise_subscriptions;
drop policy if exists operator_own_subscriptions_select on public.franchise_subscriptions;

create policy matrix_subscriptions_select
on public.franchise_subscriptions
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_own_subscriptions_select
on public.franchise_subscriptions
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

create policy operator_own_subscriptions_select
on public.franchise_subscriptions
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
);
