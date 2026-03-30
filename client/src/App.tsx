import { useImageConverter } from './hooks/useImageConverter'

export default function App() {
  const {
    imageUrl,
    setImageUrl,
    previewUrl,
    loading,
    error,
    resultSrc,
    onPickFile,
    convert,
  } = useImageConverter()

  return (
    <div id="page">
      <h1>Image to ASCII</h1>

      <div id="card">
        <div id="inputs">
          <label>
            Image URL
            <input
              type="url"
              placeholder="https://example.com/photo.jpg"
              value={imageUrl}
              onChange={(e) => setImageUrl(e.target.value)}
            />
          </label>

          <div id="fileRow">
            <label>
              Upload image
              <input
                type="file"
                accept="image/*"
                onChange={(e) => onPickFile(e.target.files?.[0] ?? null)}
              />
            </label>
          </div>

          {previewUrl ? (
            <div id="preview">
              <div id="previewLabel">Preview</div>
              <img src={previewUrl} alt="Selected upload preview" />
            </div>
          ) : null}

          <button id="convertBtn" type="button" disabled={loading} onClick={convert}>
            {loading ? 'Converting...' : 'Convert'}
          </button>

          {error ? <div id="error">{error}</div> : null}
        </div>

        <div id="output">
          <div id="outputHeader">Result</div>
          {resultSrc ? (
            <img id="resultImg" src={resultSrc} alt="ASCII converted output" />
          ) : (
            <div id="empty">Your converted ASCII image will appear here.</div>
          )}
        </div>
      </div>
    </div>
  )
}
