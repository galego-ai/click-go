-- CLICK-GO / Phase 3 additional privileged RPC hardening.

CREATE OR REPLACE FUNCTION public.adjust_driver_operational_balance(p_driver_id uuid,p_amount numeric,p_reason text)
RETURNS numeric
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_role text:=public.jwt_app_role();
  v_franchise uuid:=public.jwt_franchise_id();
  v_driver public.drivers%rowtype;
  v_global public.platform_operational_wallet_settings%rowtype;
  v_balance numeric;
  v_source text;
BEGIN
  IF auth.uid() IS NULL OR v_role NOT IN ('super_admin','franchise_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  IF p_amount=0 OR abs(p_amount)>100000 THEN RAISE EXCEPTION 'Valor inválido'; END IF;
  IF nullif(trim(coalesce(p_reason,'')),'') IS NULL THEN RAISE EXCEPTION 'Informe o motivo'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=p_driver_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  SELECT * INTO v_global FROM public.platform_operational_wallet_settings WHERE scope='global';

  IF v_role='franchise_admin' THEN
    IF v_driver.franchise_id IS DISTINCT FROM v_franchise THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
    IF NOT public.can_access_city(v_driver.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
    IF NOT v_global.franchise_manual_credit_enabled THEN RAISE EXCEPTION 'Crédito manual bloqueado pela matriz'; END IF;
    IF p_amount>0 AND v_global.franchise_manual_credit_limit IS NOT NULL AND p_amount>v_global.franchise_manual_credit_limit THEN RAISE EXCEPTION 'Valor acima do limite definido pela matriz'; END IF;
    v_source:='franchise';
  ELSE
    v_source:='matrix';
  END IF;

  INSERT INTO public.driver_operational_wallets(driver_id) VALUES(p_driver_id) ON CONFLICT(driver_id) DO NOTHING;
  SELECT balance INTO v_balance FROM public.driver_operational_wallets WHERE driver_id=p_driver_id FOR UPDATE;
  IF p_amount<0 AND v_balance+p_amount<0 THEN RAISE EXCEPTION 'Saldo insuficiente para retirada manual'; END IF;
  UPDATE public.driver_operational_wallets SET balance=balance+p_amount,updated_at=now() WHERE driver_id=p_driver_id RETURNING balance INTO v_balance;
  INSERT INTO public.driver_operational_transactions(driver_id,franchise_id,city_id,transaction_type,source,amount,status,reason,created_by,settled_at)
  VALUES(p_driver_id,v_driver.franchise_id,v_driver.city_id,CASE WHEN p_amount>0 THEN 'credit' ELSE 'debit' END,v_source,abs(p_amount),'settled',trim(p_reason),auth.uid(),now());
  RETURN v_balance;
END;
$$;

CREATE OR REPLACE FUNCTION public.approve_driver_registration(p_driver_id uuid,p_approve boolean,p_reason text DEFAULT NULL,p_commission_percent numeric DEFAULT NULL)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE d public.drivers%rowtype; v_role text:=public.jwt_app_role();
BEGIN
  IF auth.uid() IS NULL OR v_role NOT IN ('super_admin','franchise_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  SELECT * INTO d FROM public.drivers WHERE id=p_driver_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  IF v_role='franchise_admin' THEN
    IF d.franchise_id IS DISTINCT FROM public.jwt_franchise_id() THEN RAISE EXCEPTION 'Sem permissão'; END IF;
    IF NOT public.can_access_city(d.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  END IF;
  UPDATE public.drivers
  SET status=CASE WHEN p_approve THEN 'approved'::public.driver_status ELSE 'rejected'::public.driver_status END,
      approved_at=CASE WHEN p_approve THEN now() ELSE null END,
      approved_by=auth.uid(),
      rejection_reason=CASE WHEN p_approve THEN null ELSE p_reason END,
      commission_percent=coalesce(p_commission_percent,commission_percent),
      online=false
  WHERE id=p_driver_id;
  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(auth.uid(),CASE WHEN p_approve THEN 'driver_approved' ELSE 'driver_rejected' END,'driver',p_driver_id::text,
         jsonb_build_object('reason',p_reason,'commission_percent',p_commission_percent,'city_id',d.city_id));
END;
$$;

CREATE OR REPLACE FUNCTION public.set_driver_billing(p_driver_id uuid,p_billing_mode text,p_per_ride_fee numeric,p_monthly_fee numeric,p_monthly_due_day integer)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE v_role text:=public.jwt_app_role();v_franchise uuid:=public.jwt_franchise_id();v_driver public.drivers%rowtype;
BEGIN
  IF auth.uid() IS NULL OR v_role NOT IN ('franchise_admin','super_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  IF p_billing_mode NOT IN ('wallet_per_ride','monthly') THEN RAISE EXCEPTION 'Modo de cobrança inválido'; END IF;
  IF coalesce(p_per_ride_fee,0)<0 OR coalesce(p_monthly_fee,0)<0 THEN RAISE EXCEPTION 'Valores inválidos'; END IF;
  IF p_monthly_due_day NOT BETWEEN 1 AND 28 THEN RAISE EXCEPTION 'Dia de vencimento deve ficar entre 1 e 28'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=p_driver_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  IF v_role='franchise_admin' THEN
    IF v_driver.franchise_id IS DISTINCT FROM v_franchise THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
    IF NOT public.can_access_city(v_driver.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  END IF;
  INSERT INTO public.driver_billing_settings(driver_id,franchise_id,billing_mode,per_ride_fee,monthly_fee,monthly_due_day,active,updated_by,updated_at)
  VALUES(v_driver.id,v_driver.franchise_id,p_billing_mode,greatest(coalesce(p_per_ride_fee,0),0),greatest(coalesce(p_monthly_fee,0),0),p_monthly_due_day,true,auth.uid(),now())
  ON CONFLICT(driver_id) DO UPDATE SET franchise_id=excluded.franchise_id,billing_mode=excluded.billing_mode,per_ride_fee=excluded.per_ride_fee,monthly_fee=excluded.monthly_fee,monthly_due_day=excluded.monthly_due_day,updated_by=excluded.updated_by,updated_at=now();
  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(auth.uid(),'driver_billing_updated','driver',p_driver_id::text,
         jsonb_build_object('billing_mode',p_billing_mode,'per_ride_fee',p_per_ride_fee,'monthly_fee',p_monthly_fee,'monthly_due_day',p_monthly_due_day,'city_id',v_driver.city_id));
END;
$$;

CREATE OR REPLACE FUNCTION public.set_driver_billing(p_driver_id uuid,p_billing_mode text,p_per_ride_fee numeric,p_monthly_fee numeric,p_monthly_due_day integer,p_ride_fee_mode text,p_ride_fee_percentage numeric)
RETURNS void
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE v_role text:=public.jwt_app_role();v_franchise uuid:=public.jwt_franchise_id();v_driver public.drivers%rowtype;
BEGIN
  IF auth.uid() IS NULL OR v_role NOT IN ('franchise_admin','super_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  IF p_billing_mode NOT IN ('wallet_per_ride','monthly') THEN RAISE EXCEPTION 'Modo de cobrança inválido'; END IF;
  IF coalesce(p_ride_fee_mode,'fixed') NOT IN ('fixed','percentage') THEN RAISE EXCEPTION 'Tipo da taxa inválido'; END IF;
  IF coalesce(p_per_ride_fee,0)<0 OR coalesce(p_monthly_fee,0)<0 THEN RAISE EXCEPTION 'Valores inválidos'; END IF;
  IF coalesce(p_ride_fee_percentage,0)<0 OR coalesce(p_ride_fee_percentage,0)>100 THEN RAISE EXCEPTION 'Percentual deve ficar entre 0 e 100'; END IF;
  IF p_monthly_due_day NOT BETWEEN 1 AND 28 THEN RAISE EXCEPTION 'Dia de vencimento deve ficar entre 1 e 28'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=p_driver_id;
  IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  IF v_role='franchise_admin' THEN
    IF v_driver.franchise_id IS DISTINCT FROM v_franchise THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
    IF NOT public.can_access_city(v_driver.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  END IF;
  INSERT INTO public.driver_billing_settings(driver_id,franchise_id,billing_mode,per_ride_fee,ride_fee_mode,ride_fee_percentage,monthly_fee,monthly_due_day,active,updated_by,updated_at)
  VALUES(v_driver.id,v_driver.franchise_id,p_billing_mode,greatest(coalesce(p_per_ride_fee,0),0),coalesce(p_ride_fee_mode,'fixed'),greatest(coalesce(p_ride_fee_percentage,0),0),greatest(coalesce(p_monthly_fee,0),0),p_monthly_due_day,true,auth.uid(),now())
  ON CONFLICT(driver_id) DO UPDATE SET franchise_id=excluded.franchise_id,billing_mode=excluded.billing_mode,per_ride_fee=excluded.per_ride_fee,ride_fee_mode=excluded.ride_fee_mode,ride_fee_percentage=excluded.ride_fee_percentage,monthly_fee=excluded.monthly_fee,monthly_due_day=excluded.monthly_due_day,updated_by=excluded.updated_by,updated_at=now();
  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(auth.uid(),'driver_billing_updated','driver',p_driver_id::text,
         jsonb_build_object('billing_mode',p_billing_mode,'ride_fee_mode',coalesce(p_ride_fee_mode,'fixed'),'per_ride_fee',p_per_ride_fee,'ride_fee_percentage',p_ride_fee_percentage,'monthly_fee',p_monthly_fee,'monthly_due_day',p_monthly_due_day,'city_id',v_driver.city_id));
END;
$$;

CREATE OR REPLACE FUNCTION public.set_taximeter_financial_settings(p_fee_mode text,p_fee_value numeric,p_scope text DEFAULT 'franchise',p_franchise_id uuid DEFAULT NULL,p_allow_franchise_override boolean DEFAULT true,p_locked_by_matrix boolean DEFAULT false)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_uid uuid:=auth.uid();v_role text:=public.jwt_app_role();v_own uuid:=public.jwt_franchise_id();v_target uuid;
  g public.taximeter_financial_rules%rowtype;f public.taximeter_financial_rules%rowtype;v_value numeric;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  IF p_fee_mode NOT IN ('none','fixed','percentage') THEN RAISE EXCEPTION 'Modo de taxa inválido'; END IF;
  v_value:=CASE WHEN p_fee_mode='none' THEN 0 ELSE round(coalesce(p_fee_value,0)::numeric,2) END;
  IF v_value<0 THEN RAISE EXCEPTION 'Valor da taxa inválido'; END IF;
  IF p_fee_mode='percentage' AND v_value>100 THEN RAISE EXCEPTION 'Percentual deve ficar entre 0 e 100'; END IF;
  IF p_fee_mode='fixed' AND v_value>100000 THEN RAISE EXCEPTION 'Taxa fixa acima do limite permitido'; END IF;

  IF v_role='super_admin' THEN
    IF p_scope='global' THEN
      UPDATE public.taximeter_financial_rules SET fee_mode=p_fee_mode,fee_value=v_value,allow_franchise_override=coalesce(p_allow_franchise_override,true),locked_by_matrix=false,active=true,updated_by=v_uid,updated_at=now() WHERE scope='global';
      IF NOT FOUND THEN INSERT INTO public.taximeter_financial_rules(scope,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active,updated_by) VALUES('global',p_fee_mode,v_value,coalesce(p_allow_franchise_override,true),false,true,v_uid); END IF;
      RETURN public.get_taximeter_financial_settings(null);
    ELSIF p_scope='franchise' THEN
      v_target:=p_franchise_id; IF v_target IS NULL THEN RAISE EXCEPTION 'Informe a franquia'; END IF;
      UPDATE public.taximeter_financial_rules SET fee_mode=p_fee_mode,fee_value=v_value,locked_by_matrix=coalesce(p_locked_by_matrix,false),active=true,updated_by=v_uid,updated_at=now() WHERE scope='franchise' AND franchise_id=v_target;
      IF NOT FOUND THEN INSERT INTO public.taximeter_financial_rules(scope,franchise_id,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active,updated_by) VALUES('franchise',v_target,p_fee_mode,v_value,true,coalesce(p_locked_by_matrix,false),true,v_uid); END IF;
      RETURN public.get_taximeter_financial_settings(v_target);
    ELSE RAISE EXCEPTION 'Escopo inválido'; END IF;
  ELSIF v_role='franchise_admin' THEN
    v_target:=v_own; IF v_target IS NULL THEN RAISE EXCEPTION 'Franquia não identificada'; END IF;
    IF NOT public.can_manage_franchise_scope(v_target) THEN RAISE EXCEPTION 'Esta configuração afeta toda a franquia e não pode ser alterada por um administrador limitado a parte das cidades'; END IF;
    SELECT * INTO g FROM public.taximeter_financial_rules WHERE scope='global' LIMIT 1;
    SELECT * INTO f FROM public.taximeter_financial_rules WHERE scope='franchise' AND franchise_id=v_target LIMIT 1;
    IF NOT coalesce(g.allow_franchise_override,true) THEN RAISE EXCEPTION 'A matriz bloqueou alterações da taxa do taxímetro'; END IF;
    IF coalesce(f.locked_by_matrix,false) THEN RAISE EXCEPTION 'Configuração travada pela matriz'; END IF;
    UPDATE public.taximeter_financial_rules SET fee_mode=p_fee_mode,fee_value=v_value,locked_by_matrix=false,active=true,updated_by=v_uid,updated_at=now() WHERE scope='franchise' AND franchise_id=v_target;
    IF NOT FOUND THEN INSERT INTO public.taximeter_financial_rules(scope,franchise_id,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active,updated_by) VALUES('franchise',v_target,p_fee_mode,v_value,true,false,true,v_uid); END IF;
    RETURN public.get_taximeter_financial_settings(v_target);
  ELSE
    RAISE EXCEPTION 'Sem permissão';
  END IF;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.adjust_driver_operational_balance(uuid,numeric,text) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.approve_driver_registration(uuid,boolean,text,numeric) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.set_driver_billing(uuid,text,numeric,numeric,integer) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.set_driver_billing(uuid,text,numeric,numeric,integer,text,numeric) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.set_taximeter_financial_settings(text,numeric,text,uuid,boolean,boolean) FROM public,anon;

GRANT EXECUTE ON FUNCTION public.adjust_driver_operational_balance(uuid,numeric,text) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.approve_driver_registration(uuid,boolean,text,numeric) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.set_driver_billing(uuid,text,numeric,numeric,integer) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.set_driver_billing(uuid,text,numeric,numeric,integer,text,numeric) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.set_taximeter_financial_settings(text,numeric,text,uuid,boolean,boolean) TO authenticated,service_role;
