import { API_URL } from '../config/api'
import type { ConvertResponse } from '../types/convert'

export async function postConvert(payload: Record<string, unknown>): Promise<ConvertResponse> {
  const res = await fetch(API_URL, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const text = await res.text().catch(() => '')
    throw new Error(`API error (${res.status}): ${text || res.statusText}`)
  }

  return (await res.json()) as ConvertResponse
}

export function resultDataUrl(data: ConvertResponse): string {
  const mime = data.imageMimeType || 'image/png'
  return `data:${mime};base64,${data.imageBase64}`
}
