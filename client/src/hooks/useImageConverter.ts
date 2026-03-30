import { useEffect, useState } from 'react'

import { postConvert, resultDataUrl } from '../api/convertApi'
import { fileToBase64Payload } from '../utils/fileToBase64'
import { buildUrlConvertPayload } from '../utils/urlImagePayload'

export function useImageConverter() {
  const [imageUrl, setImageUrl] = useState('')
  const [file, setFile] = useState<File | null>(null)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [resultSrc, setResultSrc] = useState<string | null>(null)

  useEffect(() => {
    return () => {
      if (previewUrl) URL.revokeObjectURL(previewUrl)
    }
  }, [previewUrl])

  const onPickFile = (f: File | null) => {
    setFile(f)
    setResultSrc(null)
    setError(null)

    if (!f) {
      setPreviewUrl(null)
      return
    }
    setPreviewUrl(URL.createObjectURL(f))
  }

  const convert = async () => {
    setError(null)
    setResultSrc(null)

    if (!file && !imageUrl.trim()) {
      setError('Provide an image URL or choose an image file.')
      return
    }

    setLoading(true)
    try {
      const payload: Record<string, unknown> = file
        ? await fileToBase64Payload(file)
        : await buildUrlConvertPayload(imageUrl.trim())

      const data = await postConvert(payload)
      setResultSrc(resultDataUrl(data))
    } catch (e) {
      const msg = e instanceof Error ? e.message : String(e)
      setError(msg)
    } finally {
      setLoading(false)
    }
  }

  return {
    imageUrl,
    setImageUrl,
    file,
    previewUrl,
    loading,
    error,
    resultSrc,
    onPickFile,
    convert,
  }
}
