import type { Metadata, Viewport } from 'next'
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

export const viewport: Viewport = {
  width: 'device-width',
  initialScale: 1,
  viewportFit: 'cover',
}

export const metadata: Metadata = {
  title: 'The Wise Room — Your Reflective Companion',
  description: 'Think deeper with the greatest thinkers of history.',
  metadataBase: new URL(process.env.NEXT_PUBLIC_BASE_URL ?? 'https://philosopher.app'),
  openGraph: {
    title: 'The Wise Room',
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
                  background: 'var(--ink)',
                  color: 'var(--vellum)',
                  border: '0.5px solid var(--ink)',
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
