-- Narrow compatibility for existing Matrix UI: only status/offline/commission columns.
-- All other driver fields remain immutable from browser clients.

create or replace function public.normalize_matrix_driver_direct_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  if public.current_active_management_role()<>'super_admin' then
    return new;
  end if;

  if new.commission_percent is not null and (new.commission_percent<0 or new.commission_percent>100) then
    raise exception 'Comissão deve ficar entre 0 e 100';
  end if;

  if old.online is distinct from new.online and new.online then
    raise exception 'A Matriz não pode colocar um motorista online. O próprio motorista deve iniciar a operação.';
  end if;

  if old.status is distinct from new.status then
    new.online:=false;
    new.online_since:=null;
    if new.status='approved'::public.driver_status then
      new.approved_at:=coalesce(old.approved_at,now());
      new.approved_by:=auth.uid();
      new.rejection_reason:=null;
    elsif new.status='pending'::public.driver_status then
      new.approved_at:=null;
      new.approved_by:=null;
      new.rejection_reason:=null;
    elsif new.status='rejected'::public.driver_status then
      new.approved_at:=null;
      new.approved_by:=auth.uid();
      new.rejection_reason:=coalesce(old.rejection_reason,'Reprovado pela Matriz');
    elsif new.status='blocked'::public.driver_status then
      new.approved_by:=auth.uid();
    end if;
  end if;
  return new;
end;
$$;

create or replace function public.audit_matrix_driver_direct_update()
returns trigger
language plpgsql
security definer
set search_path=public,pg_temp
as $$
begin
  if public.current_active_management_role()='super_admin'
     and (old.status is distinct from new.status or old.commission_percent is distinct from new.commission_percent or old.online is distinct from new.online) then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(auth.uid(),'matrix_driver_fields_updated','driver',new.id::text,
      jsonb_build_object(
        'old_status',old.status,'new_status',new.status,
        'old_commission_percent',old.commission_percent,'new_commission_percent',new.commission_percent,
        'old_online',old.online,'new_online',new.online,
        'franchise_id',new.franchise_id,'city_id',new.city_id
      ));
  end if;
  return new;
end;
$$;

drop trigger if exists trg_normalize_matrix_driver_direct_update on public.drivers;
create trigger trg_normalize_matrix_driver_direct_update
before update of status,online,commission_percent on public.drivers
for each row execute function public.normalize_matrix_driver_direct_update();

drop trigger if exists trg_audit_matrix_driver_direct_update on public.drivers;
create trigger trg_audit_matrix_driver_direct_update
after update of status,online,commission_percent on public.drivers
for each row execute function public.audit_matrix_driver_direct_update();

drop policy if exists super_admin_drivers_update on public.drivers;
create policy super_admin_drivers_update
on public.drivers for update to authenticated
using (public.current_active_management_role()='super_admin')
with check (public.current_active_management_role()='super_admin');

grant update(status,online,commission_percent) on public.drivers to authenticated;
