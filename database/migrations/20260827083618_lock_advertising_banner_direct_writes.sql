drop policy if exists super_admin_banners_insert on public.advertising_banners;
drop policy if exists super_admin_banners_update on public.advertising_banners;

revoke insert, update, delete on table public.advertising_banners from anon, authenticated;

grant select on table public.advertising_banners to anon, authenticated;

revoke all on function public.management_save_advertising_banner(uuid,jsonb) from public, anon;
grant execute on function public.management_save_advertising_banner(uuid,jsonb) to authenticated, service_role;
