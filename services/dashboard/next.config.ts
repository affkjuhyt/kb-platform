import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  async rewrites() {
    return [
      {
        source: "/api/:path*",
        destination: "http://localhost:8080/api/:path*",
      },
      // Keep this for direct auth calls if needed, or map generic /auth
      {
        source: "/auth/:path*",
        destination: "http://localhost:8080/auth/:path*",
      },
    ];
  },
};

export default nextConfig;
