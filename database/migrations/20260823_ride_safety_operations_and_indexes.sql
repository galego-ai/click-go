create index if not exists ride_security_passenger_idx on public.ride_security(passenger_id);
create index if not exists ride_security_verified_by_idx on public.ride_security(pin_verified_by) where pin_verified_by is not null;
create index if not exists ride_safety_alerts_reporter_idx on public.ride_safety_alerts(reporter_id) where reporter_id is not null;

create or replace function public.get_operation_safety_alerts(p_status text default 'open', p_limit integer default 100)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text;
  v_franchise uuid;
  v_result jsonb;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select p.role::text,p.franchise_id into v_role,v_franchise from public.profiles p where p.id=v_uid;
  if coalesce(public.jwt_app_role(),'')='super_admin' then v_role:='super_admin'; end if;
  if v_role not in ('franchise_admin','super_admin') then raise exception 'Acesso exclusivo da operação'; end if;
  select coalesce(jsonb_agg(x.obj order by x.created_at desc),'[]'::jsonb) into v_result
  from (
    select a.created_at,
      jsonb_build_object(
        'id',a.id,'ride_id',a.ride_id,'alert_type',a.alert_type,'severity',a.severity,'reporter_role',a.reporter_role,
        'lat',a.lat,'lng',a.lng,'distance_from_route_m',a.distance_from_route_m,'message',a.message,'status',a.status,
        'created_at',a.created_at,'resolved_at',a.resolved_at,
        'ride_status',r.status::text,'origin_label',r.origin_label,'destination_label',r.destination_label,
        'passenger_name',pp.full_name,'driver_name',dp.full_name,'franchise_id',r.franchise_id,'city_id',r.city_id
      ) as obj
    from public.ride_safety_alerts a
    join public.rides r on r.id=a.ride_id
    left join public.profiles pp on pp.id=r.passenger_id
    left join public.profiles dp on dp.id=r.driver_id
    where (p_status is null or p_status='all' or a.status=p_status)
      and (v_role='super_admin' or r.franchise_id=v_franchise)
    order by a.created_at desc
    limit greatest(1,least(coalesce(p_limit,100),500))
  ) x;
  return v_result;
end;
$$;
revoke all on function public.get_operation_safety_alerts(text,integer) from public,anon;
grant execute on function public.get_operation_safety_alerts(text,integer) to authenticated;

create or replace function public.resolve_ride_safety_alert(p_alert_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text;
  v_franchise uuid;
  v_alert public.ride_safety_alerts%rowtype;
  v_ride public.rides%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select p.role::text,p.franchise_id into v_role,v_franchise from public.profiles p where p.id=v_uid;
  if coalesce(public.jwt_app_role(),'')='super_admin' then v_role:='super_admin'; end if;
  if v_role not in ('franchise_admin','super_admin') then raise exception 'Acesso exclusivo da operação'; end if;
  select * into v_alert from public.ride_safety_alerts where id=p_alert_id for update;
  if not found then raise exception 'Alerta não encontrado'; end if;
  select * into v_ride from public.rides where id=v_alert.ride_id;
  if v_role<>'super_admin' and v_ride.franchise_id is distinct from v_franchise then raise exception 'Alerta fora da sua franquia'; end if;
  if v_alert.status='resolved' then return jsonb_build_object('ok',true,'already_resolved',true,'resolved_at',v_alert.resolved_at); end if;
  update public.ride_safety_alerts set status='resolved',resolved_at=now() where id=p_alert_id;
  insert into public.ride_events(ride_id,driver_id,event_type,metadata)
    values(v_alert.ride_id,v_ride.driver_id,'safety_alert_resolved',jsonb_build_object('alert_id',p_alert_id,'resolved_by',v_uid,'resolved_role',v_role));
  return jsonb_build_object('ok',true,'already_resolved',false,'resolved_at',now());
end;
$$;
revoke all on function public.resolve_ride_safety_alert(uuid) from public,anon;
grant execute on function public.resolve_ride_safety_alert(uuid) to authenticated;
