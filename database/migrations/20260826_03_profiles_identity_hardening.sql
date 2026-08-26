create or replace function public.current_profile_franchise_id()
returns uuid
language sql
stable
security definer
set search_path=public,pg_temp
as $$
  select p.franchise_id
  from public.profiles p
  where p.id=auth.uid()
    and p.active
    and public.jwt_app_role()=p.role::text
  limit 1;
$$;

create or replace function public.current_profile_is_active()
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
  );
$$;

revoke all on function public.current_profile_franchise_id() from public;
revoke all on function public.current_profile_is_active() from public;
grant execute on function public.current_profile_franchise_id() to authenticated, service_role;
grant execute on function public.current_profile_is_active() to authenticated, service_role;

create or replace function public.protect_self_profile_sensitive_fields()
returns trigger
language plpgsql
security definer
set search_path=public
as $$
begin
  if auth.uid() = old.id then
    new.role := old.role;
    new.franchise_id := old.franchise_id;
    new.city_id := old.city_id;
    new.active := old.active;
    new.email := old.email;
    new.cpf := old.cpf;
  end if;
  return new;
end;
$$;

drop policy if exists super_admin_profiles_all on public.profiles;
drop policy if exists super_admin_profiles_select on public.profiles;
create policy super_admin_profiles_select
on public.profiles
for select
to authenticated
using (public.current_profile_matches_role('super_admin'));

drop policy if exists franchise_admin_own_profiles_select on public.profiles;
create policy franchise_admin_own_profiles_select
on public.profiles
for select
to authenticated
using (
  public.current_profile_matches_role('franchise_admin')
  and franchise_id = public.current_profile_franchise_id()
);

drop policy if exists franchise_admin_riders_from_own_rides on public.profiles;
create policy franchise_admin_riders_from_own_rides
on public.profiles
for select
to authenticated
using (
  public.current_profile_matches_role('franchise_admin')
  and role = 'passenger'::public.user_role
  and exists (
    select 1
    from public.rides r
    where r.passenger_id = profiles.id
      and r.franchise_id = public.current_profile_franchise_id()
  )
);

drop policy if exists operator_profiles_scope_select on public.profiles;
create policy operator_profiles_scope_select
on public.profiles
for select
to authenticated
using (
  public.current_profile_matches_role('operator')
  and franchise_id = public.staff_franchise_id()
  and (
    public.staff_has_permission('users')
    or public.staff_has_permission('drivers')
    or public.staff_has_permission('support')
    or public.staff_has_permission('operation')
  )
);

drop policy if exists profiles_self_update on public.profiles;
create policy profiles_self_update
on public.profiles
for update
to authenticated
using (auth.uid() = id and public.current_profile_is_active())
with check (auth.uid() = id and public.current_profile_is_active());

revoke all on table public.profiles from anon;
revoke all on table public.profiles from authenticated;
grant select, update on table public.profiles to authenticated;
