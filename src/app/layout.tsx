import './globals.css'
import AppShell from './AppShell'
import PasswordEyes from '@/components/PasswordEyes'
import AppNotifications from '@/components/AppNotifications'

export const metadata = { title: 'CLICK-GO', description: 'Plataforma de mobilidade urbana CLICK-GO' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><PasswordEyes/><AppNotifications/><AppShell>{children}</AppShell></body></html>
}
