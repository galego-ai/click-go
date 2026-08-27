-- Stage 1: trusted payment and wallet RPCs for franchise admins/operators.

create or replace function public.franchise_update_city_payment_settings(
  p_city_id uuid,
  p_payment jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_global public.platform_payment_settings%rowtype;
  v_local public.franchise_city_payment_settings%rowtype;
  v_cash boolean;
  v_pix boolean;
  v_card_app boolean;
  v_card_machine boolean;
  v_credit boolean;
  v_debit boolean;
  v_installments boolean;
  v_surcharge numeric;
  v_bearer text;
  v_max_installments integer;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('finance') then
    v_fid:=public.staff_franchise_id();
  else
    raise exception 'Acesso restrito ao franqueado ou operador financeiro';
  end if;
  if v_fid is null or p_city_id is null then raise exception 'Franquia/cidade inválida'; end if;
  if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=p_city_id)
     or not public.can_access_city(p_city_id) then raise exception 'Cidade fora do escopo da franquia'; end if;

  select * into v_global from public.platform_payment_settings where scope='global';
  if not found or not v_global.franchise_can_manage then raise exception 'A Matriz bloqueou alterações de meios de pagamento pelos franqueados'; end if;
  select * into v_local from public.franchise_city_payment_settings where franchise_id=v_fid and city_id=p_city_id for update;
  if found and v_local.locked_by_matrix then raise exception 'Esta cidade está bloqueada pela Matriz'; end if;

  v_cash:=coalesce((p_payment->>'cash_enabled')::boolean,v_global.cash_enabled);
  v_pix:=coalesce((p_payment->>'pix_enabled')::boolean,v_global.pix_enabled);
  v_card_app:=coalesce((p_payment->>'card_app_enabled')::boolean,v_global.card_app_enabled);
  v_card_machine:=coalesce((p_payment->>'card_machine_enabled')::boolean,v_global.card_machine_enabled);
  v_credit:=coalesce((p_payment->>'card_credit_enabled')::boolean,v_global.card_credit_enabled);
  v_debit:=coalesce((p_payment->>'card_debit_enabled')::boolean,v_global.card_debit_enabled);
  v_installments:=coalesce((p_payment->>'installments_enabled')::boolean,v_global.installments_enabled);

  if v_cash and not v_global.cash_enabled then raise exception 'Dinheiro foi bloqueado pela Matriz'; end if;
  if v_pix and not v_global.pix_enabled then raise exception 'PIX foi bloqueado pela Matriz'; end if;
  if v_card_app and not v_global.card_app_enabled then raise exception 'Cartão pelo app foi bloqueado pela Matriz'; end if;
  if v_card_machine and not v_global.card_machine_enabled then raise exception 'Maquininha foi bloqueada pela Matriz'; end if;
  if v_credit and not v_global.card_credit_enabled then raise exception 'Crédito foi bloqueado pela Matriz'; end if;
  if v_debit and not v_global.card_debit_enabled then raise exception 'Débito foi bloqueado pela Matriz'; end if;
  if v_installments and not v_global.installments_enabled then raise exception 'Parcelamento foi bloqueado pela Matriz'; end if;

  v_surcharge:=coalesce(nullif(p_payment->>'card_surcharge_percentage','')::numeric,v_global.card_surcharge_percentage);
  v_bearer:=coalesce(nullif(btrim(p_payment->>'card_fee_bearer'),''),v_global.card_fee_bearer);
  v_max_installments:=coalesce(nullif(p_payment->>'max_installments','')::integer,v_global.max_installments);
  if v_surcharge<0 or v_surcharge>100 then raise exception 'Acréscimo do cartão deve ficar entre 0 e 100%%'; end if;
  if v_bearer not in ('passenger','driver','franchise','platform') then raise exception 'Responsável pela taxa inválido'; end if;
  if v_max_installments<1 or v_max_installments>least(24,v_global.max_installments) then raise exception 'Parcelamento acima do limite da Matriz'; end if;

  insert into public.franchise_city_payment_settings(
    franchise_id,city_id,cash_enabled,pix_enabled,card_app_enabled,card_machine_enabled,
    card_credit_enabled,card_debit_enabled,app_card_gateway,card_surcharge_percentage,
    card_fee_bearer,installments_enabled,max_installments,locked_by_matrix,updated_by,updated_at
  ) values(
    v_fid,p_city_id,v_cash,v_pix,v_card_app,v_card_machine,v_credit,v_debit,
    case when p_payment ? 'app_card_gateway' then nullif(btrim(p_payment->>'app_card_gateway'),'') else v_global.app_card_gateway end,
    v_surcharge,v_bearer,v_installments,v_max_installments,false,v_uid,now()
  ) on conflict(franchise_id,city_id) do update set
    cash_enabled=excluded.cash_enabled,pix_enabled=excluded.pix_enabled,
    card_app_enabled=excluded.card_app_enabled,card_machine_enabled=excluded.card_machine_enabled,
    card_credit_enabled=excluded.card_credit_enabled,card_debit_enabled=excluded.card_debit_enabled,
    app_card_gateway=excluded.app_card_gateway,card_surcharge_percentage=excluded.card_surcharge_percentage,
    card_fee_bearer=excluded.card_fee_bearer,installments_enabled=excluded.installments_enabled,
    max_installments=excluded.max_installments,updated_by=v_uid,updated_at=now();

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_update_city_payment_settings','franchise_city_payment_settings',v_fid::text,
    jsonb_build_object('franchise_id',v_fid,'city_id',p_city_id,'source_role',v_role));
  return jsonb_build_object('ok',true,'franchise_id',v_fid,'city_id',p_city_id);
end;
$function$;

create or replace function public.franchise_update_operational_wallet_settings(p_wallet jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_global public.platform_operational_wallet_settings%rowtype;
  v_local public.franchise_operational_wallet_settings%rowtype;
  v_ride_fee numeric;
  v_minimum numeric;
  v_low numeric;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('finance') then
    v_fid:=public.staff_franchise_id();
  else
    raise exception 'Acesso restrito ao franqueado ou operador financeiro';
  end if;
  if v_fid is null or not exists(select 1 from public.franchises f where f.id=v_fid and f.deleted_at is null) then raise exception 'Franquia inválida ou excluída'; end if;
  select * into v_global from public.platform_operational_wallet_settings where scope='global';
  if not found then raise exception 'Configuração global da carteira não encontrada'; end if;
  select * into v_local from public.franchise_operational_wallet_settings where franchise_id=v_fid for update;
  if found and v_local.locked_by_matrix then raise exception 'As regras da carteira desta franquia estão bloqueadas pela Matriz'; end if;

  v_minimum:=coalesce(nullif(p_wallet->>'minimum_balance_to_receive','')::numeric,coalesce(v_local.minimum_balance_to_receive,v_global.minimum_balance_to_receive));
  v_low:=coalesce(nullif(p_wallet->>'low_balance_threshold','')::numeric,coalesce(v_local.low_balance_threshold,v_global.low_balance_threshold));
  if v_global.franchise_can_set_ride_fee then
    v_ride_fee:=coalesce(nullif(p_wallet->>'ride_fee','')::numeric,coalesce(v_local.ride_fee,v_global.default_ride_fee));
  else
    v_ride_fee:=coalesce(v_local.ride_fee,v_global.default_ride_fee);
  end if;
  if v_ride_fee<0 or v_minimum<0 or v_low<0 then raise exception 'Valores da carteira não podem ser negativos'; end if;

  insert into public.franchise_operational_wallet_settings(franchise_id,ride_fee,minimum_balance_to_receive,low_balance_threshold,locked_by_matrix,updated_by,updated_at)
  values(v_fid,v_ride_fee,v_minimum,v_low,false,v_uid,now())
  on conflict(franchise_id) do update set
    ride_fee=excluded.ride_fee,minimum_balance_to_receive=excluded.minimum_balance_to_receive,
    low_balance_threshold=excluded.low_balance_threshold,updated_by=v_uid,updated_at=now();

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_update_operational_wallet_settings','franchise_operational_wallet_settings',v_fid::text,
    jsonb_build_object('franchise_id',v_fid,'source_role',v_role,'ride_fee_edit_allowed',v_global.franchise_can_set_ride_fee));
  return jsonb_build_object('ok',true,'franchise_id',v_fid);
end;
$function$;

revoke all on function public.franchise_update_city_payment_settings(uuid,jsonb) from public, anon;
grant execute on function public.franchise_update_city_payment_settings(uuid,jsonb) to authenticated, service_role;
revoke all on function public.franchise_update_operational_wallet_settings(jsonb) from public, anon;
grant execute on function public.franchise_update_operational_wallet_settings(jsonb) to authenticated, service_role;
