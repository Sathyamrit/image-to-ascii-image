# File	Role
## src/App.tsx	
Renders the UI only; uses useImageConverter().

## src/hooks/useImageConverter.ts	
State, preview cleanup, file pick, and convert flow.

## src/api/convertApi.ts	
postConvert() + resultDataUrl() for the API response.

## src/config/api.ts	
resolveApiUrl() and API_URL.

## src/types/convert.ts	
ConvertResponse type.

## src/utils/dataUrl.ts	
extractBase64FromDataUrl().

## src/utils/fileToBase64.ts	
fileToBase64Payload() for uploads.