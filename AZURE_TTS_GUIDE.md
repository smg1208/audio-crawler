# Hướng dẫn sử dụng Azure Text-to-Speech

## Tổng quan

Azure TTS là dịch vụ TTS chính thức từ Microsoft, **ổn định hơn Edge TTS** và có **free tier** (0-500K ký tự/tháng).

**Azure TTS và Edge TTS sử dụng cùng giọng nói Microsoft**, nhưng Azure TTS:
- ✅ **Ổn định hơn** (có SLA 99.9%)
- ✅ **Có free tier** (0-500K ký tự/tháng)
- ✅ **Có support** từ Microsoft
- ✅ **Rate limiting rõ ràng**, không bị block bất ngờ
- 💰 **Trả phí** sau free tier ($15/1M ký tự cho Standard, $16/1M cho Neural)

## So sánh với Edge TTS

| Tính năng | Edge TTS | Azure TTS |
|-----------|----------|-----------|
| **Miễn phí** | ✅ Hoàn toàn | 💰 Free tier (0-500K/tháng) |
| **Ổn định** | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **SLA** | ❌ Không có | ✅ 99.9% |
| **Support** | ❌ Không có | ✅ Có |
| **Giọng nói** | Giống nhau | Giống nhau |

## Cài đặt

### 1. Cài đặt Python package

```bash
pip install azure-cognitiveservices-speech
```

### 2. Tạo Azure account và lấy subscription key

1. Truy cập https://azure.microsoft.com/free/
2. Đăng ký tài khoản Azure (có thể dùng free tier)
3. Tạo **Speech Service** resource:
   - Vào Azure Portal → Create a resource
   - Tìm "Speech" → Chọn "Speech Services"
   - Chọn subscription, resource group, region (ví dụ: `eastus`)
   - Chọn pricing tier (F0 = Free tier, S0 = Standard)
   - Tạo resource
4. Lấy **Subscription Key** và **Region**:
   - Vào resource → Keys and Endpoint
   - Copy **Key 1** (subscription key)
   - Copy **Location/Region** (ví dụ: `eastus`)

### 3. Cấu hình

Có 3 cách để cấu hình Azure TTS:

#### Cách 1: Environment variables (Khuyến nghị)

```bash
export AZURE_SPEECH_KEY="your-subscription-key-here"
export AZURE_SPEECH_REGION="eastus"  # Optional, default: eastus
```

#### Cách 2: Command-line arguments

```bash
python3 run.py --config config.json \
  --tts-backend azure \
  --azure-subscription-key "your-subscription-key" \
  --azure-region "eastus" \
  --azure-voice "vi-VN-HoaiMyNeural"
```

#### Cách 3: config.json

```json
{
  "tts_backend": "azure",
  "azure_subscription_key": "your-subscription-key-here",
  "azure_region": "eastus",
  "azure_voice_name": "vi-VN-HoaiMyNeural"
}
```

## Giọng nói tiếng Việt

Azure TTS hỗ trợ các giọng nói tiếng Việt sau (giống Edge TTS):

| Voice Name | Giới tính | Mô tả |
|------------|-----------|-------|
| `vi-VN-HoaiMyNeural` | Nữ | Giọng nữ, tự nhiên |
| `vi-VN-NamMinhNeural` | Nam | Giọng nam, tự nhiên |

## Sử dụng

### Với run.py

```bash
# Sử dụng environment variables
export AZURE_SPEECH_KEY="your-key"
export AZURE_SPEECH_REGION="eastus"

python3 run.py --config config.json --tts-backend azure --azure-voice vi-VN-HoaiMyNeural
```

### Với text_to_mp3.py

```bash
python3 text_to_mp3.py \
  --text "Xin chào, đây là test Azure TTS" \
  --output test.mp3 \
  --backend azure \
  --azure-subscription-key "your-key" \
  --azure-region "eastus" \
  --azure-voice "vi-VN-HoaiMyNeural"
```

## Pricing (Giá)

### Free Tier
- **0-500,000 ký tự/tháng**: Miễn phí
- **Sau 500K**: Trả phí

### Standard Voices
- **$15.00 / 1 triệu ký tự** (sau free tier)

### Neural Voices (Khuyến nghị)
- **$16.00 / 1 triệu ký tự** (sau free tier)
- Chất lượng cao hơn, tự nhiên hơn

**Ví dụ:**
- 100,000 ký tự/tháng: **Miễn phí** (trong free tier)
- 1 triệu ký tự/tháng: ~$15-16 (sau free tier)

## Lưu ý

1. **Free tier đủ cho nhiều trường hợp**: 500K ký tự/tháng tương đương khoảng 50-100 chương truyện (tùy độ dài)
2. **Azure TTS ổn định hơn Edge TTS**: Không gặp lỗi "No audio was received"
3. **Có retry mechanism**: Hệ thống tự động retry nếu có lỗi
4. **Rate limiting rõ ràng**: Không bị block bất ngờ như Edge TTS

## Troubleshooting

### Lỗi: "Azure TTS subscription key not provided"
- Kiểm tra `AZURE_SPEECH_KEY` environment variable hoặc `--azure-subscription-key`
- Đảm bảo key đúng và chưa hết hạn

### Lỗi: "Azure TTS canceled: Error"
- Kiểm tra region có đúng không (ví dụ: `eastus`, `westus`)
- Kiểm tra voice name có đúng không (ví dụ: `vi-VN-HoaiMyNeural`)
- Kiểm tra Azure account có billing enabled không

### Lỗi: "azure-cognitiveservices-speech not available"
- Cài đặt: `pip install azure-cognitiveservices-speech`

## Kết luận

**Azure TTS là giải pháp tốt thay thế Edge TTS** khi:
- ✅ Edge TTS đang lỗi hoặc không ổn định
- ✅ Cần ổn định cao cho production
- ✅ Có ngân sách nhỏ (free tier đủ cho nhiều trường hợp)
- ✅ Cần support từ Microsoft

**Khuyến nghị**: Sử dụng Azure TTS với free tier nếu Edge TTS không hoạt động ổn định.

