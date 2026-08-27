create or replace function public.franchise_update_operational_wallet_settings(p_wallet jsonb)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid := auth.uid();
  v_role text := public.current_active_management_role();
  v_fid uuid;
  v_global public.platform_operational_wallet_settings%rowtype;
  v_local public.franchise_operational_wallet_settings%rowtype;
  v_mode text;
  v_ride_fee numeric;
  v_percentage numeric;
  v_minimum numeric;
  v_low numeric;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role = 'franchise_admin' then v_fid := public.current_profile_franchise_id();
  elsif v_role = 'operator' and public.staff_has_permission('finance') then v_fid := public.staff_franchise_id();
  else raise exception 'Acesso restrito ao franqueado ou operador financeiro'; end if;
  if v_fid is null or not exists(select 1 from public.franchises f where f.id=v_fid and f.deleted_at is null) then raise exception 'Franquia inválida ou excluída'; end if;
  select * into v_global from public.platform_operational_wallet_settings where scope='global';
  if not found then raise exception 'Configuração global da carteira não encontrada'; end if;
  select * into v_local from public.franchise_operational_wallet_settings where franchise_id=v_fid for update;
  if found and v_local.locked_by_matrix then raise exception 'As regras da carteira desta franquia estão bloqueadas pela Matriz'; end if;
  v_minimum:=coalesce(nullif(p_wallet->>'minimum_balance_to_receive','')::numeric,v_local.minimum_balance_to_receive,v_global.minimum_balance_to_receive);
  v_low:=coalesce(nullif(p_wallet->>'low_balance_threshold','')::numeric,v_local.low_balance_threshold,v_global.low_balance_threshold);
  if v_global.franchise_can_set_ride_fee then
    v_mode:=coalesce(nullif(btrim(p_wallet->>'ride_fee_mode'),''),v_local.ride_fee_mode,v_global.default_ride_fee_mode,'fixed');
    v_ride_fee:=coalesce(nullif(p_wallet->>'ride_fee','')::numeric,v_local.ride_fee,v_global.default_ride_fee);
    v_percentage:=coalesce(nullif(p_wallet->>'ride_fee_percentage','')::numeric,v_local.ride_fee_percentage,v_global.default_ride_fee_percentage);
  else
    v_mode:=coalesce(v_local.ride_fee_mode,v_global.default_ride_fee_mode,'fixed');
    v_ride_fee:=coalesce(v_local.ride_fee,v_global.default_ride_fee);
    v_percentage:=coalesce(v_local.ride_fee_percentage,v_global.default_ride_fee_percentage);
  end if;
  if v_mode not in ('fixed','percentage') then raise exception 'Modo de taxa inválido'; end if;
  if v_ride_fee<0 then raise exception 'Taxa fixa não pode ser negativa'; end if;
  if v_percentage<0 or v_percentage>100 then raise exception 'Percentual deve ficar entre 0 e 100'; end if;
  if v_minimum<0 or v_low<0 then raise exception 'Valores da carteira não podem ser negativos'; end if;
  insert into public.franchise_operational_wallet_settings(franchise_id,ride_fee_mode,ride_fee,ride_fee_percentage,minimum_balance_to_receive,low_balance_threshold,locked_by_matrix,updated_by,updated_at)
  values(v_fid,v_mode,v_ride_fee,v_percentage,v_minimum,v_low,false,v_uid,now())
  on conflict(franchise_id) do update set ride_fee_mode=excluded.ride_fee_mode,ride_fee=excluded.ride_fee,ride_fee_percentage=excluded.ride_fee_percentage,minimum_balance_to_receive=excluded.minimum_balance_to_receive,low_balance_threshold=excluded.low_balance_threshold,updated_by=v_uid,updated_at=now();
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'franchise_update_operational_wallet_settings','franchise_operational_wallet_settings',v_fid::text,jsonb_build_object('franchise_id',v_fid,'source_role',v_role,'ride_fee_edit_allowed',v_global.franchise_can_set_ride_fee,'ride_fee_mode',v_mode));
  return jsonb_build_object('ok',true,'franchise_id',v_fid,'ride_fee_mode',v_mode,'ride_fee',v_ride_fee,'ride_fee_percentage',v_percentage);
end;
$function$;
revoke all on function public.franchise_update_operational_wallet_settings(jsonb) from public, anon;
grant execute on function public.franchise_update_operational_wallet_settings(jsonb) to authenticated, service_role;