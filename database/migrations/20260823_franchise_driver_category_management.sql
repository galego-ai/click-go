-- CLICK-GO — gestão de categorias por motorista e matching.
-- Aplicada em produção em 2026-08-23.

create or replace function public.franchise_driver_category_matrix()
returns table(driver_id uuid,driver_name text,driver_status text,vehicle_id uuid,vehicle_make text,vehicle_model text,vehicle_plate text,vehicle_type text,category_id uuid,category_name text,required_vehicle_type text,category_active boolean,assigned boolean)
language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid(); v_fid uuid; begin
 select p.franchise_id into v_fid from public.profiles p where p.id=v_uid and p.role='franchise_admin' and p.active=true;
 if v_fid is null then raise exception 'Acesso exclusivo do franqueado'; end if;
 return query
 select d.id,coalesce(pr.full_name,'Motorista'),d.status::text,v.id,v.make,v.model,v.plate,v.vehicle_type,rc.id,rc.name,rc.required_vehicle_type,rc.active,
 exists(select 1 from public.driver_category_eligibility e where e.driver_id=d.id and e.category_id=rc.id and e.active=true)
 from public.drivers d join public.profiles pr on pr.id=d.id
 left join lateral(select vv.* from public.vehicles vv where vv.driver_id=d.id and vv.active=true order by vv.created_at desc limit 1)v on true
 join public.ride_categories rc on rc.franchise_id=v_fid and rc.city_id=d.city_id
 where d.franchise_id=v_fid order by pr.full_name,rc.name;
end $$;
revoke all on function public.franchise_driver_category_matrix() from public,anon;
grant execute on function public.franchise_driver_category_matrix() to authenticated;

create or replace function public.franchise_set_driver_vehicle_type(p_driver_id uuid,p_vehicle_id uuid,p_vehicle_type text)
returns jsonb language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid();v_fid uuid;v_type text:=lower(trim(coalesce(p_vehicle_type,'')));begin
 select p.franchise_id into v_fid from public.profiles p where p.id=v_uid and p.role='franchise_admin' and p.active=true;
 if v_fid is null then raise exception 'Acesso exclusivo do franqueado'; end if;
 if v_type not in('car','motorcycle') then raise exception 'Tipo de veículo inválido'; end if;
 if not exists(select 1 from public.drivers d where d.id=p_driver_id and d.franchise_id=v_fid) then raise exception 'Motorista fora da sua franquia'; end if;
 if not exists(select 1 from public.vehicles v where v.id=p_vehicle_id and v.driver_id=p_driver_id and v.active=true) then raise exception 'Veículo ativo não encontrado'; end if;
 update public.vehicles set vehicle_type=v_type where id=p_vehicle_id;
 update public.driver_category_eligibility e set active=false where e.driver_id=p_driver_id and e.vehicle_id=p_vehicle_id and exists(select 1 from public.ride_categories rc where rc.id=e.category_id and rc.required_vehicle_type is not null and rc.required_vehicle_type<>v_type);
 return jsonb_build_object('ok',true,'vehicle_type',v_type);
end $$;
revoke all on function public.franchise_set_driver_vehicle_type(uuid,uuid,text) from public,anon;
grant execute on function public.franchise_set_driver_vehicle_type(uuid,uuid,text) to authenticated;

create or replace function public.franchise_set_driver_category(p_driver_id uuid,p_category_id uuid,p_enabled boolean)
returns jsonb language plpgsql security definer set search_path='public','pg_temp'
as $$
declare v_uid uuid:=auth.uid();v_fid uuid;v_city uuid;v_vehicle public.vehicles%rowtype;v_category public.ride_categories%rowtype;begin
 select p.franchise_id into v_fid from public.profiles p where p.id=v_uid and p.role='franchise_admin' and p.active=true;
 if v_fid is null then raise exception 'Acesso exclusivo do franqueado'; end if;
 select d.city_id into v_city from public.drivers d where d.id=p_driver_id and d.franchise_id=v_fid;
 if v_city is null then raise exception 'Motorista fora da sua franquia'; end if;
 select * into v_category from public.ride_categories rc where rc.id=p_category_id and rc.franchise_id=v_fid and rc.city_id=v_city;
 if not found then raise exception 'Categoria não pertence à operação do motorista'; end if;
 select * into v_vehicle from public.vehicles v where v.driver_id=p_driver_id and v.active=true order by v.created_at desc limit 1;
 if not found then raise exception 'Motorista sem veículo ativo'; end if;
 if coalesce(p_enabled,false) then
  if v_vehicle.vehicle_type is null or v_vehicle.vehicle_type not in('car','motorcycle') then raise exception 'Defina primeiro se o veículo é Carro ou Moto'; end if;
  if v_category.required_vehicle_type is not null and v_category.required_vehicle_type<>v_vehicle.vehicle_type then raise exception 'Categoria incompatível com o tipo de veículo'; end if;
 end if;
 insert into public.driver_category_eligibility(driver_id,category_id,vehicle_id,active,approved_at)
 values(p_driver_id,p_category_id,v_vehicle.id,coalesce(p_enabled,false),case when p_enabled then now() else null end)
 on conflict(driver_id,category_id) do update set vehicle_id=excluded.vehicle_id,active=excluded.active,approved_at=excluded.approved_at;
 return jsonb_build_object('ok',true,'enabled',coalesce(p_enabled,false));
end $$;
revoke all on function public.franchise_set_driver_category(uuid,uuid,boolean) from public,anon;
grant execute on function public.franchise_set_driver_category(uuid,uuid,boolean) to authenticated;

create or replace function public.normalize_vehicle_type_value() returns trigger language plpgsql set search_path='public','pg_temp'
as $$ begin
 if new.vehicle_type is null or trim(new.vehicle_type)='' then new.vehicle_type:=null;
 elsif lower(trim(new.vehicle_type)) in('car','carro','automovel','automóvel') then new.vehicle_type:='car';
 elsif lower(trim(new.vehicle_type)) in('motorcycle','moto','motocicleta') then new.vehicle_type:='motorcycle';
 else new.vehicle_type:=lower(trim(new.vehicle_type)); end if;
 return new;
end $$;
drop trigger if exists normalize_vehicle_type_before_write on public.vehicles;
create trigger normalize_vehicle_type_before_write before insert or update of vehicle_type on public.vehicles for each row execute function public.normalize_vehicle_type_value();

-- Observação: as funções get_passenger_nearby_online_drivers e dispatch_ride em produção
-- usam whitelist quando existir qualquer registro em driver_category_eligibility;
-- sem registros, mantêm compatibilidade automática pelo tipo do veículo.
