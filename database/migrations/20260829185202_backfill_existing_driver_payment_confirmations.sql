update public.rides
set driver_payment_confirmed_at=coalesce(driver_payment_confirmed_at,completed_at),
    driver_payment_confirmed_amount=coalesce(driver_payment_confirmed_amount,round(coalesce(final_fare,estimated_fare,0)::numeric,2)),
    driver_payment_confirmed_method=coalesce(driver_payment_confirmed_method,nullif(trim(coalesce(payment_method_preference,'')),''))
where status::text='completed'
  and driver_payment_confirmed_at is null
  and completed_at is not null;
