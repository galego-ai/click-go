revoke execute on function public.set_driver_billing(uuid,text,numeric,numeric,integer,text,numeric) from public, anon;
grant execute on function public.set_driver_billing(uuid,text,numeric,numeric,integer,text,numeric) to authenticated;

revoke execute on function public.set_driver_billing(uuid,text,numeric,numeric,integer) from public, anon;
grant execute on function public.set_driver_billing(uuid,text,numeric,numeric,integer) to authenticated;
