insert into public.app_internal_secrets(key,value)
values('payment_dispatch_secret',encode(gen_random_bytes(32),'hex'))
on conflict(key) do nothing;

create or replace function private.queue_efi_card_charge_on_ride_completion()
returns trigger
language plpgsql
security definer
set search_path to 'public','private','extensions','pg_temp'
as $$
declare
  v_secret text;
  v_request_id bigint;
begin
  if new.status::text='completed'
     and old.status::text is distinct from 'completed'
     and lower(coalesce(new.payment_method_preference,''))='card' then
    select value into v_secret from public.app_internal_secrets where key='payment_dispatch_secret';
    if nullif(v_secret,'') is not null then
      select net.http_post(
        url:='https://kyaewidapnggmhbsrqch.supabase.co/functions/v1/efi-card',
        headers:=jsonb_build_object('Content-Type','application/json','x-clickgo-payment-secret',v_secret),
        body:=jsonb_build_object('action','charge_ride_internal','ride_id',new.id)
      ) into v_request_id;
      insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
      values(new.driver_id,'efi_card_charge_queued','rides',new.id::text,jsonb_build_object('request_id',v_request_id,'passenger_id',new.passenger_id,'franchise_id',new.franchise_id));
    end if;
  end if;
  return new;
end;
$$;

revoke all on function private.queue_efi_card_charge_on_ride_completion() from public,anon,authenticated;

drop trigger if exists trg_queue_efi_card_on_ride_completion on public.rides;
create trigger trg_queue_efi_card_on_ride_completion
after update of status on public.rides
for each row execute function private.queue_efi_card_charge_on_ride_completion();