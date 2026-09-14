const apiUpstream = process.env.API_UPSTREAM || "http://127.0.0.1:8000";

/** @type {import('next').NextConfig} */
const nextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: `${apiUpstream}/api/:path*`,
      },
      {
        source: "/health",
        destination: `${apiUpstream}/health`,
      },
    ];
  },
};

export default nextConfig;
