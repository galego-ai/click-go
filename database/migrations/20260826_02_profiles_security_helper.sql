create or replace function public.current_profile_matches_role(p_role text)
returns boolean
language sql
stable
security definer
set search_path=public,pg_temp
as $$
  select exists(
    select 1
    from public.profiles p
    where p.id=auth.uid()
      and p.active
      and p.role::text=p_role
      and public.jwt_app_role()=p_role
  );
$$;

revoke all on function public.current_profile_matches_role(text) from public;
grant execute on function public.current_profile_matches_role(text) to authenticated, service_role;
