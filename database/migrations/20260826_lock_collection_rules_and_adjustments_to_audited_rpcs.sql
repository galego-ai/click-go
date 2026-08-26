drop policy if exists super_admin_collection_rules_all on public.franchise_collection_rules;
drop policy if exists franchise_admin_collection_rules_select on public.franchise_collection_rules;

create policy matrix_collection_rules_select
on public.franchise_collection_rules
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_collection_rules_select
on public.franchise_collection_rules
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

drop policy if exists super_admin_invoice_adjustments_all on public.franchise_invoice_adjustments;
drop policy if exists franchise_admin_invoice_adjustments_select on public.franchise_invoice_adjustments;
drop policy if exists operator_invoice_adjustments_select on public.franchise_invoice_adjustments;

create policy matrix_invoice_adjustments_select
on public.franchise_invoice_adjustments
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_invoice_adjustments_select
on public.franchise_invoice_adjustments
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

create policy operator_invoice_adjustments_select
on public.franchise_invoice_adjustments
for select
to authenticated
using (
  public.current_active_management_role() = 'operator'
  and franchise_id = public.staff_franchise_id()
  and public.staff_has_permission('finance')
);

revoke insert, update, delete on table public.franchise_collection_rules from authenticated, anon;
revoke insert, update, delete on table public.franchise_invoice_adjustments from authenticated, anon;
grant select on table public.franchise_collection_rules to authenticated;
grant select on table public.franchise_invoice_adjustments to authenticated;
