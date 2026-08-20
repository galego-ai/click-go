import './globals.css'
import AppChrome from '@/components/AppChrome'
export const metadata={title:'CLICK-GO',description:'Plataforma de mobilidade urbana CLICK-GO'}
export default function RootLayout({children}:{children:React.ReactNode}){return <html lang="pt-BR"><body><AppChrome>{children}</AppChrome></body></html>}
