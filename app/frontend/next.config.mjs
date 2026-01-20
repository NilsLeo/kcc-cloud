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
  webpack: (config, { isServer }) => {
    if (isServer) {
      // Fix for "self is not defined" error in middleware
      config.output.globalObject = 'globalThis'
    }

    // Add path aliases for @/ imports
    config.resolve.alias['@'] = path.resolve(__dirname)

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
