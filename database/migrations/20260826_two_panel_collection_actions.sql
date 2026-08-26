create or replace function public.matrix_set_franchise_license(
  p_franchise_id uuid,
  p_action text,
  p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_old_status text;
  v_new_status text;
  v_active boolean;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if p_action not in ('suspend','reactivate','cancel') then raise exception 'Ação inválida'; end if;

  select license_status into v_old_status from public.franchises where id=p_franchise_id and deleted_at is null for update;
  if not found then raise exception 'Franquia não encontrada'; end if;

  if p_action='suspend' then v_new_status:='suspended'; v_active:=false;
  elsif p_action='reactivate' then v_new_status:='active'; v_active:=true;
  else v_new_status:='cancelled'; v_active:=false; end if;

  update public.franchises
     set license_status=v_new_status,
         active=v_active,
         blocked_at=case when v_active then null else now() end,
         blocked_reason=case when v_active then null else v_reason end,
         updated_at=now()
   where id=p_franchise_id;

  update public.franchise_subscriptions
     set license_status=v_new_status,
         status=case when p_action='cancel' then 'cancelled' else status end,
         updated_at=now()
   where franchise_id=p_franchise_id and status='active';

  update public.drivers set online=false
   where franchise_id=p_franchise_id and p_action in ('suspend','cancel');

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'license_'||p_action,'franchises',p_franchise_id::text,
    jsonb_build_object('franchise_id',p_franchise_id,'old_value',jsonb_build_object('license_status',v_old_status),
      'new_value',jsonb_build_object('license_status',v_new_status,'active',v_active),'reason',v_reason,'source','matrix'));

  return jsonb_build_object('ok',true,'franchise_id',p_franchise_id,'old_status',v_old_status,'new_status',v_new_status);
end;
$$;
revoke all on function public.matrix_set_franchise_license(uuid,text,text) from public,anon;
grant execute on function public.matrix_set_franchise_license(uuid,text,text) to authenticated;

create or replace function public.matrix_extend_franchise_due_date(
  p_franchise_id uuid,
  p_days integer,
  p_reason text
)
returns jsonb
language plpgsql
security definer
set search_path=public,pg_temp
as $$
declare
  v_reason text:=nullif(trim(coalesce(p_reason,'')),'');
  v_invoice uuid;
  v_old_due date;
  v_new_due date;
begin
  if public.jwt_app_role()<>'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if v_reason is null then raise exception 'Justificativa obrigatória'; end if;
  if p_days<1 or p_days>180 then raise exception 'Prorrogação deve ser entre 1 e 180 dias'; end if;

  select id,due_date into v_invoice,v_old_due
  from public.franchise_invoices
  where franchise_id=p_franchise_id and status not in ('paid','cancelled')
  order by due_date desc,created_at desc limit 1 for update;
  if v_invoice is null then raise exception 'Nenhuma fatura em aberto encontrada'; end if;

  v_new_due:=v_old_due+p_days;
  update public.franchise_invoices set due_date=v_new_due where id=v_invoice;
  update public.franchises set next_due_date=v_new_due,updated_at=now() where id=p_franchise_id;
  update public.franchise_subscriptions set next_due_date=v_new_due,updated_at=now()
   where franchise_id=p_franchise_id and status='active';

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'invoice_due_date_extended','franchise_invoices',v_invoice::text,
    jsonb_build_object('franchise_id',p_franchise_id,'old_value',jsonb_build_object('due_date',v_old_due),
      'new_value',jsonb_build_object('due_date',v_new_due,'days_added',p_days),'reason',v_reason,'source','matrix'));

  return jsonb_build_object('ok',true,'invoice_id',v_invoice,'old_due_date',v_old_due,'new_due_date',v_new_due);
end;
$$;
revoke all on function public.matrix_extend_franchise_due_date(uuid,integer,text) from public,anon;
grant execute on function public.matrix_extend_franchise_due_date(uuid,integer,text) to authenticated;
