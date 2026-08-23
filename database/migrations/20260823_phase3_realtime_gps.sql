-- CLICK-GO / Phase 3
-- Private Supabase Realtime Broadcast authorization for driver GPS.
-- Topics:
--   city:<city_uuid>:driver-locations
--   ride:<ride_uuid>:driver-location

DROP POLICY IF EXISTS clickgo_gps_broadcast_receive ON realtime.messages;
CREATE POLICY clickgo_gps_broadcast_receive
ON realtime.messages
FOR SELECT
TO authenticated
USING (
  extension = 'broadcast'
  AND (
    (
      substring((SELECT realtime.topic()) FROM '^city:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-locations$') IS NOT NULL
      AND public.can_access_city(
        substring((SELECT realtime.topic()) FROM '^city:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-locations$')::uuid
      )
    )
    OR
    (
      substring((SELECT realtime.topic()) FROM '^ride:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-location$') IS NOT NULL
      AND EXISTS (
        SELECT 1
        FROM public.rides r
        WHERE r.id = substring((SELECT realtime.topic()) FROM '^ride:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-location$')::uuid
          AND (
            r.passenger_id = (SELECT auth.uid())
            OR r.driver_id = (SELECT auth.uid())
            OR (
              public.can_access_city(r.city_id)
              AND (public.jwt_app_role() <> 'franchise_admin' OR r.franchise_id = public.jwt_franchise_id())
            )
          )
      )
    )
  )
);

DROP POLICY IF EXISTS clickgo_gps_broadcast_send ON realtime.messages;
CREATE POLICY clickgo_gps_broadcast_send
ON realtime.messages
FOR INSERT
TO authenticated
WITH CHECK (
  extension = 'broadcast'
  AND (
    (
      substring((SELECT realtime.topic()) FROM '^city:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-locations$') IS NOT NULL
      AND EXISTS (
        SELECT 1
        FROM public.drivers d
        WHERE d.id = (SELECT auth.uid())
          AND d.online = true
          AND d.city_id = substring((SELECT realtime.topic()) FROM '^city:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-locations$')::uuid
      )
    )
    OR
    (
      substring((SELECT realtime.topic()) FROM '^ride:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-location$') IS NOT NULL
      AND EXISTS (
        SELECT 1
        FROM public.rides r
        WHERE r.id = substring((SELECT realtime.topic()) FROM '^ride:([0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{4}-[0-9a-fA-F]{12}):driver-location$')::uuid
          AND r.driver_id = (SELECT auth.uid())
          AND r.status IN ('accepted','driver_arriving','in_progress')
      )
    )
  )
);
