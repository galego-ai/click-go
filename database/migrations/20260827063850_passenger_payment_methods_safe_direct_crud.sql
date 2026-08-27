drop policy if exists passenger_payment_methods_own_all on public.passenger_payment_methods;
drop policy if exists passenger_payment_methods_own_select on public.passenger_payment_methods;
drop policy if exists passenger_payment_methods_own_insert on public.passenger_payment_methods;
drop policy if exists passenger_payment_methods_own_update on public.passenger_payment_methods;

create policy passenger_payment_methods_own_select
on public.passenger_payment_methods
for select
to authenticated
using (passenger_id=auth.uid());

create policy passenger_payment_methods_own_insert
on public.passenger_payment_methods
for insert
to authenticated
with check (
  passenger_id=auth.uid()
  and method_type in ('cash','pix')
  and provider_token is null
  and brand is null
  and last4 is null
  and (provider is null or (method_type='pix' and provider='pix'))
  and active=true
);

create policy passenger_payment_methods_own_update
on public.passenger_payment_methods
for update
to authenticated
using (passenger_id=auth.uid())
with check (passenger_id=auth.uid());

revoke insert, update, delete, truncate, references, trigger on table public.passenger_payment_methods from anon;
revoke update, delete, truncate, references, trigger on table public.passenger_payment_methods from authenticated;
grant select, insert on table public.passenger_payment_methods to authenticated;
grant update(is_default,active) on table public.passenger_payment_methods to authenticated;

create unique index if not exists passenger_payment_methods_one_default_active
  on public.passenger_payment_methods(passenger_id)
  where is_default=true and active=true;

alter table public.passenger_payment_methods
  drop constraint if exists passenger_payment_methods_last4_format_check;
alter table public.passenger_payment_methods
  add constraint passenger_payment_methods_last4_format_check
  check (last4 is null or last4 ~ '^[0-9]{4}$');
