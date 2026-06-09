import path from "node:path";

import type { NextConfig } from "next";

const nextConfig: NextConfig = {
  transpilePackages: ["@heartscan/api-client"],
  // Don't leak the framework/version (fingerprinting). [security: A05]
  poweredByHeader: false,
  turbopack: {
    // Keep workspace root anchored to this monorepo; avoids Next auto-picking
    // unrelated lockfiles from parent folders on developer machines.
    root: path.join(__dirname, "../.."),
  },
  async headers() {
    return [
      {
        source: "/(.*)",
        headers: [
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "Referrer-Policy", value: "strict-origin-when-cross-origin" },
          // Clickjacking defense: deny framing entirely (CSP frame-ancestors is
          // the modern form; X-Frame-Options covers older browsers). [A05]
          { key: "X-Frame-Options", value: "DENY" },
          // Force HTTPS for 2 years incl. subdomains (medical app). [A02/A05]
          { key: "Strict-Transport-Security", value: "max-age=63072000; includeSubDomains; preload" },
          // Lock down powerful browser features the app never uses. [A05]
          { key: "Permissions-Policy", value: "camera=(), microphone=(), geolocation=(), payment=()" },
          {
            key: "Content-Security-Policy",
            value: [
              "default-src 'self'",
              "script-src 'self' 'unsafe-inline' 'unsafe-eval' https://*.clerk.accounts.dev https://*.clerk.com",
              "style-src 'self' 'unsafe-inline'",
              "img-src 'self' data: blob: https:",
              "font-src 'self' data:",
              "connect-src 'self' https://*.supabase.co https://*.clerk.accounts.dev https://*.clerk.com wss:",
              "frame-src https://*.clerk.accounts.dev https://*.clerk.com",
              "frame-ancestors 'none'",
              "base-uri 'self'",
              "form-action 'self'",
            ].join("; "),
          },
        ],
      },
    ];
  },
};

export default nextConfig;
