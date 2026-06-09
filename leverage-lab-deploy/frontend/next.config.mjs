/** @type {import('next').NextConfig} */

// Resolve the backend API base URL. Render's `fromService property: host`
// provides only the hostname (no protocol), so add https:// when missing.
function resolveApiBase() {
  let api = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";
  if (!/^https?:\/\//.test(api)) {
    api = "https://" + api;
  }
  return api.replace(/\/$/, "");
}

const nextConfig = {
  reactStrictMode: true,
  async rewrites() {
    const api = resolveApiBase();
    return [{ source: "/api/:path*", destination: `${api}/api/:path*` }];
  },
};
export default nextConfig;
