revoke update on table public.user_notifications from authenticated;
grant update(read_at) on table public.user_notifications to authenticated;
revoke all on table public.user_notifications from anon;
