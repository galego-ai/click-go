create or replace function public.apply_ride_cancellation_fee()
returns trigger
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_cancel_fee numeric:=0;
  v_wait_fee numeric:=0;
  v_total numeric:=0;
  v_free integer:=coalesce(old.cancellation_free_seconds,120);
  v_arrived timestamptz:=coalesce(old.arrived_at,old.driver_departed_at);
  v_eligible boolean:=false;
  v_wait_seconds integer:=0;
  v_wait_minutes integer:=0;
  v_settings public.financial_settings%rowtype;
  v_driver numeric:=0;
  v_franchise numeric:=0;
  v_platform numeric:=0;
begin
  if new.status::text='cancelled'
     and old.status::text in ('accepted','driver_arriving')
     and coalesce(old.cancellation_fee_applied,false)=false then
    if old.status::text='driver_arriving' and v_arrived is not null then
      v_eligible:=now() >= v_arrived + make_interval(secs=>v_free);
      v_wait_seconds:=greatest(0,floor(extract(epoch from (now()-v_arrived)))::integer-coalesce(old.wait_free_seconds,0));
      v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;
      v_wait_fee:=round((v_wait_minutes*coalesce(old.wait_fee_per_minute,0))::numeric,2);
    end if;
    if v_eligible then
      v_cancel_fee:=greatest(coalesce(old.cancellation_policy_fee,0),0);
      if v_cancel_fee=0 then select coalesce(c.cancellation_fee,0) into v_cancel_fee from public.ride_categories c where c.id=old.category_id limit 1; end if;
    end if;
    v_total:=round((coalesce(v_cancel_fee,0)+coalesce(v_wait_fee,0))::numeric,2);
    new.wait_charge_amount:=greatest(coalesce(v_wait_fee,0),0);
    new.cancellation_fee_applied:=v_total>0;
    new.cancellation_fee_amount:=case when v_total>0 then v_total else 0 end;
    if v_total>0 then
      select * into v_settings from public.financial_settings order by updated_at desc limit 1;
      v_driver:=round(v_total*coalesce(v_settings.driver_share_percentage,0)/100,2);
      v_franchise:=round(v_total*coalesce(v_settings.franchise_share_percentage,0)/100,2);
      v_platform:=round(v_total*coalesce(v_settings.platform_share_percentage,0)/100,2);
      insert into public.passenger_charges(passenger_id,franchise_id,city_id,source_ride_id,source_driver_id,charge_type,amount,status,driver_share_amount,franchise_share_amount,platform_share_amount,metadata)
      values(old.passenger_id,old.franchise_id,old.city_id,old.id,old.driver_id,'cancellation_fee',v_total,'pending',v_driver,v_franchise,v_platform,
        jsonb_build_object('deferred_to_next_ride',true,'arrived_at',v_arrived,'cancellation_free_seconds',v_free,'policy_cancellation_fee_amount',round(coalesce(v_cancel_fee,0)::numeric,2),'waiting_fee_amount',round(coalesce(v_wait_fee,0)::numeric,2),'waiting_billable_minutes',v_wait_minutes,'wait_free_seconds',coalesce(old.wait_free_seconds,0),'wait_fee_per_minute',coalesce(old.wait_fee_per_minute,0),'driver_share_percentage',coalesce(v_settings.driver_share_percentage,0),'franchise_share_percentage',coalesce(v_settings.franchise_share_percentage,0),'platform_share_percentage',coalesce(v_settings.platform_share_percentage,0)))
      on conflict(source_ride_id,charge_type) do nothing;
    end if;
  end if;
  return new;
end;
$$;

create or replace function public.preview_passenger_ride_cancellation(p_ride_id uuid)
returns jsonb language plpgsql security definer set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();v_ride public.rides%rowtype;v_arrived timestamptz;v_cancel_fee numeric:=0;v_wait_fee numeric:=0;v_total numeric:=0;v_remaining integer:=0;v_fee_applies boolean:=false;v_wait_seconds integer:=0;v_wait_minutes integer:=0;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ride from public.rides where id=p_ride_id and passenger_id=v_uid;if not found then raise exception 'Corrida não encontrada'; end if;
  if v_ride.status not in ('requested','searching','accepted','driver_arriving') then raise exception 'Esta corrida não pode mais ser cancelada'; end if;
  v_arrived:=coalesce(v_ride.arrived_at,v_ride.driver_departed_at);
  if v_ride.status='driver_arriving' and v_arrived is not null then
    v_remaining:=greatest(0,ceil(extract(epoch from (v_arrived+make_interval(secs=>coalesce(v_ride.cancellation_free_seconds,120))-now())))::integer);
    v_fee_applies:=v_remaining=0;
    v_wait_seconds:=greatest(0,floor(extract(epoch from (now()-v_arrived)))::integer-coalesce(v_ride.wait_free_seconds,0));
    v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;
    v_wait_fee:=round((v_wait_minutes*coalesce(v_ride.wait_fee_per_minute,0))::numeric,2);
  end if;
  if v_fee_applies then
    v_cancel_fee:=greatest(coalesce(v_ride.cancellation_policy_fee,0),0);
    if v_cancel_fee=0 then select coalesce(c.cancellation_fee,0) into v_cancel_fee from public.ride_categories c where c.id=v_ride.category_id limit 1; end if;
  end if;
  v_total:=round((coalesce(v_cancel_fee,0)+coalesce(v_wait_fee,0))::numeric,2);
  return jsonb_build_object('can_cancel',true,'requires_confirmation',v_total>0,'cancellation_fee_amount',v_total,'policy_cancellation_fee_amount',round(coalesce(v_cancel_fee,0)::numeric,2),'wait_charge_amount',round(coalesce(v_wait_fee,0)::numeric,2),'waiting_billable_minutes',v_wait_minutes,'total_charge_amount',v_total,'remaining_free_seconds',v_remaining,'fee_deferred_to_next_ride',v_total>0,'driver_id',v_ride.driver_id);
end;
$$;

create or replace function public.cancel_passenger_ride(p_ride_id uuid,p_confirm_fee boolean default false)
returns jsonb language plpgsql security definer set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();v_ride public.rides%rowtype;v_pending numeric:=0;v_arrived timestamptz;v_cancel_fee numeric:=0;v_wait_fee numeric:=0;v_total numeric:=0;v_fee_applies boolean:=false;v_wait_seconds integer:=0;v_wait_minutes integer:=0;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ride from public.rides where id=p_ride_id and passenger_id=v_uid for update;if not found then raise exception 'Corrida não encontrada'; end if;
  if v_ride.status not in ('requested','searching','accepted','driver_arriving') then raise exception 'Esta corrida não pode mais ser cancelada'; end if;
  v_arrived:=coalesce(v_ride.arrived_at,v_ride.driver_departed_at);
  if v_ride.status='driver_arriving' and v_arrived is not null then
    v_fee_applies:=now() >= v_arrived+make_interval(secs=>coalesce(v_ride.cancellation_free_seconds,120));
    v_wait_seconds:=greatest(0,floor(extract(epoch from (now()-v_arrived)))::integer-coalesce(v_ride.wait_free_seconds,0));
    v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;
    v_wait_fee:=round((v_wait_minutes*coalesce(v_ride.wait_fee_per_minute,0))::numeric,2);
  end if;
  if v_fee_applies then
    v_cancel_fee:=greatest(coalesce(v_ride.cancellation_policy_fee,0),0);
    if v_cancel_fee=0 then select coalesce(c.cancellation_fee,0) into v_cancel_fee from public.ride_categories c where c.id=v_ride.category_id limit 1; end if;
  end if;
  v_total:=round((coalesce(v_cancel_fee,0)+coalesce(v_wait_fee,0))::numeric,2);
  if v_total>0 and not coalesce(p_confirm_fee,false) then
    return jsonb_build_object('ok',false,'requires_confirmation',true,'cancellation_fee_amount',v_total,'policy_cancellation_fee_amount',round(coalesce(v_cancel_fee,0)::numeric,2),'wait_charge_amount',round(coalesce(v_wait_fee,0)::numeric,2),'waiting_billable_minutes',v_wait_minutes,'total_charge_amount',v_total,'fee_deferred_to_next_ride',true);
  end if;
  update public.rides set status='cancelled',cancelled_at=now() where id=p_ride_id;
  select * into v_ride from public.rides where id=p_ride_id;
  select coalesce(sum(pc.amount),0) into v_pending from public.passenger_charges pc where pc.passenger_id=v_uid and pc.status='pending';
  return jsonb_build_object('ok',true,'requires_confirmation',false,'ride_id',p_ride_id,'cancellation_fee_applied',v_ride.cancellation_fee_applied,'cancellation_fee_amount',v_ride.cancellation_fee_amount,'policy_cancellation_fee_amount',round(coalesce(v_cancel_fee,0)::numeric,2),'wait_charge_amount',v_ride.wait_charge_amount,'waiting_billable_minutes',v_wait_minutes,'total_charge_amount',v_ride.cancellation_fee_amount,'fee_deferred_to_next_ride',v_ride.cancellation_fee_applied,'pending_next_ride_charges',round(v_pending::numeric,2),'free_seconds',v_ride.cancellation_free_seconds,'arrived_at',v_ride.arrived_at);
end;
$$;

revoke all on function public.preview_passenger_ride_cancellation(uuid) from public,anon;
revoke all on function public.cancel_passenger_ride(uuid,boolean) from public,anon;
grant execute on function public.preview_passenger_ride_cancellation(uuid) to authenticated;
grant execute on function public.cancel_passenger_ride(uuid,boolean) to authenticated;

-- Backward compatibility: existing cancellation UI also reads driver_departed_at.
-- From this version on, it is synchronized to the real pickup arrival event.
create or replace function public.advance_driver_ride(p_ride_id uuid,p_action text)
returns jsonb language plpgsql security definer set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();v_ride public.rides%rowtype;v_next public.ride_status;v_commission numeric:=0;v_ride_fee numeric:=0;v_cancel_collection numeric:=0;v_balance numeric:=null;
  v_loc public.driver_locations%rowtype;v_tolerance integer:=300;v_wait_fee numeric:=0.50;v_wait_seconds integer:=0;v_wait_minutes integer:=0;v_wait_charge numeric:=0;v_now timestamptz:=now();
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ride from public.rides where id=p_ride_id and driver_id=v_uid for update;if not found then raise exception 'Corrida não encontrada para este motorista'; end if;
  select * into v_loc from public.driver_locations where driver_id=v_uid;
  if p_action='arrived' and v_ride.status='accepted' then v_next:='driver_arriving';select coalesce(rc.wait_tolerance_minutes,5)*60,coalesce(rc.waiting_fee_per_minute,0.50) into v_tolerance,v_wait_fee from public.ride_categories rc where rc.id=v_ride.category_id;
  elsif p_action='start' and v_ride.status='driver_arriving' then v_next:='in_progress';v_wait_seconds:=greatest(0,floor(extract(epoch from (v_now-coalesce(v_ride.arrived_at,v_now))))::integer-coalesce(v_ride.wait_free_seconds,300));v_wait_minutes:=case when v_wait_seconds>0 then ceil(v_wait_seconds/60.0)::integer else 0 end;v_wait_charge:=round((v_wait_minutes*coalesce(v_ride.wait_fee_per_minute,0))::numeric,2);
  elsif p_action='complete' and v_ride.status='in_progress' then if lower(coalesce(v_ride.payment_method_preference,''))='card_machine' and not exists(select 1 from public.payments where ride_id=p_ride_id and method='card_machine' and status='paid') then raise exception 'Confirme o recebimento na maquininha antes de concluir'; end if;v_next:='completed';
  else raise exception 'Transição de corrida inválida';end if;
  update public.rides set status=v_next,arrived_at=case when v_next='driver_arriving' then coalesce(arrived_at,v_now) else arrived_at end,driver_departed_at=case when v_next='driver_arriving' then coalesce(driver_departed_at,v_now) else driver_departed_at end,arrived_lat=case when v_next='driver_arriving' then coalesce(v_loc.lat,arrived_lat) else arrived_lat end,arrived_lng=case when v_next='driver_arriving' then coalesce(v_loc.lng,arrived_lng) else arrived_lng end,wait_free_seconds=case when v_next='driver_arriving' then v_tolerance else wait_free_seconds end,wait_fee_per_minute=case when v_next='driver_arriving' then v_wait_fee else wait_fee_per_minute end,wait_charge_amount=case when v_next='in_progress' then v_wait_charge else wait_charge_amount end,started_at=case when v_next='in_progress' then v_now else started_at end,started_lat=case when v_next='in_progress' then coalesce(v_loc.lat,started_lat) else started_lat end,started_lng=case when v_next='in_progress' then coalesce(v_loc.lng,started_lng) else started_lng end,completed_at=case when v_next='completed' then v_now else completed_at end,completed_lat=case when v_next='completed' then coalesce(v_loc.lat,completed_lat) else completed_lat end,completed_lng=case when v_next='completed' then coalesce(v_loc.lng,completed_lng) else completed_lng end,final_fare=case when v_next='completed' then round((coalesce(final_fare,estimated_fare,0)+coalesce(wait_charge_amount,0))::numeric,2) else final_fare end where id=p_ride_id;
  if v_loc.driver_id is not null then insert into public.ride_location_points(ride_id,driver_id,lat,lng,heading,speed_kmh,phase) values(p_ride_id,v_uid,v_loc.lat,v_loc.lng,v_loc.heading,v_loc.speed_kmh,case p_action when 'arrived' then 'arrived_pickup' when 'start' then 'ride_started' else 'ride_completed' end);end if;
  insert into public.ride_events(ride_id,driver_id,event_type) values(p_ride_id,v_uid,case p_action when 'arrived' then 'driver_arriving' when 'start' then 'ride_started' else 'ride_completed' end);
  if v_next='completed' then select coalesce(sum(amount),0) into v_commission from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='ride_commission' and status='settled';select coalesce(sum(amount),0) into v_ride_fee from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='ride_fee' and status='settled';select coalesce(sum(amount),0) into v_cancel_collection from public.driver_operational_transactions where ride_id=p_ride_id and driver_id=v_uid and source='adjustment' and status='settled' and metadata->>'kind'='passenger_cancellation_collection';select balance into v_balance from public.driver_operational_wallets where driver_id=v_uid;end if;
  return jsonb_build_object('ok',true,'ride_id',p_ride_id,'status',v_next,'payment_method',v_ride.payment_method_preference,'wait_charge_amount',case when v_next='in_progress' then v_wait_charge else coalesce(v_ride.wait_charge_amount,0) end,'direct_collection_commission_debit',v_commission,'per_ride_fee_debit',v_ride_fee,'cancellation_collection_debit',v_cancel_collection,'operational_balance_after',v_balance);
end;
$$;
revoke all on function public.advance_driver_ride(uuid,text) from public,anon;
grant execute on function public.advance_driver_ride(uuid,text) to authenticated;
