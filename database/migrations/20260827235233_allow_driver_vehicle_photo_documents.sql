-- CLICK-GO: allow optional vehicle inspection photos uploaded by the driver app.
-- These photos use the same protected driver-documents bucket and audited review flow.

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
  if v_user is null then
    raise exception 'Faça login novamente para enviar documentos.';
  end if;

  if not exists (
    select 1 from public.profiles p
    where p.id=v_user and p.role='driver' and p.active=true
  ) or not exists (select 1 from public.drivers d where d.id=v_user) then
    raise exception 'Cadastro de motorista não encontrado ou inativo.';
  end if;

  if p_document_type is null or p_document_type not in (
    'profile_photo','cnh_frente','cnh_verso','selfie_cnh','crlv','comprovante_residencia',
    'vehicle_front','vehicle_left','vehicle_right','vehicle_rear'
  ) then
    raise exception 'Tipo de documento inválido.';
  end if;

  if v_path='' or split_part(v_path,'/',1)<>v_user::text or v_path like '/%' then
    raise exception 'Caminho do documento inválido.';
  end if;

  if not exists (
    select 1 from storage.objects o
    where o.bucket_id='driver-documents'
      and o.name=v_path
      and split_part(o.name,'/',1)=v_user::text
  ) then
    raise exception 'Arquivo do documento não foi encontrado no armazenamento do motorista.';
  end if;

  select dd.id into v_doc_id
  from public.driver_documents dd
  where dd.driver_id=v_user and dd.document_type=p_document_type
  order by dd.created_at desc
  limit 1
  for update;

  if v_doc_id is null then
    insert into public.driver_documents(
      driver_id,document_type,file_path,status,rejection_reason,reviewed_by,reviewed_at
    ) values (
      v_user,p_document_type,v_path,'pending',null,null,null
    ) returning id into v_doc_id;
  else
    update public.driver_documents
       set file_path=v_path,
           status='pending',
           rejection_reason=null,
           reviewed_by=null,
           reviewed_at=null
     where id=v_doc_id and driver_id=v_user;
  end if;

  return query select v_doc_id,'pending'::text;
end;
$$;

revoke all on function public.upsert_my_driver_document(text,text) from public,anon;
grant execute on function public.upsert_my_driver_document(text,text) to authenticated,service_role;
