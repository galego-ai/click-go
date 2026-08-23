create index if not exists driver_taximeter_points_driver_idx on public.driver_taximeter_points(driver_id);
create index if not exists driver_taximeter_sessions_category_idx on public.driver_taximeter_sessions(category_id);
create index if not exists driver_taximeter_sessions_city_idx on public.driver_taximeter_sessions(city_id);
create index if not exists user_notifications_ride_idx on public.user_notifications(ride_id);
