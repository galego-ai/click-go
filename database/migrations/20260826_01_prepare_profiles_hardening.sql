-- Etapa de preparação aplicada antes do hardening de identidade.
-- Sem alteração de schema: registra a transição das escritas privilegiadas de perfil
-- para a Edge Function admin-users antes do fechamento definitivo da RLS.
select 1;
