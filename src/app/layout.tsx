import './globals.css'
import AppShell from './AppShell'

export const metadata = { title: 'CLICK-GO', description: 'Plataforma de mobilidade urbana CLICK-GO' }

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return <html lang="pt-BR"><body><AppShell>{children}</AppShell></body></html>
}
