revoke all privileges on table public.configuration_events from anon, authenticated;
revoke all privileges on table public.configuration_sync_state from anon, authenticated;
grant select on table public.configuration_events to authenticated;
grant select on table public.configuration_sync_state to authenticated;

drop policy if exists franchise_admin_configuration_events_select on public.configuration_events;
drop policy if exists super_admin_configuration_events_all on public.configuration_events;
drop policy if exists matrix_configuration_events_select on public.configuration_events;
create policy matrix_configuration_events_select
on public.configuration_events
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_configuration_events_select
on public.configuration_events
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

drop policy if exists franchise_admin_configuration_sync_select on public.configuration_sync_state;
drop policy if exists super_admin_configuration_sync_all on public.configuration_sync_state;
drop policy if exists matrix_configuration_sync_select on public.configuration_sync_state;
create policy matrix_configuration_sync_select
on public.configuration_sync_state
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');
create policy franchise_admin_configuration_sync_select
on public.configuration_sync_state
for select
to authenticated
using (
  public.current_active_management_role() = 'franchise_admin'
  and franchise_id = public.jwt_franchise_id()
);

do $do$
declare
  v_ddl text;
begin
  select pg_get_functiondef(p.oid)
    into v_ddl
  from pg_proc p
  join pg_namespace n on n.oid=p.pronamespace
  where n.nspname='public'
    and p.proname='super_admin_franchise_network_snapshot'
    and pg_get_function_identity_arguments(p.oid)='';

  if v_ddl is null then
    raise exception 'Função super_admin_franchise_network_snapshot não encontrada';
  end if;

  v_ddl:=replace(
    v_ddl,
    'if public.jwt_app_role()<>''super_admin'' then raise exception ''Acesso restrito ao Super Admin''; end if;',
    'if public.current_active_management_role() is distinct from ''super_admin'' then raise exception ''Acesso restrito ao Super Admin''; end if;'
  );

  if position('current_active_management_role' in v_ddl)=0 then
    raise exception 'Não foi possível endurecer super_admin_franchise_network_snapshot';
  end if;

  execute v_ddl;
end;
$do$;
