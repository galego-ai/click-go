import { createClient } from 'npm:@supabase/supabase-js@2.112.4'

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } })
}

function generateTempPassword() {
  const bytes = crypto.getRandomValues(new Uint8Array(12))
  const alphabet = 'ABCDEFGHJKLMNPQRSTUVWXYZabcdefghijkmnopqrstuvwxyz23456789'
  let body = ''
  for (const b of bytes) body += alphabet[b % alphabet.length]
  return `Cg!${body}#9`
}

function validateTemporaryPassword(value: string) {
  if (value.length < 8) return 'A senha temporária deve ter pelo menos 8 caracteres'
  if (value.length > 72) return 'A senha temporária deve ter no máximo 72 caracteres'
  if (!/[A-Za-z]/.test(value) || !/[0-9]/.test(value)) return 'Use letras e números na senha temporária'
  return null
}

Deno.serve(async (req) => {
  if (req.method === 'OPTIONS') return new Response('ok', { headers: cors })

  try {
    const authHeader = req.headers.get('Authorization') || ''
    const token = authHeader.replace(/^Bearer\s+/i, '')
    if (!token) return json({ error: 'Não autenticado' }, 401)

    const url = Deno.env.get('SUPABASE_URL')!
    const serviceKey = Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!
    const admin = createClient(url, serviceKey, { auth: { autoRefreshToken: false, persistSession: false } })

    const { data: callerData, error: callerError } = await admin.auth.getUser(token)
    if (callerError || !callerData.user) return json({ error: 'Sessão inválida. Entre novamente.' }, 401)

    const { data: callerProfile, error: profileError } = await admin
      .from('profiles')
      .select('role,franchise_id,active')
      .eq('id', callerData.user.id)
      .maybeSingle()

    if (profileError || !callerProfile) return json({ error: 'Perfil administrativo não encontrado' }, 403)
    if (callerProfile.active !== true) return json({ error: 'Perfil inativo' }, 403)

    const body = await req.json()
    const action = String(body.action || '')
    const appRole = String(callerData.user.app_metadata?.role || '')
    const profileRole = String(callerProfile.role || '')
    if (!appRole || appRole !== profileRole) return json({ error: 'Perfil da sessão inconsistente. Entre novamente.' }, 403)

    const isSuperAdmin = profileRole === 'super_admin'
    const metadataFranchiseId = String(callerData.user.app_metadata?.franchise_id || '')
    const profileFranchiseId = String(callerProfile.franchise_id || '')
    const isFranchiseAdmin = profileRole === 'franchise_admin' && Boolean(profileFranchiseId) && metadataFranchiseId === profileFranchiseId

    if (action === 'generate') {
      if (!isSuperAdmin) return json({ error: 'Acesso restrito ao Super Admin' }, 403)
      const franchiseId = String(body.franchise_id || '')
      if (!franchiseId) return json({ error: 'Franquia obrigatória' }, 400)
      const reason = String(body.reason || body.p_reason || '').trim()
      if (reason.length < 3) return json({ error: 'Informe uma justificativa para gerar ou redefinir o acesso.' }, 400)

      const { data: franchise, error: franchiseError } = await admin
        .from('franchises')
        .select('id,trade_name,contact_name,contact_email,contact_phone,active,deleted_at')
        .eq('id', franchiseId)
        .maybeSingle()
      if (franchiseError || !franchise) return json({ error: 'Franquia não encontrada' }, 404)
      if (!franchise.active || franchise.deleted_at) return json({ error: 'Ative a franquia antes de gerar a senha temporária' }, 400)

      const { data: admins, error: adminsError } = await admin
        .from('profiles')
        .select('id,email,full_name,phone,active,created_at')
        .eq('role', 'franchise_admin')
        .eq('franchise_id', franchiseId)
        .order('created_at', { ascending: true })
        .limit(2)
      if (adminsError) throw adminsError
      if ((admins || []).length > 1) return json({ error: 'Há mais de um administrador principal vinculado à franquia. Regularize os acessos antes de redefinir a senha.' }, 409)

      const target = admins?.[0] || null
      if (target && target.active !== true) return json({ error: 'O administrador regional está inativo. Reative o perfil antes de gerar uma nova senha.' }, 409)

      const requestedPassword = String(body.temporary_password || '').trim()
      const temporaryPassword = requestedPassword || generateTempPassword()
      const passwordError = validateTemporaryPassword(temporaryPassword)
      if (passwordError) return json({ error: passwordError }, 400)

      const issuedAt = new Date().toISOString()
      const { error: requestAuditError } = await admin.from('audit_logs').insert({
        actor_id: callerData.user.id,
        action: 'franchise_temp_access_requested',
        entity: 'franchises',
        entity_id: franchiseId,
        metadata: {
          franchise_id: franchiseId,
          source: 'matrix',
          mode: target ? 'reset' : 'create',
          password_mode: requestedPassword ? 'manual' : 'generated',
          reason,
          issued_at: issuedAt,
        },
      })
      if (requestAuditError) return json({ error: 'Não foi possível registrar a auditoria. Nenhuma senha foi alterada.' }, 500)

      let createdAccess = false
      let userId = target?.id || ''
      let email = ''

      if (target) {
        const { data: authUser, error: authReadError } = await admin.auth.admin.getUserById(target.id)
        if (authReadError || !authUser.user) {
          return json({ error: 'O perfil do franqueado existe, mas a conta de login está inconsistente. Regularize o acesso antes de redefinir a senha.' }, 409)
        }

        email = String(authUser.user.email || target.email || franchise.contact_email || '').trim().toLowerCase()
        if (!email) return json({ error: 'A conta do franqueado não possui e-mail de login' }, 400)

        const { error: updateError } = await admin.auth.admin.updateUserById(target.id, {
          password: temporaryPassword,
          app_metadata: {
            ...authUser.user.app_metadata,
            role: 'franchise_admin',
            franchise_id: franchiseId,
            must_change_password: true,
            temp_password_issued_at: issuedAt,
          },
        })
        if (updateError) throw updateError

        const { error: profileUpdateError } = await admin
          .from('profiles')
          .update({ email, updated_at: issuedAt })
          .eq('id', target.id)
          .eq('active', true)
        if (profileUpdateError) throw profileUpdateError
      } else {
        email = String(franchise.contact_email || '').trim().toLowerCase()
        if (!email) return json({ error: 'Cadastre um e-mail de contato na franquia antes de gerar o acesso' }, 400)
        const fullName = String(franchise.contact_name || franchise.trade_name || 'Franqueado').trim()

        const { data: created, error: createError } = await admin.auth.admin.createUser({
          email,
          password: temporaryPassword,
          email_confirm: true,
          app_metadata: {
            role: 'franchise_admin',
            franchise_id: franchiseId,
            city_id: null,
            must_change_password: true,
            temp_password_issued_at: issuedAt,
          },
          user_metadata: { full_name: fullName, phone: franchise.contact_phone || null },
        })
        if (createError) {
          const text = String(createError.message || '')
          if (/already|registered|exists/i.test(text)) {
            return json({ error: 'Este e-mail já possui uma conta. Use outro e-mail de contato ou vincule a conta existente ao franqueado.' }, 409)
          }
          throw createError
        }

        userId = created.user.id
        email = String(created.user.email || email).toLowerCase()
        createdAccess = true
        const { error: upsertError } = await admin.from('profiles').upsert({
          id: userId,
          full_name: fullName,
          phone: franchise.contact_phone || null,
          email,
          role: 'franchise_admin',
          franchise_id: franchiseId,
          city_id: null,
          active: true,
        })
        if (upsertError) {
          await admin.auth.admin.deleteUser(userId)
          throw upsertError
        }
      }

      const { error: auditError } = await admin.from('audit_logs').insert({
        actor_id: callerData.user.id,
        action: createdAccess ? 'create_franchise_temp_access' : 'reset_franchise_temp_password',
        entity: 'profiles',
        entity_id: userId,
        metadata: {
          franchise_id: franchiseId,
          email,
          source: 'matrix',
          must_change_password: true,
          issued_at: issuedAt,
          password_mode: requestedPassword ? 'manual' : 'generated',
          reason,
        },
      })
      if (auditError) console.error('audit success log:', auditError.message)

      return json({ ok: true, franchise_id: franchiseId, user_id: userId, email, temporary_password: temporaryPassword, must_change_password: true, created_access: createdAccess })
    }

    if (action === 'complete_change') {
      if (!isFranchiseAdmin) return json({ error: 'Acesso restrito ao franqueado' }, 403)
      const newPassword = String(body.new_password || '')
      const passwordError = validateTemporaryPassword(newPassword)
      if (passwordError) return json({ error: passwordError.replace('temporária', 'nova') }, 400)

      const { data: authUser, error: authReadError } = await admin.auth.admin.getUserById(callerData.user.id)
      if (authReadError || !authUser.user) throw authReadError || new Error('Conta não encontrada')
      const { error: updateError } = await admin.auth.admin.updateUserById(callerData.user.id, {
        password: newPassword,
        app_metadata: {
          ...authUser.user.app_metadata,
          role: 'franchise_admin',
          franchise_id: profileFranchiseId,
          must_change_password: false,
          temp_password_changed_at: new Date().toISOString(),
        },
      })
      if (updateError) throw updateError

      const { error: auditError } = await admin.from('audit_logs').insert({
        actor_id: callerData.user.id,
        action: 'complete_temp_password_change',
        entity: 'profiles',
        entity_id: callerData.user.id,
        metadata: { franchise_id: profileFranchiseId, source: 'franchise' },
      })
      if (auditError) console.error('audit log:', auditError.message)

      return json({ ok: true })
    }

    return json({ error: 'Ação inválida' }, 400)
  } catch (e) {
    console.error(e)
    return json({ error: e instanceof Error ? e.message : 'Erro interno' }, 400)
  }
})