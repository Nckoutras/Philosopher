import type { Metadata } from 'next'
import { Cormorant_Garamond, Lora } from 'next/font/google'
import { ThemeProvider } from 'next-themes'
import { Toaster } from 'react-hot-toast'
import QueryProvider from '@/components/ui/QueryProvider'
import './globals.css'

const cormorant = Cormorant_Garamond({
  subsets: ['latin'],
  weight: ['300', '400', '500'],
  variable: '--font-cormorant',
  display: 'swap',
})

const lora = Lora({
  subsets: ['latin'],
  weight: ['400', '500'],
  variable: '--font-lora',
  display: 'swap',
})

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
      <body className={`${cormorant.variable} ${lora.variable} font-lora antialiased`}>
        <ThemeProvider attribute="class" forcedTheme="light" enableSystem={false}>
          <QueryProvider>
            {children}
            <Toaster
              position="bottom-right"
              toastOptions={{
                style: {
                  background: '#1F1B14',
                  color: '#FAF4E6',
                  border: '0.5px solid #1F1B14',
                  borderRadius: '4px',
                  fontSize: '12px',
                  fontFamily: 'var(--font-lora), Georgia, serif',
                },
              }}
            />
          </QueryProvider>
        </ThemeProvider>
      </body>
    </html>
  )
}
