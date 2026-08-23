alter table public.user_emergency_contacts drop constraint if exists user_emergency_contacts_phone_check;
alter table public.user_emergency_contacts add constraint user_emergency_contacts_phone_check check (
  char_length(regexp_replace(phone,'[^0-9]','','g')) between 8 and 15
);
