import type { NextConfig } from "next";

const rawBackendUrl =
  process.env.BACKEND_INTERNAL_URL ||
  "https://ai-research-assistant-backend-j2sj.onrender.com";

// Normalize URL: strip trailing slash and ensure single /api/v1 destination
const cleanBackendUrl = rawBackendUrl.replace(/\/+$/, "");
const destinationUrl = cleanBackendUrl.endsWith("/api/v1")
  ? `${cleanBackendUrl}/:path*`
  : `${cleanBackendUrl}/api/v1/:path*`;

const nextConfig: NextConfig = {
  /* config options here */
  cacheComponents: true,
  partialPrefetching: true,
  turbopack: {
    rules: {
      "*.css": {
        loaders: ["@tailwindcss/turbopack"],
        as: "*.css",
      },
    },
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: destinationUrl,
      },
    ];
  },
};

export default nextConfig;
