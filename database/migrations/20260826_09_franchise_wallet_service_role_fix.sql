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

  if auth.uid() is not null and not public.current_profile_matches_role('super_admin') then
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
