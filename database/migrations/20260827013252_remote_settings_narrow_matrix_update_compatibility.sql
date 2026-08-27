revoke update on table public.remote_app_settings from authenticated;
grant update (auto_cancel_unaccepted_minutes,taximeter_refresh_seconds,max_pickup_radius_km,taximeter_enabled,updated_at) on table public.remote_app_settings to authenticated;
drop policy if exists remote_settings_matrix_narrow_update on public.remote_app_settings;
create policy remote_settings_matrix_narrow_update on public.remote_app_settings for update to authenticated using (public.current_active_management_role()='super_admin') with check (public.current_active_management_role()='super_admin');