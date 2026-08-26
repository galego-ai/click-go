-- Evita que um metadata antigo/malformado cause erro de cast UUID ao consultar os logs.
drop policy if exists franchise_admin_own_audit_logs_select on public.audit_logs;
create policy franchise_admin_own_audit_logs_select on public.audit_logs
for select to authenticated
using (
  public.jwt_app_role()='franchise_admin'
  and coalesce(metadata->>'franchise_id','')=coalesce(public.jwt_franchise_id()::text,'')
);
