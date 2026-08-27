alter table public.account_blocks enable row level security;

drop policy if exists super_admin_blocks_all on public.account_blocks;
drop policy if exists super_admin_blocks_select on public.account_blocks;
create policy super_admin_blocks_select
on public.account_blocks
for select
to authenticated
using (public.current_active_management_role() = 'super_admin');

revoke all on table public.account_blocks from anon, authenticated;
grant select on table public.account_blocks to authenticated;
grant all on table public.account_blocks to service_role;
