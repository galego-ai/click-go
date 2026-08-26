import './globals.css'
import './management-extra.css'
import './management-light.css'
import './management-map.css'
import './simple-management.css'
import AppShell from './AppShell'
import PasswordEyes from '@/components/PasswordEyes'
import AppNotifications from '@/components/AppNotifications'
import DriverTaximeterShortcut from '@/components/DriverTaximeterShortcut'

export const metadata = { title: 'CLICK-GO Gestão', description: 'Plataforma multiempresa de mobilidade urbana CLICK-GO' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><PasswordEyes/><AppNotifications/><DriverTaximeterShortcut/><AppShell>{children}</AppShell></body></html>
}
