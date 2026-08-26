create or replace function public.audit_remote_app_settings_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(
    auth.uid(),
    'matrix_update_remote_app_settings',
    'remote_app_settings',
    new.id::text,
    jsonb_build_object(
      'scope',new.scope,
      'city_id',new.city_id,
      'franchise_id',new.franchise_id,
      'before',jsonb_build_object(
        'auto_cancel_unaccepted_minutes',old.auto_cancel_unaccepted_minutes,
        'taximeter_refresh_seconds',old.taximeter_refresh_seconds,
        'max_pickup_radius_km',old.max_pickup_radius_km,
        'taximeter_enabled',old.taximeter_enabled,
        'allow_scheduled_rides',old.allow_scheduled_rides
      ),
      'after',jsonb_build_object(
        'auto_cancel_unaccepted_minutes',new.auto_cancel_unaccepted_minutes,
        'taximeter_refresh_seconds',new.taximeter_refresh_seconds,
        'max_pickup_radius_km',new.max_pickup_radius_km,
        'taximeter_enabled',new.taximeter_enabled,
        'allow_scheduled_rides',new.allow_scheduled_rides
      )
    )
  );
  return new;
end;
$$;

drop trigger if exists trg_audit_remote_app_settings_update on public.remote_app_settings;
create trigger trg_audit_remote_app_settings_update
after update on public.remote_app_settings
for each row execute function public.audit_remote_app_settings_update();

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
  v_after public.remote_app_settings%rowtype;
begin
  if not public.current_profile_matches_role('super_admin') then
    raise exception 'Acesso restrito à Matriz';
  end if;

  update public.remote_app_settings
  set auto_cancel_unaccepted_minutes=p_auto_cancel_unaccepted_minutes,
      taximeter_refresh_seconds=p_taximeter_refresh_seconds,
      max_pickup_radius_km=p_max_pickup_radius_km,
      taximeter_enabled=p_taximeter_enabled,
      allow_scheduled_rides=coalesce(p_allow_scheduled_rides,allow_scheduled_rides),
      updated_at=now()
  where scope='global' and city_id is null and franchise_id is null
  returning * into v_after;

  if not found then
    raise exception 'Configuração global não encontrada';
  end if;

  return v_after;
end;
$$;

revoke all on function public.matrix_update_remote_app_settings(integer,integer,numeric,boolean,boolean) from public;
grant execute on function public.matrix_update_remote_app_settings(integer,integer,numeric,boolean,boolean) to authenticated,service_role;

drop policy if exists super_admin_remote_settings_all on public.remote_app_settings;
drop policy if exists super_admin_remote_settings_update on public.remote_app_settings;
create policy super_admin_remote_settings_update
on public.remote_app_settings
for update
to authenticated
using (public.current_profile_matches_role('super_admin'))
with check (public.current_profile_matches_role('super_admin'));

revoke all on table public.remote_app_settings from anon;
revoke all on table public.remote_app_settings from authenticated;
grant select,update on table public.remote_app_settings to authenticated;
