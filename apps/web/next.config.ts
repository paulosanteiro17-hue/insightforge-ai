import type { NextConfig } from "next";
import path from "node:path";
import {
  configuredApiOrigin,
  configuredWebOrigin
} from "./src/lib/api/configured-origin";

const apiOrigin = configuredApiOrigin();
const publicWebOrigin = configuredWebOrigin();
const runtimeAdapter =
  process.env.INSIGHTFORGE_API_MODE === "mock"
    ? "./src/lib/api/mock-adapter.ts"
    : "./src/lib/api/live-adapter.ts";
const runtimeServerBootstrap =
  process.env.INSIGHTFORGE_API_MODE === "mock"
    ? "./src/lib/api/mock-server-bootstrap.ts"
    : "./src/lib/api/server-bootstrap.ts";
const isDevelopment = process.env.NODE_ENV === "development";
const useStandaloneOutput = process.env.INSIGHTFORGE_STANDARD_START !== "1";
const enableHsts = publicWebOrigin.startsWith("https://");
const contentSecurityPolicy = [
  "default-src 'self'",
  `script-src 'self' 'unsafe-inline'${isDevelopment ? " 'unsafe-eval'" : ""}`,
  "style-src 'self' 'unsafe-inline'",
  "img-src 'self' blob: data:",
  "font-src 'self'",
  "connect-src 'self'",
  "media-src 'self'",
  "object-src 'none'",
  "base-uri 'self'",
  "form-action 'self'",
  "frame-ancestors 'none'",
  "manifest-src 'self'",
  "worker-src 'self' blob:"
].join("; ");

const nextConfig: NextConfig = {
  output: useStandaloneOutput ? "standalone" : undefined,
  allowedDevOrigins: ["127.0.0.1", "localhost"],
  poweredByHeader: false,
  reactStrictMode: true,
  turbopack: {
    resolveAlias: {
      "@runtime-api": runtimeAdapter,
      "@runtime-server-bootstrap": runtimeServerBootstrap
    }
  },
  webpack(config) {
    config.resolve.alias["@runtime-api"] = path.resolve(runtimeAdapter);
    config.resolve.alias["@runtime-server-bootstrap"] = path.resolve(
      runtimeServerBootstrap
    );
    return config;
  },
  async headers() {
    return [
      {
        source: "/:path*",
        headers: [
          { key: "Content-Security-Policy", value: contentSecurityPolicy },
          { key: "Referrer-Policy", value: "no-referrer" },
          { key: "X-Content-Type-Options", value: "nosniff" },
          { key: "X-Frame-Options", value: "DENY" },
          {
            key: "Permissions-Policy",
            value:
              "camera=(), display-capture=(), geolocation=(), microphone=(), payment=(), usb=()"
          },
          ...(enableHsts
            ? [
                {
                  key: "Strict-Transport-Security",
                  value: "max-age=31536000"
                }
              ]
            : [])
        ]
      }
    ];
  },
  async rewrites() {
    return [
      {
        source: "/api/v1/:path*",
        destination: `${apiOrigin}/api/v1/:path*`
      }
    ];
  }
};

export default nextConfig;
