'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { supabase } from '@/lib/supabase'

type Role = 'super_admin' | 'franchise_admin'

export default function RoleGate({ role, loginPath, children }: { role: Role; loginPath: string; children: React.ReactNode }) {
  const router = useRouter()
  const [ready, setReady] = useState(false)

  useEffect(() => {
    let alive = true

    async function verify() {
      const { data: { user } } = await supabase.auth.getUser()
      if (!alive) return

      if (!user) {
        router.replace(loginPath)
        return
      }

      let currentRole = user.app_metadata?.role as string | undefined
      if (!currentRole) {
        const { data: profile } = await supabase.from('profiles').select('role').eq('id', user.id).maybeSingle()
        currentRole = profile?.role
      }

      if (currentRole !== role) {
        const destination = currentRole === 'super_admin'
          ? '/dashboard'
          : currentRole === 'franchise_admin'
            ? '/franqueado'
            : currentRole === 'driver'
              ? '/motorista-app'
              : '/passageiro'
        router.replace(destination)
        return
      }

      setReady(true)
    }

    verify()
    return () => { alive = false }
  }, [role, loginPath, router])

  if (!ready) {
    return <div className="card" style={{ maxWidth: 520, margin: '12vh auto', textAlign: 'center' }}>
      <div className="eyebrow">CLICK-GO</div>
      <h2>Verificando acesso...</h2>
      <p className="subtitle">Aguarde a validação segura da sua sessão.</p>
    </div>
  }

  return <>{children}</>
}
