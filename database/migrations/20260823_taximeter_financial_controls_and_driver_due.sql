-- Applied to Supabase production as migration: taximeter_financial_controls_and_driver_due
-- Keeps street-hail taximeter rides financially separate from normal CLICK-GO ride billing.

create table if not exists public.taximeter_financial_rules (
  id uuid primary key default gen_random_uuid(),
  scope text not null check (scope in ('global','franchise')),
  franchise_id uuid references public.franchises(id) on delete cascade,
  fee_mode text not null default 'none' check (fee_mode in ('none','fixed','percentage')),
  fee_value numeric(12,2) not null default 0 check (fee_value >= 0),
  allow_franchise_override boolean not null default true,
  locked_by_matrix boolean not null default false,
  active boolean not null default true,
  updated_by uuid references public.profiles(id) on delete set null,
  updated_at timestamptz not null default now(),
  constraint taximeter_financial_rules_scope_franchise_chk check ((scope='global' and franchise_id is null) or (scope='franchise' and franchise_id is not null))
);
create unique index if not exists taximeter_financial_rules_global_uq on public.taximeter_financial_rules ((scope)) where scope='global';
create unique index if not exists taximeter_financial_rules_franchise_uq on public.taximeter_financial_rules (franchise_id) where scope='franchise';
alter table public.taximeter_financial_rules enable row level security;
revoke all on public.taximeter_financial_rules from anon, authenticated;
grant all on public.taximeter_financial_rules to service_role;
insert into public.taximeter_financial_rules(scope,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active)
select 'global','none',0,true,false,true
where not exists(select 1 from public.taximeter_financial_rules where scope='global');

create table if not exists public.driver_taximeter_charges (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null unique references public.driver_taximeter_sessions(id) on delete cascade,
  driver_id uuid not null references public.drivers(id) on delete cascade,
  franchise_id uuid references public.franchises(id) on delete set null,
  city_id uuid references public.cities(id) on delete set null,
  gross_amount numeric(12,2) not null default 0 check (gross_amount >= 0),
  fee_mode text not null check (fee_mode in ('none','fixed','percentage')),
  fee_value numeric(12,2) not null default 0 check (fee_value >= 0),
  fee_amount numeric(12,2) not null default 0 check (fee_amount >= 0),
  driver_net_amount numeric(12,2) not null default 0 check (driver_net_amount >= 0),
  status text not null default 'not_charged' check (status in ('not_charged','pending','settled','waived')),
  wallet_transaction_id uuid references public.driver_operational_transactions(id) on delete set null,
  created_at timestamptz not null default now(),
  settled_at timestamptz,
  updated_at timestamptz not null default now()
);
create index if not exists driver_taximeter_charges_driver_idx on public.driver_taximeter_charges(driver_id,created_at desc);
create index if not exists driver_taximeter_charges_franchise_idx on public.driver_taximeter_charges(franchise_id,created_at desc);
create index if not exists driver_taximeter_charges_status_idx on public.driver_taximeter_charges(status,created_at desc);
alter table public.driver_taximeter_charges enable row level security;
revoke all on public.driver_taximeter_charges from anon, authenticated;
grant all on public.driver_taximeter_charges to service_role;

alter table public.driver_operational_transactions drop constraint if exists driver_operational_transactions_source_check;
alter table public.driver_operational_transactions add constraint driver_operational_transactions_source_check check (source = any (array['pix'::text,'franchise'::text,'matrix'::text,'ride_fee'::text,'ride_commission'::text,'adjustment'::text,'taximeter_fee'::text]));

create or replace function public.effective_taximeter_financial_rule(p_franchise uuid)
returns table(fee_mode text, fee_value numeric, source_scope text, allow_franchise_override boolean, locked_by_matrix boolean)
language plpgsql stable security definer set search_path='public','pg_temp'
as $$
declare g public.taximeter_financial_rules%rowtype; f public.taximeter_financial_rules%rowtype;
begin
  select * into g from public.taximeter_financial_rules where scope='global' and active limit 1;
  select * into f from public.taximeter_financial_rules where scope='franchise' and franchise_id=p_franchise and active limit 1;
  if f.id is not null and (coalesce(g.allow_franchise_override,true) or f.locked_by_matrix) then
    return query select f.fee_mode,f.fee_value,'franchise'::text,coalesce(g.allow_franchise_override,true),f.locked_by_matrix;
  else
    return query select coalesce(g.fee_mode,'none'),coalesce(g.fee_value,0),'global'::text,coalesce(g.allow_franchise_override,true),false;
  end if;
end;$$;
revoke all on function public.effective_taximeter_financial_rule(uuid) from public, anon, authenticated;
grant execute on function public.effective_taximeter_financial_rule(uuid) to service_role;

create or replace function public.get_taximeter_financial_settings(p_franchise_id uuid default null)
returns jsonb language plpgsql stable security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_role text:=public.jwt_app_role(); v_own uuid:=public.jwt_franchise_id(); v_target uuid; g public.taximeter_financial_rules%rowtype; f public.taximeter_financial_rules%rowtype; e record;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='super_admin' then v_target:=p_franchise_id;
  elsif v_role='franchise_admin' then v_target:=v_own;
  else raise exception 'Acesso restrito à operação'; end if;
  select * into g from public.taximeter_financial_rules where scope='global' limit 1;
  if v_target is not null then select * into f from public.taximeter_financial_rules where scope='franchise' and franchise_id=v_target limit 1; end if;
  if v_target is not null then select * into e from public.effective_taximeter_financial_rule(v_target);
  else select coalesce(g.fee_mode,'none') fee_mode,coalesce(g.fee_value,0) fee_value,'global'::text source_scope,coalesce(g.allow_franchise_override,true) allow_franchise_override,false locked_by_matrix into e; end if;
  return jsonb_build_object('target_franchise_id',v_target,'global_fee_mode',coalesce(g.fee_mode,'none'),'global_fee_value',coalesce(g.fee_value,0),'allow_franchise_override',coalesce(g.allow_franchise_override,true),'override_exists',f.id is not null,'override_fee_mode',f.fee_mode,'override_fee_value',f.fee_value,'override_locked_by_matrix',coalesce(f.locked_by_matrix,false),'effective_fee_mode',e.fee_mode,'effective_fee_value',e.fee_value,'effective_source',e.source_scope,'can_edit',case when v_role='super_admin' then true else coalesce(g.allow_franchise_override,true) and not coalesce(f.locked_by_matrix,false) end);
end;$$;
revoke all on function public.get_taximeter_financial_settings(uuid) from public, anon;
grant execute on function public.get_taximeter_financial_settings(uuid) to authenticated, service_role;

create or replace function public.set_taximeter_financial_settings(p_fee_mode text,p_fee_value numeric,p_scope text default 'franchise',p_franchise_id uuid default null,p_allow_franchise_override boolean default true,p_locked_by_matrix boolean default false)
returns jsonb language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_role text:=public.jwt_app_role(); v_own uuid:=public.jwt_franchise_id(); v_target uuid; g public.taximeter_financial_rules%rowtype; f public.taximeter_financial_rules%rowtype; v_value numeric;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if p_fee_mode not in ('none','fixed','percentage') then raise exception 'Modo de taxa inválido'; end if;
  v_value:=case when p_fee_mode='none' then 0 else round(coalesce(p_fee_value,0)::numeric,2) end;
  if v_value<0 then raise exception 'Valor da taxa inválido'; end if;
  if p_fee_mode='percentage' and v_value>100 then raise exception 'Percentual deve ficar entre 0 e 100'; end if;
  if p_fee_mode='fixed' and v_value>100000 then raise exception 'Taxa fixa acima do limite permitido'; end if;
  if v_role='super_admin' then
    if p_scope='global' then
      update public.taximeter_financial_rules set fee_mode=p_fee_mode,fee_value=v_value,allow_franchise_override=coalesce(p_allow_franchise_override,true),locked_by_matrix=false,active=true,updated_by=v_uid,updated_at=now() where scope='global';
      if not found then insert into public.taximeter_financial_rules(scope,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active,updated_by) values('global',p_fee_mode,v_value,coalesce(p_allow_franchise_override,true),false,true,v_uid); end if;
      return public.get_taximeter_financial_settings(null);
    elsif p_scope='franchise' then
      v_target:=p_franchise_id; if v_target is null then raise exception 'Informe a franquia'; end if;
      update public.taximeter_financial_rules set fee_mode=p_fee_mode,fee_value=v_value,locked_by_matrix=coalesce(p_locked_by_matrix,false),active=true,updated_by=v_uid,updated_at=now() where scope='franchise' and franchise_id=v_target;
      if not found then insert into public.taximeter_financial_rules(scope,franchise_id,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active,updated_by) values('franchise',v_target,p_fee_mode,v_value,true,coalesce(p_locked_by_matrix,false),true,v_uid); end if;
      return public.get_taximeter_financial_settings(v_target);
    else raise exception 'Escopo inválido'; end if;
  elsif v_role='franchise_admin' then
    v_target:=v_own; if v_target is null then raise exception 'Franquia não identificada'; end if;
    select * into g from public.taximeter_financial_rules where scope='global' limit 1;
    select * into f from public.taximeter_financial_rules where scope='franchise' and franchise_id=v_target limit 1;
    if not coalesce(g.allow_franchise_override,true) then raise exception 'A matriz bloqueou alterações da taxa do taxímetro'; end if;
    if coalesce(f.locked_by_matrix,false) then raise exception 'Configuração travada pela matriz'; end if;
    update public.taximeter_financial_rules set fee_mode=p_fee_mode,fee_value=v_value,locked_by_matrix=false,active=true,updated_by=v_uid,updated_at=now() where scope='franchise' and franchise_id=v_target;
    if not found then insert into public.taximeter_financial_rules(scope,franchise_id,fee_mode,fee_value,allow_franchise_override,locked_by_matrix,active,updated_by) values('franchise',v_target,p_fee_mode,v_value,true,false,true,v_uid); end if;
    return public.get_taximeter_financial_settings(v_target);
  else raise exception 'Sem permissão'; end if;
end;$$;
revoke all on function public.set_taximeter_financial_settings(text,numeric,text,uuid,boolean,boolean) from public, anon;
grant execute on function public.set_taximeter_financial_settings(text,numeric,text,uuid,boolean,boolean) to authenticated, service_role;

create or replace function public.settle_taximeter_financial_charge(p_session_id uuid)
returns jsonb language plpgsql security definer set search_path='public','pg_temp'
as $$
declare s public.driver_taximeter_sessions%rowtype; c public.driver_taximeter_charges%rowtype; r record; v_fee numeric:=0; v_net numeric:=0; v_balance numeric:=0; v_tx uuid;
begin
  select * into c from public.driver_taximeter_charges where session_id=p_session_id;
  if found then return to_jsonb(c); end if;
  select * into s from public.driver_taximeter_sessions where id=p_session_id and status='finished' for update;
  if not found then raise exception 'Sessão finalizada não encontrada'; end if;
  select * into r from public.effective_taximeter_financial_rule(s.franchise_id);
  if r.fee_mode='percentage' then v_fee:=round(coalesce(s.final_amount,0)*coalesce(r.fee_value,0)/100,2);
  elsif r.fee_mode='fixed' then v_fee:=least(coalesce(s.final_amount,0),round(coalesce(r.fee_value,0),2)); else v_fee:=0; end if;
  v_fee:=greatest(0,least(coalesce(s.final_amount,0),v_fee)); v_net:=greatest(0,coalesce(s.final_amount,0)-v_fee);
  insert into public.driver_taximeter_charges(session_id,driver_id,franchise_id,city_id,gross_amount,fee_mode,fee_value,fee_amount,driver_net_amount,status)
  values(s.id,s.driver_id,s.franchise_id,s.city_id,coalesce(s.final_amount,0),r.fee_mode,coalesce(r.fee_value,0),v_fee,v_net,case when v_fee=0 then 'not_charged' else 'pending' end) returning * into c;
  if v_fee>0 then
    insert into public.driver_operational_wallets(driver_id) values(s.driver_id) on conflict(driver_id) do nothing;
    select balance into v_balance from public.driver_operational_wallets where driver_id=s.driver_id for update;
    if coalesce(v_balance,0)>=v_fee then
      update public.driver_operational_wallets set balance=balance-v_fee,updated_at=now() where driver_id=s.driver_id;
      insert into public.driver_operational_transactions(driver_id,franchise_id,city_id,transaction_type,source,amount,status,reason,created_by,metadata,settled_at)
      values(s.driver_id,s.franchise_id,s.city_id,'debit','taximeter_fee',v_fee,'settled','Taxa de operação do taxímetro',s.driver_id,jsonb_build_object('taximeter_session_id',s.id,'gross_amount',coalesce(s.final_amount,0),'fee_mode',r.fee_mode,'fee_value',r.fee_value),now()) returning id into v_tx;
      update public.driver_taximeter_charges set status='settled',wallet_transaction_id=v_tx,settled_at=now(),updated_at=now() where id=c.id returning * into c;
    end if;
  end if;
  return to_jsonb(c);
end;$$;
revoke all on function public.settle_taximeter_financial_charge(uuid) from public, anon, authenticated;
grant execute on function public.settle_taximeter_financial_charge(uuid) to service_role;

create or replace function public.get_my_taximeter_financial_summary(p_from timestamptz default now()-interval '30 days',p_to timestamptz default now())
returns jsonb language plpgsql stable security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_role text:=public.jwt_app_role(); v_franchise uuid; v_balance numeric:=0; r record; v_recent jsonb;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role<>'driver' then raise exception 'Acesso exclusivo do motorista'; end if;
  select franchise_id into v_franchise from public.drivers where id=v_uid;
  select coalesce(balance,0) into v_balance from public.driver_operational_wallets where driver_id=v_uid;
  select coalesce(sum(gross_amount),0) gross,coalesce(sum(fee_amount),0) fees,coalesce(sum(fee_amount) filter(where status='pending'),0) pending,coalesce(sum(driver_net_amount),0) net,count(*) total into r from public.driver_taximeter_charges where driver_id=v_uid and created_at between coalesce(p_from,now()-interval '30 days') and coalesce(p_to,now());
  select coalesce(jsonb_agg(x order by x.created_at desc),'[]'::jsonb) into v_recent from (select c.id,c.session_id,c.gross_amount,c.fee_amount,c.driver_net_amount,c.status,c.fee_mode,c.fee_value,c.created_at from public.driver_taximeter_charges c where c.driver_id=v_uid order by c.created_at desc limit 10) x;
  return jsonb_build_object('gross_amount',r.gross,'fee_amount',r.fees,'pending_amount',r.pending,'driver_net_amount',r.net,'charges_count',r.total,'wallet_balance',v_balance,'effective_rule',(select to_jsonb(e) from public.effective_taximeter_financial_rule(v_franchise) e),'recent',v_recent);
end;$$;
revoke all on function public.get_my_taximeter_financial_summary(timestamptz,timestamptz) from public, anon;
grant execute on function public.get_my_taximeter_financial_summary(timestamptz,timestamptz) to authenticated, service_role;

create or replace function public.settle_driver_taximeter_pending_fees(p_driver_id uuid default null)
returns jsonb language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_role text:=public.jwt_app_role(); v_own uuid:=public.jwt_franchise_id(); v_target uuid; v_driver public.drivers%rowtype; v_balance numeric:=0; c public.driver_taximeter_charges%rowtype; v_tx uuid; v_count int:=0; v_total numeric:=0; v_pending numeric:=0;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role='driver' then v_target:=v_uid; if p_driver_id is not null and p_driver_id<>v_uid then raise exception 'Sem permissão'; end if;
  elsif v_role in ('super_admin','franchise_admin') then v_target:=p_driver_id; if v_target is null then raise exception 'Informe o motorista'; end if;
  else raise exception 'Sem permissão'; end if;
  select * into v_driver from public.drivers where id=v_target; if not found then raise exception 'Motorista não encontrado'; end if;
  if v_role='franchise_admin' and v_driver.franchise_id is distinct from v_own then raise exception 'Motorista fora da sua franquia'; end if;
  insert into public.driver_operational_wallets(driver_id) values(v_target) on conflict(driver_id) do nothing;
  select balance into v_balance from public.driver_operational_wallets where driver_id=v_target for update;
  for c in select * from public.driver_taximeter_charges where driver_id=v_target and status='pending' order by created_at for update loop
    exit when coalesce(v_balance,0)<c.fee_amount;
    update public.driver_operational_wallets set balance=balance-c.fee_amount,updated_at=now() where driver_id=v_target returning balance into v_balance;
    insert into public.driver_operational_transactions(driver_id,franchise_id,city_id,transaction_type,source,amount,status,reason,created_by,metadata,settled_at)
    values(c.driver_id,c.franchise_id,c.city_id,'debit','taximeter_fee',c.fee_amount,'settled','Quitação de taxa pendente do taxímetro',v_uid,jsonb_build_object('taximeter_session_id',c.session_id,'charge_id',c.id),now()) returning id into v_tx;
    update public.driver_taximeter_charges set status='settled',wallet_transaction_id=v_tx,settled_at=now(),updated_at=now() where id=c.id;
    v_count:=v_count+1; v_total:=v_total+c.fee_amount;
  end loop;
  select coalesce(sum(fee_amount),0) into v_pending from public.driver_taximeter_charges where driver_id=v_target and status='pending';
  return jsonb_build_object('settled_count',v_count,'settled_amount',v_total,'pending_amount',v_pending,'wallet_balance',v_balance);
end;$$;
revoke all on function public.settle_driver_taximeter_pending_fees(uuid) from public, anon;
grant execute on function public.settle_driver_taximeter_pending_fees(uuid) to authenticated, service_role;

create or replace function public.finish_driver_taximeter(p_session_id uuid,p_lat double precision,p_lng double precision,p_payment_method text default null)
returns jsonb language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_tick jsonb; v_amount numeric; v_distance numeric; v_elapsed integer; v_financial jsonb;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  perform 1 from public.driver_taximeter_sessions where id=p_session_id and driver_id=v_uid and status='running'; if not found then raise exception 'Taxímetro não está em andamento'; end if;
  v_tick:=public.tick_driver_taximeter(p_session_id,p_lat,p_lng);
  select current_amount,distance_m,elapsed_seconds into v_amount,v_distance,v_elapsed from public.driver_taximeter_sessions where id=p_session_id and driver_id=v_uid for update;
  update public.driver_taximeter_sessions set status='finished',ended_at=now(),end_lat=p_lat,end_lng=p_lng,final_amount=v_amount,payment_method=nullif(trim(coalesce(p_payment_method,'')),''),updated_at=now() where id=p_session_id and driver_id=v_uid;
  v_financial:=public.settle_taximeter_financial_charge(p_session_id);
  return jsonb_build_object('ok',true,'session_id',p_session_id,'status','finished','final_amount',v_amount,'distance_m',v_distance,'elapsed_seconds',v_elapsed,'payment_method',nullif(trim(coalesce(p_payment_method,'')),''),'financial',v_financial);
end;$$;
revoke all on function public.finish_driver_taximeter(uuid,double precision,double precision,text) from public, anon;
grant execute on function public.finish_driver_taximeter(uuid,double precision,double precision,text) to authenticated, service_role;

drop function if exists public.get_taximeter_operations_report(timestamptz,timestamptz,integer);
create function public.get_taximeter_operations_report(p_from timestamptz default now()-interval '30 days',p_to timestamptz default now(),p_limit integer default 1000)
returns table(session_id uuid,driver_id uuid,driver_name text,franchise_id uuid,franchise_name text,city_id uuid,city_name text,status text,started_at timestamptz,ended_at timestamptz,distance_m numeric,elapsed_seconds integer,final_amount numeric,current_amount numeric,payment_method text,multiplier numeric,fee_amount numeric,fee_status text,driver_net_amount numeric,fee_mode text,fee_value numeric)
language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_role text:=public.jwt_app_role(); v_franchise uuid:=public.jwt_franchise_id();
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role not in ('super_admin','franchise_admin') then raise exception 'Acesso restrito à operação'; end if;
  return query select s.id,s.driver_id,p.full_name,s.franchise_id,coalesce(f.trade_name,f.legal_name),s.city_id,c.name,s.status,s.started_at,s.ended_at,s.distance_m,s.elapsed_seconds,s.final_amount,s.current_amount,s.payment_method,s.multiplier,coalesce(ch.fee_amount,0),coalesce(ch.status,case when s.status='finished' then 'not_charged' else null end),coalesce(ch.driver_net_amount,s.final_amount),ch.fee_mode,ch.fee_value
  from public.driver_taximeter_sessions s left join public.profiles p on p.id=s.driver_id left join public.franchises f on f.id=s.franchise_id left join public.cities c on c.id=s.city_id left join public.driver_taximeter_charges ch on ch.session_id=s.id
  where s.started_at>=coalesce(p_from,now()-interval '30 days') and s.started_at<=coalesce(p_to,now()) and (v_role='super_admin' or s.franchise_id=v_franchise)
  order by s.started_at desc limit greatest(1,least(coalesce(p_limit,1000),5000));
end;$$;
revoke all on function public.get_taximeter_operations_report(timestamptz,timestamptz,integer) from public, anon;
grant execute on function public.get_taximeter_operations_report(timestamptz,timestamptz,integer) to authenticated, service_role;
