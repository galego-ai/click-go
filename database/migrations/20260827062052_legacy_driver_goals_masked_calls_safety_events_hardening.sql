revoke insert, update, delete, truncate on table public.driver_goals from anon, authenticated;
revoke select on table public.driver_goals from anon;
grant select on table public.driver_goals to authenticated;

revoke all on table public.masked_call_sessions from anon;
revoke update, delete, truncate on table public.masked_call_sessions from authenticated;
grant select, insert on table public.masked_call_sessions to authenticated;

drop policy if exists masked_calls_passenger_insert on public.masked_call_sessions;
create policy masked_calls_passenger_insert
on public.masked_call_sessions
for insert
to authenticated
with check (
  passenger_id = auth.uid()
  and status = 'requested'
  and provider is null
  and session_reference is null
  and ended_at is null
  and exists (
    select 1
    from public.rides r
    where r.id = ride_id
      and r.passenger_id = auth.uid()
      and r.driver_id = masked_call_sessions.driver_id
      and r.status in ('accepted','driver_arriving','in_progress')
  )
);

revoke all on table public.safety_events from anon;
revoke update, delete, truncate on table public.safety_events from authenticated;
grant select, insert on table public.safety_events to authenticated;

drop policy if exists safety_events_own_all on public.safety_events;
drop policy if exists safety_events_own_select on public.safety_events;
drop policy if exists safety_events_own_insert on public.safety_events;

create policy safety_events_own_select
on public.safety_events
for select
to authenticated
using (passenger_id = auth.uid());

create policy safety_events_own_insert
on public.safety_events
for insert
to authenticated
with check (
  passenger_id = auth.uid()
  and status = 'open'
  and resolved_at is null
  and (
    ride_id is null
    or exists (
      select 1 from public.rides r
      where r.id = ride_id and r.passenger_id = auth.uid()
    )
  )
);
