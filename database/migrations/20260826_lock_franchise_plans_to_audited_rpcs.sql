drop policy if exists super_admin_plans_all on public.franchise_plans;

create policy matrix_plans_select
on public.franchise_plans
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

revoke insert, update, delete on table public.franchise_plans from authenticated, anon;
grant select on table public.franchise_plans to authenticated;
