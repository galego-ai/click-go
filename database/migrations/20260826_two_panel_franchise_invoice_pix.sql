-- Cobrança Pix real da fatura CLICK-GO (Matriz -> Franqueado), separada do Pix das corridas.

create table if not exists public.franchise_invoice_pix_charges (
  id uuid primary key default gen_random_uuid(),
  invoice_id uuid not null references public.franchise_invoices(id) on delete cascade,
  franchise_id uuid not null references public.franchises(id) on delete cascade,
  created_by uuid references public.profiles(id) on delete set null,
  provider text not null default 'efi',
  txid text not null unique,
  location_id bigint,
  location text,
  qrcode text,
  qrcode_image text,
  visualization_link text,
  amount numeric(12,2) not null check (amount > 0),
  status text not null default 'active' check (status in ('active','paid','expired','cancelled','error')),
  provider_status text,
  end_to_end_id text,
  expires_at timestamptz,
  paid_at timestamptz,
  raw_response jsonb not null default '{}'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create unique index if not exists franchise_invoice_pix_one_active_idx
  on public.franchise_invoice_pix_charges(invoice_id)
  where status='active';
create index if not exists franchise_invoice_pix_franchise_idx
  on public.franchise_invoice_pix_charges(franchise_id,created_at desc);
create index if not exists franchise_invoice_pix_created_by_idx
  on public.franchise_invoice_pix_charges(created_by)
  where created_by is not null;

alter table public.franchise_invoice_pix_charges enable row level security;
grant select on public.franchise_invoice_pix_charges to authenticated;

drop policy if exists super_admin_franchise_invoice_pix_select on public.franchise_invoice_pix_charges;
create policy super_admin_franchise_invoice_pix_select on public.franchise_invoice_pix_charges
for select to authenticated
using (public.jwt_app_role()='super_admin');

drop policy if exists franchise_admin_own_invoice_pix_select on public.franchise_invoice_pix_charges;
create policy franchise_admin_own_invoice_pix_select on public.franchise_invoice_pix_charges
for select to authenticated
using (public.jwt_app_role()='franchise_admin' and franchise_id=public.jwt_franchise_id());

drop policy if exists operator_own_invoice_pix_select on public.franchise_invoice_pix_charges;
create policy operator_own_invoice_pix_select on public.franchise_invoice_pix_charges
for select to authenticated
using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));

create or replace function public.touch_franchise_invoice_pix_charge()
returns trigger language plpgsql
set search_path=public,pg_temp
as $$
begin new.updated_at=now(); return new; end;
$$;
drop trigger if exists trg_franchise_invoice_pix_updated_at on public.franchise_invoice_pix_charges;
create trigger trg_franchise_invoice_pix_updated_at
before update on public.franchise_invoice_pix_charges
for each row execute function public.touch_franchise_invoice_pix_charge();

-- Auditoria estrutural (criação/alteração pelo serviço também terá registro explícito com o ator real).
drop trigger if exists trg_critical_audit on public.franchise_invoice_pix_charges;
create trigger trg_critical_audit
after insert or update or delete on public.franchise_invoice_pix_charges
for each row execute function public.capture_critical_audit();
