revoke all on function public.confirm_driver_ride_payment(uuid) from anon;
revoke all on function public.confirm_driver_ride_payment(uuid) from public;
grant execute on function public.confirm_driver_ride_payment(uuid) to authenticated;
