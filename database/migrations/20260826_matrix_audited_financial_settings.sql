create or replace function public.matrix_update_financial_settings(
  p_card_surcharge_type text,
  p_card_surcharge_value numeric,
  p_advance_fee_percentage numeric,
  p_driver_share_percentage numeric,
  p_franchise_share_percentage numeric,
  p_platform_share_percentage numeric,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_row public.financial_settings%rowtype;
  v_old jsonb;
  v_reason text := btrim(coalesce(p_reason,''));
  v_total numeric;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if length(v_reason) < 3 then
    raise exception 'Informe uma justificativa para alterar as regras financeiras';
  end if;
  if p_card_surcharge_type not in ('percentage','fixed') then
    raise exception 'Tipo de acréscimo do cartão inválido';
  end if;
  if least(coalesce(p_card_surcharge_value,0),coalesce(p_advance_fee_percentage,0),coalesce(p_driver_share_percentage,0),coalesce(p_franchise_share_percentage,0),coalesce(p_platform_share_percentage,0)) < 0 then
    raise exception 'Valores financeiros não podem ser negativos';
  end if;
  v_total := coalesce(p_driver_share_percentage,0)+coalesce(p_franchise_share_percentage,0)+coalesce(p_platform_share_percentage,0);
  if v_total > 100 then
    raise exception 'A soma dos repasses não pode ultrapassar 100%%';
  end if;

  select * into v_row from public.financial_settings order by updated_at desc nulls last limit 1 for update;
  if v_row.id is null then raise exception 'Configuração financeira não encontrada'; end if;

  v_old := jsonb_build_object(
    'card_surcharge_type',v_row.card_surcharge_type,
    'card_surcharge_value',v_row.card_surcharge_value,
    'advance_fee_percentage',v_row.advance_fee_percentage,
    'driver_share_percentage',v_row.driver_share_percentage,
    'franchise_share_percentage',v_row.franchise_share_percentage,
    'platform_share_percentage',v_row.platform_share_percentage
  );

  update public.financial_settings
  set card_surcharge_type=p_card_surcharge_type,
      card_surcharge_value=coalesce(p_card_surcharge_value,0),
      advance_fee_percentage=coalesce(p_advance_fee_percentage,0),
      driver_share_percentage=coalesce(p_driver_share_percentage,0),
      franchise_share_percentage=coalesce(p_franchise_share_percentage,0),
      platform_share_percentage=coalesce(p_platform_share_percentage,0),
      updated_at=now(),
      updated_by=auth.uid()
  where id=v_row.id
  returning * into v_row;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'matrix_update_financial_settings','financial_settings',v_row.id::text,
    jsonb_build_object('source','matrix','reason',v_reason,'old',v_old,'new',jsonb_build_object(
      'card_surcharge_type',v_row.card_surcharge_type,
      'card_surcharge_value',v_row.card_surcharge_value,
      'advance_fee_percentage',v_row.advance_fee_percentage,
      'driver_share_percentage',v_row.driver_share_percentage,
      'franchise_share_percentage',v_row.franchise_share_percentage,
      'platform_share_percentage',v_row.platform_share_percentage
    )));

  return jsonb_build_object('ok',true,'id',v_row.id,'updated_at',v_row.updated_at);
end;
$$;

revoke all on function public.matrix_update_financial_settings(text,numeric,numeric,numeric,numeric,numeric,text) from public, anon;
grant execute on function public.matrix_update_financial_settings(text,numeric,numeric,numeric,numeric,numeric,text) to authenticated, service_role;

drop policy if exists financial_settings_super_admin_all on public.financial_settings;