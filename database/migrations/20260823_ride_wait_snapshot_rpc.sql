create or replace function public.get_ride_wait_snapshot(p_ride_id uuid)
returns table(
  status text,
  elapsed_seconds integer,
  remaining_free_seconds integer,
  billable_seconds integer,
  billable_minutes integer,
  wait_fee_per_minute numeric,
  live_wait_charge numeric
)
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v public.rides%rowtype;
  v_elapsed integer:=0;
  v_remaining integer:=0;
  v_billable integer:=0;
  v_minutes integer:=0;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v from public.rides where id=p_ride_id;
  if not found then raise exception 'Corrida não encontrada'; end if;
  if v.passenger_id<>v_uid
     and coalesce(v.driver_id,'00000000-0000-0000-0000-000000000000'::uuid)<>v_uid
     and public.jwt_app_role()<>'super_admin' then
    raise exception 'Sem acesso a esta corrida';
  end if;
  if v.status='driver_arriving' and v.arrived_at is not null then
    v_elapsed:=greatest(0,floor(extract(epoch from (now()-v.arrived_at)))::integer);
    v_remaining:=greatest(0,coalesce(v.wait_free_seconds,0)-v_elapsed);
    v_billable:=greatest(0,v_elapsed-coalesce(v.wait_free_seconds,0));
    v_minutes:=case when v_billable>0 then ceil(v_billable/60.0)::integer else 0 end;
  end if;
  return query
  select v.status::text,v_elapsed,v_remaining,v_billable,v_minutes,
         coalesce(v.wait_fee_per_minute,0),
         round((v_minutes*coalesce(v.wait_fee_per_minute,0))::numeric,2);
end;
$$;

revoke all on function public.get_ride_wait_snapshot(uuid) from public,anon;
grant execute on function public.get_ride_wait_snapshot(uuid) to authenticated;
