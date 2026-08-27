create or replace function public.management_save_advertising_banner(
  p_banner_id uuid,
  p_payload jsonb
)
returns jsonb
language plpgsql
security definer
set search_path to 'public','pg_temp'
as $function$
declare
  v_uid uuid:=auth.uid();
  v_role text:=public.current_active_management_role();
  v_fid uuid;
  v_city uuid;
  v_existing public.advertising_banners%rowtype;
  v_title text;
  v_image text;
  v_target text;
  v_advertiser text;
  v_placement text;
  v_audience text;
  v_sort integer;
  v_active boolean;
  v_starts timestamptz;
  v_ends timestamptz;
  v_id uuid;
begin
  if v_uid is null then raise exception 'Não autenticado'; end if;
  if v_role not in ('super_admin','franchise_admin','operator') then raise exception 'Acesso administrativo obrigatório'; end if;
  if v_role='operator' and not public.staff_has_permission('marketing') then raise exception 'Permissão de marketing obrigatória'; end if;
  if p_payload is null then raise exception 'Dados do anúncio são obrigatórios'; end if;

  if p_banner_id is not null then
    select * into v_existing from public.advertising_banners where id=p_banner_id for update;
    if not found then raise exception 'Anúncio não encontrado'; end if;
  end if;

  if v_role='super_admin' then
    v_fid:=case when p_payload ? 'franchise_id' then nullif(p_payload->>'franchise_id','')::uuid else v_existing.franchise_id end;
    v_city:=case when p_payload ? 'city_id' then nullif(p_payload->>'city_id','')::uuid else v_existing.city_id end;
    if v_fid is not null and not exists(select 1 from public.franchises f where f.id=v_fid and f.deleted_at is null) then raise exception 'Franquia inválida'; end if;
    if v_city is not null and not exists(select 1 from public.cities c where c.id=v_city and c.active) then raise exception 'Cidade inválida ou inativa'; end if;
    if v_fid is not null and v_city is not null and not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) then raise exception 'Cidade não pertence à franquia informada'; end if;
  elsif v_role='franchise_admin' then
    v_fid:=public.current_profile_franchise_id();
    if v_fid is null then raise exception 'Franquia não identificada'; end if;
    if p_banner_id is not null and v_existing.franchise_id is distinct from v_fid then raise exception 'Anúncio fora da sua franquia'; end if;
    v_city:=case when p_payload ? 'city_id' then nullif(p_payload->>'city_id','')::uuid else v_existing.city_id end;
    if v_city is not null and not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city) then raise exception 'Cidade fora da sua franquia'; end if;
  else
    v_fid:=public.staff_franchise_id();
    if v_fid is null then raise exception 'Franquia do operador não identificada'; end if;
    if p_banner_id is not null and v_existing.franchise_id is distinct from v_fid then raise exception 'Anúncio fora da sua franquia'; end if;
    v_city:=case when p_payload ? 'city_id' then nullif(p_payload->>'city_id','')::uuid else v_existing.city_id end;
    if v_city is not null and (not public.can_access_city(v_city) or not exists(select 1 from public.franchise_cities fc where fc.franchise_id=v_fid and fc.city_id=v_city)) then raise exception 'Cidade fora do escopo do operador'; end if;
  end if;

  v_title:=coalesce(nullif(btrim(p_payload->>'title'),''),v_existing.title);
  v_image:=coalesce(nullif(btrim(p_payload->>'image_url'),''),v_existing.image_url);
  if v_title is null or length(v_title)>160 then raise exception 'Título do anúncio inválido'; end if;
  if v_image is null or length(v_image)>2000 then raise exception 'URL da imagem inválida'; end if;

  v_target:=case when p_payload ? 'target_url' then nullif(btrim(p_payload->>'target_url'),'') else v_existing.target_url end;
  if v_target is not null and length(v_target)>2000 then raise exception 'Link do anúncio muito longo'; end if;

  if v_role='super_admin' then
    v_advertiser:=case when p_payload ? 'advertiser_name' then nullif(btrim(p_payload->>'advertiser_name'),'') else v_existing.advertiser_name end;
  else
    select f.trade_name into v_advertiser from public.franchises f where f.id=v_fid;
  end if;

  v_placement:=coalesce(nullif(btrim(p_payload->>'placement'),''),v_existing.placement,case when v_role='super_admin' then 'passenger_home' else 'home' end);
  if length(v_placement)>80 then raise exception 'Posicionamento inválido'; end if;
  v_audience:=coalesce(nullif(btrim(p_payload->>'audience'),''),v_existing.audience,'passenger');
  if v_audience not in ('passenger','driver','both') then raise exception 'Audiência inválida'; end if;
  v_sort:=coalesce(nullif(p_payload->>'sort_order','')::integer,v_existing.sort_order,100);
  if v_sort < -10000 or v_sort > 10000 then raise exception 'Ordem de exibição inválida'; end if;
  v_active:=case when p_payload ? 'active' then (p_payload->>'active')::boolean else coalesce(v_existing.active,true) end;
  v_starts:=case when p_payload ? 'starts_at' then nullif(p_payload->>'starts_at','')::timestamptz else v_existing.starts_at end;
  v_ends:=case when p_payload ? 'ends_at' then nullif(p_payload->>'ends_at','')::timestamptz else v_existing.ends_at end;
  if v_starts is not null and v_ends is not null and v_ends<=v_starts then raise exception 'Fim do anúncio deve ser posterior ao início'; end if;

  if p_banner_id is null then
    insert into public.advertising_banners(title,image_url,target_url,advertiser_name,city_id,franchise_id,placement,sort_order,active,starts_at,ends_at,audience,created_at,updated_at)
    values(v_title,v_image,v_target,v_advertiser,v_city,v_fid,v_placement,v_sort,v_active,v_starts,v_ends,v_audience,now(),now())
    returning id into v_id;
  else
    update public.advertising_banners set
      title=v_title,image_url=v_image,target_url=v_target,advertiser_name=v_advertiser,
      city_id=v_city,franchise_id=v_fid,placement=v_placement,sort_order=v_sort,active=v_active,
      starts_at=v_starts,ends_at=v_ends,audience=v_audience,updated_at=now()
    where id=p_banner_id returning id into v_id;
  end if;

  insert into public.audit_logs(actor_id,action,entity,entity_id,metadata)
  values(v_uid,case when p_banner_id is null then 'advertising_banner_created' else 'advertising_banner_updated' end,
    'advertising_banners',v_id::text,
    jsonb_build_object('franchise_id',v_fid,'city_id',v_city,'audience',v_audience,'placement',v_placement,'active',v_active,'source_role',v_role));

  return jsonb_build_object('ok',true,'id',v_id,'franchise_id',v_fid,'city_id',v_city,'active',v_active);
end;
$function$;

revoke all on function public.management_save_advertising_banner(uuid,jsonb) from public,anon;
grant execute on function public.management_save_advertising_banner(uuid,jsonb) to authenticated,service_role;
