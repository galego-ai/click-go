create or replace function public.taximeter_force_driver_offline()
returns trigger
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
begin
  if new.status='running' then
    update public.drivers set online=false where id=new.driver_id and online=true;
  end if;
  return new;
end;
$$;
revoke all on function public.taximeter_force_driver_offline() from public,anon,authenticated;

drop trigger if exists trg_taximeter_force_driver_offline on public.driver_taximeter_sessions;
create trigger trg_taximeter_force_driver_offline
after insert on public.driver_taximeter_sessions
for each row execute function public.taximeter_force_driver_offline();

create or replace function public.prevent_online_during_taximeter()
returns trigger
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
begin
  if new.online=true and old.online is distinct from true and exists(
    select 1 from public.driver_taximeter_sessions s where s.driver_id=new.id and s.status='running'
  ) then
    raise exception 'Finalize o taxímetro e volte a maçaneta para LIVRE antes de ficar online no CLICK-GO';
  end if;
  return new;
end;
$$;
revoke all on function public.prevent_online_during_taximeter() from public,anon,authenticated;

drop trigger if exists trg_prevent_online_during_taximeter on public.drivers;
create trigger trg_prevent_online_during_taximeter
before update of online on public.drivers
for each row execute function public.prevent_online_during_taximeter();

update public.drivers d
set online=false
where d.online=true and exists(
  select 1 from public.driver_taximeter_sessions s where s.driver_id=d.id and s.status='running'
);
