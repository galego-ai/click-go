-- CLICK-GO / Phase 2
-- Driver can remain online when operational balance reaches the cash limit.
-- Only cash rides are filtered; app PIX/card remain available.

ALTER TABLE public.platform_operational_wallet_settings
  ADD COLUMN IF NOT EXISTS cash_negative_limit numeric(10,2) NOT NULL DEFAULT 0.00;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1 FROM pg_constraint
    WHERE conname='platform_operational_wallet_cash_negative_limit_chk'
      AND conrelid='public.platform_operational_wallet_settings'::regclass
  ) THEN
    ALTER TABLE public.platform_operational_wallet_settings
      ADD CONSTRAINT platform_operational_wallet_cash_negative_limit_chk
      CHECK (cash_negative_limit <= 0);
  END IF;
END $$;

CREATE TABLE IF NOT EXISTS public.city_operational_wallet_settings (
  franchise_id uuid NOT NULL,
  city_id uuid NOT NULL,
  cash_negative_limit numeric(10,2) NOT NULL DEFAULT 0.00,
  locked_by_matrix boolean NOT NULL DEFAULT false,
  updated_by uuid NULL REFERENCES public.profiles(id),
  updated_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (franchise_id, city_id),
  CONSTRAINT city_operational_wallet_settings_scope_fkey
    FOREIGN KEY (franchise_id, city_id)
    REFERENCES public.franchise_cities(franchise_id, city_id)
    ON DELETE CASCADE,
  CONSTRAINT city_operational_wallet_cash_negative_limit_chk
    CHECK (cash_negative_limit <= 0)
);

ALTER TABLE public.city_operational_wallet_settings ENABLE ROW LEVEL SECURITY;
REVOKE ALL ON TABLE public.city_operational_wallet_settings FROM anon;
GRANT SELECT, INSERT, UPDATE ON TABLE public.city_operational_wallet_settings TO authenticated;
GRANT ALL ON TABLE public.city_operational_wallet_settings TO service_role;

CREATE OR REPLACE FUNCTION public.driver_can_be_online(p_driver uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
  SELECT EXISTS(
    SELECT 1
    FROM public.drivers d
    JOIN public.profiles p ON p.id=d.id
    LEFT JOIN public.driver_billing_settings dbs ON dbs.driver_id=d.id
    WHERE d.id=p_driver
      AND d.status='approved'
      AND p.active=true
      AND d.city_id IS NOT NULL
      AND d.franchise_id IS NOT NULL
      AND coalesce(dbs.active,true)=true
      AND (
        coalesce(dbs.billing_mode,'wallet_per_ride') <> 'monthly'
        OR coalesce(dbs.monthly_fee,0)=0
        OR coalesce(dbs.monthly_paid_until,date '1900-01-01') >= current_date
      )
  );
$$;

-- Compatibility alias for already-installed clients.
CREATE OR REPLACE FUNCTION public.driver_can_go_online(p_driver uuid)
RETURNS boolean
LANGUAGE sql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
  SELECT public.driver_can_be_online(p_driver);
$$;

CREATE OR REPLACE FUNCTION public.driver_can_accept_payment_method(p_driver uuid, p_payment_method text)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_method text := lower(trim(coalesce(p_payment_method,'cash')));
  v_driver public.drivers%rowtype;
  v_balance numeric := 0;
  v_billing_mode text := 'wallet_per_ride';
  v_operational_enabled boolean := false;
  v_cash_negative_limit numeric(10,2) := 0.00;
BEGIN
  SELECT * INTO v_driver FROM public.drivers WHERE id=p_driver;
  IF NOT FOUND THEN RETURN false; END IF;

  IF v_method='card_machine' THEN
    RETURN coalesce(v_driver.has_card_machine,false)
       AND coalesce(v_driver.card_machine_approved,false);
  END IF;

  IF v_method IN ('pix','card','credit','credit_card','debit','debit_card','wallet','app') THEN
    RETURN true;
  END IF;

  IF v_method <> 'cash' THEN RETURN false; END IF;

  SELECT coalesce(ow.balance,0),
         coalesce(dbs.billing_mode,'wallet_per_ride'),
         coalesce(g.enabled,false),
         coalesce(cs.cash_negative_limit,g.cash_negative_limit,0.00)
    INTO v_balance,v_billing_mode,v_operational_enabled,v_cash_negative_limit
  FROM public.drivers d
  LEFT JOIN public.driver_operational_wallets ow ON ow.driver_id=d.id
  LEFT JOIN public.driver_billing_settings dbs ON dbs.driver_id=d.id
  LEFT JOIN public.platform_operational_wallet_settings g ON g.scope='global'
  LEFT JOIN public.city_operational_wallet_settings cs
    ON cs.franchise_id=d.franchise_id AND cs.city_id=d.city_id
  WHERE d.id=p_driver;

  IF v_billing_mode <> 'wallet_per_ride' OR NOT v_operational_enabled THEN
    RETURN true;
  END IF;

  -- Reaching the limit blocks cash. Example: limit -10.00, balance -10.00 => false.
  RETURN coalesce(v_balance,0) > coalesce(v_cash_negative_limit,0.00);
END;
$$;

CREATE OR REPLACE FUNCTION public.set_driver_online(
  p_online boolean,
  p_lat double precision DEFAULT NULL,
  p_lng double precision DEFAULT NULL
)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_uid uuid := auth.uid();
  v_driver public.drivers%rowtype;
BEGIN
  IF v_uid IS NULL THEN RAISE EXCEPTION 'Não autenticado'; END IF;
  SELECT * INTO v_driver FROM public.drivers WHERE id=v_uid FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'Cadastro de motorista não encontrado'; END IF;

  IF p_online THEN
    IF v_driver.status <> 'approved' THEN RAISE EXCEPTION 'Seu cadastro precisa estar aprovado para ficar online'; END IF;
    IF NOT public.driver_can_be_online(v_uid) THEN RAISE EXCEPTION 'Seu cadastro ou plano ainda não está liberado para operação'; END IF;
    IF p_lat IS NULL OR p_lng IS NULL OR p_lat NOT BETWEEN -90 AND 90 OR p_lng NOT BETWEEN -180 AND 180 THEN
      RAISE EXCEPTION 'Localização válida é obrigatória para ficar online';
    END IF;
    INSERT INTO public.driver_locations(driver_id,lat,lng,updated_at)
    VALUES(v_uid,p_lat,p_lng,now())
    ON CONFLICT(driver_id) DO UPDATE SET lat=excluded.lat,lng=excluded.lng,updated_at=now();
    UPDATE public.drivers SET online=true WHERE id=v_uid;
  ELSE
    UPDATE public.drivers SET online=false WHERE id=v_uid;
  END IF;

  RETURN jsonb_build_object('ok',true,'online',p_online);
END;
$$;

CREATE OR REPLACE FUNCTION public.dispatch_ride(p_ride_id uuid)
RETURNS integer
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_ride public.rides%rowtype;
  v_state public.ride_dispatch_state%rowtype;
  v_required_vehicle_type text;
  v_radii numeric[]:=array[1,2,3,5,8];
  v_radius numeric;
  v_created integer:=0;
  v_attempt integer:=0;
BEGIN
  SELECT * INTO v_ride FROM public.rides WHERE id=p_ride_id FOR UPDATE;
  IF NOT FOUND THEN RETURN 0; END IF;
  IF v_ride.driver_id IS NOT NULL OR v_ride.status NOT IN ('requested','searching') THEN RETURN 0; END IF;

  SELECT required_vehicle_type INTO v_required_vehicle_type
  FROM public.ride_categories WHERE id=v_ride.category_id;

  INSERT INTO public.ride_dispatch_state(ride_id) VALUES(p_ride_id) ON CONFLICT(ride_id) DO NOTHING;
  SELECT * INTO v_state FROM public.ride_dispatch_state WHERE ride_id=p_ride_id FOR UPDATE;

  UPDATE public.ride_offers
     SET status='expired',responded_at=coalesce(responded_at,now())
   WHERE ride_id=p_ride_id AND status='pending' AND expires_at<=now();

  IF EXISTS(SELECT 1 FROM public.ride_offers WHERE ride_id=p_ride_id AND status='pending' AND expires_at>now()) THEN
    RETURN 0;
  END IF;

  LOOP
    v_attempt:=v_attempt+1;
    IF v_attempt>5 OR v_state.radius_index>5 THEN
      UPDATE public.ride_dispatch_state SET status='exhausted',next_dispatch_at=null,updated_at=now() WHERE ride_id=p_ride_id;
      RETURN 0;
    END IF;

    v_radius:=v_radii[v_state.radius_index];

    WITH candidates AS (
      SELECT d.id driver_id,
             public.haversine_km(dl.lat,dl.lng,v_ride.origin_lat,v_ride.origin_lng) distance_km,
             coalesce(d.rating,5)::numeric rating,
             coalesce(d.consecutive_refusals,0) refusals,
             extract(epoch FROM(now()-coalesce(d.online_since,now())))/60.0 online_minutes
      FROM public.drivers d
      JOIN public.driver_locations dl ON dl.driver_id=d.id
      WHERE d.status='approved'
        AND d.online=true
        AND d.city_id=v_ride.city_id
        AND (v_ride.franchise_id IS NULL OR d.franchise_id=v_ride.franchise_id)
        AND dl.updated_at>=now()-interval '2 minutes'
        AND public.driver_can_be_online(d.id)
        AND public.driver_can_accept_payment_method(d.id,coalesce(v_ride.payment_method_preference,'cash'))
        AND NOT EXISTS(SELECT 1 FROM public.rides ar WHERE ar.driver_id=d.id AND ar.status IN ('accepted','driver_arriving','in_progress'))
        AND EXISTS(SELECT 1 FROM public.vehicles v WHERE v.driver_id=d.id AND v.active=true AND (v_required_vehicle_type IS NULL OR v.vehicle_type=v_required_vehicle_type))
        AND (
          NOT EXISTS(SELECT 1 FROM public.driver_category_eligibility e WHERE e.driver_id=d.id)
          OR EXISTS(
            SELECT 1 FROM public.driver_category_eligibility e
            JOIN public.vehicles v ON v.id=e.vehicle_id AND v.active=true
            WHERE e.driver_id=d.id AND e.category_id=v_ride.category_id AND e.active=true
              AND (v_required_vehicle_type IS NULL OR v.vehicle_type=v_required_vehicle_type)
          )
        )
        AND NOT EXISTS(SELECT 1 FROM public.ride_offers ro WHERE ro.ride_id=p_ride_id AND ro.driver_id=d.id)
    ), ranked AS (
      SELECT *,greatest(0,100-distance_km*8)
        +least(20,greatest(0,(rating-3.0)*10))
        +least(15,greatest(0,online_minutes/10))
        -least(25,refusals*5) score
      FROM candidates
      WHERE distance_km<=v_radius
      ORDER BY distance_km ASC,score DESC
      LIMIT 1
    ), ins AS (
      INSERT INTO public.ride_offers(
        ride_id,driver_id,distance_to_pickup_km,eta_to_pickup_min,
        estimated_driver_earning,status,expires_at,radius_km,dispatch_wave,match_score
      )
      SELECT p_ride_id,driver_id,round(distance_km::numeric,2),
             greatest(1,ceil(distance_km/0.5)::integer),
             round(coalesce(v_ride.estimated_fare,0)::numeric,2),
             'pending',now()+interval '20 seconds',v_radius,v_state.wave_no+1,round(score::numeric,3)
      FROM ranked
      ON CONFLICT DO NOTHING
      RETURNING driver_id
    ) SELECT count(*) INTO v_created FROM ins;

    IF v_created>0 THEN
      UPDATE public.drivers d SET last_offer_at=now()
      WHERE d.id IN(SELECT driver_id FROM public.ride_offers WHERE ride_id=p_ride_id AND dispatch_wave=v_state.wave_no+1 AND status='pending');
      UPDATE public.rides SET status='searching' WHERE id=p_ride_id AND status='requested';
      UPDATE public.ride_dispatch_state
         SET radius_km=v_radius,wave_no=wave_no+1,last_dispatched_at=now(),
             next_dispatch_at=now()+interval '21 seconds',status='active',updated_at=now()
       WHERE ride_id=p_ride_id;
      RETURN v_created;
    END IF;

    IF v_state.radius_index>=5 THEN
      UPDATE public.ride_dispatch_state SET radius_km=8,status='exhausted',next_dispatch_at=null,updated_at=now() WHERE ride_id=p_ride_id;
      RETURN 0;
    END IF;

    v_state.radius_index:=v_state.radius_index+1;
    UPDATE public.ride_dispatch_state
       SET radius_index=v_state.radius_index,radius_km=v_radii[v_state.radius_index],updated_at=now()
     WHERE ride_id=p_ride_id;
  END LOOP;
END;
$$;

CREATE OR REPLACE FUNCTION public.respond_to_ride_offer(p_offer_id uuid, p_accept boolean)
RETURNS jsonb
LANGUAGE plpgsql
SECURITY DEFINER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_offer public.ride_offers%rowtype;
  v_ride public.rides%rowtype;
  v_driver uuid:=auth.uid();
  v_method text;
BEGIN
  IF v_driver IS NULL THEN RAISE EXCEPTION 'not_authenticated'; END IF;

  SELECT * INTO v_offer
  FROM public.ride_offers
  WHERE id=p_offer_id AND driver_id=v_driver
  FOR UPDATE;
  IF NOT FOUND THEN RAISE EXCEPTION 'offer_not_found'; END IF;

  IF v_offer.status<>'pending' OR v_offer.expires_at<=now() THEN
    IF v_offer.status='pending' THEN
      UPDATE public.ride_offers SET status='expired',responded_at=now() WHERE id=p_offer_id;
    END IF;
    RETURN jsonb_build_object('ok',false,'reason','expired');
  END IF;

  IF NOT p_accept THEN
    UPDATE public.ride_offers SET status='rejected',responded_at=now() WHERE id=p_offer_id;
    UPDATE public.drivers SET consecutive_refusals=consecutive_refusals+1 WHERE id=v_driver;
    IF NOT EXISTS(SELECT 1 FROM public.ride_offers WHERE ride_id=v_offer.ride_id AND status='pending' AND expires_at>now()) THEN
      UPDATE public.ride_dispatch_state SET next_dispatch_at=now(),updated_at=now() WHERE ride_id=v_offer.ride_id AND status='active';
      PERFORM public.dispatch_ride(v_offer.ride_id);
    END IF;
    RETURN jsonb_build_object('ok',true,'accepted',false);
  END IF;

  SELECT * INTO v_ride FROM public.rides WHERE id=v_offer.ride_id FOR UPDATE;
  v_method:=lower(coalesce(v_ride.payment_method_preference,'cash'));

  IF NOT public.driver_can_be_online(v_driver) THEN
    UPDATE public.ride_offers SET status='expired',responded_at=now() WHERE id=p_offer_id;
    RETURN jsonb_build_object('ok',false,'reason','wallet_or_driver_unavailable');
  END IF;

  IF NOT public.driver_can_accept_payment_method(v_driver,v_method) THEN
    UPDATE public.ride_offers SET status='expired',responded_at=now() WHERE id=p_offer_id;
    IF v_method='card_machine' THEN RETURN jsonb_build_object('ok',false,'reason','card_machine_not_authorized'); END IF;
    IF v_method='cash' THEN RETURN jsonb_build_object('ok',false,'reason','wallet_or_driver_unavailable'); END IF;
    RETURN jsonb_build_object('ok',false,'reason','payment_method_unavailable');
  END IF;

  IF v_ride.driver_id IS NOT NULL OR v_ride.status NOT IN ('requested','searching') THEN
    UPDATE public.ride_offers SET status='expired',responded_at=now() WHERE id=p_offer_id;
    RETURN jsonb_build_object('ok',false,'reason','already_taken');
  END IF;

  UPDATE public.rides SET driver_id=v_driver,status='accepted',accepted_at=now() WHERE id=v_offer.ride_id;
  UPDATE public.ride_offers SET status='accepted',responded_at=now() WHERE id=p_offer_id;
  UPDATE public.ride_offers SET status='expired',responded_at=coalesce(responded_at,now())
  WHERE ride_id=v_offer.ride_id AND id<>p_offer_id AND status='pending';
  UPDATE public.ride_dispatch_state SET status='accepted',next_dispatch_at=null,updated_at=now() WHERE ride_id=v_offer.ride_id;
  UPDATE public.drivers SET consecutive_refusals=0 WHERE id=v_driver;
  INSERT INTO public.ride_events(ride_id,driver_id,event_type) VALUES(v_offer.ride_id,v_driver,'offer_accepted');

  RETURN jsonb_build_object('ok',true,'accepted',true,'ride_id',v_offer.ride_id);
END;
$$;

REVOKE EXECUTE ON FUNCTION public.driver_can_be_online(uuid) FROM public, anon;
GRANT EXECUTE ON FUNCTION public.driver_can_be_online(uuid) TO authenticated, service_role;
REVOKE EXECUTE ON FUNCTION public.driver_can_accept_payment_method(uuid,text) FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.driver_can_accept_payment_method(uuid,text) TO service_role;
REVOKE EXECUTE ON FUNCTION public.driver_can_go_online(uuid) FROM public, anon;
GRANT EXECUTE ON FUNCTION public.driver_can_go_online(uuid) TO authenticated, service_role;
REVOKE EXECUTE ON FUNCTION public.set_driver_online(boolean,double precision,double precision) FROM public, anon;
GRANT EXECUTE ON FUNCTION public.set_driver_online(boolean,double precision,double precision) TO authenticated, service_role;
REVOKE EXECUTE ON FUNCTION public.dispatch_ride(uuid) FROM public, anon, authenticated;
GRANT EXECUTE ON FUNCTION public.dispatch_ride(uuid) TO service_role;
REVOKE EXECUTE ON FUNCTION public.respond_to_ride_offer(uuid,boolean) FROM public, anon;
GRANT EXECUTE ON FUNCTION public.respond_to_ride_offer(uuid,boolean) TO authenticated, service_role;
