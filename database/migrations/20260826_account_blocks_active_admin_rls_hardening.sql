drop policy if exists super_admin_blocks_all on public.account_blocks;
create policy super_admin_blocks_all
on public.account_blocks
for all
to authenticated
using (public.current_active_management_role() = 'super_admin')
with check (public.current_active_management_role() = 'super_admin');

revoke all on table public.account_blocks from anon;
revoke truncate, references, trigger on table public.account_blocks from authenticated;
grant select, insert, update, delete on table public.account_blocks to authenticated;
