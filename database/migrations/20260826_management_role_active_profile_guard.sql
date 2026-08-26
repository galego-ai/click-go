create or replace function public.current_active_management_role()
returns text
language plpgsql
stable
security definer
set search_path=public,pg_temp
as $$
declare
  v_uid uuid:=auth.uid();
  v_claim_role text:=coalesce(auth.jwt()->'app_metadata'->>'role','');
  v_claim_fid text:=coalesce(auth.jwt()->'app_metadata'->>'franchise_id','');
  v_profile_role text;
  v_profile_fid uuid;
  v_profile_active boolean;
  v_staff_fid uuid;
begin
  if v_uid is null or v_claim_role not in ('super_admin','franchise_admin','operator') then return ''; end if;

  select p.role::text,p.franchise_id,p.active
    into v_profile_role,v_profile_fid,v_profile_active
  from public.profiles p
  where p.id=v_uid;

  if not found or not coalesce(v_profile_active,false) or v_profile_role is distinct from v_claim_role then return ''; end if;

  if v_claim_role='super_admin' then
    return 'super_admin';
  elsif v_claim_role='franchise_admin' then
    if v_profile_fid is null or v_claim_fid='' or v_profile_fid::text<>v_claim_fid then return ''; end if;
    return 'franchise_admin';
  else
    select sp.franchise_id into v_staff_fid
    from public.franchise_staff_permissions sp
    where sp.profile_id=v_uid and sp.active
    limit 1;
    if v_staff_fid is null then return ''; end if;
    if v_claim_fid<>'' and v_staff_fid::text<>v_claim_fid then return ''; end if;
    return 'operator';
  end if;
end;
$$;
revoke all on function public.current_active_management_role() from public,anon;
grant execute on function public.current_active_management_role() to authenticated,service_role;

create or replace function public.jwt_app_role()
returns text
language sql
stable
set search_path=''
as $$
  with c as (
    select coalesce(auth.jwt()->'app_metadata'->>'role','')::text as raw_role
  )
  select case
    when c.raw_role in ('super_admin','franchise_admin','operator') then coalesce(public.current_active_management_role(),'')
    else c.raw_role
  end
  from c;
$$;
