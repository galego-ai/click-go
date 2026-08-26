create or replace function public.guard_driver_document_legacy_write()
returns trigger
language plpgsql
security definer
set search_path to 'public','storage','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
begin
  if tg_op='INSERT' then
    if v_uid is null
       or new.driver_id is distinct from v_uid
       or new.document_type not in ('profile_photo','cnh_frente','cnh_verso','selfie_cnh','crlv','comprovante_residencia')
       or new.status is distinct from 'pending'
       or new.rejection_reason is not null
       or new.reviewed_by is not null
       or new.reviewed_at is not null
       or split_part(new.file_path,'/',1)<>v_uid::text
       or not exists (
          select 1 from storage.objects o
          where o.bucket_id='driver-documents' and o.name=new.file_path
            and split_part(o.name,'/',1)=v_uid::text
       ) then
      raise exception 'Envio direto de documento fora das regras permitidas';
    end if;
    return new;
  end if;

  if tg_op='UPDATE' then
    if new.driver_id is distinct from old.driver_id
       or new.document_type is distinct from old.document_type
       or new.created_at is distinct from old.created_at then
      raise exception 'Identidade do documento é imutável';
    end if;

    -- Trusted re-upload path. Browser PATCH by a driver remains blocked by RLS.
    if v_role='driver' or (v_role is null and v_uid=old.driver_id) then
      if v_uid is distinct from old.driver_id
         or new.status is distinct from 'pending'
         or new.rejection_reason is not null
         or new.reviewed_by is not null
         or new.reviewed_at is not null
         or split_part(new.file_path,'/',1)<>v_uid::text
         or not exists (
            select 1 from storage.objects o
            where o.bucket_id='driver-documents' and o.name=new.file_path
              and split_part(o.name,'/',1)=v_uid::text
         ) then
        raise exception 'Reenvio de documento fora das regras permitidas';
      end if;
      return new;
    end if;

    if new.file_path is distinct from old.file_path then
      raise exception 'O arquivo não pode ser trocado durante a revisão';
    end if;
    if v_role not in ('super_admin','franchise_admin','operator') then
      raise exception 'Atualização direta de documento restrita à revisão autorizada';
    end if;
    if new.status not in ('approved','rejected')
       or new.reviewed_by is distinct from v_uid
       or new.reviewed_at is null
       or (new.status='approved' and new.rejection_reason is not null)
       or (new.status='rejected' and nullif(btrim(coalesce(new.rejection_reason,'')),'') is null) then
      raise exception 'Revisão direta fora das regras permitidas';
    end if;
    return new;
  end if;

  raise exception 'Operação direta não permitida em documentos de motorista';
end;
$$;
