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
    'coalesce(s.next_due_date,(date_trunc(''month'',current_date)+((coalesce(s.due_day,10)-1)||'' days'')::interval)::date) next_due_date',
    'coalesce(s.next_due_date,(date_trunc(''month'',current_date)+((coalesce(s.due_day,10)-1)||'' days'')::interval)::date) subscription_next_due_date'
  );

  v_ddl:=replace(
    v_ddl,
    '''next_due_date'',coalesce(next_due_date,invoice_due_date)',
    '''next_due_date'',coalesce(subscription_next_due_date,next_due_date,invoice_due_date)'
  );

  if position('subscription_next_due_date' in v_ddl)=0 then
    raise exception 'Não foi possível corrigir a ambiguidade de next_due_date';
  end if;

  execute v_ddl;
end;
$do$;
