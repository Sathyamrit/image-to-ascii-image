export function extractBase64FromDataUrl(dataUrl: string) {
  const commaIdx = dataUrl.indexOf(',')
  if (commaIdx === -1) return { base64: dataUrl, mimeType: '' }
  const header = dataUrl.slice(0, commaIdx)
  const base64 = dataUrl.slice(commaIdx + 1)
  const mimeType = header.replace('data:', '').replace(';base64', '')
  return { base64, mimeType }
}
