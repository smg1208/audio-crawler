# Hướng dẫn sử dụng Google Cloud Text-to-Speech

## Tổng quan

Google Cloud Text-to-Speech là dịch vụ TTS chất lượng cao của Google, hỗ trợ nhiều ngôn ngữ và giọng đọc tự nhiên.

## Ưu điểm

- ✅ **Chất lượng cao**: Giọng đọc tự nhiên, rõ ràng
- ✅ **Nhiều giọng đọc**: Hỗ trợ nhiều giọng đọc tiếng Việt
- ✅ **Ổn định**: Dịch vụ cloud của Google
- ✅ **Tùy chỉnh**: Hỗ trợ SSML, tốc độ, cao độ

## Nhược điểm

- ⚠️ **Cần billing**: Yêu cầu Google Cloud account với billing enabled
- ⚠️ **Có phí**: Tính phí theo số ký tự (có free tier)
- ⚠️ **Cần credentials**: Yêu cầu service account credentials

## Cài đặt

### 1. Cài đặt thư viện

```bash
pip install google-cloud-texttospeech
```

### 2. Tạo Google Cloud Project

1. Truy cập: https://console.cloud.google.com/
2. Tạo project mới hoặc chọn project hiện có
3. Bật billing (cần thiết để sử dụng API)

### 3. Bật Text-to-Speech API

1. Vào **APIs & Services** > **Library**
2. Tìm "Cloud Text-to-Speech API"
3. Click **Enable**

### 4. Tạo Service Account

1. Vào **IAM & Admin** > **Service Accounts**
2. Click **Create Service Account**
3. Điền tên và mô tả
4. Click **Create and Continue**
5. Chọn role: **Cloud Text-to-Speech API User**
6. Click **Done**

### 5. Tạo và tải credentials

1. Click vào service account vừa tạo
2. Vào tab **Keys**
3. Click **Add Key** > **Create new key**
4. Chọn **JSON**
5. Tải file JSON về máy
6. Lưu file vào thư mục an toàn (ví dụ: `credentials/google-cloud-tts.json`)

**⚠️ Lưu ý bảo mật:**
- Không commit file credentials vào Git
- Thêm vào `.gitignore`: `credentials/*.json`
- Giữ file credentials an toàn

## Cấu hình

### Trong config.json

```json
{
  "tts_backend": "google-cloud",
  "google_cloud_credentials_path": "credentials/google-cloud-tts.json",
  "google_cloud_language_code": "vi-VN",
  "google_cloud_voice_name": "vi-VN-Standard-A",
  "google_cloud_ssml_gender": "FEMALE"
}
```

**Các tham số:**
- `google_cloud_credentials_path`: **Bắt buộc** - Đường dẫn đến file credentials JSON
- `google_cloud_language_code`: Mã ngôn ngữ (mặc định: `"vi-VN"`)
- `google_cloud_voice_name`: Tên giọng đọc cụ thể (tùy chọn)
- `google_cloud_ssml_gender`: Giới tính (`"FEMALE"`, `"MALE"`, `"NEUTRAL"`)

### Sử dụng Environment Variable

Thay vì dùng `credentials_path`, bạn có thể set environment variable:

```bash
export GOOGLE_APPLICATION_CREDENTIALS="path/to/credentials.json"
```

Sau đó trong config.json, để trống `google_cloud_credentials_path`:

```json
{
  "tts_backend": "google-cloud",
  "google_cloud_language_code": "vi-VN"
}
```

## Giọng đọc tiếng Việt

### Standard Voices (Chất lượng tốt)

- `vi-VN-Standard-A` - Nữ
- `vi-VN-Standard-B` - Nam
- `vi-VN-Standard-C` - Nữ
- `vi-VN-Standard-D` - Nam

### Neural Voices (Chất lượng cao, tự nhiên hơn)

- `vi-VN-Neural2-A` - Nữ
- `vi-VN-Neural2-B` - Nam
- `vi-VN-Neural2-C` - Nữ
- `vi-VN-Neural2-D` - Nam

### WaveNet Voices (Chất lượng rất cao)

- `vi-VN-Wavenet-A` - Nữ
- `vi-VN-Wavenet-B` - Nam
- `vi-VN-Wavenet-C` - Nữ
- `vi-VN-Wavenet-D` - Nam

**Lưu ý:** WaveNet voices có giá cao hơn Standard và Neural.

## Sử dụng

### 1. Với run.py

```bash
python3 run.py --config config.json \
  --tts-backend google-cloud \
  --google-cloud-credentials credentials/google-cloud-tts.json
```

### 2. Trong code Python

```python
from crawler.tts_engines import GoogleCloudTTS
import asyncio

# Khởi tạo
gcloud = GoogleCloudTTS(
    credentials_path='credentials/google-cloud-tts.json',
    language_code='vi-VN',
    voice_name='vi-VN-Neural2-A',
    ssml_gender='FEMALE'
)

# Synthesize
asyncio.run(gcloud.speak('Xin chào các bạn', 'output.mp3'))
```

### 3. Với TextToAudioConverter

```python
from crawler.converter import TextToAudioConverter

converter = TextToAudioConverter(
    backend='google-cloud',
    google_cloud_credentials_path='credentials/google-cloud-tts.json',
    google_cloud_language_code='vi-VN',
    google_cloud_voice_name='vi-VN-Neural2-A'
)

converter.convert('input.txt', 'output.mp3')
```

## Giá cả

Google Cloud TTS tính phí theo số ký tự:

- **Standard voices**: $4.00 / 1 triệu ký tự
- **Neural voices**: $16.00 / 1 triệu ký tự
- **WaveNet voices**: $16.00 / 1 triệu ký tự

**Free tier:**
- 0-4 triệu ký tự/tháng: Miễn phí (chỉ cho Standard voices)
- Sau 4 triệu: Tính phí theo bảng giá

**Ví dụ:**
- 100,000 ký tự với Standard: Miễn phí (trong free tier)
- 100,000 ký tự với Neural: ~$1.60

## So sánh với các engine khác

| Engine | Chất lượng | Giá | Offline | Cần Config |
|--------|------------|-----|---------|------------|
| **google-cloud** | ⭐⭐⭐⭐⭐ | 💰💰 | ❌ | ✅ Credentials |
| **edge-tts** | ⭐⭐⭐⭐⭐ | ✅ Free | ❌ | ❌ |
| **fpt-ai** | ⭐⭐⭐⭐⭐ | 💰 (free tier) | ❌ | ✅ API key |
| **piper** | ⭐⭐⭐⭐ | ✅ Free | ✅ | ✅ Model |
| **macos** | ⭐⭐⭐ | ✅ Free | ✅ | ❌ |

## Troubleshooting

### Lỗi: "google-cloud-texttospeech library is not available"

**Giải pháp:**
```bash
pip install google-cloud-texttospeech
```

### Lỗi: "Failed to initialize Google Cloud TTS client"

**Nguyên nhân có thể:**
1. Credentials file không đúng
2. Service account không có quyền
3. Billing chưa được bật

**Giải pháp:**
1. Kiểm tra file credentials có đúng không
2. Đảm bảo service account có role "Cloud Text-to-Speech API User"
3. Kiểm tra billing đã được bật trong Google Cloud Console

### Lỗi: "API not enabled"

**Giải pháp:**
1. Vào Google Cloud Console
2. Bật "Cloud Text-to-Speech API"

### Lỗi: "Quota exceeded"

**Nguyên nhân:** Đã vượt quá free tier hoặc quota

**Giải pháp:**
1. Kiểm tra usage trong Google Cloud Console
2. Nâng cấp billing account nếu cần

## Best Practices

1. **Bảo mật credentials:**
   - Không commit file credentials vào Git
   - Sử dụng environment variable khi có thể
   - Giới hạn quyền của service account

2. **Tối ưu chi phí:**
   - Sử dụng Standard voices cho free tier
   - Chỉ dùng Neural/WaveNet khi cần chất lượng cao
   - Monitor usage trong Google Cloud Console

3. **Error handling:**
   - Luôn có fallback engine
   - Handle quota errors gracefully
   - Log errors để debug

## Ví dụ cấu hình đầy đủ

```json
{
  "tts_backend": "google-cloud",
  "google_cloud_credentials_path": "credentials/google-cloud-tts.json",
  "google_cloud_language_code": "vi-VN",
  "google_cloud_voice_name": "vi-VN-Neural2-A",
  "google_cloud_ssml_gender": "FEMALE",
  "enable_tts_fallback": true,
  "fallback_engines": ["edge-tts", "macos"]
}
```

## Tài liệu tham khảo

- Google Cloud TTS Documentation: https://cloud.google.com/text-to-speech/docs
- Pricing: https://cloud.google.com/text-to-speech/pricing
- Available Voices: https://cloud.google.com/text-to-speech/docs/voices

