alter table public.franchise_billing_profiles enable row level security;
revoke all on table public.franchise_billing_profiles from anon, authenticated;
grant select on table public.franchise_billing_profiles to authenticated;
grant all on table public.franchise_billing_profiles to service_role;
