import nextEnv from "@next/env";
import path from "path";
import { fileURLToPath } from "url";

const { loadEnvConfig } = nextEnv;
const __dirname = path.dirname(fileURLToPath(import.meta.url));
// Load repo-root `.env` so `NEXT_PUBLIC_*` matches Docker / one file (Next only auto-loads `frontend/.env*`).
loadEnvConfig(path.join(__dirname, ".."));

const serverActionAllowedOrigins = ["localhost:3000"];
for (const raw of [process.env.NEXTAUTH_URL, process.env.NEXT_PUBLIC_API_URL]) {
  if (!raw) continue;
  try {
    serverActionAllowedOrigins.push(new URL(raw).host);
  } catch {
    /* ignore invalid URL */
  }
}
const uniqueServerActionOrigins = [...new Set(serverActionAllowedOrigins)];

/** @type {import('next').NextConfig} */
const nextConfig = {
  output: "standalone",
  experimental: {
    serverActions: {
      allowedOrigins: uniqueServerActionOrigins,
    },
  },
  env: {
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL || "http://localhost:8001",
  },
};

export default nextConfig;
