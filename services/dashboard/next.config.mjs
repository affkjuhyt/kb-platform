/** @type {import('next').NextConfig} */
const nextConfig = {
    async rewrites() {
        const apiUrl = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8080";
        return [
            {
                source: "/api/:path*",
                destination: `${apiUrl}/:path*`,
            },
            // Keep this for direct auth calls if needed, or map generic /auth
            {
                source: "/auth/:path*",
                destination: `${apiUrl}/auth/:path*`,
            },
        ];
    },
};

export default nextConfig;
