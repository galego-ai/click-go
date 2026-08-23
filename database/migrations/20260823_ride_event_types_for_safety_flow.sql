alter table public.ride_events drop constraint if exists ride_events_event_type_check;
alter table public.ride_events add constraint ride_events_event_type_check check (event_type in (
  'offer_received','offer_accepted','offer_rejected','arrived_pickup','driver_arriving','ride_started','ride_completed','ride_cancelled',
  'pickup_pin_verified','sos_triggered','route_deviation_detected','safety_alert_resolved'
));
