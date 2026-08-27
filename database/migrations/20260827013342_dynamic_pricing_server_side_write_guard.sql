alter table public.dynamic_pricing_rules
  add column if not exists source text not null default 'franchise',
  add column if not exists locked_by_matrix boolean not null default false,
  add column if not exists updated_by uuid null references public.profiles(id) on delete set null;

do $$ begin
  alter table public.dynamic_pricing_rules add constraint dynamic_pricing_source_check check (source in ('franchise','matrix'));
exception when duplicate_object then null; end $$;

create or replace function public.guard_dynamic_pricing_write()
returns trigger language plpgsql security definer set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_service boolean:=coalesce(current_setting('request.jwt.claim.role',true),'')='service_role';
begin
  if v_service then new.updated_at:=now(); return new; end if;
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if new.multiplier<1 then raise exception 'Multiplicador deve ser maior ou igual a 1'; end if;
  if new.city_id is null then raise exception 'Cidade obrigatória'; end if;

  if v_role='super_admin' then
    select fc.franchise_id into v_fid from public.franchise_cities fc where fc.city_id=new.city_id limit 1;
    if v_fid is null then raise exception 'Cidade sem franquia responsável'; end if;
    new.franchise_id:=v_fid; new.source:='matrix'; new.locked_by_matrix:=true;
  elsif v_role='franchise_admin' then
    v_fid:=public.current_profile_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=new.city_id) or not public.can_access_city(new.city_id) then raise exception 'Cidade fora do escopo da franquia'; end if;
    if tg_op='UPDATE' and old.locked_by_matrix then raise exception 'Regra bloqueada pela Matriz'; end if;
    new.franchise_id:=v_fid; new.source:='franchise'; new.locked_by_matrix:=false;
  elsif v_role='operator' and public.staff_has_permission('pricing') then
    v_fid:=public.staff_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=new.city_id) or not public.can_access_city(new.city_id) then raise exception 'Cidade fora do escopo do operador'; end if;
    if tg_op='UPDATE' and old.locked_by_matrix then raise exception 'Regra bloqueada pela Matriz'; end if;
    new.franchise_id:=v_fid; new.source:='franchise'; new.locked_by_matrix:=false;
  else raise exception 'Sem permissão para alterar preço dinâmico'; end if;

  if new.category_id is not null and not exists(select 1 from public.ride_categories c where c.id=new.category_id and c.city_id=new.city_id and c.franchise_id=new.franchise_id) then raise exception 'Categoria fora da cidade/franquia da regra'; end if;
  if new.service_area_id is not null and not exists(select 1 from public.service_areas a where a.id=new.service_area_id and a.city_id=new.city_id and a.franchise_id=new.franchise_id) then raise exception 'Área fora da cidade/franquia da regra'; end if;
  new.updated_by:=v_uid; new.updated_at:=now(); return new;
end;
$function$;

create or replace function public.audit_dynamic_pricing_write()
returns trigger language plpgsql security definer set search_path to 'public','pg_temp'
as $function$
begin
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),case when tg_op='INSERT' then 'dynamic_pricing_created' else 'dynamic_pricing_updated' end,'dynamic_pricing_rules',new.id::text,jsonb_build_object('franchise_id',new.franchise_id,'city_id',new.city_id,'name',new.name,'multiplier',new.multiplier,'active',new.active,'source',new.source,'locked_by_matrix',new.locked_by_matrix));
  return new;
end;
$function$;

drop trigger if exists trg_guard_dynamic_pricing_write on public.dynamic_pricing_rules;
create trigger trg_guard_dynamic_pricing_write before insert or update on public.dynamic_pricing_rules for each row execute function public.guard_dynamic_pricing_write();
drop trigger if exists trg_audit_dynamic_pricing_write on public.dynamic_pricing_rules;
create trigger trg_audit_dynamic_pricing_write after insert or update on public.dynamic_pricing_rules for each row execute function public.audit_dynamic_pricing_write();

revoke delete,truncate,trigger,references on table public.dynamic_pricing_rules from anon,authenticated;
revoke insert,update on table public.dynamic_pricing_rules from anon;
grant select on table public.dynamic_pricing_rules to anon,authenticated;
grant insert,update on table public.dynamic_pricing_rules to authenticated;

drop policy if exists super_admin_dynamic_pricing_all on public.dynamic_pricing_rules;
drop policy if exists franchise_admin_dynamic_pricing_all on public.dynamic_pricing_rules;
drop policy if exists operator_dynamic_pricing_write on public.dynamic_pricing_rules;

create policy super_admin_dynamic_pricing_insert on public.dynamic_pricing_rules for insert to authenticated with check (public.current_active_management_role()='super_admin');
create policy super_admin_dynamic_pricing_update on public.dynamic_pricing_rules for update to authenticated using (public.current_active_management_role()='super_admin') with check (public.current_active_management_role()='super_admin');
create policy franchise_dynamic_pricing_insert on public.dynamic_pricing_rules for insert to authenticated with check (public.current_active_management_role()='franchise_admin' and franchise_id=public.current_profile_franchise_id() and public.can_access_city(city_id) and not locked_by_matrix);
create policy franchise_dynamic_pricing_update on public.dynamic_pricing_rules for update to authenticated using (public.current_active_management_role()='franchise_admin' and franchise_id=public.current_profile_franchise_id() and public.can_access_city(city_id) and not locked_by_matrix) with check (public.current_active_management_role()='franchise_admin' and franchise_id=public.current_profile_franchise_id() and public.can_access_city(city_id) and not locked_by_matrix);
create policy operator_dynamic_pricing_insert on public.dynamic_pricing_rules for insert to authenticated with check (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('pricing') and public.can_access_city(city_id) and not locked_by_matrix);
create policy operator_dynamic_pricing_update on public.dynamic_pricing_rules for update to authenticated using (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('pricing') and public.can_access_city(city_id) and not locked_by_matrix) with check (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('pricing') and public.can_access_city(city_id) and not locked_by_matrix);

drop policy if exists dynamic_pricing_management_read on public.dynamic_pricing_rules;
create policy dynamic_pricing_management_read on public.dynamic_pricing_rules for select to authenticated using (public.current_active_management_role()='super_admin' or (public.current_active_management_role()='franchise_admin' and franchise_id=public.current_profile_franchise_id() and public.can_access_city(city_id)) or (public.current_active_management_role()='operator' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission('pricing') or public.staff_has_permission('operation')) and public.can_access_city(city_id)));