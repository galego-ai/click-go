-- Snapshot consolidado para o Super Admin: evita dezenas de consultas por franquia.
create or replace function public.super_admin_franchise_network_snapshot()
returns jsonb
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
  v_result jsonb;
begin
  if public.jwt_app_role()<>'super_admin' then
    raise exception 'Acesso restrito ao Super Admin';
  end if;

  with active_sub as (
    select distinct on (s.franchise_id)
      s.franchise_id,s.id subscription_id,s.plan_id,s.status subscription_status,s.license_status subscription_license_status,
      coalesce(s.custom_monthly_fee,p.monthly_fee,0) monthly_fee,
      coalesce(s.custom_percentage_rate,p.percentage_rate,0) percentage_rate,
      coalesce(s.custom_fixed_fee_per_ride,p.fixed_fee_per_ride,0) fixed_fee_per_ride,
      coalesce(s.custom_included_rides,p.included_rides,0) included_rides,
      coalesce(s.custom_overage_fee_per_ride,p.overage_fee_per_ride,0) overage_fee_per_ride,
      coalesce(s.custom_setup_fee,p.setup_fee,0) setup_fee,
      coalesce(s.matrix_commission_percentage,p.matrix_commission_percentage,0) matrix_commission_percentage,
      p.name plan_name,p.billing_model,p.enabled_modules,p.support_level,p.white_label_level,p.grace_days,
      coalesce(s.next_due_date,(date_trunc('month',current_date) + ((coalesce(s.due_day,10)-1)||' days')::interval)::date) next_due_date
    from public.franchise_subscriptions s
    join public.franchise_plans p on p.id=s.plan_id
    where s.status='active'
    order by s.franchise_id,s.starts_at desc
  ), ride_month as (
    select franchise_id,count(*)::int rides_month,count(distinct passenger_id)::int passengers_month,coalesce(sum(final_fare),0)::numeric gross_month
    from public.rides
    where requested_at>=date_trunc('month',now())
    group by franchise_id
  ), driver_counts as (
    select franchise_id,count(*)::int drivers,count(*) filter(where online)::int drivers_online,count(*) filter(where status='pending')::int drivers_pending
    from public.drivers group by franchise_id
  ), admins as (
    select distinct on (franchise_id) franchise_id,id admin_id,full_name admin_name,email admin_email
    from public.profiles where role='franchise_admin' and active order by franchise_id,created_at
  ), territories as (
    select fc.franchise_id,count(*)::int city_count,jsonb_agg(jsonb_build_object('id',c.id,'name',c.name,'state',c.state) order by c.name) cities
    from public.franchise_cities fc join public.cities c on c.id=fc.city_id group by fc.franchise_id
  ), onboarding as (
    select franchise_id,count(*)::int total_steps,count(*) filter(where completed)::int completed_steps
    from public.franchise_onboarding_steps group by franchise_id
  ), current_invoice as (
    select distinct on (franchise_id) franchise_id,id invoice_id,total_due,monthly_fee invoice_monthly_fee,usage_fee,matrix_commission,due_date invoice_due_date,status invoice_status
    from public.franchise_invoices
    where reference_month=date_trunc('month',current_date)::date
    order by franchise_id,created_at desc
  ), base as (
    select
      f.*,
      s.*,
      coalesce(r.rides_month,0) rides_month,coalesce(r.passengers_month,0) passengers_month,coalesce(r.gross_month,0) gross_month,
      coalesce(d.drivers,0) drivers,coalesce(d.drivers_online,0) drivers_online,coalesce(d.drivers_pending,0) drivers_pending,
      a.admin_id,a.admin_name,a.admin_email,
      coalesce(t.city_count,0) city_count,coalesce(t.cities,'[]'::jsonb) cities,
      coalesce(o.total_steps,0) total_steps,coalesce(o.completed_steps,0) completed_steps,
      i.invoice_id,i.total_due invoice_total_due,i.usage_fee invoice_usage_fee,i.matrix_commission invoice_matrix_commission,i.invoice_due_date,i.invoice_status,
      coalesce(cs.version,0) config_version,cs.last_change_at config_changed_at,cs.last_change_source config_changed_source
    from public.franchises f
    left join active_sub s on s.franchise_id=f.id
    left join ride_month r on r.franchise_id=f.id
    left join driver_counts d on d.franchise_id=f.id
    left join admins a on a.franchise_id=f.id
    left join territories t on t.franchise_id=f.id
    left join onboarding o on o.franchise_id=f.id
    left join current_invoice i on i.franchise_id=f.id
    left join public.configuration_sync_state cs on cs.franchise_id=f.id
    where f.deleted_at is null
  ), calc as (
    select base.*,
      greatest(rides_month-coalesce(included_rides,0),0)::int overage_rides,
      case
        when subscription_id is null then 0::numeric
        when billing_model='percentage' then gross_month*coalesce(percentage_rate,0)/100
        when billing_model='hybrid' then (greatest(rides_month-coalesce(included_rides,0),0)*coalesce(overage_fee_per_ride,0)) + (gross_month*coalesce(percentage_rate,0)/100)
        when billing_model='fixed_per_ride' and coalesce(included_rides,0)>0 then greatest(rides_month-included_rides,0)*coalesce(overage_fee_per_ride,0)
        when billing_model='fixed_per_ride' then rides_month*coalesce(fixed_fee_per_ride,0)
        else 0::numeric
      end computed_usage_fee
    from base
  )
  select coalesce(jsonb_agg(jsonb_build_object(
    'id',id,'trade_name',trade_name,'legal_name',legal_name,'document',document,'active',active,
    'contact_name',contact_name,'contact_email',contact_email,'contact_phone',contact_phone,
    'license_status',license_status,'activation_date',activation_date,'next_due_date',coalesce(next_due_date,invoice_due_date),
    'due_day',due_day,'contract_status',contract_status,'contract_reference',contract_reference,
    'territory_type',territory_type,'onboarding_status',onboarding_status,'support_mode_enabled',support_mode_enabled,
    'white_label_mode',white_label_mode,'commercial_notes',commercial_notes,
    'subscription_id',subscription_id,'plan_id',plan_id,'plan_name',plan_name,'billing_model',billing_model,
    'monthly_fee',coalesce(monthly_fee,0),'setup_fee',coalesce(setup_fee,0),'percentage_rate',coalesce(percentage_rate,0),
    'fixed_fee_per_ride',coalesce(fixed_fee_per_ride,0),'included_rides',coalesce(included_rides,0),
    'overage_fee_per_ride',coalesce(overage_fee_per_ride,0),'matrix_commission_percentage',coalesce(matrix_commission_percentage,0),
    'enabled_modules',coalesce(enabled_modules,'{}'::jsonb),'support_level',support_level,'white_label_level',white_label_level,
    'cities',cities,'city_count',city_count,'admin_id',admin_id,'admin_name',admin_name,'admin_email',admin_email,
    'drivers',drivers,'drivers_online',drivers_online,'drivers_pending',drivers_pending,'passengers_month',passengers_month,
    'rides_month',rides_month,'gross_month',gross_month,'overage_rides',overage_rides,
    'computed_usage_fee',computed_usage_fee,'computed_total_due',coalesce(monthly_fee,0)+computed_usage_fee,
    'invoice_id',invoice_id,'invoice_total_due',invoice_total_due,'invoice_usage_fee',invoice_usage_fee,'invoice_matrix_commission',invoice_matrix_commission,'invoice_status',invoice_status,
    'onboarding_total',total_steps,'onboarding_completed',completed_steps,
    'config_version',config_version,'config_changed_at',config_changed_at,'config_changed_source',config_changed_source,
    'created_at',created_at,'updated_at',updated_at
  ) order by created_at desc),'[]'::jsonb) into v_result from calc;
  return v_result;
end;
$$;

grant execute on function public.super_admin_franchise_network_snapshot() to authenticated;
