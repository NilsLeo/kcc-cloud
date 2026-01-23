import path from 'path'
import { fileURLToPath } from 'url'

const __filename = fileURLToPath(import.meta.url)
const __dirname = path.dirname(__filename)

let userConfig = undefined
try {
  userConfig = await import('./v0-user-next.config')
} catch (e) {
  // ignore error
}

/** @type {import('next').NextConfig} */
const nextConfig = {
  typescript: {
    ignoreBuildErrors: true,
  },
  images: {
    unoptimized: true,
  },
  output: 'standalone',
  // Keep experimental features off in dev containers to avoid instability/timeouts
  experimental: process.env.NODE_ENV === 'production' ? {
    webpackBuildWorker: true,
    parallelServerBuildTraces: true,
    parallelServerCompiles: true,
  } : {},
  // Proxy API requests to backend (for development)
  // Note: WebSocket connections need to go directly to backend - Next.js rewrites don't support WS upgrades
  // In production, nginx handles routing so these rewrites are not used
  async rewrites() {
    // BACKEND_URL is set in docker-compose for dev (http://backend:8060)
    // Default to localhost for production fallback (single container)
    const backendUrl = process.env.BACKEND_URL || 'http://127.0.0.1:8060'
    return [
      {
        source: '/api/:path*',
        destination: `${backendUrl}/:path*`,
      },
      {
        source: '/jobs',
        destination: `${backendUrl}/jobs`,
      },
      {
        source: '/jobs/:path*',
        destination: `${backendUrl}/jobs/:path*`,
      },
      {
        source: '/download/:path*',
        destination: `${backendUrl}/download/:path*`,
      },
      {
        source: '/downloads',
        destination: `${backendUrl}/downloads`,
      },
      {
        source: '/downloads/:path*',
        destination: `${backendUrl}/downloads/:path*`,
      },
    ]
  },
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Fix for "self is not defined" error in middleware
      config.output.globalObject = 'globalThis'
    }

    // Add path aliases for @/ imports
    config.resolve.alias = {
      ...config.resolve.alias,
      '@': path.resolve(__dirname),
      '@/lib': path.resolve(__dirname, 'lib'),
      '@/components': path.resolve(__dirname, 'components'),
      '@/app': path.resolve(__dirname, 'app'),
    }

    return config
  },
}

mergeConfig(nextConfig, userConfig)

function mergeConfig(nextConfig, userConfig) {
  if (!userConfig) {
    return
  }

  for (const key in userConfig) {
    if (
      typeof nextConfig[key] === 'object' &&
      !Array.isArray(nextConfig[key])
    ) {
      nextConfig[key] = {
        ...nextConfig[key],
        ...userConfig[key],
      }
    } else {
      nextConfig[key] = userConfig[key]
    }
  }
}

// Export plain Next.js config without Sentry
export default nextConfig
