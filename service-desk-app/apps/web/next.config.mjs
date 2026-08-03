import process from 'node:process';

const nextConfig = {
  basePath: process.env.SERVICE_DESK_BASE_PATH || '',
  env: {
    NEXT_PUBLIC_BASE_PATH: process.env.SERVICE_DESK_BASE_PATH || '',
  },
  serverExternalPackages: ['jsonwebtoken'],
  transpilePackages: [
    '@service-desk/ui',
    '@service-desk/shared',
    '@service-desk/simulation-engine',
  ],
};

export default nextConfig;
