revoke all on function public.ensure_franchise_onboarding(uuid) from public, anon, authenticated;
grant execute on function public.ensure_franchise_onboarding(uuid) to service_role;

revoke all on function public.seed_franchise_onboarding_trigger() from public, anon, authenticated;
grant execute on function public.seed_franchise_onboarding_trigger() to service_role;

revoke all on function public.staff_franchise_id() from public, anon;
grant execute on function public.staff_franchise_id() to authenticated, service_role;

revoke all on function public.staff_has_permission(text) from public, anon;
grant execute on function public.staff_has_permission(text) to authenticated, service_role;
