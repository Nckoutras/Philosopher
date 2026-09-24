/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  typescript: {
    // Type errors fail the build. CI's Typecheck step gates the same thing earlier.
    ignoreBuildErrors: false,
  },
  eslint: {
    // Left on deliberately (ruling 2026-09-24): ESLint is not installed, so
    // setting this false would not lint anything — Next logs "ESLint must be
    // installed" and builds anyway. Making lint a gate is its own change.
    ignoreDuringBuilds: true,
  },
  experimental: {
    optimizePackageImports: ['lucide-react', 'framer-motion'],
  },
  async rewrites() {
    return [
      {
        source: '/api/:path*',
        destination: `${process.env.API_URL ?? 'http://localhost:8000'}/api/:path*`,
      },
    ]
  },
}

module.exports = nextConfig
