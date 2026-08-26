create or replace function public.audit_platform_payment_settings_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  new.updated_by:=auth.uid();
  new.updated_at:=now();
  return new;
end;
$$;

drop trigger if exists trg_stamp_platform_payment_settings_update on public.platform_payment_settings;
create trigger trg_stamp_platform_payment_settings_update
before update on public.platform_payment_settings
for each row execute function public.audit_platform_payment_settings_update();

create or replace function public.log_platform_payment_settings_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    'matrix_update_platform_payment_settings',
    'platform_payment_settings',
    new.scope,
    jsonb_build_object(
      'before',jsonb_build_object(
        'cash_enabled',old.cash_enabled,
        'pix_enabled',old.pix_enabled,
        'card_app_enabled',old.card_app_enabled,
        'card_machine_enabled',old.card_machine_enabled,
        'card_credit_enabled',old.card_credit_enabled,
        'card_debit_enabled',old.card_debit_enabled,
        'app_card_gateway',old.app_card_gateway,
        'card_surcharge_percentage',old.card_surcharge_percentage,
        'card_fee_bearer',old.card_fee_bearer,
        'installments_enabled',old.installments_enabled,
        'max_installments',old.max_installments,
        'franchise_can_manage',old.franchise_can_manage
      ),
      'after',jsonb_build_object(
        'cash_enabled',new.cash_enabled,
        'pix_enabled',new.pix_enabled,
        'card_app_enabled',new.card_app_enabled,
        'card_machine_enabled',new.card_machine_enabled,
        'card_credit_enabled',new.card_credit_enabled,
        'card_debit_enabled',new.card_debit_enabled,
        'app_card_gateway',new.app_card_gateway,
        'card_surcharge_percentage',new.card_surcharge_percentage,
        'card_fee_bearer',new.card_fee_bearer,
        'installments_enabled',new.installments_enabled,
        'max_installments',new.max_installments,
        'franchise_can_manage',new.franchise_can_manage
      )
    )
  );
  return new;
end;
$$;

drop trigger if exists trg_audit_platform_payment_settings_update on public.platform_payment_settings;
create trigger trg_audit_platform_payment_settings_update
after update on public.platform_payment_settings
for each row execute function public.log_platform_payment_settings_update();

create or replace function public.stamp_platform_operational_wallet_settings_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  new.updated_by:=auth.uid();
  new.updated_at:=now();
  return new;
end;
$$;

drop trigger if exists trg_stamp_platform_operational_wallet_settings_update on public.platform_operational_wallet_settings;
create trigger trg_stamp_platform_operational_wallet_settings_update
before update on public.platform_operational_wallet_settings
for each row execute function public.stamp_platform_operational_wallet_settings_update();

create or replace function public.log_platform_operational_wallet_settings_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    'matrix_update_platform_operational_wallet_settings',
    'platform_operational_wallet_settings',
    new.scope,
    jsonb_build_object(
      'before',jsonb_build_object(
        'enabled',old.enabled,
        'minimum_balance_to_receive',old.minimum_balance_to_receive,
        'low_balance_threshold',old.low_balance_threshold,
        'default_ride_fee',old.default_ride_fee,
        'default_ride_fee_mode',old.default_ride_fee_mode,
        'default_ride_fee_percentage',old.default_ride_fee_percentage,
        'cash_negative_limit',old.cash_negative_limit,
        'franchise_can_set_ride_fee',old.franchise_can_set_ride_fee,
        'franchise_manual_credit_enabled',old.franchise_manual_credit_enabled,
        'franchise_manual_credit_limit',old.franchise_manual_credit_limit
      ),
      'after',jsonb_build_object(
        'enabled',new.enabled,
        'minimum_balance_to_receive',new.minimum_balance_to_receive,
        'low_balance_threshold',new.low_balance_threshold,
        'default_ride_fee',new.default_ride_fee,
        'default_ride_fee_mode',new.default_ride_fee_mode,
        'default_ride_fee_percentage',new.default_ride_fee_percentage,
        'cash_negative_limit',new.cash_negative_limit,
        'franchise_can_set_ride_fee',new.franchise_can_set_ride_fee,
        'franchise_manual_credit_enabled',new.franchise_manual_credit_enabled,
        'franchise_manual_credit_limit',new.franchise_manual_credit_limit
      )
    )
  );
  return new;
end;
$$;

drop trigger if exists trg_audit_platform_operational_wallet_settings_update on public.platform_operational_wallet_settings;
create trigger trg_audit_platform_operational_wallet_settings_update
after update on public.platform_operational_wallet_settings
for each row execute function public.log_platform_operational_wallet_settings_update();

drop policy if exists platform_payment_settings_matrix on public.platform_payment_settings;
drop policy if exists platform_payment_settings_matrix_update on public.platform_payment_settings;
create policy platform_payment_settings_matrix_update
on public.platform_payment_settings
for update
to authenticated
using (public.current_profile_matches_role('super_admin'))
with check (public.current_profile_matches_role('super_admin'));

drop policy if exists platform_operational_settings_matrix on public.platform_operational_wallet_settings;
drop policy if exists platform_operational_settings_matrix_update on public.platform_operational_wallet_settings;
create policy platform_operational_settings_matrix_update
on public.platform_operational_wallet_settings
for update
to authenticated
using (public.current_profile_matches_role('super_admin'))
with check (public.current_profile_matches_role('super_admin'));

revoke all on table public.platform_payment_settings from anon;
revoke all on table public.platform_payment_settings from authenticated;
grant select,update on table public.platform_payment_settings to authenticated;

revoke all on table public.platform_operational_wallet_settings from anon;
revoke all on table public.platform_operational_wallet_settings from authenticated;
grant select,update on table public.platform_operational_wallet_settings to authenticated;
