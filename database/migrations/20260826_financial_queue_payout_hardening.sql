-- CLICK-GO — integridade das filas financeiras e reserva de repasses

alter table public.payouts drop constraint if exists payouts_status_check;
alter table public.payouts add constraint payouts_status_check
  check (status in ('requested','approved','processing','paid','rejected','cancelled'));

alter table public.advance_requests drop constraint if exists advance_requests_status_check;
alter table public.advance_requests add constraint advance_requests_status_check
  check (status in ('requested','approved','paid','rejected','cancelled'));

create or replace function public.request_franchise_payout(p_amount numeric,p_destination_key text)
returns public.payouts
language plpgsql security definer set search_path=public,pg_temp
as $$
declare
  v_uid uuid:=auth.uid(); v_fid uuid; v_wallet public.franchise_wallets%rowtype; v_payout public.payouts%rowtype;
begin
  if public.current_active_management_role()<>'franchise_admin' then raise exception 'Acesso restrito ao administrador ativo da franquia'; end if;
  select p.franchise_id into v_fid from public.profiles p where p.id=v_uid and p.active and p.role='franchise_admin';
  if v_fid is null then raise exception 'Franquia não identificada'; end if;
  if coalesce(p_amount,0)<=0 then raise exception 'Valor do repasse deve ser maior que zero'; end if;
  if nullif(btrim(coalesce(p_destination_key,'')),'') is null then raise exception 'Chave PIX obrigatória'; end if;
  select * into v_wallet from public.franchise_wallets where franchise_id=v_fid for update;
  if not found then raise exception 'Carteira da franquia não encontrada'; end if;
  if v_wallet.available_balance<p_amount then raise exception 'Saldo disponível insuficiente'; end if;
  update public.franchise_wallets set available_balance=available_balance-p_amount,held_balance=held_balance+p_amount,updated_at=now() where franchise_id=v_fid;
  insert into public.payouts(franchise_id,driver_id,amount,destination_type,destination_key,status,notes)
  values(v_fid,null,round(p_amount,2),'pix',btrim(p_destination_key),'requested','Solicitado pelo painel do franqueado') returning * into v_payout;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'request_franchise_payout','payouts',v_payout.id::text,jsonb_build_object('franchise_id',v_fid,'amount',v_payout.amount,'destination_type','pix'));
  return v_payout;
end;$$;
revoke all on function public.request_franchise_payout(numeric,text) from public,anon;
grant execute on function public.request_franchise_payout(numeric,text) to authenticated,service_role;

create or replace function public.matrix_set_payout_status(p_payout_id uuid,p_status text,p_notes text default null)
returns public.payouts
language plpgsql security definer set search_path=public,pg_temp
as $$
declare
  v_uid uuid:=auth.uid(); v_p public.payouts%rowtype; v_w public.franchise_wallets%rowtype; v_old text;
begin
  if public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_status not in ('approved','processing','paid','rejected','cancelled') then raise exception 'Status de repasse inválido'; end if;
  select * into v_p from public.payouts where id=p_payout_id for update;
  if not found then raise exception 'Repasse não encontrado'; end if;
  if v_p.franchise_id is null or v_p.driver_id is not null then raise exception 'Este fluxo processa somente repasses de franquia'; end if;
  v_old:=v_p.status;
  if v_old in ('paid','rejected','cancelled') then raise exception 'Repasse já finalizado'; end if;
  if v_old='approved' and p_status not in ('processing','paid','rejected','cancelled') then raise exception 'Transição inválida'; end if;
  if v_old='processing' and p_status not in ('paid','rejected','cancelled') then raise exception 'Transição inválida'; end if;
  select * into v_w from public.franchise_wallets where franchise_id=v_p.franchise_id for update;
  if not found then raise exception 'Carteira da franquia não encontrada'; end if;
  if v_w.held_balance<v_p.amount then raise exception 'Saldo reservado inconsistente'; end if;
  if p_status='paid' then
    update public.franchise_wallets set held_balance=held_balance-v_p.amount,updated_at=now() where franchise_id=v_p.franchise_id;
  elsif p_status in ('rejected','cancelled') then
    update public.franchise_wallets set held_balance=held_balance-v_p.amount,available_balance=available_balance+v_p.amount,updated_at=now() where franchise_id=v_p.franchise_id;
  end if;
  update public.payouts set status=p_status,
    approved_at=case when p_status in ('approved','processing','paid') then coalesce(approved_at,now()) else approved_at end,
    paid_at=case when p_status='paid' then coalesce(paid_at,now()) else paid_at end,
    notes=coalesce(p_notes,notes)
  where id=p_payout_id returning * into v_p;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'matrix_set_payout_status','payouts',v_p.id::text,jsonb_build_object('franchise_id',v_p.franchise_id,'amount',v_p.amount,'old_status',v_old,'new_status',p_status));
  return v_p;
end;$$;
revoke all on function public.matrix_set_payout_status(uuid,text,text) from public,anon;
grant execute on function public.matrix_set_payout_status(uuid,text,text) to authenticated,service_role;

create or replace function public.matrix_set_payment_status(p_payment_id uuid,p_status text)
returns public.payments
language plpgsql security definer set search_path=public,pg_temp
as $$
declare v_uid uuid:=auth.uid();v_p public.payments%rowtype;v_old text;
begin
  if public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_status not in ('pending','authorized','paid','failed','cancelled') then raise exception 'Status de pagamento inválido. Estorno exige fluxo contábil próprio.'; end if;
  select * into v_p from public.payments where id=p_payment_id for update;
  if not found then raise exception 'Pagamento não encontrado'; end if;
  v_old:=v_p.status;
  if v_old='paid' and p_status<>v_old then raise exception 'Pagamento já liquidado. Use o fluxo de estorno quando disponível.'; end if;
  if v_old in ('cancelled','refunded') and p_status<>v_old then raise exception 'Pagamento já finalizado'; end if;
  if v_old='authorized' and p_status not in ('authorized','paid','failed','cancelled') then raise exception 'Transição inválida'; end if;
  if v_old='failed' and p_status not in ('failed','pending','cancelled') then raise exception 'Transição inválida'; end if;
  update public.payments set status=p_status,paid_at=case when p_status='paid' then coalesce(paid_at,now()) else paid_at end where id=p_payment_id returning * into v_p;
  if p_status is distinct from v_old then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(v_uid,'matrix_set_payment_status','payments',v_p.id::text,jsonb_build_object('old_status',v_old,'new_status',p_status,'amount',v_p.amount,'purpose',v_p.purpose,'franchise_id',v_p.franchise_id));
  end if;
  return v_p;
end;$$;
revoke all on function public.matrix_set_payment_status(uuid,text) from public,anon;
grant execute on function public.matrix_set_payment_status(uuid,text) to authenticated,service_role;

create or replace function public.matrix_set_advance_status(p_advance_id uuid,p_status text)
returns public.advance_requests
language plpgsql security definer set search_path=public,pg_temp
as $$
declare v_uid uuid:=auth.uid();v_a public.advance_requests%rowtype;v_old text;
begin
  if public.current_active_management_role()<>'super_admin' then raise exception 'Acesso restrito ao Super Admin ativo'; end if;
  if p_status not in ('requested','approved','paid','rejected','cancelled') then raise exception 'Status de antecipação inválido'; end if;
  select * into v_a from public.advance_requests where id=p_advance_id for update;
  if not found then raise exception 'Antecipação não encontrada'; end if;
  v_old:=v_a.status;
  if v_old in ('paid','rejected','cancelled') and p_status<>v_old then raise exception 'Antecipação já finalizada'; end if;
  if v_old='approved' and p_status not in ('approved','paid','rejected','cancelled') then raise exception 'Transição inválida'; end if;
  update public.advance_requests set status=p_status,
    processed_at=case when p_status in ('approved','paid','rejected','cancelled') then coalesce(processed_at,now()) else processed_at end
  where id=p_advance_id returning * into v_a;
  if p_status is distinct from v_old then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(v_uid,'matrix_set_advance_status','advance_requests',v_a.id::text,jsonb_build_object('old_status',v_old,'new_status',p_status,'amount',v_a.amount,'fee',v_a.fee,'franchise_id',v_a.franchise_id,'driver_id',v_a.driver_id));
  end if;
  return v_a;
end;$$;
revoke all on function public.matrix_set_advance_status(uuid,text) from public,anon;
grant execute on function public.matrix_set_advance_status(uuid,text) to authenticated,service_role;

-- Finance table RLS.
drop policy if exists franchise_admin_request_payout on public.payouts;
drop policy if exists payouts_driver_insert on public.payouts;
drop policy if exists super_admin_payouts_all on public.payouts;
drop policy if exists super_admin_payouts_select on public.payouts;
create policy super_admin_payouts_select on public.payouts for select to authenticated using(public.current_active_management_role()='super_admin');

drop policy if exists franchise_admin_own_advances_all on public.advance_requests;
drop policy if exists super_admin_advances_all on public.advance_requests;
drop policy if exists franchise_admin_own_advances_select on public.advance_requests;
drop policy if exists super_admin_advances_select on public.advance_requests;
create policy franchise_admin_own_advances_select on public.advance_requests for select to authenticated using(public.current_active_management_role()='franchise_admin' and franchise_id=public.current_profile_franchise_id());
create policy super_admin_advances_select on public.advance_requests for select to authenticated using(public.current_active_management_role()='super_admin');

drop policy if exists advance_driver_insert on public.advance_requests;
create policy advance_driver_insert on public.advance_requests for insert to authenticated with check(
  driver_id=auth.uid() and status='requested' and amount>0 and processed_at is null
  and exists(select 1 from public.drivers d where d.id=auth.uid() and d.franchise_id is not distinct from advance_requests.franchise_id)
);

drop policy if exists super_admin_payments_all on public.payments;
drop policy if exists super_admin_payments_select on public.payments;
create policy super_admin_payments_select on public.payments for select to authenticated using(public.current_active_management_role()='super_admin');

revoke all on public.payouts from anon;
revoke insert,update,delete,truncate,references,trigger on public.payouts from authenticated;
grant select on public.payouts to authenticated;

revoke all on public.advance_requests from anon;
revoke update,delete,truncate,references,trigger on public.advance_requests from authenticated;
grant select,insert on public.advance_requests to authenticated;

revoke all on public.payments from anon;
revoke insert,update,delete,truncate,references,trigger on public.payments from authenticated;
grant select on public.payments to authenticated;

grant all on public.payouts,public.advance_requests,public.payments to service_role;
