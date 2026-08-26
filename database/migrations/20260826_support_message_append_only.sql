drop policy if exists super_admin_ticket_messages_all on public.support_messages;
drop policy if exists franchise_admin_support_messages_select on public.support_messages;
drop policy if exists franchise_admin_support_messages_insert on public.support_messages;
drop policy if exists operator_support_messages_scope on public.support_messages;
drop policy if exists super_admin_support_messages_select on public.support_messages;
drop policy if exists super_admin_support_messages_insert on public.support_messages;
drop policy if exists operator_support_messages_select on public.support_messages;
drop policy if exists operator_support_messages_insert on public.support_messages;
drop policy if exists passenger_support_messages_select on public.support_messages;
drop policy if exists passenger_support_messages_insert on public.support_messages;
drop policy if exists driver_support_messages_select on public.support_messages;
drop policy if exists driver_support_messages_insert on public.support_messages;

create policy super_admin_support_messages_select on public.support_messages for select to authenticated using (public.current_active_management_role()='super_admin');
create policy super_admin_support_messages_insert on public.support_messages for insert to authenticated with check (
 public.current_active_management_role()='super_admin' and sender_id=auth.uid()
 and exists(select 1 from public.support_tickets t where t.id=support_messages.ticket_id)
);

create policy franchise_admin_support_messages_select on public.support_messages for select to authenticated using (
 public.current_active_management_role()='franchise_admin' and exists(
   select 1 from public.support_tickets t where t.id=support_messages.ticket_id and t.franchise_id=public.jwt_franchise_id()
   and (t.city_id is null or exists(select 1 from public.franchise_cities fc where fc.franchise_id=public.jwt_franchise_id() and fc.city_id=t.city_id))
 )
);
create policy franchise_admin_support_messages_insert on public.support_messages for insert to authenticated with check (
 public.current_active_management_role()='franchise_admin' and sender_id=auth.uid() and exists(
   select 1 from public.support_tickets t where t.id=support_messages.ticket_id and t.franchise_id=public.jwt_franchise_id()
   and (t.city_id is null or exists(select 1 from public.franchise_cities fc where fc.franchise_id=public.jwt_franchise_id() and fc.city_id=t.city_id))
 )
);

create policy operator_support_messages_select on public.support_messages for select to authenticated using (
 public.current_active_management_role()='operator' and public.staff_has_permission('support') and exists(
   select 1 from public.support_tickets t where t.id=support_messages.ticket_id and t.franchise_id=public.staff_franchise_id()
   and (t.city_id is null or public.can_access_city(t.city_id))
 )
);
create policy operator_support_messages_insert on public.support_messages for insert to authenticated with check (
 public.current_active_management_role()='operator' and sender_id=auth.uid() and public.staff_has_permission('support') and exists(
   select 1 from public.support_tickets t where t.id=support_messages.ticket_id and t.franchise_id=public.staff_franchise_id()
   and (t.city_id is null or public.can_access_city(t.city_id))
 )
);

create policy passenger_support_messages_select on public.support_messages for select to authenticated using (
 exists(select 1 from public.support_tickets t join public.profiles p on p.id=auth.uid()
   where t.id=support_messages.ticket_id and t.requester_id=auth.uid() and p.role::text='passenger' and p.active)
);
create policy passenger_support_messages_insert on public.support_messages for insert to authenticated with check (
 sender_id=auth.uid() and exists(select 1 from public.support_tickets t join public.profiles p on p.id=auth.uid()
   where t.id=support_messages.ticket_id and t.requester_id=auth.uid() and p.role::text='passenger' and p.active)
);

create policy driver_support_messages_select on public.support_messages for select to authenticated using (
 exists(select 1 from public.support_tickets t join public.profiles p on p.id=auth.uid()
   where t.id=support_messages.ticket_id and t.requester_id=auth.uid() and p.role::text='driver' and p.active)
);
create policy driver_support_messages_insert on public.support_messages for insert to authenticated with check (
 sender_id=auth.uid() and exists(select 1 from public.support_tickets t join public.profiles p on p.id=auth.uid()
   where t.id=support_messages.ticket_id and t.requester_id=auth.uid() and p.role::text='driver' and p.active)
);

revoke all on table public.support_messages from anon;
revoke all on table public.support_messages from authenticated;
grant select,insert on table public.support_messages to authenticated;
