-- CLICK-GO: global financial and remote app settings mutate through audited Matrix RPCs only.

revoke all on table public.financial_settings from anon, authenticated;
grant select on table public.financial_settings to authenticated;
grant all on table public.financial_settings to service_role;

revoke all on table public.remote_app_settings from anon, authenticated;
grant select on table public.remote_app_settings to authenticated;
grant all on table public.remote_app_settings to service_role;

drop policy if exists super_admin_remote_settings_update on public.remote_app_settings;

revoke all on function public.matrix_update_financial_settings(text,numeric,numeric,numeric,numeric,numeric,text) from public, anon;
grant execute on function public.matrix_update_financial_settings(text,numeric,numeric,numeric,numeric,numeric,text) to authenticated, service_role;

revoke all on function public.matrix_update_remote_app_settings(integer,integer,numeric,boolean,boolean) from public, anon;
grant execute on function public.matrix_update_remote_app_settings(integer,integer,numeric,boolean,boolean) to authenticated, service_role;
