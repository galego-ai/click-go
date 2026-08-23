-- CLICK-GO / Phase 3
-- Final hardening of regional SECURITY DEFINER RPCs and audited city cash-limit API.

CREATE OR REPLACE FUNCTION public.can_manage_franchise_scope(p_franchise_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_uid uuid := auth.uid();
  v_role text := public.jwt_app_role();
  v_profile_role text;
  v_profile_franchise uuid;
  v_active boolean;
BEGIN
  IF v_uid IS NULL OR p_franchise_id IS NULL THEN RETURN false; END IF;

  SELECT p.role::text,p.franchise_id,p.active
    INTO v_profile_role,v_profile_franchise,v_active
  FROM public.profiles p WHERE p.id=v_uid;

  IF NOT coalesce(v_active,false) OR v_profile_role IS DISTINCT FROM v_role THEN RETURN false; END IF;
  IF v_role='super_admin' THEN RETURN true; END IF;
  IF v_role<>'franchise_admin' OR v_profile_franchise IS DISTINCT FROM p_franchise_id THEN RETURN false; END IF;

  RETURN NOT EXISTS (
    SELECT 1 FROM public.franchise_cities fc
    WHERE fc.franchise_id=p_franchise_id
      AND NOT EXISTS (
        SELECT 1 FROM public.profile_city_access a
        WHERE a.profile_id=v_uid AND a.city_id=fc.city_id
      )
  );
END;
$$;
REVOKE EXECUTE ON FUNCTION public.can_manage_franchise_scope(uuid) FROM public,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.can_manage_franchise_scope(uuid) TO service_role;

-- Consolidated read access. Regional writes are RPC-only and audited.
DROP POLICY IF EXISTS city_operational_wallet_regional_insert ON public.city_operational_wallet_settings;
DROP POLICY IF EXISTS city_operational_wallet_regional_update ON public.city_operational_wallet_settings;
DROP POLICY IF EXISTS city_operational_wallet_regional_select ON public.city_operational_wallet_settings;
DROP POLICY IF EXISTS city_operational_wallet_matrix_all ON public.city_operational_wallet_settings;
DROP POLICY IF EXISTS city_wallet_settings_select ON public.city_operational_wallet_settings;
CREATE POLICY city_wallet_settings_select
ON public.city_operational_wallet_settings
FOR SELECT TO authenticated
USING (
  public.jwt_app_role()='super_admin'
  OR (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id))
  OR (public.jwt_app_role()='operator' AND public.can_access_city(city_id))
);
DROP POLICY IF EXISTS city_wallet_settings_super_admin_all ON public.city_operational_wallet_settings;
CREATE POLICY city_wallet_settings_super_admin_all
ON public.city_operational_wallet_settings
FOR ALL TO authenticated
USING (public.jwt_app_role()='super_admin')
WITH CHECK (public.jwt_app_role()='super_admin');

CREATE OR REPLACE FUNCTION public.set_city_cash_negative_limit(
  p_franchise_id uuid,
  p_city_id uuid,
  p_cash_negative_limit numeric
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_uid uuid:=auth.uid();
  v_role text:=public.jwt_app_role();
  v_own uuid:=public.jwt_franchise_id();
  v_limit numeric(10,2);
  v_existing public.city_operational_wallet_settings%rowtype;
BEGIN
  IF v_uid IS NULL OR v_role NOT IN ('super_admin','franchise_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  v_limit:=round(coalesce(p_cash_negative_limit,0)::numeric,2);
  IF v_limit>0 OR v_limit<-1000 THEN RAISE EXCEPTION 'O limite para dinheiro deve ficar entre R$ 0,00 e -R$ 1.000,00'; END IF;

  IF NOT EXISTS(SELECT 1 FROM public.franchise_cities fc WHERE fc.franchise_id=p_franchise_id AND fc.city_id=p_city_id) THEN
    RAISE EXCEPTION 'Cidade não pertence à franquia';
  END IF;

  IF v_role='franchise_admin' THEN
    IF p_franchise_id IS DISTINCT FROM v_own THEN RAISE EXCEPTION 'Franquia fora do seu escopo'; END IF;
    IF NOT public.can_access_city(p_city_id) THEN RAISE EXCEPTION 'Cidade fora da sua região'; END IF;
  END IF;

  SELECT * INTO v_existing
  FROM public.city_operational_wallet_settings
  WHERE franchise_id=p_franchise_id AND city_id=p_city_id
  FOR UPDATE;

  IF FOUND AND v_role='franchise_admin' AND coalesce(v_existing.locked_by_matrix,false) THEN
    RAISE EXCEPTION 'A Matriz bloqueou a configuração desta cidade';
  END IF;

  INSERT INTO public.city_operational_wallet_settings(franchise_id,city_id,cash_negative_limit,locked_by_matrix,updated_by,updated_at)
  VALUES(p_franchise_id,p_city_id,v_limit,coalesce(v_existing.locked_by_matrix,false),v_uid,now())
  ON CONFLICT(franchise_id,city_id) DO UPDATE
    SET cash_negative_limit=excluded.cash_negative_limit,updated_by=excluded.updated_by,updated_at=now();

  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(v_uid,'city_cash_negative_limit_updated','city',p_city_id::text,
         jsonb_build_object('franchise_id',p_franchise_id,'cash_negative_limit',v_limit));

  RETURN jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'city_id',p_city_id,'cash_negative_limit',v_limit);
END;
$$;
REVOKE EXECUTE ON FUNCTION public.set_city_cash_negative_limit(uuid,uuid,numeric) FROM public,anon;
GRANT EXECUTE ON FUNCTION public.set_city_cash_negative_limit(uuid,uuid,numeric) TO authenticated,service_role;

CREATE OR REPLACE FUNCTION public.get_my_driver_wallet_summary_v2()
RETURNS TABLE(
  operational_balance numeric,
  earnings_balance numeric,
  minimum_balance numeric,
  low_balance_threshold numeric,
  ride_fee numeric,
  operational_enabled boolean,
  billing_mode text,
  monthly_fee numeric,
  monthly_due_day integer,
  monthly_paid_until date,
  cash_negative_limit numeric,
  cash_allowed boolean
)
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE v_uid uuid:=auth.uid(); v_rules record;
BEGIN
  IF v_uid IS NULL OR NOT EXISTS(SELECT 1 FROM public.profiles WHERE id=v_uid AND role='driver' AND active=true) THEN
    RAISE EXCEPTION 'Acesso exclusivo do motorista';
  END IF;
  INSERT INTO public.driver_operational_wallets(driver_id) VALUES(v_uid) ON CONFLICT(driver_id) DO NOTHING;
  SELECT * INTO v_rules FROM public.get_effective_driver_billing(v_uid);
  RETURN QUERY
  SELECT ow.balance,coalesce(w.balance,0),coalesce(v_rules.minimum_balance,0),coalesce(v_rules.low_balance_threshold,5),
         coalesce(v_rules.per_ride_fee,0),coalesce(v_rules.operational_enabled,false),coalesce(v_rules.billing_mode,'wallet_per_ride'),
         coalesce(v_rules.monthly_fee,0),coalesce(v_rules.monthly_due_day,10),v_rules.monthly_paid_until,
         coalesce(cs.cash_negative_limit,g.cash_negative_limit,0.00)::numeric,
         public.driver_can_accept_payment_method(v_uid,'cash')
  FROM public.driver_operational_wallets ow
  JOIN public.drivers d ON d.id=ow.driver_id
  LEFT JOIN public.wallets w ON w.owner_id=v_uid
  LEFT JOIN public.platform_operational_wallet_settings g ON g.scope='global'
  LEFT JOIN public.city_operational_wallet_settings cs ON cs.franchise_id=d.franchise_id AND cs.city_id=d.city_id
  WHERE ow.driver_id=v_uid;
END;
$$;
REVOKE EXECUTE ON FUNCTION public.get_my_driver_wallet_summary_v2() FROM public,anon;
GRANT EXECUTE ON FUNCTION public.get_my_driver_wallet_summary_v2() TO authenticated,service_role;

CREATE OR REPLACE FUNCTION public.franchise_review_driver(p_driver_id uuid,p_approve boolean,p_reason text DEFAULT NULL)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_actor uuid:=auth.uid(); v_role text; v_franchise uuid; v_driver_franchise uuid; v_city uuid;
  v_avatar text; v_full_name text; v_phone text; v_doc_count integer; v_unapproved_count integer;
  v_missing_docs text[]; v_vehicle_count integer;
BEGIN
  IF v_actor IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  SELECT role::text,franchise_id INTO v_role,v_franchise FROM public.profiles WHERE id=v_actor AND active=true;
  IF v_role<>'franchise_admin' OR public.jwt_app_role()<>'franchise_admin' OR v_franchise IS NULL OR v_franchise IS DISTINCT FROM public.jwt_franchise_id() THEN
    RAISE EXCEPTION 'Acesso restrito ao franqueado';
  END IF;
  IF NOT EXISTS(SELECT 1 FROM public.franchises f WHERE f.id=v_franchise AND f.active=true AND f.deleted_at IS NULL AND f.blocked_at IS NULL) THEN
    RAISE EXCEPTION 'Sua franquia está inativa, bloqueada ou excluída';
  END IF;

  SELECT d.franchise_id,d.city_id,p.avatar_url,p.full_name,p.phone
    INTO v_driver_franchise,v_city,v_avatar,v_full_name,v_phone
  FROM public.drivers d JOIN public.profiles p ON p.id=d.id WHERE d.id=p_driver_id;
  IF v_driver_franchise IS NULL OR v_driver_franchise<>v_franchise THEN RAISE EXCEPTION 'Motorista não pertence à sua franquia'; END IF;
  IF v_city IS NULL OR NOT public.can_access_city(v_city) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;

  IF p_approve THEN
    IF NOT EXISTS(SELECT 1 FROM public.franchise_cities fc WHERE fc.franchise_id=v_franchise AND fc.city_id=v_city) THEN RAISE EXCEPTION 'Motorista não está vinculado a uma cidade válida desta franquia'; END IF;
    IF coalesce(trim(v_full_name),'')='' OR coalesce(trim(v_phone),'')='' THEN RAISE EXCEPTION 'Nome e telefone do motorista precisam estar completos'; END IF;
    IF coalesce(trim(v_avatar),'')='' THEN RAISE EXCEPTION 'A foto real de perfil é obrigatória antes da aprovação'; END IF;
    SELECT count(*),count(*) FILTER(WHERE status::text<>'approved') INTO v_doc_count,v_unapproved_count FROM public.driver_documents WHERE driver_id=p_driver_id;
    IF v_doc_count=0 THEN RAISE EXCEPTION 'O motorista ainda não enviou documentos'; END IF;
    IF v_unapproved_count>0 THEN RAISE EXCEPTION 'Todos os documentos enviados precisam estar aprovados'; END IF;
    SELECT array_agg(req.doc_type ORDER BY req.doc_type) INTO v_missing_docs
    FROM (VALUES('profile_photo'),('cnh_frente'),('cnh_verso'),('selfie_cnh'),('crlv'),('comprovante_residencia')) req(doc_type)
    WHERE NOT EXISTS(SELECT 1 FROM public.driver_documents dd WHERE dd.driver_id=p_driver_id AND dd.document_type=req.doc_type AND dd.status::text='approved');
    IF coalesce(array_length(v_missing_docs,1),0)>0 THEN RAISE EXCEPTION 'Faltam documentos obrigatórios aprovados: %',array_to_string(v_missing_docs,', '); END IF;
    SELECT count(*) INTO v_vehicle_count FROM public.vehicles v WHERE v.driver_id=p_driver_id AND v.active=true AND coalesce(trim(v.make),'')<>'' AND coalesce(trim(v.model),'')<>'' AND coalesce(trim(v.plate),'')<>'';
    IF v_vehicle_count=0 THEN RAISE EXCEPTION 'Cadastre e confira um veículo ativo com marca, modelo e placa'; END IF;
    UPDATE public.drivers SET status='approved',approved_at=now(),approved_by=v_actor,rejection_reason=null,online=false WHERE id=p_driver_id;
  ELSE
    UPDATE public.drivers SET status='rejected',approved_at=null,approved_by=v_actor,rejection_reason=coalesce(nullif(trim(p_reason),''),'Cadastro reprovado pelo franqueado'),online=false WHERE id=p_driver_id;
  END IF;

  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(v_actor,CASE WHEN p_approve THEN 'approve_driver_full_review' ELSE 'reject_driver' END,'drivers',p_driver_id,
         jsonb_build_object('franchise_id',v_franchise,'city_id',v_city,'approved',p_approve,'full_review',p_approve));
  RETURN jsonb_build_object('ok',true,'driver_id',p_driver_id,'approved',p_approve);
END;
$$;

CREATE OR REPLACE FUNCTION public.franchise_set_driver_category(p_driver_id uuid,p_category_id uuid,p_enabled boolean)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid(); v_fid uuid; v_city uuid; v_vehicle public.vehicles%rowtype; v_category public.ride_categories%rowtype;
BEGIN
  SELECT p.franchise_id INTO v_fid FROM public.profiles p WHERE p.id=v_uid AND p.role='franchise_admin' AND p.active=true;
  IF v_fid IS NULL OR public.jwt_app_role()<>'franchise_admin' OR v_fid IS DISTINCT FROM public.jwt_franchise_id() THEN RAISE EXCEPTION 'Acesso exclusivo do franqueado'; END IF;
  SELECT d.city_id INTO v_city FROM public.drivers d WHERE d.id=p_driver_id AND d.franchise_id=v_fid;
  IF v_city IS NULL THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
  IF NOT public.can_access_city(v_city) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  SELECT * INTO v_category FROM public.ride_categories rc WHERE rc.id=p_category_id AND rc.franchise_id=v_fid AND rc.city_id=v_city;
  IF NOT FOUND THEN RAISE EXCEPTION 'Categoria não pertence à operação do motorista'; END IF;
  SELECT * INTO v_vehicle FROM public.vehicles v WHERE v.driver_id=p_driver_id AND v.active=true ORDER BY v.created_at DESC LIMIT 1;
  IF NOT FOUND THEN RAISE EXCEPTION 'Motorista sem veículo ativo'; END IF;
  IF coalesce(p_enabled,false) THEN
    IF v_vehicle.vehicle_type IS NULL OR v_vehicle.vehicle_type NOT IN ('car','motorcycle') THEN RAISE EXCEPTION 'Defina primeiro se o veículo é Carro ou Moto'; END IF;
    IF v_category.required_vehicle_type IS NOT NULL AND v_category.required_vehicle_type<>v_vehicle.vehicle_type THEN RAISE EXCEPTION 'Categoria incompatível com o tipo de veículo'; END IF;
  END IF;
  INSERT INTO public.driver_category_eligibility(driver_id,category_id,vehicle_id,active,approved_at)
  VALUES(p_driver_id,p_category_id,v_vehicle.id,coalesce(p_enabled,false),CASE WHEN p_enabled THEN now() ELSE null END)
  ON CONFLICT(driver_id,category_id) DO UPDATE SET vehicle_id=excluded.vehicle_id,active=excluded.active,approved_at=excluded.approved_at;
  RETURN jsonb_build_object('ok',true,'enabled',coalesce(p_enabled,false));
END; $$;

CREATE OR REPLACE FUNCTION public.franchise_set_driver_vehicle_type(p_driver_id uuid,p_vehicle_id uuid,p_vehicle_type text)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid(); v_fid uuid; v_city uuid; v_type text:=lower(trim(coalesce(p_vehicle_type,'')));
BEGIN
  SELECT p.franchise_id INTO v_fid FROM public.profiles p WHERE p.id=v_uid AND p.role='franchise_admin' AND p.active=true;
  IF v_fid IS NULL OR public.jwt_app_role()<>'franchise_admin' OR v_fid IS DISTINCT FROM public.jwt_franchise_id() THEN RAISE EXCEPTION 'Acesso exclusivo do franqueado'; END IF;
  IF v_type NOT IN ('car','motorcycle') THEN RAISE EXCEPTION 'Tipo de veículo inválido'; END IF;
  SELECT d.city_id INTO v_city FROM public.drivers d WHERE d.id=p_driver_id AND d.franchise_id=v_fid;
  IF v_city IS NULL THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
  IF NOT public.can_access_city(v_city) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  IF NOT EXISTS(SELECT 1 FROM public.vehicles v WHERE v.id=p_vehicle_id AND v.driver_id=p_driver_id AND v.active=true) THEN RAISE EXCEPTION 'Veículo ativo não encontrado'; END IF;
  UPDATE public.vehicles SET vehicle_type=v_type WHERE id=p_vehicle_id;
  UPDATE public.driver_category_eligibility e SET active=false
   WHERE e.driver_id=p_driver_id AND e.vehicle_id=p_vehicle_id
     AND EXISTS(SELECT 1 FROM public.ride_categories rc WHERE rc.id=e.category_id AND rc.required_vehicle_type IS NOT NULL AND rc.required_vehicle_type<>v_type);
  RETURN jsonb_build_object('ok',true,'vehicle_type',v_type);
END; $$;

CREATE OR REPLACE FUNCTION public.franchise_driver_category_matrix()
RETURNS TABLE(driver_id uuid,driver_name text,driver_status text,vehicle_id uuid,vehicle_make text,vehicle_model text,vehicle_plate text,vehicle_type text,category_id uuid,category_name text,required_vehicle_type text,category_active boolean,assigned boolean)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid(); v_fid uuid;
BEGIN
  SELECT p.franchise_id INTO v_fid FROM public.profiles p WHERE p.id=v_uid AND p.role='franchise_admin' AND p.active=true;
  IF v_fid IS NULL OR public.jwt_app_role()<>'franchise_admin' OR v_fid IS DISTINCT FROM public.jwt_franchise_id() THEN RAISE EXCEPTION 'Acesso exclusivo do franqueado'; END IF;
  RETURN QUERY
  SELECT d.id,coalesce(pr.full_name,'Motorista'),d.status::text,v.id,v.make,v.model,v.plate,v.vehicle_type,
         rc.id,rc.name,rc.required_vehicle_type,rc.active,
         EXISTS(SELECT 1 FROM public.driver_category_eligibility e WHERE e.driver_id=d.id AND e.category_id=rc.id AND e.active=true)
  FROM public.drivers d
  JOIN public.profiles pr ON pr.id=d.id
  LEFT JOIN LATERAL(SELECT vv.* FROM public.vehicles vv WHERE vv.driver_id=d.id AND vv.active=true ORDER BY vv.created_at DESC LIMIT 1)v ON true
  JOIN public.ride_categories rc ON rc.franchise_id=v_fid AND rc.city_id=d.city_id
  WHERE d.franchise_id=v_fid AND public.can_access_city(d.city_id)
  ORDER BY pr.full_name,rc.name;
END; $$;

CREATE OR REPLACE FUNCTION public.mark_driver_monthly_paid(p_driver_id uuid,p_paid_until date,p_reason text DEFAULT 'Mensalidade registrada pelo franqueado')
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_role text:=public.jwt_app_role();v_franchise uuid:=public.jwt_franchise_id();v_driver public.drivers%rowtype;v_cfg public.driver_billing_settings%rowtype;v_ref date:=date_trunc('month',current_date)::date;
BEGIN
  IF auth.uid() IS NULL OR v_role NOT IN ('franchise_admin','super_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=p_driver_id; IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  IF v_role='franchise_admin' THEN
    IF v_driver.franchise_id IS DISTINCT FROM v_franchise THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
    IF NOT public.can_access_city(v_driver.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  END IF;
  SELECT * INTO v_cfg FROM public.driver_billing_settings WHERE driver_id=p_driver_id;
  IF NOT FOUND OR v_cfg.billing_mode<>'monthly' THEN RAISE EXCEPTION 'Motorista não está no plano mensal'; END IF;
  IF p_paid_until<current_date THEN RAISE EXCEPTION 'A validade precisa ser hoje ou uma data futura'; END IF;
  UPDATE public.driver_billing_settings SET monthly_paid_until=p_paid_until,updated_by=auth.uid(),updated_at=now() WHERE driver_id=p_driver_id;
  INSERT INTO public.driver_monthly_payments(driver_id,franchise_id,reference_month,amount,method,status,paid_at,paid_until,created_by)
  VALUES(p_driver_id,v_driver.franchise_id,v_ref,v_cfg.monthly_fee,'manual','paid',now(),p_paid_until,auth.uid())
  ON CONFLICT(driver_id,reference_month) DO UPDATE SET amount=excluded.amount,method='manual',status='paid',paid_at=now(),paid_until=excluded.paid_until,created_by=excluded.created_by;
  INSERT INTO public.financial_transactions(payer_id,driver_id,franchise_id,city_id,tipo_pagamento,valor_total,tipo_operacao,status_pagamento,data_pagamento,metadata)
  SELECT p_driver_id,p_driver_id,v_driver.franchise_id,v_driver.city_id,'MANUAL',v_cfg.monthly_fee,'MENSALIDADE_MOTORISTA','PAGO',now(),jsonb_build_object('reference_month',v_ref,'paid_until',p_paid_until,'reason',p_reason)
  WHERE NOT EXISTS(SELECT 1 FROM public.financial_transactions ft WHERE ft.driver_id=p_driver_id AND ft.tipo_operacao='MENSALIDADE_MOTORISTA' AND ft.status_pagamento='PAGO' AND ft.metadata->>'reference_month'=v_ref::text);
  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(auth.uid(),'driver_monthly_payment_registered','driver',p_driver_id::text,jsonb_build_object('paid_until',p_paid_until,'reason',p_reason,'reference_month',v_ref,'city_id',v_driver.city_id));
END; $$;

CREATE OR REPLACE FUNCTION public.set_driver_card_machine_approval(p_driver_id uuid,p_approved boolean)
RETURNS void LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_role text:=public.jwt_app_role();v_franchise uuid:=public.jwt_franchise_id();v_driver public.drivers%rowtype;
BEGIN
  IF auth.uid() IS NULL OR v_role NOT IN ('franchise_admin','super_admin') THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=p_driver_id; IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  IF v_role='franchise_admin' THEN
    IF v_driver.franchise_id IS DISTINCT FROM v_franchise THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
    IF NOT public.can_access_city(v_driver.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  END IF;
  IF p_approved AND NOT v_driver.has_card_machine THEN RAISE EXCEPTION 'Motorista ainda não informou que possui maquininha'; END IF;
  UPDATE public.drivers SET card_machine_approved=p_approved WHERE id=p_driver_id;
  INSERT INTO public.audit_logs(actor_id,action,entity,entity_id,metadata)
  VALUES(auth.uid(),CASE WHEN p_approved THEN 'driver_card_machine_approved' ELSE 'driver_card_machine_revoked' END,'driver',p_driver_id::text,jsonb_build_object('approved',p_approved,'city_id',v_driver.city_id));
END; $$;

CREATE OR REPLACE FUNCTION public.settle_driver_taximeter_pending_fees(p_driver_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid();v_role text:=public.jwt_app_role();v_own uuid:=public.jwt_franchise_id();v_target uuid;v_driver public.drivers%rowtype;v_balance numeric:=0;c public.driver_taximeter_charges%rowtype;v_tx uuid;v_count int:=0;v_total numeric:=0;v_pending numeric:=0;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  IF v_role='driver' THEN v_target:=v_uid; IF p_driver_id IS NOT NULL AND p_driver_id<>v_uid THEN RAISE EXCEPTION 'Sem permissão'; END IF;
  ELSIF v_role IN ('super_admin','franchise_admin') THEN v_target:=p_driver_id; IF v_target IS NULL THEN RAISE EXCEPTION 'Informe o motorista'; END IF;
  ELSE RAISE EXCEPTION 'Sem permissão'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=v_target; IF NOT FOUND THEN RAISE EXCEPTION 'Motorista não encontrado'; END IF;
  IF v_role='franchise_admin' THEN
    IF v_driver.franchise_id IS DISTINCT FROM v_own THEN RAISE EXCEPTION 'Motorista fora da sua franquia'; END IF;
    IF NOT public.can_access_city(v_driver.city_id) THEN RAISE EXCEPTION 'Motorista fora da sua cidade/região'; END IF;
  END IF;
  INSERT INTO public.driver_operational_wallets(driver_id) VALUES(v_target) ON CONFLICT(driver_id) DO NOTHING;
  SELECT balance INTO v_balance FROM public.driver_operational_wallets WHERE driver_id=v_target FOR UPDATE;
  FOR c IN SELECT * FROM public.driver_taximeter_charges WHERE driver_id=v_target AND status='pending' ORDER BY created_at FOR UPDATE LOOP
    EXIT WHEN coalesce(v_balance,0)<c.fee_amount;
    UPDATE public.driver_operational_wallets SET balance=balance-c.fee_amount,updated_at=now() WHERE driver_id=v_target RETURNING balance INTO v_balance;
    INSERT INTO public.driver_operational_transactions(driver_id,franchise_id,city_id,transaction_type,source,amount,status,reason,created_by,metadata,settled_at)
    VALUES(c.driver_id,c.franchise_id,c.city_id,'debit','taximeter_fee',c.fee_amount,'settled','Quitação de taxa pendente do taxímetro',v_uid,jsonb_build_object('taximeter_session_id',c.session_id,'charge_id',c.id),now()) RETURNING id INTO v_tx;
    UPDATE public.driver_taximeter_charges SET status='settled',wallet_transaction_id=v_tx,settled_at=now(),updated_at=now() WHERE id=c.id;
    v_count:=v_count+1;v_total:=v_total+c.fee_amount;
  END LOOP;
  SELECT coalesce(sum(fee_amount),0) INTO v_pending FROM public.driver_taximeter_charges WHERE driver_id=v_target AND status='pending';
  RETURN jsonb_build_object('settled_count',v_count,'settled_amount',v_total,'pending_amount',v_pending,'wallet_balance',v_balance);
END; $$;

CREATE OR REPLACE FUNCTION public.get_operation_safety_alerts(p_status text DEFAULT 'open',p_limit integer DEFAULT 100)
RETURNS jsonb LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid();v_role text:=public.jwt_app_role();v_profile_role text;v_franchise uuid;v_profile_franchise uuid;v_active boolean;v_result jsonb;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  SELECT p.role::text,p.franchise_id,p.active INTO v_profile_role,v_profile_franchise,v_active FROM public.profiles p WHERE p.id=v_uid;
  IF NOT coalesce(v_active,false) OR v_profile_role IS DISTINCT FROM v_role OR v_role NOT IN ('franchise_admin','super_admin') THEN RAISE EXCEPTION 'Acesso exclusivo da operação'; END IF;
  v_franchise:=CASE WHEN v_role='franchise_admin' THEN v_profile_franchise ELSE null END;
  SELECT coalesce(jsonb_agg(x.obj ORDER BY x.created_at DESC),'[]'::jsonb) INTO v_result
  FROM(
    SELECT a.created_at,jsonb_build_object('id',a.id,'ride_id',a.ride_id,'alert_type',a.alert_type,'severity',a.severity,'reporter_role',a.reporter_role,'lat',a.lat,'lng',a.lng,'distance_from_route_m',a.distance_from_route_m,'message',a.message,'status',a.status,'created_at',a.created_at,'resolved_at',a.resolved_at,'ride_status',r.status::text,'origin_label',r.origin_label,'destination_label',r.destination_label,'passenger_name',pp.full_name,'driver_name',dp.full_name,'franchise_id',r.franchise_id,'city_id',r.city_id)obj
    FROM public.ride_safety_alerts a
    JOIN public.rides r ON r.id=a.ride_id
    LEFT JOIN public.profiles pp ON pp.id=r.passenger_id
    LEFT JOIN public.profiles dp ON dp.id=r.driver_id
    WHERE (p_status IS NULL OR p_status='all' OR a.status=p_status)
      AND (v_role='super_admin' OR (r.franchise_id=v_franchise AND public.can_access_city(r.city_id)))
    ORDER BY a.created_at DESC LIMIT greatest(1,least(coalesce(p_limit,100),500))
  )x;
  RETURN v_result;
END; $$;

CREATE OR REPLACE FUNCTION public.get_taximeter_operations_report(p_from timestamptz DEFAULT now()-interval '30 days',p_to timestamptz DEFAULT now(),p_limit integer DEFAULT 1000)
RETURNS TABLE(session_id uuid,driver_id uuid,driver_name text,franchise_id uuid,franchise_name text,city_id uuid,city_name text,status text,started_at timestamptz,ended_at timestamptz,distance_m numeric,elapsed_seconds integer,final_amount numeric,current_amount numeric,payment_method text,multiplier numeric,fee_amount numeric,fee_status text,driver_net_amount numeric,fee_mode text,fee_value numeric)
LANGUAGE plpgsql SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid();v_role text:=public.jwt_app_role();v_franchise uuid:=public.jwt_franchise_id();v_profile_role text;v_active boolean;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  SELECT p.role::text,p.active INTO v_profile_role,v_active FROM public.profiles p WHERE p.id=v_uid;
  IF NOT coalesce(v_active,false) OR v_profile_role IS DISTINCT FROM v_role OR v_role NOT IN ('super_admin','franchise_admin') THEN RAISE EXCEPTION 'Acesso restrito à operação'; END IF;
  RETURN QUERY SELECT s.id,s.driver_id,p.full_name,s.franchise_id,coalesce(f.trade_name,f.legal_name),s.city_id,c.name,s.status,s.started_at,s.ended_at,s.distance_m,s.elapsed_seconds,s.final_amount,s.current_amount,s.payment_method,s.multiplier,coalesce(ch.fee_amount,0),coalesce(ch.status,CASE WHEN s.status='finished' THEN 'not_charged' ELSE null END),coalesce(ch.driver_net_amount,s.final_amount),ch.fee_mode,ch.fee_value
  FROM public.driver_taximeter_sessions s
  LEFT JOIN public.profiles p ON p.id=s.driver_id
  LEFT JOIN public.franchises f ON f.id=s.franchise_id
  LEFT JOIN public.cities c ON c.id=s.city_id
  LEFT JOIN public.driver_taximeter_charges ch ON ch.session_id=s.id
  WHERE s.started_at>=coalesce(p_from,now()-interval '30 days') AND s.started_at<=coalesce(p_to,now())
    AND (v_role='super_admin' OR (s.franchise_id=v_franchise AND public.can_access_city(s.city_id)))
  ORDER BY s.started_at DESC LIMIT greatest(1,least(coalesce(p_limit,1000),5000));
END; $$;

-- Taximeter fee settings are franchise-wide. A city-limited admin cannot mutate
-- them if the franchise later spans cities outside their access list.
CREATE OR REPLACE FUNCTION public.get_taximeter_financial_settings(p_franchise_id uuid DEFAULT NULL)
RETURNS jsonb LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v_uid uuid:=auth.uid();v_role text:=public.jwt_app_role();v_own uuid:=public.jwt_franchise_id();v_target uuid;g public.taximeter_financial_rules%rowtype;f public.taximeter_financial_rules%rowtype;e record;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  IF v_role='super_admin' THEN v_target:=p_franchise_id;
  ELSIF v_role='franchise_admin' THEN v_target:=v_own;IF NOT public.can_manage_franchise_scope(v_target) THEN RAISE EXCEPTION 'Configuração de escopo da franquia indisponível para um administrador limitado a parte das cidades';END IF;
  ELSE RAISE EXCEPTION 'Acesso restrito à operação'; END IF;
  SELECT * INTO g FROM public.taximeter_financial_rules WHERE scope='global' LIMIT 1;
  IF v_target IS NOT NULL THEN SELECT * INTO f FROM public.taximeter_financial_rules WHERE scope='franchise' AND franchise_id=v_target LIMIT 1;END IF;
  IF v_target IS NOT NULL THEN SELECT * INTO e FROM public.effective_taximeter_financial_rule(v_target);
  ELSE SELECT coalesce(g.fee_mode,'none') fee_mode,coalesce(g.fee_value,0) fee_value,'global'::text source_scope,coalesce(g.allow_franchise_override,true) allow_franchise_override,false locked_by_matrix INTO e;END IF;
  RETURN jsonb_build_object('target_franchise_id',v_target,'global_fee_mode',coalesce(g.fee_mode,'none'),'global_fee_value',coalesce(g.fee_value,0),'allow_franchise_override',coalesce(g.allow_franchise_override,true),'override_exists',f.id IS NOT NULL,'override_fee_mode',f.fee_mode,'override_fee_value',f.fee_value,'override_locked_by_matrix',coalesce(f.locked_by_matrix,false),'effective_fee_mode',e.fee_mode,'effective_fee_value',e.fee_value,'effective_source',e.source_scope,'can_edit',CASE WHEN v_role='super_admin' THEN true ELSE coalesce(g.allow_franchise_override,true) AND NOT coalesce(f.locked_by_matrix,false) END);
END; $$;

-- Explicit ACLs: no anonymous access to privileged regional operations.
REVOKE EXECUTE ON FUNCTION public.franchise_review_driver(uuid,boolean,text) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.franchise_set_driver_category(uuid,uuid,boolean) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.franchise_set_driver_vehicle_type(uuid,uuid,text) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.franchise_driver_category_matrix() FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.mark_driver_monthly_paid(uuid,date,text) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.set_driver_card_machine_approval(uuid,boolean) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.settle_driver_taximeter_pending_fees(uuid) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.get_operation_safety_alerts(text,integer) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.get_taximeter_operations_report(timestamptz,timestamptz,integer) FROM public,anon;
REVOKE EXECUTE ON FUNCTION public.get_taximeter_financial_settings(uuid) FROM public,anon;

GRANT EXECUTE ON FUNCTION public.franchise_review_driver(uuid,boolean,text) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.franchise_set_driver_category(uuid,uuid,boolean) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.franchise_set_driver_vehicle_type(uuid,uuid,text) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.franchise_driver_category_matrix() TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.mark_driver_monthly_paid(uuid,date,text) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.set_driver_card_machine_approval(uuid,boolean) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.settle_driver_taximeter_pending_fees(uuid) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.get_operation_safety_alerts(text,integer) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.get_taximeter_operations_report(timestamptz,timestamptz,integer) TO authenticated,service_role;
GRANT EXECUTE ON FUNCTION public.get_taximeter_financial_settings(uuid) TO authenticated,service_role;

-- Internal dispatch remains backend-only.
REVOKE EXECUTE ON FUNCTION public.dispatch_ride(uuid) FROM public,anon,authenticated;
GRANT EXECUTE ON FUNCTION public.dispatch_ride(uuid) TO service_role;
