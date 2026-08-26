revoke insert, update, delete on table public.franchise_onboarding_steps from anon, authenticated;
grant select on table public.franchise_onboarding_steps to authenticated;

drop policy if exists franchise_admin_onboarding_scope on public.franchise_onboarding_steps;
drop policy if exists super_admin_onboarding_all on public.franchise_onboarding_steps;
drop policy if exists matrix_onboarding_select on public.franchise_onboarding_steps;
drop policy if exists franchise_admin_onboarding_select on public.franchise_onboarding_steps;
drop policy if exists operator_onboarding_select on public.franchise_onboarding_steps;

create policy matrix_onboarding_select
on public.franchise_onboarding_steps
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_onboarding_select
on public.franchise_onboarding_steps
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

create policy operator_onboarding_select
on public.franchise_onboarding_steps
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
);
