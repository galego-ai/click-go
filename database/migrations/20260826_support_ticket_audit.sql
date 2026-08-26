create or replace function public.audit_support_ticket_change()
returns trigger
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_profile_role text;
  v_source text;
begin
  select p.role::text into v_profile_role from public.profiles p where p.id=auth.uid();
  v_source:=case
    when public.current_active_management_role()='super_admin' then 'matrix'
    when public.current_active_management_role()='franchise_admin' then 'franchise'
    when public.current_active_management_role()='operator' then 'staff'
    when v_profile_role='driver' then 'driver_app'
    when v_profile_role='passenger' then 'passenger_app'
    else 'system'
  end;

  if tg_op='INSERT' then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(auth.uid(),'support_ticket_created','support_tickets',new.id::text,
      jsonb_build_object('franchise_id',new.franchise_id,'city_id',new.city_id,'requester_id',new.requester_id,'status',new.status,'priority',new.priority,'source',v_source));
  elsif tg_op='UPDATE' and (
    old.status is distinct from new.status or old.priority is distinct from new.priority or old.assigned_to is distinct from new.assigned_to
  ) then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(auth.uid(),'support_ticket_updated','support_tickets',new.id::text,
      jsonb_build_object(
        'franchise_id',new.franchise_id,'city_id',new.city_id,'source',v_source,
        'old_value',jsonb_build_object('status',old.status,'priority',old.priority,'assigned_to',old.assigned_to),
        'new_value',jsonb_build_object('status',new.status,'priority',new.priority,'assigned_to',new.assigned_to)
      ));
  end if;
  return new;
end;
$$;

drop trigger if exists trg_audit_support_ticket_insert on public.support_tickets;
create trigger trg_audit_support_ticket_insert after insert on public.support_tickets for each row execute function public.audit_support_ticket_change();

drop trigger if exists trg_audit_support_ticket_update on public.support_tickets;
create trigger trg_audit_support_ticket_update after update of status,priority,assigned_to on public.support_tickets for each row execute function public.audit_support_ticket_change();
