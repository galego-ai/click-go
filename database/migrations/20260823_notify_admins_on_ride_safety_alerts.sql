create or replace function public.notify_admins_on_ride_safety_alert()
returns trigger
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_ride public.rides%rowtype;
  v_title text;
  v_body text;
begin
  select * into v_ride from public.rides where id=new.ride_id;
  if not found then return new; end if;

  if new.alert_type='sos' then
    v_title:='🆘 SOS em corrida CLICK-GO';
    v_body:=format(
      'Alerta crítico na corrida %s. %s → %s. Acionado por: %s.',
      left(new.ride_id::text,8),
      coalesce(v_ride.origin_label,'—'),
      coalesce(v_ride.destination_label,'—'),
      new.reporter_role
    );
  else
    v_title:='⚠️ Possível desvio de rota';
    v_body:=format(
      'Corrida %s desviou aproximadamente %s m da rota planejada. %s → %s.',
      left(new.ride_id::text,8),
      coalesce(round(new.distance_from_route_m),0),
      coalesce(v_ride.origin_label,'—'),
      coalesce(v_ride.destination_label,'—')
    );
  end if;

  insert into public.admin_notifications(type,title,body,profile_id,driver_id,city_id,franchise_id)
  values(
    case when new.alert_type='sos' then 'safety_sos' else 'safety_route_deviation' end,
    v_title,
    v_body,
    new.reporter_id,
    v_ride.driver_id,
    v_ride.city_id,
    v_ride.franchise_id
  );

  return new;
end;
$$;

revoke all on function public.notify_admins_on_ride_safety_alert() from public,anon,authenticated;

drop trigger if exists trg_notify_admins_on_ride_safety_alert on public.ride_safety_alerts;
create trigger trg_notify_admins_on_ride_safety_alert
after insert on public.ride_safety_alerts
for each row execute function public.notify_admins_on_ride_safety_alert();
