create or replace function public.create_passenger_ride(
 p_origin_label text,
 p_origin_lat double precision,
 p_origin_lng double precision,
 p_destination_label text,
 p_destination_lat double precision,
 p_destination_lng double precision,
 p_category_id uuid,
 p_payment_method text default 'cash',
 p_payment_method_id uuid default null
) returns uuid
language plpgsql security definer set search_path to 'public','private','pg_temp' as $$
declare v_uid uuid:=auth.uid(); v_ctx record; v_distance numeric; v_duration numeric; v_ride_id uuid; v_pay record;
begin
 if v_uid is null or not exists(select 1 from public.profiles p where p.id=v_uid and p.role='passenger' and p.active=true) then raise exception 'Acesso exclusivo do passageiro autenticado'; end if;
 if nullif(trim(p_origin_label),'') is null or nullif(trim(p_destination_label),'') is null then raise exception 'Informe origem e destino'; end if;
 if p_payment_method not in ('cash','pix','card','card_machine') then raise exception 'Forma de pagamento inválida'; end if;
 select * into v_ctx from private.resolve_ride_context(p_origin_lat,p_origin_lng);
 select * into v_pay from public.get_effective_payment_settings(v_ctx.city_id);
 if (p_payment_method='cash' and not v_pay.cash_enabled) or (p_payment_method='pix' and not v_pay.pix_enabled) or (p_payment_method='card' and (not v_pay.card_app_enabled or not v_pay.card_credit_enabled)) or (p_payment_method='card_machine' and not v_pay.card_machine_enabled) then raise exception 'Forma de pagamento indisponível nesta cidade'; end if;
 if p_payment_method='card' then
   if p_payment_method_id is null then
     select pm.id into p_payment_method_id
     from public.passenger_payment_methods pm
     where pm.passenger_id=v_uid and pm.active=true and pm.method_type='card' and lower(coalesce(pm.provider,''))='efi'
     order by pm.is_default desc,pm.created_at desc
     limit 1;
   end if;
   if p_payment_method_id is null or not exists(
     select 1 from public.passenger_payment_methods pm
     where pm.id=p_payment_method_id and pm.passenger_id=v_uid and pm.active=true and pm.method_type='card' and lower(coalesce(pm.provider,''))='efi'
   ) then raise exception 'Cadastre ou selecione um cartão Efí válido'; end if;
 else
   p_payment_method_id:=null;
 end if;
 if not exists(select 1 from public.ride_categories rc where rc.id=p_category_id and rc.active=true and rc.city_id=v_ctx.city_id and rc.franchise_id=v_ctx.franchise_id) then raise exception 'Categoria indisponível nesta cidade'; end if;
 v_distance:=round(greatest(public.haversine_km(p_origin_lat,p_origin_lng,p_destination_lat,p_destination_lng)*1.18,0.5)::numeric,2);
 v_duration:=round(greatest(v_distance/0.45,2)::numeric,1);
 insert into public.rides(passenger_id,franchise_id,city_id,category_id,status,origin_label,origin_lat,origin_lng,destination_label,destination_lat,destination_lng,estimated_distance_km,estimated_duration_min,payment_method_preference,payment_method_id,dispatch_mode,created_by_profile_id)
 values(v_uid,v_ctx.franchise_id,v_ctx.city_id,p_category_id,'requested',trim(p_origin_label),p_origin_lat,p_origin_lng,trim(p_destination_label),p_destination_lat,p_destination_lng,v_distance,v_duration,p_payment_method,p_payment_method_id,'auto',v_uid) returning id into v_ride_id;
 return v_ride_id;
end;$$;
revoke all on function public.create_passenger_ride(text,double precision,double precision,text,double precision,double precision,uuid,text,uuid) from public,anon;
grant execute on function public.create_passenger_ride(text,double precision,double precision,text,double precision,double precision,uuid,text,uuid) to authenticated,service_role;