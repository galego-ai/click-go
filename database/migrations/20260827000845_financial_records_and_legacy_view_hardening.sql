-- CLICK-GO: financial records are read-only for browser/app roles.

alter view public.transacoes set (security_invoker = true);
revoke all on public.transacoes from anon, authenticated;
grant select on public.transacoes to authenticated;
grant all on public.transacoes to service_role;

revoke all on table public.pix_payments from anon, authenticated;
grant select on table public.pix_payments to authenticated;
grant all on table public.pix_payments to service_role;

revoke all on table public.passenger_charges from anon, authenticated;
grant select on table public.passenger_charges to authenticated;
grant all on table public.passenger_charges to service_role;

revoke all on table public.franchise_invoices from anon, authenticated;
grant select on table public.franchise_invoices to authenticated;
grant all on table public.franchise_invoices to service_role;

revoke all on table public.franchise_invoice_pix_charges from anon, authenticated;
grant select on table public.franchise_invoice_pix_charges to authenticated;
grant all on table public.franchise_invoice_pix_charges to service_role;

revoke all on table public.franchise_invoice_card_charges from anon, authenticated;
grant select on table public.franchise_invoice_card_charges to authenticated;
grant all on table public.franchise_invoice_card_charges to service_role;

drop policy if exists "pix admins read" on public.pix_payments;
create policy "pix admins read" on public.pix_payments
for select to authenticated
using (
  public.current_active_management_role() = 'super_admin'
  or (
    public.current_active_management_role() = 'franchise_admin'
    and franchise_id = public.jwt_franchise_id()
  )
);

drop policy if exists passenger_charges_scope_read on public.passenger_charges;
create policy passenger_charges_scope_read on public.passenger_charges
for select to authenticated
using (
  passenger_id = auth.uid()
  or public.current_active_management_role() = 'super_admin'
  or (
    public.current_active_management_role() = 'franchise_admin'
    and franchise_id = public.jwt_franchise_id()
  )
);

drop policy if exists franchise_admin_own_invoice_pix_select on public.franchise_invoice_pix_charges;
drop policy if exists operator_own_invoice_pix_select on public.franchise_invoice_pix_charges;
drop policy if exists super_admin_franchise_invoice_pix_select on public.franchise_invoice_pix_charges;
create policy franchise_admin_own_invoice_pix_select on public.franchise_invoice_pix_charges
for select to authenticated
using (public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());
create policy operator_own_invoice_pix_select on public.franchise_invoice_pix_charges
for select to authenticated
using (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));
create policy super_admin_franchise_invoice_pix_select on public.franchise_invoice_pix_charges
for select to authenticated
using (public.current_active_management_role()='super_admin');

drop policy if exists franchise_admin_own_invoice_card_select on public.franchise_invoice_card_charges;
drop policy if exists operator_own_invoice_card_select on public.franchise_invoice_card_charges;
drop policy if exists super_admin_invoice_card_select on public.franchise_invoice_card_charges;
create policy franchise_admin_own_invoice_card_select on public.franchise_invoice_card_charges
for select to authenticated
using (public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());
create policy operator_own_invoice_card_select on public.franchise_invoice_card_charges
for select to authenticated
using (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));
create policy super_admin_invoice_card_select on public.franchise_invoice_card_charges
for select to authenticated
using (public.current_active_management_role()='super_admin');

drop policy if exists financial_transactions_franchise_read on public.financial_transactions;
create policy financial_transactions_franchise_read on public.financial_transactions
for select to authenticated
using (
  public.current_active_management_role()='franchise_admin'
  and franchise_id=public.jwt_franchise_id()
  and public.can_access_city(city_id)
);

drop policy if exists operator_city_financial_select on public.financial_transactions;
create policy operator_city_financial_select on public.financial_transactions
for select to authenticated
using (
  public.current_active_management_role()='operator'
  and franchise_id=public.staff_franchise_id()
  and public.can_access_city(city_id)
  and public.staff_has_permission('finance')
);
