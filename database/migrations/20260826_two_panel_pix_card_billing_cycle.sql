-- CLICK-GO: formas de pagamento oficiais da fatura da franquia = Pix QR + cartão.
-- Remove a estrutura Bolix (nenhuma cobrança Bolix foi emitida) e corrige o ciclo pós-pago.

drop table if exists public.franchise_invoice_bolix_charges cascade;

create table if not exists public.franchise_invoice_card_charges (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references public.franchise_invoices(id) on delete cascade,
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  created_by uuid references public.profiles(id) on delete set null,
  provider text not null default 'efi',
  charge_id bigint not null unique,
  payment_url text not null,
  amount numeric(12,2) not null check (amount >= 0),
  status text not null default 'active' check (status in ('active','paid','cancelled','expired','failed','unpaid')),
  provider_status text,
  paid_at timestamptz,
  raw_response jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index if not exists franchise_invoice_card_invoice_idx on public.franchise_invoice_card_charges(invoice_id,created_at desc);
create index if not exists franchise_invoice_card_franchise_idx on public.franchise_invoice_card_charges(franchise_id,created_at desc);

alter table public.franchise_invoice_card_charges enable row level security;
revoke all on table public.franchise_invoice_card_charges from anon;
grant select on table public.franchise_invoice_card_charges to authenticated;

drop policy if exists super_admin_invoice_card_select on public.franchise_invoice_card_charges;
create policy super_admin_invoice_card_select on public.franchise_invoice_card_charges
for select to authenticated using (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_own_invoice_card_select on public.franchise_invoice_card_charges;
create policy franchise_admin_own_invoice_card_select on public.franchise_invoice_card_charges
for select to authenticated using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists operator_own_invoice_card_select on public.franchise_invoice_card_charges;
create policy operator_own_invoice_card_select on public.franchise_invoice_card_charges
for select to authenticated using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));

create or replace function public.materialize_franchise_invoice(p_franchise_id uuid,p_reference_month date)
returns uuid language plpgsql security definer set search_path=public,pg_temp as $$
declare
  v_month date:=date_trunc('month',p_reference_month)::date; v_franchise record; v_sub record;
  v_existing public.franchise_invoices%rowtype; v_rides integer:=0; v_gross numeric:=0; v_overage integer:=0;
  v_monthly numeric:=0; v_usage numeric:=0; v_per_ride numeric:=0; v_overage_amount numeric:=0;
  v_percentage_amount numeric:=0; v_adjustments numeric:=0; v_total numeric:=0; v_due date; v_default_due date;
  v_start timestamptz; v_end timestamptz; v_id uuid;
begin
  select id,due_day,next_due_date,activation_date into v_franchise from public.franchises where id=p_franchise_id and deleted_at is null;
  if not found then return null; end if;
  select s.id subscription_id,s.starts_at,s.ends_at,s.next_due_date,p.billing_model,
    coalesce(s.custom_monthly_fee,p.monthly_fee,0)::numeric monthly_fee,
    coalesce(s.custom_percentage_rate,p.percentage_rate,0)::numeric percentage_rate,
    coalesce(s.custom_fixed_fee_per_ride,p.fixed_fee_per_ride,0)::numeric fixed_fee_per_ride,
    coalesce(s.custom_included_rides,p.included_rides,0)::integer included_rides,
    coalesce(s.custom_overage_fee_per_ride,p.overage_fee_per_ride,0)::numeric overage_fee_per_ride
  into v_sub from public.franchise_subscriptions s join public.franchise_plans p on p.id=s.plan_id
  where s.franchise_id=p_franchise_id and s.starts_at<(v_month+interval '1 month') and (s.ends_at is null or s.ends_at>=v_month)
  order by case when s.status='active' then 0 else 1 end,s.starts_at desc limit 1;
  if not found then return null; end if;
  v_start:=greatest(v_month::timestamptz,v_sub.starts_at);
  v_end:=least((v_month+interval '1 month')::timestamptz,coalesce(v_sub.ends_at,(v_month+interval '1 month')::timestamptz));
  if v_start>=v_end then return null; end if;
  select count(*)::int,coalesce(sum(final_fare),0)::numeric into v_rides,v_gross from public.rides
   where franchise_id=p_franchise_id and status='completed' and completed_at>=v_start and completed_at<v_end;
  v_monthly:=v_sub.monthly_fee; v_overage:=greatest(v_rides-v_sub.included_rides,0);
  if v_sub.billing_model='fixed_per_ride' then v_per_ride:=v_rides*v_sub.fixed_fee_per_ride;
  elsif v_sub.billing_model='percentage' then v_percentage_amount:=v_gross*v_sub.percentage_rate/100;
  elsif v_sub.billing_model='hybrid' then v_per_ride:=v_rides*v_sub.fixed_fee_per_ride; v_overage_amount:=v_overage*v_sub.overage_fee_per_ride; end if;
  v_usage:=v_per_ride+v_overage_amount+v_percentage_amount;
  select coalesce(sum(amount),0)::numeric into v_adjustments from public.franchise_invoice_adjustments where franchise_id=p_franchise_id and reference_month=v_month;
  v_total:=greatest(v_monthly+v_usage+v_adjustments,0);
  select * into v_existing from public.franchise_invoices where franchise_id=p_franchise_id and reference_month=v_month limit 1 for update;
  if found and v_existing.status in ('paid','cancelled') then return v_existing.id; end if;
  v_default_due:=(date_trunc('month',v_month+interval '1 month')::date+(greatest(1,least(28,coalesce(v_franchise.due_day,10)))-1));
  if v_existing.id is not null and v_existing.due_date is not null then v_due:=v_existing.due_date;
  elsif v_franchise.next_due_date is not null and v_franchise.next_due_date>=v_sub.starts_at::date and date_trunc('month',v_franchise.next_due_date)=date_trunc('month',v_default_due) then v_due:=v_franchise.next_due_date;
  elsif v_sub.next_due_date is not null and v_sub.next_due_date>=v_sub.starts_at::date and date_trunc('month',v_sub.next_due_date)=date_trunc('month',v_default_due) then v_due:=v_sub.next_due_date;
  else v_due:=v_default_due; end if;
  insert into public.franchise_invoices(franchise_id,subscription_id,reference_month,rides_count,gross_ride_value,monthly_fee,usage_fee,matrix_commission,total_due,due_date,status)
  values(p_franchise_id,v_sub.subscription_id,v_month,v_rides,v_gross,v_monthly,v_usage,0,v_total,v_due,case when v_due<current_date then 'overdue' else 'pending' end)
  on conflict(franchise_id,reference_month) do update set subscription_id=excluded.subscription_id,rides_count=excluded.rides_count,gross_ride_value=excluded.gross_ride_value,monthly_fee=excluded.monthly_fee,usage_fee=excluded.usage_fee,matrix_commission=excluded.matrix_commission,total_due=excluded.total_due,due_date=coalesce(public.franchise_invoices.due_date,excluded.due_date),status=case when public.franchise_invoices.status in ('paid','cancelled') then public.franchise_invoices.status when coalesce(public.franchise_invoices.due_date,excluded.due_date)<current_date then 'overdue' else 'pending' end
  returning id into v_id; return v_id;
end; $$;
revoke all on function public.materialize_franchise_invoice(uuid,date) from public,anon,authenticated;
grant execute on function public.materialize_franchise_invoice(uuid,date) to service_role;

create or replace function public.materialize_franchise_invoices()
returns integer language plpgsql security definer set search_path=public,pg_temp as $$
declare rec record; v_month date; v_count integer:=0;
begin
  for rec in select distinct f.id,s.starts_at from public.franchises f join public.franchise_subscriptions s on s.franchise_id=f.id and s.status='active' where f.deleted_at is null and f.license_status<>'cancelled' loop
    foreach v_month in array array[(date_trunc('month',current_date)-interval '1 month')::date,date_trunc('month',current_date)::date] loop
      if v_month>=date_trunc('month',rec.starts_at)::date then perform public.materialize_franchise_invoice(rec.id,v_month); v_count:=v_count+1; end if;
    end loop;
  end loop;
  perform public.refresh_franchise_license_statuses(); return v_count;
end; $$;
revoke all on function public.materialize_franchise_invoices() from public,anon,authenticated;
grant execute on function public.materialize_franchise_invoices() to service_role;

create or replace function public.mark_franchise_invoice_paid(p_invoice_id uuid,p_paid_at timestamptz,p_actor_id uuid,p_source text,p_method text,p_provider_ref text default null)
returns jsonb language plpgsql security definer set search_path=public,pg_temp as $$
declare v_invoice public.franchise_invoices%rowtype; v_franchise public.franchises%rowtype; v_rule public.franchise_collection_rules%rowtype; v_auto boolean:=true; v_next_due date;
begin
  select * into v_invoice from public.franchise_invoices where id=p_invoice_id for update; if not found then raise exception 'Fatura não encontrada'; end if;
  if v_invoice.status='paid' then return jsonb_build_object('ok',true,'already_paid',true,'invoice_id',p_invoice_id,'paid_at',v_invoice.paid_at); end if;
  update public.franchise_invoices set status='paid',paid_at=coalesce(p_paid_at,now()) where id=p_invoice_id;
  select * into v_franchise from public.franchises where id=v_invoice.franchise_id for update;
  select * into v_rule from public.franchise_collection_rules where franchise_id=v_invoice.franchise_id; if found then v_auto:=coalesce(v_rule.auto_reactivate_on_payment,true); end if;
  if v_invoice.due_date is not null and (v_franchise.next_due_date is null or v_franchise.next_due_date<=v_invoice.due_date) then
    v_next_due:=date_trunc('month',v_invoice.due_date+interval '1 month')::date+(greatest(1,least(28,coalesce(v_franchise.due_day,10)))-1);
    update public.franchises set next_due_date=v_next_due,updated_at=now() where id=v_invoice.franchise_id;
    update public.franchise_subscriptions set next_due_date=v_next_due,updated_at=now() where franchise_id=v_invoice.franchise_id and status='active';
  end if;
  if v_auto and v_franchise.license_status<>'cancelled' then
    update public.franchises set license_status='active',active=true,blocked_at=null,blocked_reason=null,updated_at=now() where id=v_invoice.franchise_id;
    update public.franchise_subscriptions set license_status='active',updated_at=now() where franchise_id=v_invoice.franchise_id and status='active';
  end if;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata) values(p_actor_id,'franchise_invoice_paid','franchise_invoices',p_invoice_id::text,jsonb_build_object('franchise_id',v_invoice.franchise_id,'invoice_id',p_invoice_id,'amount',v_invoice.total_due,'method',p_method,'provider_ref',p_provider_ref,'auto_reactivated',v_auto,'next_due_date',v_next_due,'source',coalesce(p_source,'system')));
  return jsonb_build_object('ok',true,'invoice_id',p_invoice_id,'franchise_id',v_invoice.franchise_id,'paid_at',coalesce(p_paid_at,now()),'auto_reactivated',v_auto,'next_due_date',v_next_due);
end; $$;
revoke all on function public.mark_franchise_invoice_paid(uuid,timestamptz,uuid,text,text,text) from public,anon,authenticated;
grant execute on function public.mark_franchise_invoice_paid(uuid,timestamptz,uuid,text,text,text) to service_role;

create or replace function public.get_franchise_billing_summary(p_franchise_id uuid,p_reference_month date default date_trunc('month',current_date)::date)
returns jsonb language plpgsql stable security definer set search_path=public,pg_temp as $$
declare
  v_role text:=public.jwt_app_role(); v_month date:=date_trunc('month',p_reference_month)::date; v_sub record; v_invoice record; v_franchise record;
  v_rides integer:=0; v_gross numeric:=0; v_overage integer:=0; v_monthly numeric:=0; v_per_ride numeric:=0; v_overage_amount numeric:=0; v_percentage_amount numeric:=0; v_adjustments numeric:=0; v_adjustment_rows jsonb:='[]'::jsonb; v_total numeric:=0; v_due date; v_default_due date; v_start timestamptz; v_end timestamptz;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if v_role='super_admin' then null; elsif v_role='franchise_admin' and p_franchise_id=public.jwt_franchise_id() then null; elsif v_role='operator' and p_franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') then null; else raise exception 'Acesso não autorizado à fatura'; end if;
  select id,trade_name,due_day,next_due_date,activation_date into v_franchise from public.franchises where id=p_franchise_id and deleted_at is null; if not found then raise exception 'Franquia não encontrada'; end if;
  select s.id subscription_id,s.plan_id,s.starts_at,s.ends_at,s.next_due_date,p.name plan_name,p.billing_model,coalesce(s.custom_monthly_fee,p.monthly_fee,0)::numeric monthly_fee,coalesce(s.custom_percentage_rate,p.percentage_rate,0)::numeric percentage_rate,coalesce(s.custom_fixed_fee_per_ride,p.fixed_fee_per_ride,0)::numeric fixed_fee_per_ride,coalesce(s.custom_included_rides,p.included_rides,0)::integer included_rides,coalesce(s.custom_overage_fee_per_ride,p.overage_fee_per_ride,0)::numeric overage_fee_per_ride into v_sub from public.franchise_subscriptions s join public.franchise_plans p on p.id=s.plan_id where s.franchise_id=p_franchise_id and s.starts_at<(v_month+interval '1 month') and (s.ends_at is null or s.ends_at>=v_month) order by case when s.status='active' then 0 else 1 end,s.starts_at desc limit 1;
  if not found then return jsonb_build_object('franchise_id',p_franchise_id,'reference_month',v_month,'has_plan',false,'total_due',0,'adjustments','[]'::jsonb); end if;
  v_start:=greatest(v_month::timestamptz,v_sub.starts_at); v_end:=least((v_month+interval '1 month')::timestamptz,coalesce(v_sub.ends_at,(v_month+interval '1 month')::timestamptz));
  select count(*)::int,coalesce(sum(final_fare),0)::numeric into v_rides,v_gross from public.rides where franchise_id=p_franchise_id and status='completed' and completed_at>=v_start and completed_at<v_end;
  v_monthly:=v_sub.monthly_fee; v_overage:=greatest(v_rides-v_sub.included_rides,0);
  if v_sub.billing_model='fixed_per_ride' then v_per_ride:=v_rides*v_sub.fixed_fee_per_ride; elsif v_sub.billing_model='percentage' then v_percentage_amount:=v_gross*v_sub.percentage_rate/100; elsif v_sub.billing_model='hybrid' then v_per_ride:=v_rides*v_sub.fixed_fee_per_ride; v_overage_amount:=v_overage*v_sub.overage_fee_per_ride; end if;
  select coalesce(sum(amount),0)::numeric,coalesce(jsonb_agg(jsonb_build_object('id',id,'type',adjustment_type,'description',description,'amount',amount,'created_at',created_at) order by created_at),'[]'::jsonb) into v_adjustments,v_adjustment_rows from public.franchise_invoice_adjustments where franchise_id=p_franchise_id and reference_month=v_month;
  select id,total_due,due_date,status,paid_at into v_invoice from public.franchise_invoices where franchise_id=p_franchise_id and reference_month=v_month order by created_at desc limit 1;
  v_default_due:=(date_trunc('month',v_month+interval '1 month')::date+(greatest(1,least(28,coalesce(v_franchise.due_day,10)))-1));
  if v_invoice.due_date is not null then v_due:=v_invoice.due_date; elsif v_franchise.next_due_date is not null and v_franchise.next_due_date>=v_sub.starts_at::date and date_trunc('month',v_franchise.next_due_date)=date_trunc('month',v_default_due) then v_due:=v_franchise.next_due_date; elsif v_sub.next_due_date is not null and v_sub.next_due_date>=v_sub.starts_at::date and date_trunc('month',v_sub.next_due_date)=date_trunc('month',v_default_due) then v_due:=v_sub.next_due_date; else v_due:=v_default_due; end if;
  v_total:=greatest(v_monthly+v_per_ride+v_overage_amount+v_percentage_amount+v_adjustments,0);
  return jsonb_build_object('franchise_id',p_franchise_id,'franchise_name',v_franchise.trade_name,'reference_month',v_month,'has_plan',true,'plan_id',v_sub.plan_id,'plan_name',v_sub.plan_name,'billing_model',v_sub.billing_model,'rides_count',v_rides,'gross_ride_value',v_gross,'included_rides',v_sub.included_rides,'overage_rides',v_overage,'monthly_fee',v_monthly,'fixed_fee_per_ride',v_sub.fixed_fee_per_ride,'per_ride_amount',v_per_ride,'overage_fee_per_ride',v_sub.overage_fee_per_ride,'overage_amount',v_overage_amount,'percentage_rate',v_sub.percentage_rate,'percentage_amount',v_percentage_amount,'adjustments_total',v_adjustments,'adjustments',v_adjustment_rows,'total_due',v_total,'due_date',v_due,'invoice_id',v_invoice.id,'invoice_status',coalesce(v_invoice.status,'open'),'paid_at',v_invoice.paid_at);
end; $$;
revoke all on function public.get_franchise_billing_summary(uuid,date) from public,anon;
grant execute on function public.get_franchise_billing_summary(uuid,date) to authenticated;

do $$ declare v_jobid bigint; begin
  if exists(select 1 from pg_extension where extname='pg_cron') then
    select jobid into v_jobid from cron.job where jobname='clickgo-franchise-invoice-materialize' limit 1;
    if v_jobid is not null then perform cron.unschedule(v_jobid); end if;
    perform cron.schedule('clickgo-franchise-invoice-materialize','5 3 * * *','select public.materialize_franchise_invoices();');
  end if;
end $$;
