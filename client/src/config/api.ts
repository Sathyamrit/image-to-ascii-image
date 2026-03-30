export function resolveApiUrl(): string {
  const fromEnv = (import.meta.env.VITE_API_URL as string | undefined)?.trim()
  if (fromEnv) return fromEnv
  return '/api/convert'
}

export const API_URL = resolveApiUrl()
