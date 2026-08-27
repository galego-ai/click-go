-- CLICK-GO: audit logs are append-only for trusted backend/RPC code.

revoke all on table public.audit_logs from anon, authenticated;
grant select on table public.audit_logs to authenticated;
grant all on table public.audit_logs to service_role;

drop policy if exists super_admin_audit_logs_select on public.audit_logs;
drop policy if exists franchise_admin_own_audit_logs_select on public.audit_logs;

create policy super_admin_audit_logs_select on public.audit_logs
for select to authenticated
using (public.current_active_management_role() = 'super_admin');

create policy franchise_admin_own_audit_logs_select on public.audit_logs
for select to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and coalesce(metadata->>'franchise_id','') = coalesce(public.jwt_franchise_id()::text,'')
);
