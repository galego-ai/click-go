import { createClient } from 'npm:@supabase/supabase-js@2'

const cors = {
  'Access-Control-Allow-Origin': '*',
  'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
}

function json(body: unknown, status = 200) {
  return new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } })
}

async function syncAdminCityAccess(admin:any, profileId:string, franchiseId:string){
  const { data:cities, error:cityError } = await admin.from('franchise_cities').select('city_id').eq('franchise_id', franchiseId)
  if (cityError) throw cityError
  const { error:deleteError } = await admin.from('profile_city_access').delete().eq('profile_id', profileId)
  if (deleteError) throw deleteError
  const rows=(cities||[]).map((x:any)=>({profile_id:profileId,city_id:x.city_id}))
  if(rows.length){
    const { error:insertError } = await admin.from('profile_city_access').upsert(rows,{onConflict:'profile_id,city_id'})
    if(insertError) throw insertError
  }
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
    if (callerError || !callerData.user) return json({ error: 'Sessão inválida' }, 401)

    const { data: callerProfile, error: profileError } = await admin
      .from('profiles')
      .select('role,franchise_id,active')
      .eq('id', callerData.user.id)
      .single()
    if (profileError || !callerProfile || !callerProfile.active) return json({ error: 'Perfil administrativo inválido ou inativo' }, 403)

    const tokenRole=String(callerData.user.app_metadata?.role||'')
    const profileRole=String(callerProfile.role||'')
    if(!tokenRole || tokenRole!==profileRole) return json({error:'Sessão desatualizada. Saia e entre novamente.'},403)

    const body = await req.json()
    const action = body.action
    const isSuperAdmin = profileRole === 'super_admin' && tokenRole === 'super_admin'
    const isFranchiseAdmin = profileRole === 'franchise_admin' && tokenRole === 'franchise_admin'

    if (action === 'create_operational_user') {
      if (!isFranchiseAdmin || !callerProfile.franchise_id) return json({ error: 'Acesso restrito ao administrador da franquia' }, 403)
      const { email, password, full_name, phone, city_id, user_role } = body
      if (!['driver', 'passenger'].includes(user_role)) return json({ error: 'Tipo de usuário inválido' }, 400)
      if (!email || !password || !full_name || !city_id) return json({ error: 'Nome, e-mail, senha e cidade são obrigatórios' }, 400)
      if (String(password).length < 6) return json({ error: 'A senha temporária deve ter pelo menos 6 caracteres' }, 400)

      const { data: linkedCity, error: cityError } = await admin
        .from('franchise_cities')
        .select('city_id')
        .eq('franchise_id', callerProfile.franchise_id)
        .eq('city_id', city_id)
        .maybeSingle()
      if (cityError || !linkedCity) return json({ error: 'Essa cidade não pertence à sua franquia' }, 403)

      const { data, error } = await admin.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
        app_metadata: { role: user_role, franchise_id: callerProfile.franchise_id, city_id },
        user_metadata: { full_name, phone: phone || null },
      })
      if (error) throw error
      const userId = data.user.id

      try {
        const { error: newProfileError } = await admin.from('profiles').upsert({
          id: userId,
          full_name,
          phone: phone || null,
          email: String(email).toLowerCase(),
          role: user_role,
          franchise_id: callerProfile.franchise_id,
          city_id,
          active: true,
        })
        if (newProfileError) throw newProfileError

        if (user_role === 'driver') {
          const { error: driverError } = await admin.from('drivers').insert({
            id: userId,
            status: 'pending',
            franchise_id: callerProfile.franchise_id,
            city_id,
            online: false,
          })
          if (driverError) throw driverError
          await admin.from('admin_notifications').insert({
            type: 'new_driver',
            title: 'Novo motorista aguardando aprovação',
            body: full_name,
            profile_id: userId,
            driver_id: userId,
            franchise_id: callerProfile.franchise_id,
            city_id,
          })
        }

        await admin.from('wallets').upsert({ owner_id: userId, balance: 0 }, { onConflict: 'owner_id' })
        await admin.from('audit_logs').insert({
          actor_id: callerData.user.id,
          action: user_role === 'driver' ? 'create_driver' : 'create_passenger',
          entity: user_role === 'driver' ? 'drivers' : 'profiles',
          entity_id: userId,
          metadata: { franchise_id: callerProfile.franchise_id, city_id, email },
        })
        return json({ ok: true, user_id: userId })
      } catch (e) {
        await admin.auth.admin.deleteUser(userId)
        throw e
      }
    }

    if (!isSuperAdmin) return json({ error: 'Acesso restrito ao Super Admin' }, 403)

    if (action === 'create_franchise_admin') {
      const { email, password, full_name, phone, franchise_id, city_id } = body
      if (!email || !password || !franchise_id) throw new Error('E-mail, senha temporária e franquia são obrigatórios')
      const { data: franchise } = await admin.from('franchises').select('id').eq('id', franchise_id).eq('active', true).is('deleted_at', null).maybeSingle()
      if (!franchise) throw new Error('Franquia inválida ou inativa')
      const { data, error } = await admin.auth.admin.createUser({
        email,
        password,
        email_confirm: true,
        app_metadata: { role: 'franchise_admin', franchise_id, city_id: city_id || null },
        user_metadata: { full_name, phone },
      })
      if (error) throw error
      const userId = data.user.id
      try{
        const { error: newProfileError } = await admin.from('profiles').upsert({ id: userId, full_name, phone, email: String(email).toLowerCase(), role: 'franchise_admin', franchise_id, city_id: city_id || null, active: true })
        if (newProfileError) throw newProfileError
        await syncAdminCityAccess(admin,userId,String(franchise_id))
      }catch(e){
        await admin.auth.admin.deleteUser(userId)
        throw e
      }
      await admin.from('audit_logs').insert({ actor_id: callerData.user.id, action: 'create_franchise_admin', entity: 'profiles', entity_id: userId, metadata: { email, franchise_id, city_id } })
      return json({ ok: true, user_id: userId })
    }

    if (action === 'change_franchise_admin') {
      const { user_id, franchise_id } = body
      if (!user_id || !franchise_id) throw new Error('Usuário e franquia são obrigatórios')
      const { data: franchise } = await admin.from('franchises').select('id').eq('id', franchise_id).eq('active', true).is('deleted_at', null).maybeSingle()
      if (!franchise) throw new Error('Franquia inválida ou inativa')
      const { data: target } = await admin.from('profiles').select('role').eq('id', user_id).maybeSingle()
      if (!target || target.role !== 'franchise_admin') throw new Error('Usuário não é administrador de franquia')
      const { data: authUser, error: authReadError } = await admin.auth.admin.getUserById(user_id)
      if (authReadError || !authUser.user) throw authReadError || new Error('Usuário não encontrado')
      const { error: authError } = await admin.auth.admin.updateUserById(user_id, {
        app_metadata: { ...authUser.user.app_metadata, role: 'franchise_admin', franchise_id, city_id: null },
      })
      if (authError) throw authError
      const { error: updateError } = await admin.from('profiles').update({ franchise_id, city_id: null, active: true, updated_at: new Date().toISOString() }).eq('id', user_id)
      if (updateError) throw updateError
      await syncAdminCityAccess(admin,String(user_id),String(franchise_id))
      await admin.from('audit_logs').insert({ actor_id: callerData.user.id, action: 'change_franchise_admin', entity: 'profiles', entity_id: user_id, metadata: { franchise_id } })
      return json({ ok: true })
    }

    if (action === 'block_user' || action === 'unblock_user') {
      const { user_id } = body
      if (!user_id) throw new Error('user_id obrigatório')
      const ban = action === 'block_user' ? '876000h' : 'none'
      const { error } = await admin.auth.admin.updateUserById(user_id, { ban_duration: ban })
      if (error) throw error
      await admin.from('profiles').update({ active: action !== 'block_user' }).eq('id', user_id)
      if (action === 'block_user') await admin.from('drivers').update({ status: 'blocked', online: false }).eq('id', user_id)
      await admin.from('audit_logs').insert({ actor_id: callerData.user.id, action, entity: 'profiles', entity_id: user_id })
      return json({ ok: true })
    }

    if (action === 'delete_user') {
      const { user_id } = body
      if (!user_id) throw new Error('user_id obrigatório')
      const { error } = await admin.auth.admin.deleteUser(user_id, true)
      if (error) throw error
      await admin.from('audit_logs').insert({ actor_id: callerData.user.id, action: 'delete_user', entity: 'auth.users', entity_id: user_id })
      return json({ ok: true })
    }

    return json({ error: 'Ação inválida' }, 400)
  } catch (e) {
    return json({ error: e instanceof Error ? e.message : 'Erro interno' }, 400)
  }
})
