create or replace function public.matrix_save_franchise_plan(
  p_plan_id uuid,
  p_name text,
  p_description text,
  p_setup_fee numeric,
  p_monthly_fee numeric,
  p_billing_model text,
  p_percentage_rate numeric,
  p_fixed_fee_per_ride numeric,
  p_included_rides integer,
  p_overage_fee_per_ride numeric,
  p_matrix_commission_percentage numeric,
  p_grace_days integer,
  p_max_cities integer,
  p_enabled_modules jsonb,
  p_white_label_level text,
  p_support_level text,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_name text:=btrim(coalesce(p_name,''));
  v_description text:=nullif(btrim(coalesce(p_description,'')),'');
  v_billing text:=lower(btrim(coalesce(p_billing_model,'')));
  v_white_label text:=lower(btrim(coalesce(p_white_label_level,'')));
  v_support text:=lower(btrim(coalesce(p_support_level,'')));
  v_modules jsonb:=coalesce(p_enabled_modules,'{}'::jsonb);
  v_id uuid;
  v_action text;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then
    raise exception 'Acesso restrito à Matriz';
  end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da alteração do plano'; end if;
  if length(v_name)<2 then raise exception 'Informe um nome válido para o plano'; end if;
  if p_setup_fee is null or p_setup_fee<0 or p_monthly_fee is null or p_monthly_fee<0 then raise exception 'Valores de implantação e mensalidade devem ser zero ou positivos'; end if;
  if v_billing not in ('percentage','fixed_per_ride','hybrid','unlimited') then raise exception 'Estrutura de cobrança inválida'; end if;
  if coalesce(p_percentage_rate,-1)<0 or p_percentage_rate>100 then raise exception 'Percentual sobre faturamento inválido'; end if;
  if coalesce(p_fixed_fee_per_ride,-1)<0 or coalesce(p_overage_fee_per_ride,-1)<0 then raise exception 'Taxas por corrida devem ser zero ou positivas'; end if;
  if coalesce(p_included_rides,-1)<0 then raise exception 'Quantidade de corridas incluídas inválida'; end if;
  if coalesce(p_matrix_commission_percentage,-1)<0 or p_matrix_commission_percentage>100 then raise exception 'Comissão da Matriz inválida'; end if;
  if coalesce(p_grace_days,-1)<0 or p_grace_days>60 then raise exception 'Carência inválida'; end if;
  if p_max_cities is not null and p_max_cities<1 then raise exception 'Máximo de cidades deve ser maior que zero'; end if;
  if jsonb_typeof(v_modules) is distinct from 'object' then raise exception 'Módulos do plano inválidos'; end if;
  if v_white_label not in ('brand_locked','controlled','custom') then raise exception 'Nível de personalização inválido'; end if;
  if v_support not in ('standard','priority','dedicated') then raise exception 'Nível de suporte inválido'; end if;

  perform set_config('app.audit_reason',v_reason,true);

  if p_plan_id is null then
    insert into public.franchise_plans(
      name,description,setup_fee,monthly_fee,billing_model,percentage_rate,fixed_fee_per_ride,
      included_rides,overage_fee_per_ride,matrix_commission_percentage,grace_days,max_cities,
      enabled_modules,white_label_level,support_level,active,updated_at
    ) values(
      v_name,v_description,p_setup_fee,p_monthly_fee,v_billing,p_percentage_rate,p_fixed_fee_per_ride,
      p_included_rides,p_overage_fee_per_ride,p_matrix_commission_percentage,p_grace_days,p_max_cities,
      v_modules,v_white_label,v_support,true,now()
    ) returning id into v_id;
    v_action:='created';
  else
    if not exists(select 1 from public.franchise_plans where id=p_plan_id) then raise exception 'Plano não encontrado'; end if;
    update public.franchise_plans set
      name=v_name,description=v_description,setup_fee=p_setup_fee,monthly_fee=p_monthly_fee,
      billing_model=v_billing,percentage_rate=p_percentage_rate,fixed_fee_per_ride=p_fixed_fee_per_ride,
      included_rides=p_included_rides,overage_fee_per_ride=p_overage_fee_per_ride,
      matrix_commission_percentage=p_matrix_commission_percentage,grace_days=p_grace_days,max_cities=p_max_cities,
      enabled_modules=v_modules,white_label_level=v_white_label,support_level=v_support,updated_at=now()
    where id=p_plan_id
    returning id into v_id;
    v_action:='updated';
  end if;

  return jsonb_build_object('ok',true,'id',v_id,'action',v_action);
end;
$$;

create or replace function public.matrix_set_franchise_plan_active(
  p_plan_id uuid,
  p_active boolean,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_name text;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da alteração do status'; end if;
  if p_active is null then raise exception 'Status do plano inválido'; end if;
  perform set_config('app.audit_reason',v_reason,true);
  update public.franchise_plans set active=p_active,updated_at=now() where id=p_plan_id returning name into v_name;
  if not found then raise exception 'Plano não encontrado'; end if;
  return jsonb_build_object('ok',true,'id',p_plan_id,'name',v_name,'active',p_active);
end;
$$;

create or replace function public.matrix_delete_franchise_plan(
  p_plan_id uuid,
  p_reason text
) returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $$
declare
  v_reason text:=btrim(coalesce(p_reason,''));
  v_name text;
begin
  if public.current_active_management_role() is distinct from 'super_admin' then raise exception 'Acesso restrito à Matriz'; end if;
  if length(v_reason)<3 then raise exception 'Informe a justificativa da exclusão'; end if;
  select name into v_name from public.franchise_plans where id=p_plan_id;
  if not found then raise exception 'Plano não encontrado'; end if;
  if exists(select 1 from public.franchise_subscriptions where plan_id=p_plan_id) then
    raise exception 'Plano já utilizado por franquia: desative-o em vez de excluir';
  end if;
  perform set_config('app.audit_reason',v_reason,true);
  delete from public.franchise_plans where id=p_plan_id;
  return jsonb_build_object('ok',true,'id',p_plan_id,'name',v_name);
end;
$$;

revoke all on function public.matrix_save_franchise_plan(uuid,text,text,numeric,numeric,text,numeric,numeric,integer,numeric,numeric,integer,integer,jsonb,text,text,text) from public,anon;
grant execute on function public.matrix_save_franchise_plan(uuid,text,text,numeric,numeric,text,numeric,numeric,integer,numeric,numeric,integer,integer,jsonb,text,text,text) to authenticated,service_role;
revoke all on function public.matrix_set_franchise_plan_active(uuid,boolean,text) from public,anon;
grant execute on function public.matrix_set_franchise_plan_active(uuid,boolean,text) to authenticated,service_role;
revoke all on function public.matrix_delete_franchise_plan(uuid,text) from public,anon;
grant execute on function public.matrix_delete_franchise_plan(uuid,text) to authenticated,service_role;
