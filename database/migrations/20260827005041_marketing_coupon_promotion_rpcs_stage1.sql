create or replace function public.create_marketing_coupon(p_coupon jsonb)
returns uuid
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_city uuid;
  v_code text:=upper(btrim(coalesce(p_coupon->>'code','')));
  v_type text:=lower(btrim(coalesce(p_coupon->>'discount_type','')));
  v_value numeric:=nullif(p_coupon->>'discount_value','')::numeric;
  v_min numeric:=coalesce(nullif(p_coupon->>'min_ride_value','')::numeric,0);
  v_max_discount numeric:=nullif(p_coupon->>'max_discount','')::numeric;
  v_max_uses integer:=nullif(p_coupon->>'max_uses','')::integer;
  v_starts timestamptz:=nullif(p_coupon->>'starts_at','')::timestamptz;
  v_ends timestamptz:=nullif(p_coupon->>'ends_at','')::timestamptz;
  v_source text;
  v_locked boolean:=false;
  v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_type in ('percent','percentage') then v_type:='percentage'; end if;
  if v_code !~ '^[A-Z0-9_-]{3,32}$' then raise exception 'Código do cupom deve ter 3 a 32 caracteres (letras, números, _ ou -)'; end if;
  if v_type not in ('percentage','fixed') then raise exception 'Tipo de desconto inválido'; end if;
  if v_value is null or v_value<=0 then raise exception 'Valor do desconto deve ser maior que zero'; end if;
  if v_type='percentage' and v_value>100 then raise exception 'Desconto percentual não pode passar de 100%%'; end if;
  if v_min<0 or (v_max_discount is not null and v_max_discount<0) then raise exception 'Valores mínimos/máximos inválidos'; end if;
  if v_max_uses is not null and v_max_uses<1 then raise exception 'Máximo de usos deve ser maior que zero'; end if;
  if v_starts is not null and v_ends is not null and v_ends<=v_starts then raise exception 'Fim deve ser posterior ao início'; end if;

  if v_role='super_admin' then
    v_fid:=nullif(p_coupon->>'franchise_id','')::uuid;
    v_city:=nullif(p_coupon->>'city_id','')::uuid;
    if v_fid is not null and not exists(select 1 from public.franchises f where f.id=v_fid and f.deleted_at is null) then raise exception 'Franquia inválida'; end if;
    if v_city is not null and not exists(select 1 from public.cities c where c.id=v_city and c.active=true) then raise exception 'Cidade inválida'; end if;
    if v_fid is not null and v_city is not null and not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) then raise exception 'Cidade não pertence à franquia indicada'; end if;
    v_source:='matrix';
    v_locked:=case when v_fid is null then false else coalesce((p_coupon->>'locked_by_matrix')::boolean,true) end;
  elsif v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id();
    v_city:=nullif(p_coupon->>'city_id','')::uuid;
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if v_city is not null and (not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city)) then raise exception 'Cidade fora do escopo da franquia'; end if;
    v_source:='franchise'; v_locked:=false;
  elsif v_role='operator' and public.staff_has_permission('marketing') then
    v_fid:=public.staff_franchise_id();
    v_city:=nullif(p_coupon->>'city_id','')::uuid;
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if v_city is not null and (not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city)) then raise exception 'Cidade fora do escopo da equipe'; end if;
    v_source:='franchise'; v_locked:=false;
  else
    raise exception 'Sem permissão para criar cupons';
  end if;

  insert into public.coupons(code,description,discount_type,discount_value,max_discount,min_ride_value,max_uses,uses_count,starts_at,ends_at,active,city_id,franchise_id,source,locked_by_matrix)
  values(v_code,nullif(btrim(coalesce(p_coupon->>'description','')),''),v_type,v_value,v_max_discount,v_min,v_max_uses,0,v_starts,v_ends,true,v_city,v_fid,v_source,v_locked)
  returning id into v_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'marketing_coupon_created','coupons',v_id::text,jsonb_build_object('franchise_id',v_fid,'city_id',v_city,'source',v_source,'code',v_code,'discount_type',v_type));
  return v_id;
end;
$$;

create or replace function public.set_marketing_coupon_active(p_coupon_id uuid,p_active boolean)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_row public.coupons%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.coupons where id=p_coupon_id for update;
  if not found then raise exception 'Cupom não encontrado'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  elsif v_role='operator' and public.staff_has_permission('marketing') and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  else raise exception 'Sem permissão para alterar este cupom'; end if;
  update public.coupons set active=coalesce(p_active,false) where id=p_coupon_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'marketing_coupon_status_changed','coupons',p_coupon_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'active',coalesce(p_active,false)));
  return jsonb_build_object('ok',true,'active',coalesce(p_active,false));
end;
$$;

create or replace function public.delete_marketing_coupon(p_coupon_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_row public.coupons%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.coupons where id=p_coupon_id for update;
  if not found then raise exception 'Cupom não encontrado'; end if;
  if coalesce(v_row.uses_count,0)>0 then raise exception 'Cupom já utilizado; pause o cupom em vez de excluir'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  elsif v_role='operator' and public.staff_has_permission('marketing') and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  else raise exception 'Sem permissão para excluir este cupom'; end if;
  delete from public.coupons where id=p_coupon_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'marketing_coupon_deleted','coupons',p_coupon_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'code',v_row.code));
  return jsonb_build_object('ok',true);
end;
$$;

create or replace function public.create_marketing_promotion(p_promotion jsonb)
returns uuid
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid; v_city uuid;
  v_title text:=btrim(coalesce(p_promotion->>'title',''));
  v_type text:=lower(btrim(coalesce(p_promotion->>'promotion_type','')));
  v_value numeric:=coalesce(nullif(p_promotion->>'value','')::numeric,0);
  v_starts timestamptz:=nullif(p_promotion->>'starts_at','')::timestamptz;
  v_ends timestamptz:=nullif(p_promotion->>'ends_at','')::timestamptz;
  v_source text; v_locked boolean:=false; v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_type='percent' then v_type:='discount'; end if;
  if char_length(v_title)<3 or char_length(v_title)>120 then raise exception 'Título deve ter 3 a 120 caracteres'; end if;
  if v_type not in ('discount','cashback','bonus','campaign') then raise exception 'Tipo de promoção inválido'; end if;
  if v_value<0 or (v_type in ('discount','cashback','bonus') and v_value<=0) then raise exception 'Valor da promoção inválido'; end if;
  if v_starts is not null and v_ends is not null and v_ends<=v_starts then raise exception 'Fim deve ser posterior ao início'; end if;

  if v_role='super_admin' then
    v_fid:=nullif(p_promotion->>'franchise_id','')::uuid; v_city:=nullif(p_promotion->>'city_id','')::uuid;
    if v_fid is not null and not exists(select 1 from public.franchises f where f.id=v_fid and f.deleted_at is null) then raise exception 'Franquia inválida'; end if;
    if v_city is not null and not exists(select 1 from public.cities c where c.id=v_city and c.active=true) then raise exception 'Cidade inválida'; end if;
    if v_fid is not null and v_city is not null and not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) then raise exception 'Cidade não pertence à franquia indicada'; end if;
    v_source:='matrix'; v_locked:=case when v_fid is null then false else coalesce((p_promotion->>'locked_by_matrix')::boolean,true) end;
  elsif v_role='franchise_admin' then
    v_fid:=public.jwt_franchise_id(); v_city:=nullif(p_promotion->>'city_id','')::uuid;
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if v_city is not null and (not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city)) then raise exception 'Cidade fora do escopo da franquia'; end if;
    v_source:='franchise'; v_locked:=false;
  elsif v_role='operator' and public.staff_has_permission('marketing') then
    v_fid:=public.staff_franchise_id(); v_city:=nullif(p_promotion->>'city_id','')::uuid;
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if v_city is not null and (not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) or not public.can_access_city(v_city)) then raise exception 'Cidade fora do escopo da equipe'; end if;
    v_source:='franchise'; v_locked:=false;
  else raise exception 'Sem permissão para criar promoções'; end if;

  insert into public.promotions(title,description,promotion_type,value,city_id,franchise_id,starts_at,ends_at,active,source,locked_by_matrix)
  values(v_title,nullif(btrim(coalesce(p_promotion->>'description','')),''),v_type,v_value,v_city,v_fid,v_starts,v_ends,true,v_source,v_locked)
  returning id into v_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'marketing_promotion_created','promotions',v_id::text,jsonb_build_object('franchise_id',v_fid,'city_id',v_city,'source',v_source,'promotion_type',v_type));
  return v_id;
end;
$$;

create or replace function public.set_marketing_promotion_active(p_promotion_id uuid,p_active boolean)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_row public.promotions%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.promotions where id=p_promotion_id for update;
  if not found then raise exception 'Promoção não encontrada'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  elsif v_role='operator' and public.staff_has_permission('marketing') and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  else raise exception 'Sem permissão para alterar esta promoção'; end if;
  update public.promotions set active=coalesce(p_active,false) where id=p_promotion_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'marketing_promotion_status_changed','promotions',p_promotion_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'active',coalesce(p_active,false)));
  return jsonb_build_object('ok',true,'active',coalesce(p_active,false));
end;
$$;

create or replace function public.delete_marketing_promotion(p_promotion_id uuid)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $$
declare
  v_uid uuid:=auth.uid(); v_role text:=public.current_active_management_role(); v_row public.promotions%rowtype;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  select * into v_row from public.promotions where id=p_promotion_id for update;
  if not found then raise exception 'Promoção não encontrada'; end if;
  if v_role='super_admin' then null;
  elsif v_role='franchise_admin' and v_row.franchise_id=public.jwt_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  elsif v_role='operator' and public.staff_has_permission('marketing') and v_row.franchise_id=public.staff_franchise_id() and not v_row.locked_by_matrix and (v_row.city_id is null or public.can_access_city(v_row.city_id)) then null;
  else raise exception 'Sem permissão para excluir esta promoção'; end if;
  delete from public.promotions where id=p_promotion_id;
  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,'marketing_promotion_deleted','promotions',p_promotion_id::text,jsonb_build_object('franchise_id',v_row.franchise_id,'city_id',v_row.city_id,'title',v_row.title));
  return jsonb_build_object('ok',true);
end;
$$;

revoke all on function public.create_marketing_coupon(jsonb) from public,anon;
revoke all on function public.set_marketing_coupon_active(uuid,boolean) from public,anon;
revoke all on function public.delete_marketing_coupon(uuid) from public,anon;
revoke all on function public.create_marketing_promotion(jsonb) from public,anon;
revoke all on function public.set_marketing_promotion_active(uuid,boolean) from public,anon;
revoke all on function public.delete_marketing_promotion(uuid) from public,anon;
grant execute on function public.create_marketing_coupon(jsonb) to authenticated,service_role;
grant execute on function public.set_marketing_coupon_active(uuid,boolean) to authenticated,service_role;
grant execute on function public.delete_marketing_coupon(uuid) to authenticated,service_role;
grant execute on function public.create_marketing_promotion(jsonb) to authenticated,service_role;
grant execute on function public.set_marketing_promotion_active(uuid,boolean) to authenticated,service_role;
grant execute on function public.delete_marketing_promotion(uuid) to authenticated,service_role;
