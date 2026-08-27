alter table public.coupons enable row level security;
alter table public.promotions enable row level security;

drop policy if exists franchise_admin_own_coupons_all on public.coupons;
drop policy if exists operator_coupons_write on public.coupons;
drop policy if exists super_admin_coupons_all on public.coupons;
drop policy if exists super_admin_coupons_select on public.coupons;
create policy super_admin_coupons_select
on public.coupons
for select
to authenticated
using (public.current_active_management_role()='super_admin');

drop policy if exists franchise_admin_own_promotions_all on public.promotions;
drop policy if exists operator_promotions_write on public.promotions;
drop policy if exists super_admin_promotions_all on public.promotions;
drop policy if exists super_admin_promotions_select on public.promotions;
create policy super_admin_promotions_select
on public.promotions
for select
to authenticated
using (public.current_active_management_role()='super_admin');

revoke all on table public.coupons from anon,authenticated;
revoke all on table public.promotions from anon,authenticated;
grant select on table public.coupons to authenticated;
grant select on table public.promotions to authenticated;
grant all on table public.coupons to service_role;
grant all on table public.promotions to service_role;
