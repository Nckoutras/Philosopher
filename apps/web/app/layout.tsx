import type { Metadata } from 'next'
import { Inter, Lora } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import { Toaster } from 'react-hot-toast'
import QueryProvider from '@/components/ui/QueryProvider'
import './globals.css'

const inter = Inter({ subsets: ['latin'], variable: '--font-sans', display: 'swap' })
const lora = Lora({ subsets: ['latin'], variable: '--font-serif', display: 'swap' })

export const metadata: Metadata = {
  title: 'Philosopher — Your Reflective Companion',
  description: 'Think deeper with the great minds of history.',
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL ?? 'https://philosopher.app'),
  openGraph: {
    title: 'Philosopher',
    description: 'A premium AI reflective companion grounded in historical philosophy.',
    type: 'website',
  },
}

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" suppressHydrationWarning>
      <body className={`${inter.variable} ${lora.variable} font-sans antialiased`}>
        <ThemeProvider attribute="class" defaultTheme="dark" enableSystem>
          <QueryProvider>
            {children}
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: 'var(--toast-bg, #1a1a1a)',
                  color: 'var(--toast-fg, #e5e5e5)',
                  border: '1px solid rgba(255,255,255,0.08)',
                  borderRadius: '10px',
                  fontSize: '14px',
                },
              }}
            />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
