-- CLICK-GO: sensitive driver profile mutations via trusted self-service RPC.

revoke all on table public.driver_profiles from anon, authenticated;
grant select on table public.driver_profiles to authenticated;
grant all on table public.driver_profiles to service_role;

drop policy if exists driver_profiles_self_all on public.driver_profiles;
drop policy if exists driver_profiles_self_select on public.driver_profiles;
create policy driver_profiles_self_select on public.driver_profiles
for select to authenticated
using (driver_id = auth.uid());

create or replace function public.update_my_driver_profile(
  p_cpf text default null,
  p_cnh_number text default null,
  p_cnh_category text default null,
  p_cnh_expiry date default null,
  p_pix_key text default null,
  p_emergency_contact_name text default null,
  p_emergency_contact_phone text default null
)
returns jsonb
language plpgsql
security definer
set search_path = public, pg_temp
as $function$
declare
  v_uid uuid := auth.uid();
  v_dp public.driver_profiles%rowtype;
  v_driver public.drivers%rowtype;
  v_cpf text;
  v_cnh_number text;
  v_cnh_category text;
  v_pix text;
  v_emergency_name text;
  v_emergency_phone text;
  v_identity_changed boolean := false;
  v_pix_changed boolean := false;
  v_emergency_changed boolean := false;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if not exists(select 1 from public.profiles p where p.id=v_uid and p.role='driver' and p.active=true) then
    raise exception 'Perfil de motorista não encontrado ou inativo';
  end if;

  select * into v_driver from public.drivers where id=v_uid for update;
  if not found then raise exception 'Cadastro de motorista não encontrado'; end if;

  select * into v_dp from public.driver_profiles where driver_id=v_uid for update;
  if not found then
    insert into public.driver_profiles(driver_id) values(v_uid)
    returning * into v_dp;
  end if;

  v_cpf := case
    when p_cpf is null then v_dp.cpf
    else nullif(regexp_replace(p_cpf,'[^0-9]','','g'),'')
  end;
  if v_cpf is not null and not public.is_valid_cpf(v_cpf) then
    raise exception 'CPF inválido';
  end if;

  v_cnh_number := case when p_cnh_number is null then v_dp.cnh_number else nullif(btrim(p_cnh_number),'') end;
  v_cnh_category := case when p_cnh_category is null then v_dp.cnh_category else nullif(upper(btrim(p_cnh_category)),'') end;
  if v_cnh_category is not null and v_cnh_category !~ '^[A-Z]{1,3}$' then
    raise exception 'Categoria da CNH inválida';
  end if;
  if p_cnh_expiry is not null and p_cnh_expiry < current_date - interval '10 years' then
    raise exception 'Data de validade da CNH inválida';
  end if;

  v_pix := case when p_pix_key is null then v_dp.pix_key else nullif(btrim(p_pix_key),'') end;
  v_emergency_name := case when p_emergency_contact_name is null then v_dp.emergency_contact_name else nullif(btrim(p_emergency_contact_name),'') end;
  v_emergency_phone := case when p_emergency_contact_phone is null then v_dp.emergency_contact_phone else nullif(regexp_replace(p_emergency_contact_phone,'[^0-9+]','','g'),'') end;

  v_identity_changed :=
       v_dp.cpf is distinct from v_cpf
    or v_dp.cnh_number is distinct from v_cnh_number
    or v_dp.cnh_category is distinct from v_cnh_category
    or (p_cnh_expiry is not null and v_dp.cnh_expiry is distinct from p_cnh_expiry);
  v_pix_changed := v_dp.pix_key is distinct from v_pix;
  v_emergency_changed := v_dp.emergency_contact_name is distinct from v_emergency_name
                      or v_dp.emergency_contact_phone is distinct from v_emergency_phone;

  update public.driver_profiles
     set cpf=v_cpf,
         cnh_number=v_cnh_number,
         cnh_category=v_cnh_category,
         cnh_expiry=case when p_cnh_expiry is null then v_dp.cnh_expiry else p_cnh_expiry end,
         pix_key=v_pix,
         emergency_contact_name=v_emergency_name,
         emergency_contact_phone=v_emergency_phone,
         updated_at=now()
   where driver_id=v_uid;

  if v_identity_changed and v_driver.status='approved' then
    update public.drivers
       set status='pending',
           online=false,
           approved_at=null,
           approved_by=null,
           rejection_reason=null
     where id=v_uid;

    update public.driver_documents
       set status='pending',
           rejection_reason=null,
           reviewed_by=null,
           reviewed_at=null
     where driver_id=v_uid
       and document_type in ('cnh_frente','cnh_verso','selfie_cnh');
  end if;

  if v_identity_changed or v_pix_changed or v_emergency_changed then
    insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
    values(
      v_uid,
      'driver_update_sensitive_profile',
      'driver_profiles',
      v_uid::text,
      jsonb_build_object(
        'identity_changed',v_identity_changed,
        'pix_changed',v_pix_changed,
        'emergency_contact_changed',v_emergency_changed,
        'driver_was_approved',v_driver.status='approved'
      )
    );
  end if;

  return jsonb_build_object(
    'ok',true,
    'identity_changed',v_identity_changed,
    'requires_review',v_identity_changed and v_driver.status='approved'
  );
end;
$function$;

revoke all on function public.update_my_driver_profile(text,text,text,date,text,text,text) from public, anon;
grant execute on function public.update_my_driver_profile(text,text,text,date,text,text,text) to authenticated, service_role;
