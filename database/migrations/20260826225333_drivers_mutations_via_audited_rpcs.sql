-- Centralize driver mutations in audited RPCs; browser table access becomes read-only.

create or replace function public.approve_driver_registration(
  p_driver_id uuid,
  p_approve boolean,
  p_reason text default null,
  p_commission_percent numeric default null
)
returns void
language plpgsql
security definer
set search_path to public,pg_temp
as $$
declare
  d public.drivers%rowtype;
  v_role text:=public.jwt_app_role();
  v_scope_franchise uuid;
begin
  if auth.uid() is null or v_role not in ('super_admin','franchise_admin','operator') then raise exception 'Sem permissão'; end if;
  select * into d from public.drivers where id=p_driver_id;
  if not found then raise exception 'Motorista não encontrado'; end if;

  if p_commission_percent is not null and (p_commission_percent<0 or p_commission_percent>100) then
    raise exception 'Comissão deve ficar entre 0 e 100';
  end if;

  if v_role='franchise_admin' then
    v_scope_franchise:=public.jwt_franchise_id();
    if d.franchise_id is distinct from v_scope_franchise then raise exception 'Sem permissão'; end if;
    if not public.can_access_city(d.city_id) then raise exception 'Motorista fora da sua cidade/região'; end if;
  elsif v_role='operator' then
    if not public.staff_has_permission('drivers') then raise exception 'Permissão de motoristas não concedida'; end if;
    v_scope_franchise:=public.staff_franchise_id();
    if d.franchise_id is distinct from v_scope_franchise then raise exception 'Motorista fora da sua franquia'; end if;
    if not public.can_access_city(d.city_id) then raise exception 'Motorista fora da sua cidade/região'; end if;
  end if;

  update public.drivers
  set status=case when p_approve then 'approved'::public.driver_status else 'rejected'::public.driver_status end,
      approved_at=case when p_approve then now() else null end,
      approved_by=auth.uid(),
      rejection_reason=case when p_approve then null else coalesce(nullif(btrim(p_reason),''),'Reprovado pela gestão') end,
      commission_percent=coalesce(p_commission_percent,commission_percent),
      online=false,
      online_since=null
  where id=p_driver_id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),case when p_approve then 'driver_approved' else 'driver_rejected' end,'driver',p_driver_id::text,
    jsonb_build_object('reason',p_reason,'commission_percent',p_commission_percent,'city_id',d.city_id,'franchise_id',d.franchise_id,'actor_role',v_role));
end;
$$;
revoke all on function public.approve_driver_registration(uuid,boolean,text,numeric) from public,anon;
grant execute on function public.approve_driver_registration(uuid,boolean,text,numeric) to authenticated,service_role;

create or replace function public.matrix_set_driver_status(
  p_driver_id uuid,
  p_status text,
  p_reason text default null
)
returns void
language plpgsql
security definer
set search_path to public,pg_temp
as $$
declare
  d public.drivers%rowtype;
  v_old text;
begin
  if public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_status not in ('pending','approved','rejected','blocked') then raise exception 'Status de motorista inválido'; end if;
  select * into d from public.drivers where id=p_driver_id for update;
  if not found then raise exception 'Motorista não encontrado'; end if;
  v_old:=d.status::text;

  update public.drivers
  set status=p_status::public.driver_status,
      online=false,
      online_since=null,
      approved_at=case when p_status='approved' then coalesce(approved_at,now()) when p_status in ('pending','rejected') then null else approved_at end,
      approved_by=case when p_status in ('approved','rejected','blocked') then auth.uid() when p_status='pending' then null else approved_by end,
      rejection_reason=case
        when p_status='rejected' then coalesce(nullif(btrim(p_reason),''),rejection_reason,'Reprovado pela Matriz')
        when p_status in ('pending','approved') then null
        else rejection_reason
      end
  where id=p_driver_id;

  if p_status is distinct from v_old then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(auth.uid(),'matrix_set_driver_status','driver',p_driver_id::text,
      jsonb_build_object('old_status',v_old,'new_status',p_status,'reason',p_reason,'franchise_id',d.franchise_id,'city_id',d.city_id));
  end if;
end;
$$;
revoke all on function public.matrix_set_driver_status(uuid,text,text) from public,anon;
grant execute on function public.matrix_set_driver_status(uuid,text,text) to authenticated,service_role;

create or replace function public.matrix_set_driver_commission(
  p_driver_id uuid,
  p_commission_percent numeric
)
returns void
language plpgsql
security definer
set search_path to public,pg_temp
as $$
declare
  d public.drivers%rowtype;
  v_old numeric;
begin
  if public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_commission_percent is not null and (p_commission_percent<0 or p_commission_percent>100) then raise exception 'Comissão deve ficar entre 0 e 100'; end if;
  select * into d from public.drivers where id=p_driver_id for update;
  if not found then raise exception 'Motorista não encontrado'; end if;
  v_old:=d.commission_percent;
  update public.drivers set commission_percent=p_commission_percent where id=p_driver_id;
  if v_old is distinct from p_commission_percent then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(auth.uid(),'matrix_set_driver_commission','driver',p_driver_id::text,
      jsonb_build_object('old_commission_percent',v_old,'new_commission_percent',p_commission_percent,'franchise_id',d.franchise_id,'city_id',d.city_id));
  end if;
end;
$$;
revoke all on function public.matrix_set_driver_commission(uuid,numeric) from public,anon;
grant execute on function public.matrix_set_driver_commission(uuid,numeric) to authenticated,service_role;

drop policy if exists franchise_admin_own_drivers_all on public.drivers;
drop policy if exists super_admin_drivers_all on public.drivers;
drop policy if exists operator_drivers_scope_update on public.drivers;
drop policy if exists drivers_self_update on public.drivers;
drop policy if exists super_admin_drivers_select on public.drivers;
create policy super_admin_drivers_select on public.drivers for select to authenticated
using (public.current_active_management_role()='super_admin');

revoke all on public.drivers from anon;
revoke insert,update,delete,truncate,references,trigger on public.drivers from authenticated;
grant select on public.drivers to authenticated;
grant all on public.drivers to service_role;
