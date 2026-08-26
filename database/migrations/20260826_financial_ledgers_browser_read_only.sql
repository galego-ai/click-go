-- CLICK-GO — livros-caixa e saldos são somente leitura para clientes.
-- Mutações permanecem nos fluxos SECURITY DEFINER e service_role.

-- financial_transactions
drop policy if exists financial_transactions_super_admin_all on public.financial_transactions;
drop policy if exists financial_transactions_super_admin_select on public.financial_transactions;
create policy financial_transactions_super_admin_select
on public.financial_transactions for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.financial_transactions from anon;
revoke insert,update,delete,truncate,references,trigger on public.financial_transactions from authenticated;
grant select on public.financial_transactions to authenticated;
grant all on public.financial_transactions to service_role;

-- franchise_wallets
drop policy if exists franchise_wallets_super_admin_all on public.franchise_wallets;
drop policy if exists franchise_wallets_super_admin_select on public.franchise_wallets;
create policy franchise_wallets_super_admin_select
on public.franchise_wallets for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.franchise_wallets from anon;
revoke insert,update,delete,truncate,references,trigger on public.franchise_wallets from authenticated;
grant select on public.franchise_wallets to authenticated;
grant all on public.franchise_wallets to service_role;

-- wallets
drop policy if exists super_admin_wallets_all on public.wallets;
drop policy if exists super_admin_wallets_select on public.wallets;
create policy super_admin_wallets_select
on public.wallets for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.wallets from anon;
revoke insert,update,delete,truncate,references,trigger on public.wallets from authenticated;
grant select on public.wallets to authenticated;
grant all on public.wallets to service_role;

-- wallet_transactions
drop policy if exists super_admin_wallet_transactions_all on public.wallet_transactions;
drop policy if exists super_admin_wallet_transactions_select on public.wallet_transactions;
create policy super_admin_wallet_transactions_select
on public.wallet_transactions for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.wallet_transactions from anon;
revoke insert,update,delete,truncate,references,trigger on public.wallet_transactions from authenticated;
grant select on public.wallet_transactions to authenticated;
grant all on public.wallet_transactions to service_role;

-- driver_operational_wallets
drop policy if exists driver_operational_wallet_matrix_all on public.driver_operational_wallets;
drop policy if exists driver_operational_wallet_matrix_select on public.driver_operational_wallets;
create policy driver_operational_wallet_matrix_select
on public.driver_operational_wallets for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.driver_operational_wallets from anon;
revoke insert,update,delete,truncate,references,trigger on public.driver_operational_wallets from authenticated;
grant select on public.driver_operational_wallets to authenticated;
grant all on public.driver_operational_wallets to service_role;

-- driver_operational_transactions
drop policy if exists driver_operational_tx_matrix_all on public.driver_operational_transactions;
drop policy if exists driver_operational_tx_matrix_select on public.driver_operational_transactions;
create policy driver_operational_tx_matrix_select
on public.driver_operational_transactions for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.driver_operational_transactions from anon;
revoke insert,update,delete,truncate,references,trigger on public.driver_operational_transactions from authenticated;
grant select on public.driver_operational_transactions to authenticated;
grant all on public.driver_operational_transactions to service_role;
