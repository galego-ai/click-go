-- CLICK-GO Gestão: equipe regional com permissões por função.
create or replace function public.staff_franchise_id()
returns uuid
language sql
stable
security definer
set search_path=public,pg_temp
as $$
  select sp.franchise_id
  from public.franchise_staff_permissions sp
  join public.profiles p on p.id=sp.profile_id
  where sp.profile_id=auth.uid() and sp.active and p.active and p.role='operator'
  limit 1;
$$;

create or replace function public.staff_has_permission(p_permission text)
returns boolean
language sql
stable
security definer
set search_path=public,pg_temp
as $$
  select coalesce((
    select sp.staff_role='manager' or coalesce((sp.permissions->>p_permission)::boolean,false)
    from public.franchise_staff_permissions sp
    join public.profiles p on p.id=sp.profile_id
    where sp.profile_id=auth.uid() and sp.active and p.active and p.role='operator'
    limit 1
  ),false);
$$;

grant execute on function public.staff_franchise_id() to authenticated;
grant execute on function public.staff_has_permission(text) to authenticated;

drop policy if exists staff_permissions_self_select on public.franchise_staff_permissions;
create policy staff_permissions_self_select on public.franchise_staff_permissions for select using (profile_id=auth.uid());

drop policy if exists operator_franchise_select on public.franchises;
create policy operator_franchise_select on public.franchises for select using (public.jwt_app_role()='operator' and id=public.staff_franchise_id());
drop policy if exists operator_franchise_cities_select on public.franchise_cities;
create policy operator_franchise_cities_select on public.franchise_cities for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id());
drop policy if exists operator_profiles_scope_select on public.profiles;
create policy operator_profiles_scope_select on public.profiles for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission('users') or public.staff_has_permission('drivers') or public.staff_has_permission('support') or public.staff_has_permission('operation')));

drop policy if exists operator_drivers_scope_select on public.drivers;
create policy operator_drivers_scope_select on public.drivers for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission('drivers') or public.staff_has_permission('operation') or public.staff_has_permission('support')));
drop policy if exists operator_drivers_scope_update on public.drivers;
create policy operator_drivers_scope_update on public.drivers for update using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('drivers')) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('drivers'));
drop policy if exists operator_driver_documents_select on public.driver_documents;
create policy operator_driver_documents_select on public.driver_documents for select using (public.jwt_app_role()='operator' and exists(select 1 from public.drivers d where d.id=driver_documents.driver_id and d.franchise_id=public.staff_franchise_id()) and (public.staff_has_permission('drivers') or public.staff_has_permission('support')));
drop policy if exists operator_driver_documents_update on public.driver_documents;
create policy operator_driver_documents_update on public.driver_documents for update using (public.jwt_app_role()='operator' and exists(select 1 from public.drivers d where d.id=driver_documents.driver_id and d.franchise_id=public.staff_franchise_id()) and public.staff_has_permission('drivers'));

drop policy if exists operator_rides_scope_select on public.rides;
create policy operator_rides_scope_select on public.rides for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission('operation') or public.staff_has_permission('finance') or public.staff_has_permission('support')));
drop policy if exists operator_rides_scope_insert on public.rides;
create policy operator_rides_scope_insert on public.rides for insert with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('operation'));
drop policy if exists operator_rides_scope_update on public.rides;
create policy operator_rides_scope_update on public.rides for update using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('operation')) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('operation'));

drop policy if exists operator_categories_select on public.ride_categories;
create policy operator_categories_select on public.ride_categories for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission('pricing') or public.staff_has_permission('operation')));
drop policy if exists operator_categories_write on public.ride_categories;
create policy operator_categories_write on public.ride_categories for all using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('pricing') and not locked_by_matrix) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('pricing') and not locked_by_matrix);
drop policy if exists operator_franchise_settings_select on public.franchise_settings;
create policy operator_franchise_settings_select on public.franchise_settings for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id());
drop policy if exists operator_franchise_settings_write on public.franchise_settings;
create policy operator_franchise_settings_write on public.franchise_settings for all using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('settings') and not locked_by_matrix) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('settings') and not locked_by_matrix);

-- Anúncios não possuem trava de Matriz no legado; o escopo da franquia e permissão de marketing continuam obrigatórios.
drop policy if exists operator_advertising_banners_select on public.advertising_banners;
create policy operator_advertising_banners_select on public.advertising_banners for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission('marketing') or public.staff_has_permission('operation')));
drop policy if exists operator_advertising_banners_write on public.advertising_banners;
create policy operator_advertising_banners_write on public.advertising_banners for all using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('marketing')) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('marketing'));

-- Promoções e cupons respeitam locked_by_matrix.
do $$
declare t text;
begin
 foreach t in array array['promotions','coupons'] loop
   execute format('drop policy if exists operator_%I_select on public.%I',t,t);
   execute format('create policy operator_%I_select on public.%I for select using (public.jwt_app_role()=''operator'' and franchise_id=public.staff_franchise_id() and (public.staff_has_permission(''marketing'') or public.staff_has_permission(''operation'')))',t,t);
   execute format('drop policy if exists operator_%I_write on public.%I',t,t);
   execute format('create policy operator_%I_write on public.%I for all using (public.jwt_app_role()=''operator'' and franchise_id=public.staff_franchise_id() and public.staff_has_permission(''marketing'') and not locked_by_matrix) with check (public.jwt_app_role()=''operator'' and franchise_id=public.staff_franchise_id() and public.staff_has_permission(''marketing'') and not locked_by_matrix)',t,t);
 end loop;
end $$;

drop policy if exists operator_payment_settings_select on public.franchise_city_payment_settings;
create policy operator_payment_settings_select on public.franchise_city_payment_settings for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));
drop policy if exists operator_payment_settings_write on public.franchise_city_payment_settings;
create policy operator_payment_settings_write on public.franchise_city_payment_settings for all using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix);
drop policy if exists operator_wallet_settings_select on public.franchise_operational_wallet_settings;
create policy operator_wallet_settings_select on public.franchise_operational_wallet_settings for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));
drop policy if exists operator_wallet_settings_write on public.franchise_operational_wallet_settings;
create policy operator_wallet_settings_write on public.franchise_operational_wallet_settings for all using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance') and not locked_by_matrix);
drop policy if exists operator_franchise_wallet_select on public.franchise_wallets;
create policy operator_franchise_wallet_select on public.franchise_wallets for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));
drop policy if exists operator_franchise_invoices_select on public.franchise_invoices;
create policy operator_franchise_invoices_select on public.franchise_invoices for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));
drop policy if exists operator_payments_select on public.payments;
create policy operator_payments_select on public.payments for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('finance'));

drop policy if exists operator_support_tickets_select on public.support_tickets;
create policy operator_support_tickets_select on public.support_tickets for select using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('support'));
drop policy if exists operator_support_tickets_update on public.support_tickets;
create policy operator_support_tickets_update on public.support_tickets for update using (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('support')) with check (public.jwt_app_role()='operator' and franchise_id=public.staff_franchise_id() and public.staff_has_permission('support'));
drop policy if exists operator_support_messages_scope on public.support_messages;
create policy operator_support_messages_scope on public.support_messages for all using (public.jwt_app_role()='operator' and public.staff_has_permission('support') and exists(select 1 from public.support_tickets t where t.id=support_messages.ticket_id and t.franchise_id=public.staff_franchise_id())) with check (public.jwt_app_role()='operator' and public.staff_has_permission('support') and exists(select 1 from public.support_tickets t where t.id=support_messages.ticket_id and t.franchise_id=public.staff_franchise_id()));
