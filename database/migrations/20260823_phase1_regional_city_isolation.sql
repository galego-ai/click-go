-- CLICK-GO / Phase 1
-- Strict franchise + city isolation for regional administration.

-- Existing single-city franchise admins receive explicit city access.
INSERT INTO public.profile_city_access(profile_id, city_id)
SELECT p.id, fc.city_id
FROM public.profiles p
JOIN public.franchise_cities fc ON fc.franchise_id = p.franchise_id
WHERE p.role = 'franchise_admin'
  AND p.active = true
  AND p.franchise_id IS NOT NULL
  AND (SELECT count(*) FROM public.franchise_cities x WHERE x.franchise_id = p.franchise_id) = 1
ON CONFLICT (profile_id, city_id) DO NOTHING;

CREATE OR REPLACE FUNCTION public.can_access_city(p_city_id uuid)
RETURNS boolean
LANGUAGE plpgsql
STABLE
SECURITY INVOKER
SET search_path = public, pg_temp
AS $$
DECLARE
  v_uid uuid := auth.uid();
  v_profile_role text;
  v_profile_franchise uuid;
  v_profile_active boolean;
  v_jwt_role text := public.jwt_app_role();
  v_jwt_franchise uuid := public.jwt_franchise_id();
BEGIN
  IF v_uid IS NULL OR p_city_id IS NULL THEN RETURN false; END IF;

  SELECT p.role::text, p.franchise_id, p.active
    INTO v_profile_role, v_profile_franchise, v_profile_active
  FROM public.profiles p
  WHERE p.id = v_uid;

  IF NOT coalesce(v_profile_active, false) THEN RETURN false; END IF;

  IF v_profile_role = 'super_admin' AND v_jwt_role = 'super_admin' THEN
    RETURN true;
  END IF;

  IF v_profile_role = 'franchise_admin'
     AND v_jwt_role = 'franchise_admin'
     AND v_profile_franchise IS NOT DISTINCT FROM v_jwt_franchise THEN
    RETURN EXISTS (
      SELECT 1
      FROM public.profile_city_access a
      JOIN public.franchise_cities fc
        ON fc.city_id = a.city_id
       AND fc.franchise_id = v_profile_franchise
      WHERE a.profile_id = v_uid
        AND a.city_id = p_city_id
    );
  END IF;

  IF v_profile_role = 'operator' AND v_jwt_role = 'operator' THEN
    RETURN EXISTS (
      SELECT 1
      FROM public.profile_city_access a
      WHERE a.profile_id = v_uid
        AND a.city_id = p_city_id
    );
  END IF;

  RETURN false;
END;
$$;

REVOKE EXECUTE ON FUNCTION public.can_access_city(uuid) FROM public, anon;
GRANT EXECUTE ON FUNCTION public.can_access_city(uuid) TO authenticated, service_role;

CREATE INDEX IF NOT EXISTS driver_operational_tx_city_idx
  ON public.driver_operational_transactions(city_id, created_at DESC);
CREATE INDEX IF NOT EXISTS financial_transactions_city_idx
  ON public.financial_transactions(city_id, data_criacao DESC);

ALTER TABLE public.rides ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.drivers ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.driver_locations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.driver_documents ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.driver_operational_wallets ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.driver_operational_transactions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.financial_transactions ENABLE ROW LEVEL SECURITY;

-- RESTRICTIVE guards are defense-in-depth: every permissive regional policy
-- still has to pass the franchise + city boundary.
DROP POLICY IF EXISTS regional_city_guard_rides ON public.rides;
CREATE POLICY regional_city_guard_rides
ON public.rides AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
);

DROP POLICY IF EXISTS regional_city_guard_drivers ON public.drivers;
CREATE POLICY regional_city_guard_drivers
ON public.drivers AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
);

DROP POLICY IF EXISTS regional_city_guard_driver_locations ON public.driver_locations;
CREATE POLICY regional_city_guard_driver_locations
ON public.driver_locations AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = driver_locations.driver_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = driver_locations.driver_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
);

DROP POLICY IF EXISTS regional_city_guard_driver_documents ON public.driver_documents;
CREATE POLICY regional_city_guard_driver_documents
ON public.driver_documents AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = driver_documents.driver_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = driver_documents.driver_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
);

DROP POLICY IF EXISTS regional_city_guard_driver_operational_wallets ON public.driver_operational_wallets;
CREATE POLICY regional_city_guard_driver_operational_wallets
ON public.driver_operational_wallets AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = driver_operational_wallets.driver_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = driver_operational_wallets.driver_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
);

DROP POLICY IF EXISTS regional_city_guard_driver_operational_transactions ON public.driver_operational_transactions;
CREATE POLICY regional_city_guard_driver_operational_transactions
ON public.driver_operational_transactions AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
);

DROP POLICY IF EXISTS regional_city_guard_payments ON public.payments;
CREATE POLICY regional_city_guard_payments
ON public.payments AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.rides r
    WHERE r.id = payments.ride_id
      AND r.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(r.city_id)
  )
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = payments.beneficiary_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR EXISTS (
    SELECT 1 FROM public.rides r
    WHERE r.id = payments.ride_id
      AND r.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(r.city_id)
  )
  OR EXISTS (
    SELECT 1 FROM public.drivers d
    WHERE d.id = payments.beneficiary_id
      AND d.franchise_id = public.jwt_franchise_id()
      AND public.can_access_city(d.city_id)
  )
);

DROP POLICY IF EXISTS regional_city_guard_financial_transactions ON public.financial_transactions;
CREATE POLICY regional_city_guard_financial_transactions
ON public.financial_transactions AS RESTRICTIVE FOR ALL TO authenticated
USING (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
)
WITH CHECK (
  public.jwt_app_role() <> 'franchise_admin'
  OR (franchise_id = public.jwt_franchise_id() AND public.can_access_city(city_id))
);

-- Replace broad regional policies with city-aware equivalents.
DROP POLICY IF EXISTS franchise_admin_own_rides_select ON public.rides;
CREATE POLICY franchise_admin_own_rides_select ON public.rides FOR SELECT TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));

DROP POLICY IF EXISTS franchise_admin_own_rides_insert ON public.rides;
CREATE POLICY franchise_admin_own_rides_insert ON public.rides FOR INSERT TO authenticated
WITH CHECK (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));

DROP POLICY IF EXISTS franchise_admin_own_rides_update ON public.rides;
CREATE POLICY franchise_admin_own_rides_update ON public.rides FOR UPDATE TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id))
WITH CHECK (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));

DROP POLICY IF EXISTS franchise_admin_own_drivers_all ON public.drivers;
CREATE POLICY franchise_admin_own_drivers_all ON public.drivers FOR ALL TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id))
WITH CHECK (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));

DROP POLICY IF EXISTS franchise_admin_requested_driver_read ON public.drivers;
CREATE POLICY franchise_admin_requested_driver_read ON public.drivers FOR SELECT TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));

DROP POLICY IF EXISTS franchise_admin_locations_select ON public.driver_locations;
CREATE POLICY franchise_admin_locations_select ON public.driver_locations FOR SELECT TO authenticated
USING (EXISTS (
  SELECT 1 FROM public.drivers d
  WHERE d.id=driver_locations.driver_id
    AND public.jwt_app_role()='franchise_admin'
    AND d.franchise_id=public.jwt_franchise_id()
    AND public.can_access_city(d.city_id)
));

DROP POLICY IF EXISTS driver_operational_wallet_franchise_select ON public.driver_operational_wallets;
CREATE POLICY driver_operational_wallet_franchise_select ON public.driver_operational_wallets FOR SELECT TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND EXISTS (
  SELECT 1 FROM public.drivers d
  WHERE d.id=driver_operational_wallets.driver_id
    AND d.franchise_id=public.jwt_franchise_id()
    AND public.can_access_city(d.city_id)
));

DROP POLICY IF EXISTS driver_operational_tx_franchise_select ON public.driver_operational_transactions;
CREATE POLICY driver_operational_tx_franchise_select ON public.driver_operational_transactions FOR SELECT TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));

DROP POLICY IF EXISTS franchise_admin_own_payments_select ON public.payments;
CREATE POLICY franchise_admin_own_payments_select ON public.payments FOR SELECT TO authenticated
USING (
  public.jwt_app_role()='franchise_admin'
  AND (
    EXISTS (SELECT 1 FROM public.rides r WHERE r.id=payments.ride_id AND r.franchise_id=public.jwt_franchise_id() AND public.can_access_city(r.city_id))
    OR EXISTS (SELECT 1 FROM public.drivers d WHERE d.id=payments.beneficiary_id AND d.franchise_id=public.jwt_franchise_id() AND public.can_access_city(d.city_id))
  )
);

DROP POLICY IF EXISTS financial_transactions_franchise_read ON public.financial_transactions;
CREATE POLICY financial_transactions_franchise_read ON public.financial_transactions FOR SELECT TO authenticated
USING (public.jwt_app_role()='franchise_admin' AND franchise_id=public.jwt_franchise_id() AND public.can_access_city(city_id));
