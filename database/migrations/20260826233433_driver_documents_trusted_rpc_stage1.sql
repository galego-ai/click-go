-- Stage 1: trusted driver-document mutation RPCs and Matrix read access.

create or replace function public.upsert_my_driver_document(
  p_document_type text,
  p_file_path text
)
returns table(document_id uuid, document_status text)
language plpgsql
security definer
set search_path to 'public','storage','pg_temp'
as $$
declare
  v_user uuid := auth.uid();
  v_doc_id uuid;
  v_path text := btrim(coalesce(p_file_path,''));
begin
  if v_user is null then raise exception 'Faça login novamente para enviar documentos.'; end if;
  if not exists (select 1 from public.profiles p where p.id=v_user and p.role='driver' and p.active=true)
     or not exists (select 1 from public.drivers d where d.id=v_user) then
    raise exception 'Cadastro de motorista não encontrado ou inativo.';
  end if;
  if p_document_type is null or p_document_type not in (
    'profile_photo','cnh_frente','cnh_verso','selfie_cnh','crlv','comprovante_residencia'
  ) then raise exception 'Tipo de documento inválido.'; end if;
  if v_path='' or split_part(v_path,'/',1)<>v_user::text or v_path like '/%' then
    raise exception 'Caminho do documento inválido.';
  end if;
  if not exists (
    select 1 from storage.objects o
    where o.bucket_id='driver-documents' and o.name=v_path
      and split_part(o.name,'/',1)=v_user::text
  ) then raise exception 'Arquivo do documento não foi encontrado no armazenamento do motorista.'; end if;

  select dd.id into v_doc_id
  from public.driver_documents dd
  where dd.driver_id=v_user and dd.document_type=p_document_type
  order by dd.created_at desc limit 1 for update;

  if v_doc_id is null then
    insert into public.driver_documents(driver_id,document_type,file_path,status,rejection_reason,reviewed_by,reviewed_at)
    values(v_user,p_document_type,v_path,'pending',null,null,null)
    returning id into v_doc_id;
  else
    update public.driver_documents
       set file_path=v_path,status='pending',rejection_reason=null,reviewed_by=null,reviewed_at=null
     where id=v_doc_id and driver_id=v_user;
  end if;
  return query select v_doc_id,'pending'::text;
end;
$$;
revoke all on function public.upsert_my_driver_document(text,text) from public,anon;
grant execute on function public.upsert_my_driver_document(text,text) to authenticated,service_role;

create or replace function public.review_driver_document(
  p_document_id uuid,
  p_approve boolean,
  p_reason text default null
)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_actor uuid:=auth.uid();
  v_role text;
  v_doc public.driver_documents%rowtype;
  v_driver public.drivers%rowtype;
  v_reason text:=nullif(btrim(coalesce(p_reason,'')),'');
begin
  if v_actor is null then raise exception 'Não autenticado'; end if;
  v_role:=public.current_active_management_role();
  if v_role not in ('super_admin','franchise_admin','operator') then raise exception 'Acesso restrito à gestão autorizada'; end if;
  select * into v_doc from public.driver_documents where id=p_document_id for update;
  if not found then raise exception 'Documento não encontrado'; end if;
  select * into v_driver from public.drivers where id=v_doc.driver_id;
  if not found then raise exception 'Motorista do documento não encontrado'; end if;

  if v_role='franchise_admin' then
    if v_driver.franchise_id is null or v_driver.franchise_id is distinct from public.jwt_franchise_id()
       or v_driver.city_id is null or not public.can_access_city(v_driver.city_id)
       or not exists (select 1 from public.franchises f where f.id=v_driver.franchise_id and f.active=true and f.deleted_at is null and f.blocked_at is null) then
      raise exception 'Documento fora do escopo da sua franquia';
    end if;
  elsif v_role='operator' then
    if v_driver.franchise_id is null or v_driver.franchise_id is distinct from public.staff_franchise_id()
       or v_driver.city_id is null or not public.can_access_city(v_driver.city_id)
       or not public.staff_has_permission('drivers') then
      raise exception 'Documento fora do escopo ou sem permissão de motoristas';
    end if;
  end if;
  if not coalesce(p_approve,false) and v_reason is null then raise exception 'Informe o motivo da reprovação'; end if;

  update public.driver_documents
     set status=case when coalesce(p_approve,false) then 'approved' else 'rejected' end,
         rejection_reason=case when coalesce(p_approve,false) then null else v_reason end,
         reviewed_by=v_actor,reviewed_at=now()
   where id=p_document_id;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_actor,case when coalesce(p_approve,false) then 'approve_driver_document' else 'reject_driver_document' end,
         'driver_document',p_document_id::text,
         jsonb_build_object('driver_id',v_doc.driver_id,'document_type',v_doc.document_type,
                            'franchise_id',v_driver.franchise_id,'city_id',v_driver.city_id,
                            'reviewer_role',v_role,'reason',case when coalesce(p_approve,false) then null else v_reason end));
  return jsonb_build_object('ok',true,'document_id',p_document_id,'driver_id',v_doc.driver_id,
                            'status',case when coalesce(p_approve,false) then 'approved' else 'rejected' end);
end;
$$;
revoke all on function public.review_driver_document(uuid,boolean,text) from public,anon;
grant execute on function public.review_driver_document(uuid,boolean,text) to authenticated,service_role;

drop policy if exists super_admin_driver_documents_select on public.driver_documents;
create policy super_admin_driver_documents_select on public.driver_documents for select to authenticated
using (public.current_active_management_role()='super_admin');

drop policy if exists super_admin_read_driver_documents on storage.objects;
create policy super_admin_read_driver_documents on storage.objects for select to authenticated
using (bucket_id='driver-documents' and public.current_active_management_role()='super_admin');
