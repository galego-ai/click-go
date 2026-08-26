create or replace function public.get_app_configuration_state(p_franchise_id uuid default null::uuid,p_city_id uuid default null::uuid)
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
 v_franchise uuid:=p_franchise_id;
 v_state public.configuration_sync_state%rowtype;
 v_result jsonb;
 v_overdue integer:=0;
 v_restrict_drivers integer:=5;
 v_block_rides integer:=10;
 v_suspend integer:=30;
 v_override_until date;
 v_override boolean:=false;
begin
 if auth.uid() is null then raise exception 'Não autenticado'; end if;
 if v_franchise is null and p_city_id is not null then
   select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=p_city_id limit 1;
 end if;
 if v_franchise is null then
   return jsonb_build_object('version',0,'license_status','active','operation_enabled',true,'allow_new_drivers',true,'allow_new_rides',true,'operation_suspended',false,'features','{}'::jsonb,'settings','{}'::jsonb,'categories','[]'::jsonb,'banners','[]'::jsonb);
 end if;

 select * into v_state from public.configuration_sync_state where scope_key=v_franchise::text;
 select coalesce(max(current_date-due_date),0)::int into v_overdue
 from public.franchise_invoices
 where franchise_id=v_franchise and status not in ('paid','cancelled') and due_date<current_date;
 select coalesce(restrict_new_drivers_after_days,5),coalesce(block_new_rides_after_days,10),coalesce(suspend_operation_after_days,30),manual_override_until
 into v_restrict_drivers,v_block_rides,v_suspend,v_override_until
 from public.franchise_collection_rules where franchise_id=v_franchise;
 v_restrict_drivers:=coalesce(v_restrict_drivers,5);v_block_rides:=coalesce(v_block_rides,10);v_suspend:=coalesce(v_suspend,30);
 v_override:=v_override_until is not null and v_override_until>=current_date;

 select jsonb_build_object(
   'franchise_id',f.id,
   'version',coalesce(v_state.version,0),
   'changed_at',v_state.last_change_at,
   'license_status',f.license_status,
   'operation_enabled',(f.active and f.license_status not in ('suspended','cancelled') and (v_override or v_overdue<=v_block_rides)),
   'allow_new_drivers',(f.active and f.license_status not in ('suspended','cancelled') and (v_override or v_overdue<=v_restrict_drivers)),
   'allow_new_rides',(f.active and f.license_status not in ('suspended','cancelled') and (v_override or v_overdue<=v_block_rides)),
   'operation_suspended',((not f.active) or f.license_status in ('suspended','cancelled') or (not v_override and v_overdue>v_suspend)),
   'restriction_reason',case
      when not f.active or f.license_status in ('suspended','cancelled') then 'license_suspended'
      when not v_override and v_overdue>v_suspend then 'financial_suspension'
      when not v_override and v_overdue>v_block_rides then 'financial_rides_block'
      when not v_override and v_overdue>v_restrict_drivers then 'financial_driver_restriction'
      else null end,
   'features',coalesce(p.enabled_modules,'{}'::jsonb),
   'settings',coalesce((select jsonb_object_agg(fs.setting_key,fs.setting_value) from public.franchise_settings fs where fs.franchise_id=f.id),'{}'::jsonb),
   'categories',coalesce((select jsonb_agg(jsonb_build_object('id',c.id,'city_id',c.city_id,'name',c.name,'base_fare',c.base_fare,'price_per_km',c.price_per_km,'price_per_minute',c.price_per_minute,'minimum_fare',c.minimum_fare,'cancellation_fee',c.cancellation_fee,'dynamic_multiplier',c.dynamic_multiplier,'vehicle_type',c.required_vehicle_type,'icon_url',c.icon_url,'map_marker_url',c.map_marker_url,'wait_tolerance_minutes',c.wait_tolerance_minutes,'waiting_fee_per_minute',c.waiting_fee_per_minute)) from public.ride_categories c where c.franchise_id=f.id and c.active and (p_city_id is null or c.city_id=p_city_id)),'[]'::jsonb),
   'banners',coalesce((select jsonb_agg(jsonb_build_object('id',b.id,'title',b.title,'image_url',b.image_url,'target_url',b.target_url,'placement',b.placement,'audience',b.audience,'sort_order',b.sort_order)) from public.advertising_banners b where b.franchise_id=f.id and b.active and (p_city_id is null or b.city_id is null or b.city_id=p_city_id) and (b.starts_at is null or b.starts_at<=now()) and (b.ends_at is null or b.ends_at>=now())),'[]'::jsonb),
   'payment_settings',(select to_jsonb(ps)-'updated_by' from public.franchise_city_payment_settings ps where ps.franchise_id=f.id and (p_city_id is null or ps.city_id=p_city_id) order by ps.updated_at desc limit 1)
 ) into v_result
 from public.franchises f
 left join lateral (select fp.* from public.franchise_subscriptions s join public.franchise_plans fp on fp.id=s.plan_id where s.franchise_id=f.id and s.status='active' order by s.starts_at desc limit 1) p on true
 where f.id=v_franchise and f.deleted_at is null;
 return coalesce(v_result,jsonb_build_object('version',0,'operation_enabled',false,'allow_new_drivers',false,'allow_new_rides',false,'operation_suspended',true));
end;
$$;
revoke all on function public.get_app_configuration_state(uuid,uuid) from public,anon;
grant execute on function public.get_app_configuration_state(uuid,uuid) to authenticated;
