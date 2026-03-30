import { extractBase64FromDataUrl } from './dataUrl'

export async function fileToBase64Payload(file: File) {
  const dataUrl = await new Promise<string>((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(new Error('Failed to read file'))
    reader.readAsDataURL(file)
  })
  const { base64, mimeType } = extractBase64FromDataUrl(dataUrl)
  return {
    imageBase64: base64,
    imageMimeType: file.type || mimeType || 'image/png',
  }
}
