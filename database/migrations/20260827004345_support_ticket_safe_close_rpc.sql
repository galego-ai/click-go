create or replace function public.close_support_ticket(p_ticket_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_ticket public.support_tickets%rowtype;
  v_allowed boolean:=false;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_ticket from public.support_tickets where id=p_ticket_id for update;
  if not found then raise exception 'Chamado não encontrado'; end if;

  if v_ticket.requester_id=v_uid then
    v_allowed:=true;
  elsif v_role='super_admin' then
    v_allowed:=true;
  elsif v_role='franchise_admin' and v_ticket.franchise_id=public.jwt_franchise_id() then
    v_allowed:=true;
  elsif v_role='operator' and v_ticket.franchise_id=public.staff_franchise_id() and public.staff_has_permission('support') then
    v_allowed:=true;
  end if;
  if not v_allowed then raise exception 'Acesso negado ao chamado'; end if;

  if v_ticket.status<>'closed' then
    update public.support_tickets
       set status='closed',closed_at=now(),updated_at=now()
     where id=p_ticket_id;
  end if;

  return jsonb_build_object('ok',true,'ticket_id',p_ticket_id,'status','closed');
end;
$$;
revoke all on function public.close_support_ticket(uuid) from public,anon;
grant execute on function public.close_support_ticket(uuid) to authenticated,service_role;
