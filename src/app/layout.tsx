import './globals.css'
import AppShell from './AppShell'
import PasswordEyes from '@/components/PasswordEyes'

export const metadata = { title: 'CLICK-GO', description: 'Plataforma de mobilidade urbana CLICK-GO' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><PasswordEyes/><AppShell>{children}</AppShell></body></html>
}
