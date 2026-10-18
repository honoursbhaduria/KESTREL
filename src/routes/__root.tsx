/// <reference types="vite/client" />
import type { ReactNode } from 'react'
import { HeadContent, Outlet, Scripts, createRootRoute } from '@tanstack/react-router'
import appCss from '~/styles/app.css?url'
import { meta } from '~/content/site'
import { Header } from '~/components/layout/Header'
import { Footer } from '~/components/layout/Footer'
import { Cursor } from '~/components/layout/Cursor'
import { Frame } from '~/components/layout/Frame'
import { CookieBanner } from '~/components/layout/CookieBanner'
import { Preloader } from '~/components/layout/Preloader'
import { SmoothScroll } from '~/components/layout/SmoothScroll'
import { PageTransition } from '~/components/layout/PageTransition'
import { NotFound } from '~/components/NotFound'
import { useSiteMotion } from '~/hooks/useSiteMotion'

const { title, description } = meta

export const Route = createRootRoute({
  head: () => ({
    meta: [
      { charSet: 'utf-8' },
      { name: 'viewport', content: 'width=device-width, initial-scale=1' },
      { title },
      { name: 'description', content: description },
      { name: 'theme-color', content: '#f3f2ee' },
      { property: 'og:title', content: title },
      { property: 'og:description', content: description },
      { property: 'og:type', content: 'website' },
      { name: 'twitter:card', content: 'summary_large_image' },
    ],
    links: [
      { rel: 'icon', href: '/favicon.svg', type: 'image/svg+xml' },
      { rel: 'preconnect', href: 'https://fonts.googleapis.com' },
      { rel: 'preconnect', href: 'https://fonts.gstatic.com', crossOrigin: 'anonymous' },
      {
        rel: 'stylesheet',
        href: 'https://fonts.googleapis.com/css2?family=Inter+Tight:wght@400;500;600;700&family=Geist+Mono:wght@400;500&display=swap',
      },
      { rel: 'stylesheet', href: appCss },
    ],
  }),
  shellComponent: RootDocument,
  component: RootLayout,
  notFoundComponent: NotFound,
})

function RootLayout() {
  useSiteMotion()
  return (
    <SmoothScroll>
      <a className="skip-link" href="#main">Skip to content</a>
      <Preloader />
      <PageTransition />
      <Cursor />
      <Frame />
      <Header />
      <main id="main">
        <Outlet />
      </main>
      <Footer />
      <CookieBanner />
    </SmoothScroll>
  )
}

function RootDocument({ children }: { children: ReactNode }) {
  return (
    <html lang="en" className="is-loading" suppressHydrationWarning>
      <head>
        <HeadContent />
        <noscript>
          <style>{'.loader{display:none}html.is-loading{overflow:auto}'}</style>
        </noscript>
      </head>
      <body>
        {children}
        <Scripts />
      </body>
    </html>
  )
}
