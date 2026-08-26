drop policy if exists super_admin_invoices_all on public.franchise_invoices;
drop policy if exists franchise_admin_own_invoices_select on public.franchise_invoices;
drop policy if exists operator_franchise_invoices_select on public.franchise_invoices;

create policy super_admin_invoices_select
on public.franchise_invoices
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_own_invoices_select
on public.franchise_invoices
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

create policy operator_franchise_invoices_select
on public.franchise_invoices
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('finance')
);