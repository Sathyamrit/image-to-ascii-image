import { extractBase64FromDataUrl } from './dataUrl'

async function blobToBase64Payload(blob: Blob): Promise<{ imageBase64: string; imageMimeType: string }> {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('Failed to read image'))
    reader.readAsDataURL(blob)
  })
  const { base64, mimeType } = extractBase64FromDataUrl(dataUrl)
  return {
    imageBase64: base64,
    imageMimeType: mimeType || blob.type || 'image/png',
  }
}

const OG_IMAGE_META = /<meta\s+property=["']og:image["']\s+content=["']([^"']+)["']/i

/** ImgBB page URLs (ibb.co/xxx) are HTML; og:image points to i.ibb.co. */
async function resolveImgbbGalleryUrl(url: string): Promise<string> {
  try {
    const u = new URL(url)
    if (u.hostname.replace(/^www\./, '') !== 'ibb.co') return url
    if (u.hostname.includes('i.ibb.co')) return url
    const page = await fetch(url, { mode: 'cors', credentials: 'omit', cache: 'no-store' })
    if (!page.ok) return url
    const html = await page.text()
    const m = html.match(OG_IMAGE_META)
    if (m?.[1]) return m[1].replace(/&amp;/g, '&')
  } catch {
    // CORS on HTML fetch — backend can still resolve
  }
  return url
}

/**
 * Load the image in the browser (same cookies/UA/network as the user), then send bytes as base64.
 * Many hosts block server-side hotlink fetches but allow normal browser loads or CORS GET.
 */
async function tryBrowserFetchImageAsPayload(url: string): Promise<{ imageBase64: string; imageMimeType: string }> {
  const imageUrl = await resolveImgbbGalleryUrl(url.trim())
  const res = await fetch(imageUrl, {
    mode: 'cors',
    credentials: 'omit',
    cache: 'no-store',
  })
  if (!res.ok) throw new Error(`Fetch failed (${res.status})`)

  const blob = await res.blob()
  const head = (await blob.slice(0, 64).text()).trimStart().toLowerCase()
  if (head.startsWith('<') || head.startsWith('<!doctype')) {
    throw new Error('Not an image (got HTML)')
  }
  if (blob.type.startsWith('text/')) {
    throw new Error('Not an image (got text)')
  }

  return blobToBase64Payload(blob)
}

/** Prefer browser fetch + base64; fall back to server-side URL download (may still fail on strict hotlink blocks). */
export async function buildUrlConvertPayload(url: string): Promise<Record<string, unknown>> {
  try {
    return await tryBrowserFetchImageAsPayload(url)
  } catch {
    return { imageUrl: url }
  }
}
