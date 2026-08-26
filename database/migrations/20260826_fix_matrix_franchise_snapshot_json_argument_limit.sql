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

  v_ddl:=regexp_replace(
    v_ddl,
    $re$'admin_id',admin_id,'admin_name',admin_name,'admin_email',admin_email,\s*'drivers',drivers$re$,
    $rep$'admin_id',admin_id,'admin_name',admin_name,'admin_email',admin_email) || jsonb_build_object(
    'drivers',drivers$rep$
  );

  if position('admin_email) || jsonb_build_object' in v_ddl)=0 then
    raise exception 'Não foi possível dividir o JSON do snapshot';
  end if;

  execute v_ddl;
end;
$do$;
