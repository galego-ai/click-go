create or replace function public.capture_critical_audit()
returns trigger
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_old jsonb;
  v_new jsonb;
  v_row jsonb;
  v_franchise uuid;
  v_city uuid;
  v_entity_id text;
  v_source text;
  v_reason text;
  v_role text;
begin
  if tg_op='INSERT' then v_old:=null; v_new:=to_jsonb(new);
  elsif tg_op='DELETE' then v_old:=to_jsonb(old); v_new:=null;
  else v_old:=to_jsonb(old); v_new:=to_jsonb(new); end if;

  v_row:=coalesce(v_new,v_old,'{}'::jsonb);
  begin
    if tg_table_name='franchises' then v_franchise:=nullif(v_row->>'id','')::uuid;
    else v_franchise:=nullif(v_row->>'franchise_id','')::uuid; end if;
  exception when others then v_franchise:=null; end;
  begin v_city:=nullif(v_row->>'city_id','')::uuid; exception when others then v_city:=null; end;
  if v_franchise is null and v_city is not null then
    select fc.franchise_id into v_franchise from public.franchise_cities fc where fc.city_id=v_city limit 1;
  end if;

  v_entity_id:=coalesce(v_row->>'id',concat_ws(':',v_row->>'franchise_id',v_row->>'city_id'),v_row->>'franchise_id');
  v_role:=public.jwt_app_role();
  if v_role='super_admin' and v_franchise is not null and exists(
    select 1 from public.franchise_support_sessions s
    where s.matrix_user_id=auth.uid() and s.franchise_id=v_franchise and s.active
  ) then v_source:='matrix_support';
  else
    v_source:=case v_role
      when 'super_admin' then 'matrix'
      when 'franchise_admin' then 'franchise'
      when 'operator' then 'staff'
      when 'driver' then 'driver_app'
      when 'passenger' then 'passenger_app'
      else 'system' end;
  end if;
  v_reason:=coalesce(
    nullif(current_setting('app.audit_reason',true),''),
    v_row->>'reason',v_row->>'blocked_reason',v_row->>'description',v_row->>'commercial_notes'
  );

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),lower(tg_op),tg_table_name,v_entity_id,
    jsonb_build_object('franchise_id',v_franchise,'city_id',v_city,'source',v_source,'reason',v_reason,'old_value',v_old,'new_value',v_new));
  if tg_op='DELETE' then return old; end if;
  return new;
end;
$$;

create or replace function public.matrix_update_franchise_collection_rules(
  p_franchise_id uuid,
  p_alert_before_due_days integer,
  p_restrict_new_drivers_after_days integer,
  p_block_new_rides_after_days integer,
  p_suspend_operation_after_days integer,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_row public.franchise_collection_rules%rowtype;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da alteração'; end if;
  if not exists(select 1 from public.franchises f where f.id=p_franchise_id and f.deleted_at is null) then
    raise exception 'Franquia não encontrada';
  end if;
  if p_alert_before_due_days not between 0 and 60
    or p_restrict_new_drivers_after_days not between 0 and 180
    or p_block_new_rides_after_days not between 0 and 180
    or p_suspend_operation_after_days not between 0 and 365
    or p_restrict_new_drivers_after_days>p_block_new_rides_after_days
    or p_block_new_rides_after_days>p_suspend_operation_after_days then
    raise exception 'Regras de cobrança inválidas ou fora da ordem permitida';
  end if;

  perform set_config('app.audit_reason',v_reason,true);
  insert into public.franchise_collection_rules(
    franchise_id,alert_before_due_days,restrict_new_drivers_after_days,
    block_new_rides_after_days,suspend_operation_after_days,updated_by,updated_at
  ) values(
    p_franchise_id,p_alert_before_due_days,p_restrict_new_drivers_after_days,
    p_block_new_rides_after_days,p_suspend_operation_after_days,auth.uid(),now()
  )
  on conflict(franchise_id) do update set
    alert_before_due_days=excluded.alert_before_due_days,
    restrict_new_drivers_after_days=excluded.restrict_new_drivers_after_days,
    block_new_rides_after_days=excluded.block_new_rides_after_days,
    suspend_operation_after_days=excluded.suspend_operation_after_days,
    updated_by=auth.uid(),updated_at=now()
  returning * into v_row;

  return jsonb_build_object('ok',true,'franchise_id',v_row.franchise_id,'updated_at',v_row.updated_at);
end;
$$;

create or replace function public.matrix_add_franchise_invoice_adjustment(
  p_franchise_id uuid,
  p_invoice_id uuid,
  p_reference_month date,
  p_adjustment_type text,
  p_description text,
  p_amount numeric,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_description text:=btrim(coalesce(p_description,''));
  v_type text:=lower(btrim(coalesce(p_adjustment_type,'')));
  v_amount numeric:=abs(coalesce(p_amount,0));
  v_signed numeric;
  v_month date:=date_trunc('month',coalesce(p_reference_month,current_date))::date;
  v_invoice_franchise uuid;
  v_invoice_status text;
  v_invoice_month date;
  v_id uuid;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa do ajuste'; end if;
  if length(v_description)<3 then raise exception 'Informe a descrição do ajuste'; end if;
  if v_type not in ('fine','credit','discount','other') then raise exception 'Tipo de ajuste inválido'; end if;
  if v_amount<=0 or v_amount>1000000000 then raise exception 'Valor de ajuste inválido'; end if;
  if not exists(select 1 from public.franchises f where f.id=p_franchise_id and f.deleted_at is null) then
    raise exception 'Franquia não encontrada';
  end if;

  if p_invoice_id is not null then
    select fi.franchise_id,fi.status,fi.reference_month
      into v_invoice_franchise,v_invoice_status,v_invoice_month
    from public.franchise_invoices fi where fi.id=p_invoice_id;
    if not found then raise exception 'Fatura não encontrada'; end if;
    if v_invoice_franchise is distinct from p_franchise_id then raise exception 'Fatura não pertence à franquia'; end if;
    if v_invoice_status in ('paid','cancelled') then raise exception 'Não é permitido ajustar fatura paga ou cancelada'; end if;
    v_month:=v_invoice_month;
  end if;

  v_signed:=case when v_type in ('credit','discount') then -v_amount else v_amount end;
  perform set_config('app.audit_reason',v_reason,true);
  insert into public.franchise_invoice_adjustments(
    franchise_id,invoice_id,reference_month,adjustment_type,description,amount,created_by
  ) values(
    p_franchise_id,p_invoice_id,v_month,v_type,v_description,v_signed,auth.uid()
  ) returning id into v_id;

  perform public.materialize_franchise_invoice(p_franchise_id,v_month);
  return jsonb_build_object('ok',true,'id',v_id,'reference_month',v_month,'amount',v_signed);
end;
$$;

revoke all on function public.matrix_update_franchise_collection_rules(uuid,integer,integer,integer,integer,text) from public,anon;
grant execute on function public.matrix_update_franchise_collection_rules(uuid,integer,integer,integer,integer,text) to authenticated,service_role;
revoke all on function public.matrix_add_franchise_invoice_adjustment(uuid,uuid,date,text,text,numeric,text) from public,anon;
grant execute on function public.matrix_add_franchise_invoice_adjustment(uuid,uuid,date,text,text,numeric,text) to authenticated,service_role;