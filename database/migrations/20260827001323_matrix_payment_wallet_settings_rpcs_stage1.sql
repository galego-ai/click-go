-- Stage 1: audited Matrix RPCs for payment and operational-wallet settings.

create or replace function public.matrix_update_platform_payment_wallet_settings(
  p_payment jsonb,
  p_wallet jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $function$
declare
  v_uid uuid:=auth.uid();
  v_pay public.platform_payment_settings%rowtype;
  v_wallet public.platform_operational_wallet_settings%rowtype;
  v_surcharge numeric;
  v_fee_bearer text;
  v_max_installments integer;
  v_minimum numeric;
  v_low numeric;
  v_ride_fee numeric;
  v_credit_limit numeric;
begin
  if v_uid is null or public.current_active_management_role()<>'super_admin' then
    raise exception 'Acesso restrito ao Super Admin ativo';
  end if;
  if p_payment is null or p_wallet is null then raise exception 'Configurações incompletas'; end if;

  select * into v_pay from public.platform_payment_settings where scope='global' for update;
  if not found then raise exception 'Configuração global de pagamentos não encontrada'; end if;
  select * into v_wallet from public.platform_operational_wallet_settings where scope='global' for update;
  if not found then raise exception 'Configuração global da carteira não encontrada'; end if;

  v_surcharge:=coalesce(nullif(p_payment->>'card_surcharge_percentage','')::numeric,v_pay.card_surcharge_percentage);
  v_fee_bearer:=coalesce(nullif(btrim(p_payment->>'card_fee_bearer'),''),v_pay.card_fee_bearer);
  v_max_installments:=coalesce(nullif(p_payment->>'max_installments','')::integer,v_pay.max_installments);
  v_minimum:=coalesce(nullif(p_wallet->>'minimum_balance_to_receive','')::numeric,v_wallet.minimum_balance_to_receive);
  v_low:=coalesce(nullif(p_wallet->>'low_balance_threshold','')::numeric,v_wallet.low_balance_threshold);
  v_ride_fee:=coalesce(nullif(p_wallet->>'default_ride_fee','')::numeric,v_wallet.default_ride_fee);
  v_credit_limit:=case
    when not (p_wallet ? 'franchise_manual_credit_limit') then v_wallet.franchise_manual_credit_limit
    when nullif(p_wallet->>'franchise_manual_credit_limit','') is null then null
    else (p_wallet->>'franchise_manual_credit_limit')::numeric
  end;

  if v_surcharge<0 or v_surcharge>100 then raise exception 'Acréscimo do cartão deve ficar entre 0 e 100%%'; end if;
  if v_fee_bearer not in ('passenger','driver','franchise','platform') then raise exception 'Responsável pela taxa do cartão inválido'; end if;
  if v_max_installments<1 or v_max_installments>24 then raise exception 'Máximo de parcelas deve ficar entre 1 e 24'; end if;
  if v_minimum<0 or v_low<0 or v_ride_fee<0 then raise exception 'Valores da carteira não podem ser negativos'; end if;
  if v_credit_limit is not null and v_credit_limit<=0 then raise exception 'Limite de crédito manual deve ser maior que zero ou vazio'; end if;

  update public.platform_payment_settings
     set cash_enabled=coalesce((p_payment->>'cash_enabled')::boolean,v_pay.cash_enabled),
         pix_enabled=coalesce((p_payment->>'pix_enabled')::boolean,v_pay.pix_enabled),
         card_app_enabled=coalesce((p_payment->>'card_app_enabled')::boolean,v_pay.card_app_enabled),
         card_machine_enabled=coalesce((p_payment->>'card_machine_enabled')::boolean,v_pay.card_machine_enabled),
         card_credit_enabled=coalesce((p_payment->>'card_credit_enabled')::boolean,v_pay.card_credit_enabled),
         card_debit_enabled=coalesce((p_payment->>'card_debit_enabled')::boolean,v_pay.card_debit_enabled),
         app_card_gateway=case when p_payment ? 'app_card_gateway' then nullif(btrim(p_payment->>'app_card_gateway'),'') else v_pay.app_card_gateway end,
         card_surcharge_percentage=v_surcharge,
         card_fee_bearer=v_fee_bearer,
         installments_enabled=coalesce((p_payment->>'installments_enabled')::boolean,v_pay.installments_enabled),
         max_installments=v_max_installments,
         franchise_can_manage=coalesce((p_payment->>'franchise_can_manage')::boolean,v_pay.franchise_can_manage),
         updated_by=v_uid,
         updated_at=now()
   where scope='global';

  update public.platform_operational_wallet_settings
     set enabled=coalesce((p_wallet->>'enabled')::boolean,v_wallet.enabled),
         minimum_balance_to_receive=v_minimum,
         low_balance_threshold=v_low,
         default_ride_fee=v_ride_fee,
         franchise_can_set_ride_fee=coalesce((p_wallet->>'franchise_can_set_ride_fee')::boolean,v_wallet.franchise_can_set_ride_fee),
         franchise_manual_credit_enabled=coalesce((p_wallet->>'franchise_manual_credit_enabled')::boolean,v_wallet.franchise_manual_credit_enabled),
         franchise_manual_credit_limit=v_credit_limit,
         updated_by=v_uid,
         updated_at=now()
   where scope='global';

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'matrix_update_platform_payment_wallet_settings','platform_settings','global',jsonb_build_object('payment_changed',true,'wallet_changed',true));
  return jsonb_build_object('ok',true);
end;
$function$;

create or replace function public.matrix_set_franchise_payment_wallet_override(
  p_franchise_id uuid,
  p_city_id uuid,
  p_payment jsonb,
  p_wallet jsonb
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $function$
declare
  v_uid uuid:=auth.uid();
  v_ride_fee numeric;
  v_minimum numeric;
  v_low numeric;
begin
  if v_uid is null or public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_franchise_id is null or p_city_id is null then raise exception 'Franquia e cidade são obrigatórias'; end if;
  if not exists(
    select 1 from public.franchise_cities fc
    join public.franchises f on f.id=fc.franchise_id
    join public.cities c on c.id=fc.city_id
    where fc.franchise_id=p_franchise_id and fc.city_id=p_city_id and f.deleted_at is null and c.active=true
  ) then raise exception 'Franquia/cidade não vinculada ou indisponível'; end if;

  v_ride_fee:=coalesce(nullif(p_wallet->>'ride_fee','')::numeric,0);
  v_minimum:=coalesce(nullif(p_wallet->>'minimum_balance_to_receive','')::numeric,0);
  v_low:=coalesce(nullif(p_wallet->>'low_balance_threshold','')::numeric,0);
  if v_ride_fee<0 or v_minimum<0 or v_low<0 then raise exception 'Valores da carteira não podem ser negativos'; end if;

  insert into public.franchise_city_payment_settings(franchise_id,city_id,cash_enabled,pix_enabled,card_app_enabled,card_machine_enabled,locked_by_matrix,updated_by,updated_at)
  values(
    p_franchise_id,p_city_id,
    case when p_payment ? 'cash_enabled' then (p_payment->>'cash_enabled')::boolean else null end,
    case when p_payment ? 'pix_enabled' then (p_payment->>'pix_enabled')::boolean else null end,
    case when p_payment ? 'card_app_enabled' then (p_payment->>'card_app_enabled')::boolean else null end,
    case when p_payment ? 'card_machine_enabled' then (p_payment->>'card_machine_enabled')::boolean else null end,
    coalesce((p_payment->>'locked_by_matrix')::boolean,false),v_uid,now()
  ) on conflict(franchise_id,city_id) do update set
    cash_enabled=excluded.cash_enabled,pix_enabled=excluded.pix_enabled,
    card_app_enabled=excluded.card_app_enabled,card_machine_enabled=excluded.card_machine_enabled,
    locked_by_matrix=excluded.locked_by_matrix,updated_by=v_uid,updated_at=now();

  insert into public.franchise_operational_wallet_settings(franchise_id,ride_fee,minimum_balance_to_receive,low_balance_threshold,locked_by_matrix,updated_by,updated_at)
  values(p_franchise_id,v_ride_fee,v_minimum,v_low,coalesce((p_wallet->>'locked_by_matrix')::boolean,false),v_uid,now())
  on conflict(franchise_id) do update set
    ride_fee=excluded.ride_fee,minimum_balance_to_receive=excluded.minimum_balance_to_receive,
    low_balance_threshold=excluded.low_balance_threshold,locked_by_matrix=excluded.locked_by_matrix,
    updated_by=v_uid,updated_at=now();

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'matrix_set_franchise_payment_wallet_override','franchise',p_franchise_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'city_id',p_city_id,'payment_override',p_payment,'wallet_override',p_wallet));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'city_id',p_city_id);
end;
$function$;

revoke all on function public.matrix_update_platform_payment_wallet_settings(jsonb,jsonb) from public, anon;
grant execute on function public.matrix_update_platform_payment_wallet_settings(jsonb,jsonb) to authenticated, service_role;
revoke all on function public.matrix_set_franchise_payment_wallet_override(uuid,uuid,jsonb,jsonb) from public, anon;
grant execute on function public.matrix_set_franchise_payment_wallet_override(uuid,uuid,jsonb,jsonb) to authenticated, service_role;
