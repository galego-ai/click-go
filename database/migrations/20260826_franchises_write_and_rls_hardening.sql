revoke insert, update, delete on table public.franchises from anon, authenticated;
grant select on table public.franchises to authenticated;

drop policy if exists super_admin_franchises_all on public.franchises;
drop policy if exists franchise_admin_own_franchise_select on public.franchises;
drop policy if exists operator_franchise_select on public.franchises;
drop policy if exists matrix_franchises_select on public.franchises;

create policy matrix_franchises_select
on public.franchises
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_own_franchise_select
on public.franchises
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and id = public.jwt_franchise_id()
);

create policy operator_franchise_select
on public.franchises
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and id = public.staff_franchise_id()
);
