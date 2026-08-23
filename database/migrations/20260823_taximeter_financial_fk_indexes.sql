create index if not exists driver_taximeter_charges_city_idx on public.driver_taximeter_charges(city_id) where city_id is not null;
create index if not exists driver_taximeter_charges_wallet_tx_idx on public.driver_taximeter_charges(wallet_transaction_id) where wallet_transaction_id is not null;
create index if not exists taximeter_financial_rules_updated_by_idx on public.taximeter_financial_rules(updated_by) where updated_by is not null;
