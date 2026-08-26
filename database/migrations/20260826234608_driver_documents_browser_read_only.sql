-- Final cutover: all driver-document mutations go through trusted RPCs.
revoke all on table public.driver_documents from anon;
revoke insert,update,delete,truncate,references,trigger on table public.driver_documents from authenticated;
grant select on table public.driver_documents to authenticated;

-- Remove legacy direct-write RLS paths. Read policies remain scoped.
drop policy if exists driver_documents_driver_insert on public.driver_documents;
drop policy if exists driver_documents_self_insert on public.driver_documents;
drop policy if exists driver_documents_franchise_update on public.driver_documents;
drop policy if exists franchise_admin_documents_review on public.driver_documents;
drop policy if exists operator_driver_documents_update on public.driver_documents;

-- Keep the guard trigger as defense in depth for writes executed by trusted RPCs/service code.
revoke all on function public.upsert_my_driver_document(text,text) from public,anon;
grant execute on function public.upsert_my_driver_document(text,text) to authenticated,service_role;
revoke all on function public.review_driver_document(uuid,boolean,text) from public,anon;
grant execute on function public.review_driver_document(uuid,boolean,text) to authenticated,service_role;
