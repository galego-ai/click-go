create or replace function public.matrix_create_city(
  p_name text,
  p_state text,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_name text:=btrim(coalesce(p_name,''));
  v_state text:=upper(btrim(coalesce(p_state,'')));
  v_reason text:=btrim(coalesce(p_reason,''));
  v_row public.cities%rowtype;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa do cadastro da cidade'; end if;
  if length(v_name)<2 then raise exception 'Informe um nome válido para a cidade'; end if;
  if v_state !~ '^[A-Z]{2}$' then raise exception 'UF inválida'; end if;

  insert into public.cities(name,state,country,active)
  values(v_name,v_state,'BR',true)
  returning * into v_row;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'create_city','cities',v_row.id::text,
    jsonb_build_object('source','matrix','reason',v_reason,'city_id',v_row.id,'old_value',null,'new_value',to_jsonb(v_row)));

  return jsonb_build_object('ok',true,'id',v_row.id,'name',v_row.name,'state',v_row.state,'active',v_row.active);
exception
  when unique_violation then raise exception 'Esta cidade/UF já está cadastrada';
end;
$$;

create or replace function public.matrix_set_city_active(
  p_city_id uuid,
  p_active boolean,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_old public.cities%rowtype;
  v_new public.cities%rowtype;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da alteração da cidade'; end if;
  if p_active is null then raise exception 'Status da cidade inválido'; end if;

  select * into v_old from public.cities where id=p_city_id for update;
  if not found then raise exception 'Cidade não encontrada'; end if;

  update public.cities set active=p_active where id=p_city_id returning * into v_new;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),case when p_active then 'activate_city' else 'block_city' end,'cities',p_city_id::text,
    jsonb_build_object('source','matrix','reason',v_reason,'city_id',p_city_id,'old_value',to_jsonb(v_old),'new_value',to_jsonb(v_new)));

  return jsonb_build_object('ok',true,'id',v_new.id,'name',v_new.name,'state',v_new.state,'active',v_new.active);
end;
$$;

create or replace function public.matrix_delete_city(
  p_city_id uuid,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_old public.cities%rowtype;
  v_fk record;
  v_used boolean;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da exclusão da cidade'; end if;

  select * into v_old from public.cities where id=p_city_id for update;
  if not found then raise exception 'Cidade não encontrada'; end if;

  for v_fk in
    select c.conrelid::regclass as rel,
           a.attname as col
    from pg_constraint c
    join pg_attribute a on a.attrelid=c.conrelid and a.attnum=c.conkey[1]
    where c.contype='f'
      and c.confrelid='public.cities'::regclass
      and array_length(c.conkey,1)=1
  loop
    execute format('select exists(select 1 from %s where %I=$1 limit 1)',v_fk.rel,v_fk.col)
      into v_used using p_city_id;
    if v_used then
      raise exception 'Cidade já possui território, histórico ou configuração vinculada. Bloqueie a cidade em vez de excluir';
    end if;
  end loop;

  delete from public.cities where id=p_city_id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'delete_city','cities',p_city_id::text,
    jsonb_build_object('source','matrix','reason',v_reason,'city_id',p_city_id,'old_value',to_jsonb(v_old),'new_value',null));

  return jsonb_build_object('ok',true,'id',p_city_id,'name',v_old.name,'state',v_old.state);
end;
$$;

revoke all on function public.matrix_create_city(text,text,text) from public,anon;
grant execute on function public.matrix_create_city(text,text,text) to authenticated,service_role;
revoke all on function public.matrix_set_city_active(uuid,boolean,text) from public,anon;
grant execute on function public.matrix_set_city_active(uuid,boolean,text) to authenticated,service_role;
revoke all on function public.matrix_delete_city(uuid,text) from public,anon;
grant execute on function public.matrix_delete_city(uuid,text) to authenticated,service_role;
