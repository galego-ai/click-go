create or replace function public.stamp_franchise_operational_wallet_settings()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_can_set_fee boolean;
begin
  if tg_op='UPDATE' then new.franchise_id:=old.franchise_id; end if;

  if not public.current_profile_matches_role('super_admin') then
    select g.franchise_can_set_ride_fee into v_can_set_fee
    from public.platform_operational_wallet_settings g where g.scope='global';
    if not coalesce(v_can_set_fee,false) then
      if tg_op='UPDATE' then
        new.ride_fee:=old.ride_fee;
        new.ride_fee_mode:=old.ride_fee_mode;
        new.ride_fee_percentage:=old.ride_fee_percentage;
      else
        new.ride_fee:=null;
        new.ride_fee_mode:=null;
        new.ride_fee_percentage:=null;
      end if;
    end if;
  end if;

  new.updated_by:=coalesce(auth.uid(),new.updated_by);
  new.updated_at:=now();
  return new;
end;
$$;

drop trigger if exists trg_stamp_franchise_operational_wallet_settings on public.franchise_operational_wallet_settings;
create trigger trg_stamp_franchise_operational_wallet_settings
before insert or update on public.franchise_operational_wallet_settings
for each row execute function public.stamp_franchise_operational_wallet_settings();

create or replace function public.log_franchise_operational_wallet_settings()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    case when tg_op='INSERT' then 'create_franchise_operational_wallet_settings' else 'update_franchise_operational_wallet_settings' end,
    'franchise_operational_wallet_settings',
    new.franchise_id::text,
    jsonb_build_object(
      'franchise_id',new.franchise_id,
      'before',case when tg_op='UPDATE' then jsonb_build_object(
        'ride_fee',old.ride_fee,'ride_fee_mode',old.ride_fee_mode,'ride_fee_percentage',old.ride_fee_percentage,
        'minimum_balance_to_receive',old.minimum_balance_to_receive,'low_balance_threshold',old.low_balance_threshold,
        'locked_by_matrix',old.locked_by_matrix
      ) else null end,
      'after',jsonb_build_object(
        'ride_fee',new.ride_fee,'ride_fee_mode',new.ride_fee_mode,'ride_fee_percentage',new.ride_fee_percentage,
        'minimum_balance_to_receive',new.minimum_balance_to_receive,'low_balance_threshold',new.low_balance_threshold,
        'locked_by_matrix',new.locked_by_matrix
      )
    )
  );
  return new;
end;
$$;

drop trigger if exists trg_audit_franchise_operational_wallet_settings on public.franchise_operational_wallet_settings;
create trigger trg_audit_franchise_operational_wallet_settings
after insert or update on public.franchise_operational_wallet_settings
for each row execute function public.log_franchise_operational_wallet_settings();

drop policy if exists franchise_operational_settings_franchise_update on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_matrix on public.franchise_operational_wallet_settings;
drop policy if exists franchise_operational_settings_read on public.franchise_operational_wallet_settings;
drop policy if exists operator_wallet_settings_select on public.franchise_operational_wallet_settings;
drop policy if exists operator_wallet_settings_write on public.franchise_operational_wallet_settings;

create policy franchise_operational_settings_read
on public.franchise_operational_wallet_settings for select to authenticated
using (
  public.current_profile_matches_role('super_admin')
  or (public.current_profile_matches_role('franchise_admin') and franchise_id=public.current_profile_franchise_id())
  or (public.current_profile_matches_role('operator') and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'))
);

create policy franchise_operational_settings_matrix_insert
on public.franchise_operational_wallet_settings for insert to authenticated
with check (public.current_profile_matches_role('super_admin') and exists(select 1 from public.franchises f where f.id=franchise_id and f.deleted_at is null));

create policy franchise_operational_settings_matrix_update
on public.franchise_operational_wallet_settings for update to authenticated
using (public.current_profile_matches_role('super_admin'))
with check (public.current_profile_matches_role('super_admin') and exists(select 1 from public.franchises f where f.id=franchise_id and f.deleted_at is null));

create policy franchise_operational_settings_franchise_insert
on public.franchise_operational_wallet_settings for insert to authenticated
with check (
  public.current_profile_matches_role('franchise_admin')
  and franchise_id=public.current_profile_franchise_id()
  and not locked_by_matrix
);

create policy franchise_operational_settings_franchise_update
on public.franchise_operational_wallet_settings for update to authenticated
using (public.current_profile_matches_role('franchise_admin') and franchise_id=public.current_profile_franchise_id() and not locked_by_matrix)
with check (public.current_profile_matches_role('franchise_admin') and franchise_id=public.current_profile_franchise_id() and not locked_by_matrix);

create policy franchise_operational_settings_operator_insert
on public.franchise_operational_wallet_settings for insert to authenticated
with check (public.current_profile_matches_role('operator') and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix);

create policy franchise_operational_settings_operator_update
on public.franchise_operational_wallet_settings for update to authenticated
using (public.current_profile_matches_role('operator') and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix)
with check (public.current_profile_matches_role('operator') and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix);

revoke all on table public.franchise_operational_wallet_settings from anon;
revoke all on table public.franchise_operational_wallet_settings from authenticated;
grant select,insert,update on table public.franchise_operational_wallet_settings to authenticated;
