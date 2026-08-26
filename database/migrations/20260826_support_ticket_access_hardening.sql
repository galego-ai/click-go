drop policy if exists super_admin_tickets_all on public.support_tickets;
drop policy if exists franchise_admin_own_tickets_all on public.support_tickets;
drop policy if exists operator_city_tickets_select on public.support_tickets;
drop policy if exists operator_support_tickets_select on public.support_tickets;
drop policy if exists operator_support_tickets_update on public.support_tickets;
drop policy if exists operator_support_tickets_insert on public.support_tickets;
drop policy if exists super_admin_tickets_select on public.support_tickets;
drop policy if exists super_admin_tickets_insert on public.support_tickets;
drop policy if exists super_admin_tickets_update on public.support_tickets;
drop policy if exists franchise_admin_tickets_select on public.support_tickets;
drop policy if exists franchise_admin_tickets_insert on public.support_tickets;
drop policy if exists franchise_admin_tickets_update on public.support_tickets;

create policy super_admin_tickets_select on public.support_tickets for select to authenticated using (public.current_active_management_role()='super_admin');
create policy super_admin_tickets_insert on public.support_tickets for insert to authenticated with check (public.current_active_management_role()='super_admin' and status='open');
create policy super_admin_tickets_update on public.support_tickets for update to authenticated using (public.current_active_management_role()='super_admin') with check (public.current_active_management_role()='super_admin');

create policy franchise_admin_tickets_select on public.support_tickets for select to authenticated using (
 public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id()
 and (city_id is null or exists(select 1 from public.franchise_cities fc where fc.franchise_id=public.jwt_franchise_id() and fc.city_id=support_tickets.city_id))
);
create policy franchise_admin_tickets_insert on public.support_tickets for insert to authenticated with check (
 public.current_active_management_role()='franchise_admin' and requester_id=auth.uid() and franchise_id=public.jwt_franchise_id()
 and status='open' and assigned_to is null
 and (city_id is null or exists(select 1 from public.franchise_cities fc where fc.franchise_id=public.jwt_franchise_id() and fc.city_id=support_tickets.city_id))
);
create policy franchise_admin_tickets_update on public.support_tickets for update to authenticated using (
 public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id()
 and (city_id is null or exists(select 1 from public.franchise_cities fc where fc.franchise_id=public.jwt_franchise_id() and fc.city_id=support_tickets.city_id))
) with check (
 public.current_active_management_role()='franchise_admin' and franchise_id=public.jwt_franchise_id()
 and (city_id is null or exists(select 1 from public.franchise_cities fc where fc.franchise_id=public.jwt_franchise_id() and fc.city_id=support_tickets.city_id))
);

create policy operator_support_tickets_select on public.support_tickets for select to authenticated using (
 public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('support')
 and (city_id is null or public.can_access_city(city_id))
);
create policy operator_support_tickets_insert on public.support_tickets for insert to authenticated with check (
 public.current_active_management_role()='operator' and requester_id=auth.uid() and franchise_id=public.staff_franchise_id()
 and public.staff_has_permission('support') and status='open' and assigned_to is null
 and (city_id is null or public.can_access_city(city_id))
);
create policy operator_support_tickets_update on public.support_tickets for update to authenticated using (
 public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('support')
 and (city_id is null or public.can_access_city(city_id))
) with check (
 public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('support')
 and (city_id is null or public.can_access_city(city_id))
);

drop policy if exists passenger_support_tickets_select on public.support_tickets;
drop policy if exists passenger_support_tickets_insert on public.support_tickets;
create policy passenger_support_tickets_select on public.support_tickets for select to authenticated using (
 requester_id=auth.uid() and exists(select 1 from public.profiles p where p.id=auth.uid() and p.role::text='passenger' and p.active)
);
create policy passenger_support_tickets_insert on public.support_tickets for insert to authenticated with check (
 requester_id=auth.uid() and status='open' and assigned_to is null
 and exists(select 1 from public.profiles p where p.id=auth.uid() and p.role::text='passenger' and p.active)
 and ((franchise_id is null and city_id is null) or exists(
   select 1 from public.rides r where r.passenger_id=auth.uid()
   and (franchise_id is null or r.franchise_id=support_tickets.franchise_id)
   and (city_id is null or r.city_id=support_tickets.city_id)
 ))
);

drop policy if exists driver_support_tickets_select on public.support_tickets;
drop policy if exists driver_support_tickets_insert on public.support_tickets;
create policy driver_support_tickets_select on public.support_tickets for select to authenticated using (
 requester_id=auth.uid() and exists(select 1 from public.profiles p where p.id=auth.uid() and p.role::text='driver' and p.active)
);
create policy driver_support_tickets_insert on public.support_tickets for insert to authenticated with check (
 requester_id=auth.uid() and status='open' and assigned_to is null and exists(
   select 1 from public.drivers d join public.profiles p on p.id=d.id
   where d.id=auth.uid() and p.role::text='driver' and p.active
   and d.franchise_id=support_tickets.franchise_id and d.city_id=support_tickets.city_id
 )
);

revoke all on table public.support_tickets from anon;
revoke all on table public.support_tickets from authenticated;
grant select,insert on table public.support_tickets to authenticated;
grant update(status,priority,assigned_to,updated_at,closed_at) on table public.support_tickets to authenticated;
