create or replace function public.matrix_update_remote_app_settings(
  p_auto_cancel_unaccepted_minutes integer,
  p_taximeter_refresh_seconds integer,
  p_max_pickup_radius_km numeric,
  p_taximeter_enabled boolean,
  p_allow_scheduled_rides boolean default null
)
returns public.remote_app_settings
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_before public.remote_app_settings%rowtype;
  v_after public.remote_app_settings%rowtype;
begin
  if not public.current_profile_matches_role('super_admin') then
    raise exception 'Acesso restrito à Matriz';
  end if;

  select * into v_before
  from public.remote_app_settings
  where scope='global' and city_id is null and franchise_id is null
  for update;

  if not found then
    raise exception 'Configuração global não encontrada';
  end if;

  update public.remote_app_settings
  set auto_cancel_unaccepted_minutes=p_auto_cancel_unaccepted_minutes,
      taximeter_refresh_seconds=p_taximeter_refresh_seconds,
      max_pickup_radius_km=p_max_pickup_radius_km,
      taximeter_enabled=p_taximeter_enabled,
      allow_scheduled_rides=coalesce(p_allow_scheduled_rides,allow_scheduled_rides),
      updated_at=now()
  where id=v_before.id
  returning * into v_after;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    'matrix_update_remote_app_settings',
    'remote_app_settings',
    v_after.id::text,
    jsonb_build_object(
      'before',jsonb_build_object(
        'auto_cancel_unaccepted_minutes',v_before.auto_cancel_unaccepted_minutes,
        'taximeter_refresh_seconds',v_before.taximeter_refresh_seconds,
        'max_pickup_radius_km',v_before.max_pickup_radius_km,
        'taximeter_enabled',v_before.taximeter_enabled,
        'allow_scheduled_rides',v_before.allow_scheduled_rides
      ),
      'after',jsonb_build_object(
        'auto_cancel_unaccepted_minutes',v_after.auto_cancel_unaccepted_minutes,
        'taximeter_refresh_seconds',v_after.taximeter_refresh_seconds,
        'max_pickup_radius_km',v_after.max_pickup_radius_km,
        'taximeter_enabled',v_after.taximeter_enabled,
        'allow_scheduled_rides',v_after.allow_scheduled_rides
      )
    )
  );

  return v_after;
end;
$$;

revoke all on function public.matrix_update_remote_app_settings(integer,integer,numeric,boolean,boolean) from public;
grant execute on function public.matrix_update_remote_app_settings(integer,integer,numeric,boolean,boolean) to authenticated,service_role;
