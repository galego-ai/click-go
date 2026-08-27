-- CLICK-GO: internal ride engine tables are mutated only by trusted RPCs/triggers.

revoke all on table public.ride_dispatch_state from anon, authenticated;
grant select on table public.ride_dispatch_state to authenticated;
grant all on table public.ride_dispatch_state to service_role;

revoke all on table public.ride_offers from anon, authenticated;
grant select on table public.ride_offers to authenticated;
grant all on table public.ride_offers to service_role;

revoke all on table public.ride_location_points from anon, authenticated;
grant select on table public.ride_location_points to authenticated;
grant all on table public.ride_location_points to service_role;

revoke all on table public.ride_events from anon, authenticated;
grant select on table public.ride_events to authenticated;
grant all on table public.ride_events to service_role;

revoke all on table public.ride_receipts from anon, authenticated;
grant select on table public.ride_receipts to authenticated;
grant all on table public.ride_receipts to service_role;

-- Legacy direct event insertion is replaced by trusted ride/safety RPCs.
drop policy if exists ride_events_driver_insert on public.ride_events;

-- Route history read access stays scoped to active management identities.
drop policy if exists ride_location_points_franchise_select on public.ride_location_points;
create policy ride_location_points_franchise_select on public.ride_location_points
for select to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and exists (
    select 1 from public.rides r
    where r.id = ride_location_points.ride_id
      and r.franchise_id = public.jwt_franchise_id()
      and r.city_id is not null
      and public.can_access_city(r.city_id)
  )
);

drop policy if exists ride_location_points_super_admin_select on public.ride_location_points;
create policy ride_location_points_super_admin_select on public.ride_location_points
for select to authenticated
using (public.current_active_management_role() = 'super_admin');
