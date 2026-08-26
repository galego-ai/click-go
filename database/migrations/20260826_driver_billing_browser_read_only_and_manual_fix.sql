-- CLICK-GO — cobrança individual/mensal de motoristas somente via RPC auditado.

drop policy if exists driver_billing_franchise_all on public.driver_billing_settings;
drop policy if exists driver_billing_matrix_all on public.driver_billing_settings;
drop policy if exists driver_billing_franchise_select on public.driver_billing_settings;
drop policy if exists driver_billing_matrix_select on public.driver_billing_settings;
create policy driver_billing_franchise_select
on public.driver_billing_settings for select to authenticated
using (
  public.current_active_management_role()='franchise_admin'
  and franchise_id=public.current_profile_franchise_id()
  and exists(select 1 from public.drivers d where d.id=driver_billing_settings.driver_id and public.can_access_city(d.city_id))
);
create policy driver_billing_matrix_select
on public.driver_billing_settings for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.driver_billing_settings from anon;
revoke insert,update,delete,truncate,references,trigger on public.driver_billing_settings from authenticated;
grant select on public.driver_billing_settings to authenticated;
grant all on public.driver_billing_settings to service_role;

drop policy if exists driver_monthly_payments_franchise_all on public.driver_monthly_payments;
drop policy if exists driver_monthly_payments_matrix_all on public.driver_monthly_payments;
drop policy if exists driver_monthly_payments_franchise_select on public.driver_monthly_payments;
drop policy if exists driver_monthly_payments_matrix_select on public.driver_monthly_payments;
create policy driver_monthly_payments_franchise_select
on public.driver_monthly_payments for select to authenticated
using (
  public.current_active_management_role()='franchise_admin'
  and franchise_id=public.current_profile_franchise_id()
  and exists(select 1 from public.drivers d where d.id=driver_monthly_payments.driver_id and public.can_access_city(d.city_id))
);
create policy driver_monthly_payments_matrix_select
on public.driver_monthly_payments for select to authenticated
using (public.current_active_management_role()='super_admin');
revoke all on public.driver_monthly_payments from anon;
revoke insert,update,delete,truncate,references,trigger on public.driver_monthly_payments from authenticated;
grant select on public.driver_monthly_payments to authenticated;
grant all on public.driver_monthly_payments to service_role;

-- Manual monthly registration uses the accepted accounting category OUTRO;
-- the monthly history itself keeps method='manual'.
create or replace function public.mark_driver_monthly_paid(p_driver_id uuid,p_paid_until date,p_reason text default 'Mensalidade registrada pelo franqueado')
returns void
language plpgsql security definer set search_path to public,pg_temp
as $$
declare
  v_role text:=public.jwt_app_role(); v_franchise uuid:=public.jwt_franchise_id(); v_driver public.drivers%rowtype;
  v_cfg public.driver_billing_settings%rowtype; v_ref date:=date_trunc('month',current_date)::date;
begin
  if auth.uid() is null or v_role not in ('franchise_admin','super_admin') then raise exception 'Sem permissão'; end if;
  select * into v_driver from public.drivers where id=p_driver_id; if not found then raise exception 'Motorista não encontrado'; end if;
  if v_role='franchise_admin' then
    if v_driver.franchise_id is distinct from v_franchise then raise exception 'Motorista fora da sua franquia'; end if;
    if not public.can_access_city(v_driver.city_id) then raise exception 'Motorista fora da sua cidade/região'; end if;
  end if;
  select * into v_cfg from public.driver_billing_settings where driver_id=p_driver_id;
  if not found or v_cfg.billing_mode<>'monthly' then raise exception 'Motorista não está no plano mensal'; end if;
  if p_paid_until<current_date then raise exception 'A validade precisa ser hoje ou uma data futura'; end if;
  update public.driver_billing_settings set monthly_paid_until=p_paid_until,updated_by=auth.uid(),updated_at=now() where driver_id=p_driver_id;
  insert into public.driver_monthly_payments(driver_id,franchise_id,reference_month,amount,method,status,paid_at,paid_until,created_by)
  values(p_driver_id,v_driver.franchise_id,v_ref,v_cfg.monthly_fee,'manual','paid',now(),p_paid_until,auth.uid())
  on conflict(driver_id,reference_month) do update set amount=excluded.amount,method='manual',status='paid',paid_at=now(),paid_until=excluded.paid_until,created_by=excluded.created_by;
  insert into public.financial_transactions(payer_id,driver_id,franchise_id,city_id,tipo_pagamento,valor_total,tipo_operacao,status_pagamento,data_pagamento,metadata)
  select p_driver_id,p_driver_id,v_driver.franchise_id,v_driver.city_id,'OUTRO',v_cfg.monthly_fee,'MENSALIDADE_MOTORISTA','PAGO',now(),jsonb_build_object('reference_month',v_ref,'paid_until',p_paid_until,'reason',p_reason,'payment_method','manual')
  where not exists(select 1 from public.financial_transactions ft where ft.driver_id=p_driver_id and ft.tipo_operacao='MENSALIDADE_MOTORISTA' and ft.status_pagamento='PAGO' and ft.metadata->>'reference_month'=v_ref::text);
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'driver_monthly_payment_registered','driver',p_driver_id::text,jsonb_build_object('paid_until',p_paid_until,'reason',p_reason,'reference_month',v_ref,'city_id',v_driver.city_id,'payment_method','manual'));
end;
$$;
revoke all on function public.mark_driver_monthly_paid(uuid,date,text) from public,anon;
grant execute on function public.mark_driver_monthly_paid(uuid,date,text) to authenticated,service_role;
