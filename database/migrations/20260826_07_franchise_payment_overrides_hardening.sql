create or replace function public.stamp_franchise_city_payment_settings()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  if tg_op='UPDATE' then
    new.franchise_id:=old.franchise_id;
    new.city_id:=old.city_id;
  end if;
  new.updated_by:=coalesce(auth.uid(),new.updated_by);
  new.updated_at:=now();
  return new;
end;
$$;

drop trigger if exists trg_stamp_franchise_city_payment_settings on public.franchise_city_payment_settings;
create trigger trg_stamp_franchise_city_payment_settings
before insert or update on public.franchise_city_payment_settings
for each row execute function public.stamp_franchise_city_payment_settings();

create or replace function public.log_franchise_city_payment_settings()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    case when tg_op='INSERT' then 'create_franchise_city_payment_settings' else 'update_franchise_city_payment_settings' end,
    'franchise_city_payment_settings',
    new.franchise_id::text||':'||new.city_id::text,
    jsonb_build_object(
      'franchise_id',new.franchise_id,
      'city_id',new.city_id,
      'before',case when tg_op='UPDATE' then jsonb_build_object(
        'cash_enabled',old.cash_enabled,'pix_enabled',old.pix_enabled,'card_app_enabled',old.card_app_enabled,'card_machine_enabled',old.card_machine_enabled,
        'card_credit_enabled',old.card_credit_enabled,'card_debit_enabled',old.card_debit_enabled,'app_card_gateway',old.app_card_gateway,
        'card_surcharge_percentage',old.card_surcharge_percentage,'card_fee_bearer',old.card_fee_bearer,'installments_enabled',old.installments_enabled,
        'max_installments',old.max_installments,'locked_by_matrix',old.locked_by_matrix
      ) else null end,
      'after',jsonb_build_object(
        'cash_enabled',new.cash_enabled,'pix_enabled',new.pix_enabled,'card_app_enabled',new.card_app_enabled,'card_machine_enabled',new.card_machine_enabled,
        'card_credit_enabled',new.card_credit_enabled,'card_debit_enabled',new.card_debit_enabled,'app_card_gateway',new.app_card_gateway,
        'card_surcharge_percentage',new.card_surcharge_percentage,'card_fee_bearer',new.card_fee_bearer,'installments_enabled',new.installments_enabled,
        'max_installments',new.max_installments,'locked_by_matrix',new.locked_by_matrix
      )
    )
  );
  return new;
end;
$$;

drop trigger if exists trg_audit_franchise_city_payment_settings on public.franchise_city_payment_settings;
create trigger trg_audit_franchise_city_payment_settings
after insert or update on public.franchise_city_payment_settings
for each row execute function public.log_franchise_city_payment_settings();

drop policy if exists franchise_city_payment_settings_franchise_all on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_matrix on public.franchise_city_payment_settings;
drop policy if exists franchise_city_payment_settings_read on public.franchise_city_payment_settings;
drop policy if exists operator_payment_settings_select on public.franchise_city_payment_settings;
drop policy if exists operator_payment_settings_write on public.franchise_city_payment_settings;

create policy franchise_city_payment_settings_read
on public.franchise_city_payment_settings for select to authenticated
using (
  public.current_profile_matches_role('super_admin')
  or (public.current_profile_matches_role('franchise_admin') and franchise_id=public.current_profile_franchise_id())
  or (public.current_profile_matches_role('operator') and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and public.can_access_city(city_id))
);

create policy franchise_city_payment_settings_matrix_insert
on public.franchise_city_payment_settings for insert to authenticated
with check (
  public.current_profile_matches_role('super_admin')
  and exists(select 1 from public.franchise_cities fc where fc.franchise_id=franchise_id and fc.city_id=city_id)
);

create policy franchise_city_payment_settings_matrix_update
on public.franchise_city_payment_settings for update to authenticated
using (public.current_profile_matches_role('super_admin'))
with check (
  public.current_profile_matches_role('super_admin')
  and exists(select 1 from public.franchise_cities fc where fc.franchise_id=franchise_id and fc.city_id=city_id)
);

create policy franchise_city_payment_settings_franchise_insert
on public.franchise_city_payment_settings for insert to authenticated
with check (
  public.current_profile_matches_role('franchise_admin')
  and franchise_id=public.current_profile_franchise_id()
  and public.can_access_city(city_id)
  and not locked_by_matrix
  and exists(select 1 from public.platform_payment_settings g where g.scope='global' and g.franchise_can_manage)
);

create policy franchise_city_payment_settings_franchise_update
on public.franchise_city_payment_settings for update to authenticated
using (
  public.current_profile_matches_role('franchise_admin')
  and franchise_id=public.current_profile_franchise_id()
  and public.can_access_city(city_id)
  and not locked_by_matrix
  and exists(select 1 from public.platform_payment_settings g where g.scope='global' and g.franchise_can_manage)
)
with check (
  public.current_profile_matches_role('franchise_admin')
  and franchise_id=public.current_profile_franchise_id()
  and public.can_access_city(city_id)
  and not locked_by_matrix
  and exists(select 1 from public.platform_payment_settings g where g.scope='global' and g.franchise_can_manage)
);

create policy franchise_city_payment_settings_operator_insert
on public.franchise_city_payment_settings for insert to authenticated
with check (
  public.current_profile_matches_role('operator')
  and franchise_id=public.staff_franchise_id()
  and public.staff_has_permission('finance')
  and public.can_access_city(city_id)
  and not locked_by_matrix
  and exists(select 1 from public.platform_payment_settings g where g.scope='global' and g.franchise_can_manage)
);

create policy franchise_city_payment_settings_operator_update
on public.franchise_city_payment_settings for update to authenticated
using (
  public.current_profile_matches_role('operator')
  and franchise_id=public.staff_franchise_id()
  and public.staff_has_permission('finance')
  and public.can_access_city(city_id)
  and not locked_by_matrix
  and exists(select 1 from public.platform_payment_settings g where g.scope='global' and g.franchise_can_manage)
)
with check (
  public.current_profile_matches_role('operator')
  and franchise_id=public.staff_franchise_id()
  and public.staff_has_permission('finance')
  and public.can_access_city(city_id)
  and not locked_by_matrix
  and exists(select 1 from public.platform_payment_settings g where g.scope='global' and g.franchise_can_manage)
);

revoke all on table public.franchise_city_payment_settings from anon;
revoke all on table public.franchise_city_payment_settings from authenticated;
grant select,insert,update on table public.franchise_city_payment_settings to authenticated;
