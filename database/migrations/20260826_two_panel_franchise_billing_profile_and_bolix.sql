create table if not exists public.franchise_billing_profiles (
  franchise_id uuid primary key references public.franchises(id) on delete cascade,
  payer_type text not null default 'cnpj' check (payer_type in ('cpf','cnpj')),
  name text,
  corporate_name text,
  document text not null,
  email text not null,
  phone text not null,
  street text not null,
  number text not null,
  neighborhood text not null,
  zipcode text not null,
  city text not null,
  state text not null,
  complement text,
  updated_by uuid references public.profiles(id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

alter table public.franchise_billing_profiles enable row level security;
revoke all on table public.franchise_billing_profiles from anon;
grant select on table public.franchise_billing_profiles to authenticated;

drop policy if exists super_admin_billing_profiles_select on public.franchise_billing_profiles;
create policy super_admin_billing_profiles_select on public.franchise_billing_profiles
for select to authenticated using (public.jwt_app_role() = 'super_admin');

drop policy if exists franchise_admin_billing_profile_select on public.franchise_billing_profiles;
create policy franchise_admin_billing_profile_select on public.franchise_billing_profiles
for select to authenticated using (public.jwt_app_role() = 'franchise_admin' and franchise_id = public.jwt_franchise_id());

drop policy if exists operator_billing_profile_select on public.franchise_billing_profiles;
create policy operator_billing_profile_select on public.franchise_billing_profiles
for select to authenticated using (public.jwt_app_role() = 'operator' and franchise_id = public.staff_franchise_id() and public.staff_has_permission('finance'));

create table if not exists public.franchise_invoice_bolix_charges (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references public.franchise_invoices(id) on delete cascade,
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  created_by uuid references public.profiles(id) on delete set null,
  provider text not null default 'efi',
  charge_id bigint not null unique,
  barcode text,
  pix_qrcode text,
  pix_qrcode_image text,
  link text,
  pdf_url text,
  amount numeric(12,2) not null check (amount >= 0),
  status text not null default 'active' check (status in ('active','paid','cancelled','expired','failed')),
  provider_status text,
  due_date date,
  paid_at timestamptz,
  raw_response jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists franchise_invoice_bolix_invoice_idx on public.franchise_invoice_bolix_charges(invoice_id, created_at desc);
create index if not exists franchise_invoice_bolix_franchise_idx on public.franchise_invoice_bolix_charges(franchise_id, created_at desc);

alter table public.franchise_invoice_bolix_charges enable row level security;
revoke all on table public.franchise_invoice_bolix_charges from anon;
grant select on table public.franchise_invoice_bolix_charges to authenticated;

drop policy if exists super_admin_invoice_bolix_select on public.franchise_invoice_bolix_charges;
create policy super_admin_invoice_bolix_select on public.franchise_invoice_bolix_charges
for select to authenticated using (public.jwt_app_role() = 'super_admin');

drop policy if exists franchise_admin_own_invoice_bolix_select on public.franchise_invoice_bolix_charges;
create policy franchise_admin_own_invoice_bolix_select on public.franchise_invoice_bolix_charges
for select to authenticated using (public.jwt_app_role() = 'franchise_admin' and franchise_id = public.jwt_franchise_id());

drop policy if exists operator_own_invoice_bolix_select on public.franchise_invoice_bolix_charges;
create policy operator_own_invoice_bolix_select on public.franchise_invoice_bolix_charges
for select to authenticated using (public.jwt_app_role() = 'operator' and franchise_id = public.staff_franchise_id() and public.staff_has_permission('finance'));

create or replace function public.get_franchise_billing_profile(p_franchise_id uuid default null)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_role text := public.jwt_app_role();
  v_target uuid;
  v_result jsonb;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if v_role = 'super_admin' then
    v_target := p_franchise_id;
  elsif v_role = 'franchise_admin' then
    v_target := public.jwt_franchise_id();
    if p_franchise_id is not null and p_franchise_id <> v_target then raise exception 'Acesso negado'; end if;
  elsif v_role = 'operator' and public.staff_has_permission('finance') then
    v_target := public.staff_franchise_id();
    if p_franchise_id is not null and p_franchise_id <> v_target then raise exception 'Acesso negado'; end if;
  else
    raise exception 'Acesso negado';
  end if;
  if v_target is null then raise exception 'Franquia não identificada'; end if;

  select to_jsonb(bp) || jsonb_build_object(
    'complete',
    bp.document <> '' and bp.email <> '' and bp.phone <> '' and bp.street <> '' and bp.number <> '' and bp.neighborhood <> '' and bp.zipcode <> '' and bp.city <> '' and bp.state <> '' and
    ((bp.payer_type = 'cpf' and coalesce(bp.name,'') <> '') or (bp.payer_type = 'cnpj' and coalesce(bp.corporate_name,'') <> ''))
  ) into v_result
  from public.franchise_billing_profiles bp where bp.franchise_id = v_target;

  if v_result is null then
    select jsonb_build_object(
      'franchise_id', f.id,
      'payer_type', case when length(regexp_replace(coalesce(f.document,''),'\D','','g')) = 11 then 'cpf' else 'cnpj' end,
      'name', case when length(regexp_replace(coalesce(f.document,''),'\D','','g')) = 11 then coalesce(f.legal_name,'') else '' end,
      'corporate_name', case when length(regexp_replace(coalesce(f.document,''),'\D','','g')) = 14 then coalesce(f.legal_name,'') else '' end,
      'document', regexp_replace(coalesce(f.document,''),'\D','','g'),
      'email', coalesce(f.contact_email,''),
      'phone', regexp_replace(coalesce(f.contact_phone,''),'\D','','g'),
      'street','', 'number','', 'neighborhood','', 'zipcode','', 'city','', 'state','', 'complement','',
      'complete', false
    ) into v_result from public.franchises f where f.id = v_target;
  end if;
  return coalesce(v_result, jsonb_build_object('franchise_id',v_target,'complete',false));
end;
$$;

revoke all on function public.get_franchise_billing_profile(uuid) from public, anon;
grant execute on function public.get_franchise_billing_profile(uuid) to authenticated;

create or replace function public.save_franchise_billing_profile(p_franchise_id uuid, p_profile jsonb)
returns jsonb
language plpgsql
security definer
set search_path = public, auth
as $$
declare
  v_role text := public.jwt_app_role();
  v_target uuid;
  v_type text := lower(trim(coalesce(p_profile->>'payer_type','')));
  v_document text := regexp_replace(coalesce(p_profile->>'document',''),'\D','','g');
  v_email text := lower(trim(coalesce(p_profile->>'email','')));
  v_phone text := regexp_replace(coalesce(p_profile->>'phone',''),'\D','','g');
  v_zip text := regexp_replace(coalesce(p_profile->>'zipcode',''),'\D','','g');
  v_state text := upper(trim(coalesce(p_profile->>'state','')));
  v_old jsonb;
  v_new jsonb;
begin
  if auth.uid() is null then raise exception 'Não autenticado'; end if;
  if v_role = 'super_admin' then
    v_target := p_franchise_id;
  elsif v_role = 'franchise_admin' then
    v_target := public.jwt_franchise_id();
    if p_franchise_id is not null and p_franchise_id <> v_target then raise exception 'Acesso negado'; end if;
  elsif v_role = 'operator' and public.staff_has_permission('finance') then
    v_target := public.staff_franchise_id();
    if p_franchise_id is not null and p_franchise_id <> v_target then raise exception 'Acesso negado'; end if;
  else
    raise exception 'Acesso negado';
  end if;
  if v_target is null then raise exception 'Franquia não identificada'; end if;
  if v_type not in ('cpf','cnpj') then raise exception 'Tipo de pagador inválido'; end if;
  if (v_type='cpf' and length(v_document)<>11) or (v_type='cnpj' and length(v_document)<>14) then raise exception 'CPF/CNPJ inválido'; end if;
  if position('@' in v_email) <= 1 then raise exception 'E-mail de cobrança inválido'; end if;
  if length(v_phone) not between 10 and 11 then raise exception 'Telefone deve ter DDD e número'; end if;
  if length(v_zip) <> 8 then raise exception 'CEP deve ter 8 dígitos'; end if;
  if v_state !~ '^[A-Z]{2}$' then raise exception 'UF inválida'; end if;
  if trim(coalesce(p_profile->>'street',''))='' or trim(coalesce(p_profile->>'number',''))='' or trim(coalesce(p_profile->>'neighborhood',''))='' or trim(coalesce(p_profile->>'city',''))='' then raise exception 'Endereço incompleto'; end if;
  if v_type='cpf' and trim(coalesce(p_profile->>'name',''))='' then raise exception 'Nome do pagador é obrigatório'; end if;
  if v_type='cnpj' and trim(coalesce(p_profile->>'corporate_name',''))='' then raise exception 'Razão social é obrigatória'; end if;

  select to_jsonb(bp) into v_old from public.franchise_billing_profiles bp where bp.franchise_id=v_target;
  insert into public.franchise_billing_profiles(franchise_id,payer_type,name,corporate_name,document,email,phone,street,number,neighborhood,zipcode,city,state,complement,updated_by,updated_at)
  values(v_target,v_type,nullif(trim(p_profile->>'name'),''),nullif(trim(p_profile->>'corporate_name'),''),v_document,v_email,v_phone,trim(p_profile->>'street'),trim(p_profile->>'number'),trim(p_profile->>'neighborhood'),v_zip,trim(p_profile->>'city'),v_state,nullif(trim(coalesce(p_profile->>'complement','')),''),auth.uid(),now())
  on conflict(franchise_id) do update set payer_type=excluded.payer_type,name=excluded.name,corporate_name=excluded.corporate_name,document=excluded.document,email=excluded.email,phone=excluded.phone,street=excluded.street,number=excluded.number,neighborhood=excluded.neighborhood,zipcode=excluded.zipcode,city=excluded.city,state=excluded.state,complement=excluded.complement,updated_by=excluded.updated_by,updated_at=excluded.updated_at;

  select to_jsonb(bp) || jsonb_build_object('complete',true) into v_new from public.franchise_billing_profiles bp where bp.franchise_id=v_target;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(auth.uid(),'franchise_billing_profile_updated','franchise_billing_profiles',v_target::text,jsonb_build_object(
    'franchise_id',v_target,
    'payer_type',v_type,
    'document_suffix',right(v_document,4),
    'changed',coalesce(v_old,'{}'::jsonb) is distinct from (v_new - 'complete'),
    'source',case when v_role='super_admin' then 'matrix' else 'franchise' end
  ));
  return v_new;
end;
$$;

revoke all on function public.save_franchise_billing_profile(uuid,jsonb) from public, anon;
grant execute on function public.save_franchise_billing_profile(uuid,jsonb) to authenticated;
