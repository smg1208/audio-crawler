# Hướng dẫn cấu hình TTS trong config.json

## Tổng quan

File `config.json` hỗ trợ cấu hình cho tất cả các TTS engines:
- `edge-tts` (Microsoft Edge TTS)
- `macos` (macOS native TTS)
- `gtts` (Google Text-to-Speech - Simple)
- `fpt-ai` (FPT.AI TTS)
- `piper` (Piper TTS - Offline)
- `google-cloud` (Google Cloud Text-to-Speech)

## Cấu hình chung

### `tts_backend`
Chọn engine TTS sử dụng:
- `"edge-tts"` - Microsoft Edge TTS (mặc định)
- `"macos"` - macOS native TTS
- `"gtts"` - Google Text-to-Speech (Simple)
- `"fpt-ai"` - FPT.AI TTS
- `"piper"` - Piper TTS (Offline)
- `"google-cloud"` - Google Cloud Text-to-Speech

### `tts_voice`
Tên giọng đọc (tùy chọn, tùy theo engine)

### `enable_tts_fallback`
Bật/tắt fallback tự động khi engine chính lỗi:
- `true` - Tự động fallback sang engine dự phòng
- `false` - Không fallback (mặc định)

### `fallback_engines`
Danh sách engine dự phòng khi fallback:
- Mặc định: `["macos", "gtts"]`
- Ví dụ: `["macos", "gtts", "piper"]`

## Cấu hình cho từng engine

### 1. Edge TTS (`edge-tts`)

```json
{
  "tts_backend": "edge-tts",
  "tts_voice": "vi-VN-NamMinhNeural",
  "edge_rate": 1.0
}
```

**Các tham số:**
- `tts_voice`: Tên giọng đọc
  - `"vi-VN-NamMinhNeural"` - Nam (mặc định)
  - `"vi-VN-HoaiMyNeural"` - Nữ
- `edge_rate`: Tốc độ đọc (0.5-2.0, mặc định: 1.0)

### 2. macOS TTS (`macos`)

```json
{
  "tts_backend": "macos",
  "macos_voice": "Linh"
}
```

**Các tham số:**
- `macos_voice`: Tên giọng đọc macOS
  - `"Linh"` - Nữ, miền Bắc (mặc định)
  - `"Nam"` - Nam (nếu có)

**Lưu ý:** Chỉ hoạt động trên macOS

### 3. Google TTS (`gtts`)

```json
{
  "tts_backend": "gtts"
}
```

**Các tham số:**
- Không cần cấu hình thêm
- Tự động sử dụng tiếng Việt (`lang='vi'`)

### 4. FPT.AI TTS (`fpt-ai`)

```json
{
  "tts_backend": "fpt-ai",
  "fpt_api_key": "YOUR_API_KEY",
  "fpt_voice": "banmai"
}
```

**Các tham số:**
- `fpt_api_key`: **Bắt buộc** - API key từ FPT.AI
  - Đăng ký tại: https://fpt.ai/tts
- `fpt_voice`: Tên giọng đọc
  - `"banmai"` - Nữ, miền Bắc (mặc định)
  - `"lannhi"` - Nữ, miền Nam
  - `"leminh"` - Nam, miền Bắc
  - `"giahuy"` - Nam, miền Nam

### 5. Piper TTS (`piper`)

```json
{
  "tts_backend": "piper",
  "piper_model_path": "models/vi_VN-vivos-x_low.onnx",
  "piper_config_path": "models/vi_VN-vivos-x_low.onnx.json"
}
```

**Các tham số:**
- `piper_model_path`: **Bắt buộc** - Đường dẫn đến file model `.onnx`
  - Ví dụ: `"models/vi_VN-vivos-x_low.onnx"`
- `piper_config_path`: **Tùy chọn** - Đường dẫn đến file config `.json`
  - Ví dụ: `"models/vi_VN-vivos-x_low.onnx.json"`
  - Nếu để trống, hệ thống sẽ tự tìm file `.json` cùng tên

**Lưu ý:**
- Model phải được tải về trước
- Xem hướng dẫn tải model: `models/README_DOWNLOAD.md`

### 6. Google Cloud TTS (`google-cloud`)

```json
{
  "tts_backend": "google-cloud",
  "google_cloud_credentials_path": "credentials/google-cloud-tts.json",
  "google_cloud_language_code": "vi-VN",
  "google_cloud_voice_name": "vi-VN-Neural2-A",
  "google_cloud_ssml_gender": "FEMALE"
}
```

**Các tham số:**
- `google_cloud_credentials_path`: **Bắt buộc** - Đường dẫn đến file credentials JSON
  - Ví dụ: `"credentials/google-cloud-tts.json"`
  - Hoặc set environment variable: `GOOGLE_APPLICATION_CREDENTIALS`
- `google_cloud_language_code`: Mã ngôn ngữ (mặc định: `"vi-VN"`)
- `google_cloud_voice_name`: Tên giọng đọc cụ thể (tùy chọn)
  - Ví dụ: `"vi-VN-Neural2-A"`, `"vi-VN-Standard-A"`, `"vi-VN-Wavenet-A"`
- `google_cloud_ssml_gender`: Giới tính (`"FEMALE"`, `"MALE"`, `"NEUTRAL"`)

**Lưu ý:**
- Cần Google Cloud account với billing enabled
- Cần tạo service account và download credentials
- Có free tier: 4 triệu ký tự/tháng (Standard voices)
- Xem hướng dẫn chi tiết: `GOOGLE_CLOUD_TTS_GUIDE.md`

## Ví dụ cấu hình đầy đủ

### Ví dụ 1: Edge TTS với fallback

```json
{
  "tts_backend": "edge-tts",
  "tts_voice": "vi-VN-NamMinhNeural",
  "edge_rate": 1.0,
  "enable_tts_fallback": true,
  "fallback_engines": ["macos", "gtts"]
}
```

### Ví dụ 2: macOS TTS (Offline)

```json
{
  "tts_backend": "macos",
  "macos_voice": "Linh"
}
```

### Ví dụ 3: Piper TTS (Offline, nhanh)

```json
{
  "tts_backend": "piper",
  "piper_model_path": "models/vi_VN-vivos-x_low.onnx",
  "piper_config_path": "models/vi_VN-vivos-x_low.onnx.json"
}
```

### Ví dụ 4: FPT.AI TTS (Chất lượng cao)

```json
{
  "tts_backend": "fpt-ai",
  "fpt_api_key": "YOUR_API_KEY_HERE",
  "fpt_voice": "banmai"
}
```

### Ví dụ 5: Google Cloud TTS (Chất lượng rất cao)

```json
{
  "tts_backend": "google-cloud",
  "google_cloud_credentials_path": "credentials/google-cloud-tts.json",
  "google_cloud_language_code": "vi-VN",
  "google_cloud_voice_name": "vi-VN-Neural2-A",
  "google_cloud_ssml_gender": "FEMALE"
}
```

## So sánh các engines

| Engine | Online/Offline | Cần Config | Chất lượng | Tốc độ | Giá |
|--------|---------------|------------|------------|--------|-----|
| **edge-tts** | Online | `tts_voice`, `edge_rate` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Free |
| **macos** | Offline | `macos_voice` | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Free |
| **gtts** | Online | Không | ⭐⭐⭐ | ⭐⭐⭐⭐ | ✅ Free |
| **fpt-ai** | Online | `fpt_api_key`, `fpt_voice` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 💰 Free tier |
| **piper** | Offline | `piper_model_path` | ⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Free |
| **google-cloud** | Online | `credentials_path` | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐ | 💰 Free tier |

## Lưu ý

1. **Chỉ cần cấu hình cho engine đang sử dụng**: Các tham số khác có thể để trống
2. **Fallback**: Nếu bật `enable_tts_fallback`, đảm bảo các engine dự phòng có sẵn
3. **Model files**: Piper TTS cần tải model trước khi sử dụng
4. **API keys**: FPT.AI cần API key hợp lệ

## Troubleshooting

### Lỗi: "Unknown backend"
- Kiểm tra `tts_backend` có đúng tên không
- Tên hợp lệ: `edge-tts`, `macos`, `gtts`, `fpt-ai`, `piper`

### Lỗi: "Model file not found" (Piper)
- Kiểm tra `piper_model_path` có đúng không
- Đảm bảo file `.onnx` tồn tại

### Lỗi: "API key required" (FPT.AI)
- Kiểm tra `fpt_api_key` đã được điền chưa
- Đảm bảo API key hợp lệ

### Fallback không hoạt động
- Kiểm tra `enable_tts_fallback` = `true`
- Đảm bảo các engine trong `fallback_engines` có sẵn

