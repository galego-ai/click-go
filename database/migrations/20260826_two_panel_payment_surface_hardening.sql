-- Perfil fiscal não precisa mais ser gravado/lido diretamente pelo cliente.
-- Pix e cartão usam Edge Functions autenticadas e service_role.
revoke all on function public.get_franchise_billing_profile(uuid) from public,anon,authenticated;
grant execute on function public.get_franchise_billing_profile(uuid) to service_role;
revoke all on function public.save_franchise_billing_profile(uuid,jsonb) from public,anon,authenticated;
grant execute on function public.save_franchise_billing_profile(uuid,jsonb) to service_role;
