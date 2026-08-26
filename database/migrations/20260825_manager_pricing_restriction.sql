-- Gerente regional herda somente as permissões explicitamente gravadas.
-- Tarifas permanecem restritas ao Franqueado/Matriz por padrão.
create or replace function public.staff_has_permission(p_permission text)
returns boolean
language sql
stable
security definer
set search_path=public,pg_temp
as $$
  select coalesce((
    select coalesce((sp.permissions->>p_permission)::boolean,false)
    from public.franchise_staff_permissions sp
    join public.profiles p on p.id=sp.profile_id
    where sp.profile_id=auth.uid() and sp.active and p.active and p.role='operator'
    limit 1
  ),false);
$$;

grant execute on function public.staff_has_permission(text) to authenticated;

update public.franchise_staff_permissions
set permissions=jsonb_set(coalesce(permissions,'{}'::jsonb),'{pricing}','false'::jsonb,true),
    updated_at=now()
where staff_role='manager';
