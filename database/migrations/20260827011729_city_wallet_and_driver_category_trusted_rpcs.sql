create or replace function public.set_city_cash_negative_limit(p_franchise_id uuid,p_city_id uuid,p_cash_negative_limit numeric)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_scope_fid uuid;
  v_limit numeric(10,2);
  v_existing public.city_operational_wallet_settings%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='super_admin' then v_scope_fid:=p_franchise_id;
  elsif v_role='franchise_admin' then v_scope_fid:=public.current_profile_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('finance') then v_scope_fid:=public.staff_franchise_id();
  else raise exception 'Sem permissão para alterar limite de dinheiro'; end if;
  if p_franchise_id is null or p_city_id is null or v_scope_fid is null then raise exception 'Franquia/cidade inválida'; end if;
  if v_role<>'super_admin' and p_franchise_id is distinct from v_scope_fid then raise exception 'Franquia fora do seu escopo'; end if;
  v_limit:=round(coalesce(p_cash_negative_limit,0)::numeric,2);
  if v_limit>0 or v_limit<-1000 then raise exception 'O limite para dinheiro deve ficar entre R$ 0,00 e -R$ 1.000,00'; end if;
  if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=p_franchise_id and fc.city_id=p_city_id) then raise exception 'Cidade não pertence à franquia'; end if;
  if v_role<>'super_admin' and not public.can_access_city(p_city_id) then raise exception 'Cidade fora da sua região'; end if;
  select * into v_existing from public.city_operational_wallet_settings where franchise_id=p_franchise_id and city_id=p_city_id for update;
  if found and v_role<>'super_admin' and coalesce(v_existing.locked_by_matrix,false) then raise exception 'A Matriz bloqueou a configuração desta cidade'; end if;
  insert into public.city_operational_wallet_settings(franchise_id,city_id,cash_negative_limit,locked_by_matrix,updated_by,updated_at)
  values(p_franchise_id,p_city_id,v_limit,coalesce(v_existing.locked_by_matrix,false),v_uid,now())
  on conflict(franchise_id,city_id) do update set cash_negative_limit=excluded.cash_negative_limit,updated_by=excluded.updated_by,updated_at=now();
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'city_cash_negative_limit_updated','city',p_city_id::text,jsonb_build_object('franchise_id',p_franchise_id,'cash_negative_limit',v_limit,'source_role',v_role));
  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'city_id',p_city_id,'cash_negative_limit',v_limit);
end;
$function$;

create or replace function public.franchise_set_driver_category(p_driver_id uuid,p_category_id uuid,p_enabled boolean)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_city uuid;
  v_vehicle public.vehicles%rowtype;
  v_category public.ride_categories%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='franchise_admin' then v_fid:=public.current_profile_franchise_id();
  elsif v_role='operator' and public.staff_has_permission('drivers') then v_fid:=public.staff_franchise_id();
  else raise exception 'Acesso restrito ao franqueado ou operador de motoristas'; end if;
  if v_fid is null then raise exception 'Franquia não identificada'; end if;
  select d.city_id into v_city from public.drivers d where d.id=p_driver_id and d.franchise_id=v_fid;
  if v_city is null then raise exception 'Motorista fora da sua franquia'; end if;
  if not public.can_access_city(v_city) then raise exception 'Motorista fora da sua cidade/região'; end if;
  select * into v_category from public.ride_categories rc where rc.id=p_category_id and rc.franchise_id=v_fid and rc.city_id=v_city;
  if not found then raise exception 'Categoria não pertence à operação do motorista'; end if;
  select * into v_vehicle from public.vehicles v where v.driver_id=p_driver_id and v.active=true order by v.created_at desc limit 1;
  if not found then raise exception 'Motorista sem veículo ativo'; end if;
  if coalesce(p_enabled,false) then
    if v_vehicle.vehicle_type is null or v_vehicle.vehicle_type not in ('car','motorcycle') then raise exception 'Defina primeiro se o veículo é Carro ou Moto'; end if;
    if v_category.required_vehicle_type is not null and v_category.required_vehicle_type<>v_vehicle.vehicle_type then raise exception 'Categoria incompatível com o tipo de veículo'; end if;
  end if;
  insert into public.driver_category_eligibility(driver_id,category_id,vehicle_id,active,approved_at)
  values(p_driver_id,p_category_id,v_vehicle.id,coalesce(p_enabled,false),case when p_enabled then now() else null end)
  on conflict(driver_id,category_id) do update set vehicle_id=excluded.vehicle_id,active=excluded.active,approved_at=excluded.approved_at;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'driver_category_eligibility_updated','driver',p_driver_id::text,jsonb_build_object('category_id',p_category_id,'enabled',coalesce(p_enabled,false),'franchise_id',v_fid,'city_id',v_city,'source_role',v_role));
  return jsonb_build_object('ok',true,'enabled',coalesce(p_enabled,false));
end;
$function$;

revoke all on function public.set_city_cash_negative_limit(uuid,uuid,numeric) from public, anon;
grant execute on function public.set_city_cash_negative_limit(uuid,uuid,numeric) to authenticated, service_role;
revoke all on function public.franchise_set_driver_category(uuid,uuid,boolean) from public, anon;
grant execute on function public.franchise_set_driver_category(uuid,uuid,boolean) to authenticated, service_role;

revoke insert,update,delete,truncate on table public.city_operational_wallet_settings from anon,authenticated;
revoke all on table public.city_operational_wallet_settings from anon;
grant select on table public.city_operational_wallet_settings to authenticated;
drop policy if exists city_wallet_settings_super_admin_all on public.city_operational_wallet_settings;
drop policy if exists city_wallet_settings_select on public.city_operational_wallet_settings;
create policy city_wallet_settings_select on public.city_operational_wallet_settings
for select to authenticated using (
  public.current_active_management_role()='super_admin'
  or (public.current_active_management_role()='franchise_admin' and franchise_id=public.current_profile_franchise_id() and public.can_access_city(city_id))
  or (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and public.can_access_city(city_id))
);

revoke insert,update,delete,truncate on table public.driver_category_eligibility from anon,authenticated;
revoke all on table public.driver_category_eligibility from anon;
grant select on table public.driver_category_eligibility to authenticated;