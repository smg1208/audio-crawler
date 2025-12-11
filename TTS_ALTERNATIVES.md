# Giải pháp thay thế cho Edge TTS

## Tổng quan

Dự án hỗ trợ 4 backend TTS:
1. **ttx** - Command-line tool (mặc định)
2. **edge-tts** - Microsoft Edge TTS (miễn phí, chất lượng cao)
3. **gtts** - Google Text-to-Speech (miễn phí, đơn giản, không cần API key)
4. **fpt-ai** - FPT.AI TTS (chất lượng cao, có free tier, cần API key)

## So sánh các giải pháp

| Backend | Miễn phí | Chất lượng | Ổn định | Tùy chỉnh | Cần API Key | Hỗ trợ tiếng Việt |
|---------|----------|------------|---------|-----------|-------------|-------------------|
| **gtts** | ✅ Hoàn toàn | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐ | ❌ Không | ✅ Tốt |
| **fpt-ai** | ✅ Free tier | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ | ✅ Có | ✅ Rất tốt |
| **edge-tts** | ✅ Hoàn toàn | ⭐⭐⭐⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐ | ❌ Không | ✅ Tốt |
| **ttx** | ✅ Hoàn toàn | ⭐⭐⭐ | ⭐⭐⭐⭐ | ⭐⭐⭐ | ❌ Không | ✅ Tốt |

## 1. gTTS (Google Text-to-Speech) - Khuyến nghị cho giải pháp tạm thời

### Ưu điểm
- ✅ **Hoàn toàn miễn phí**, không cần API key
- ✅ **Đơn giản**, dễ sử dụng
- ✅ **Ổn định**, ít lỗi kết nối
- ✅ Hỗ trợ tiếng Việt tốt
- ✅ Không có rate limiting nghiêm ngặt

### Nhược điểm
- ⚠️ Chất lượng thấp hơn edge-tts và fpt-ai
- ⚠️ Tùy chỉnh hạn chế (chỉ có tốc độ nhanh/chậm)
- ⚠️ Cần kết nối Internet

### Cài đặt
```bash
pip install gtts
```

### Sử dụng
```bash
# Sử dụng gTTS backend
python3 run.py --config config.json --tts-backend gtts

# Hoặc với text_to_mp3.py
python3 text_to_mp3.py --text "Xin chào" --output test.mp3 --backend gtts
```

### Cấu hình trong config.json
```json
{
  "tts_backend": "gtts"
}
```

## 2. FPT.AI TTS - Khuyến nghị cho chất lượng cao

### Ưu điểm
- ✅ **Chất lượng rất cao**, giọng đọc tự nhiên
- ✅ **Ổn định**, ít lỗi
- ✅ **Tùy chỉnh cao**: tốc độ, cao độ, ngắt nghỉ
- ✅ Hỗ trợ nhiều giọng đọc tiếng Việt:
  - `banmai` - Nữ, miền Bắc (mặc định)
  - `lannhi` - Nữ, miền Nam
  - `leminh` - Nam, miền Bắc
  - `giahuy` - Nam, miền Nam
- ✅ Có free tier (giới hạn ký tự/tháng)

### Nhược điểm
- ⚠️ Cần API key (đăng ký miễn phí tại https://fpt.ai)
- ⚠️ Có giới hạn free tier

### Đăng ký API key
1. Truy cập https://fpt.ai/tts
2. Đăng ký tài khoản miễn phí
3. Lấy API key từ dashboard

### Cài đặt
```bash
pip install requests  # Đã có sẵn trong requirements.txt
```

### Sử dụng
```bash
# Sử dụng FPT.AI backend với API key
python3 run.py --config config.json --tts-backend fpt-ai --fpt-api-key YOUR_API_KEY

# Hoặc thêm vào config.json
```

### Cấu hình trong config.json
```json
{
  "tts_backend": "fpt-ai",
  "fpt_api_key": "YOUR_API_KEY_HERE",
  "fpt_voice": "banmai"
}
```

## 3. edge-tts (Microsoft Edge TTS)

### Ưu điểm
- ✅ Miễn phí, không cần API key
- ✅ Chất lượng cao
- ✅ Hỗ trợ nhiều giọng đọc

### Nhược điểm
- ⚠️ Có thể gặp lỗi "No audio was received" (vấn đề tạm thời)
- ⚠️ Rate limiting không rõ ràng

### Sử dụng
```bash
python3 run.py --config config.json --tts-backend edge-tts --tts-voice vi-VN-NamMinhNeural
```

## 4. ttx (Command-line tool)

### Ưu điểm
- ✅ Miễn phí
- ✅ Ổn định
- ✅ Offline (không cần Internet)

### Nhược điểm
- ⚠️ Cần cài đặt tool riêng
- ⚠️ Chất lượng trung bình

## Khuyến nghị

### Cho giải pháp tạm thời (khi edge-tts lỗi):
**Sử dụng gTTS** - Đơn giản, miễn phí, không cần API key, ổn định

```bash
pip install gtts
python3 run.py --config config.json --tts-backend gtts
```

### Cho chất lượng cao lâu dài:
**Sử dụng FPT.AI TTS** - Chất lượng tốt nhất, ổn định, có free tier

```bash
# Thêm vào config.json
{
  "tts_backend": "fpt-ai",
  "fpt_api_key": "YOUR_API_KEY",
  "fpt_voice": "banmai"
}
python3 run.py --config config.json
```

## Troubleshooting

### gTTS lỗi kết nối
- Kiểm tra kết nối Internet
- Thử lại sau vài phút (có thể bị rate limit tạm thời)

### FPT.AI lỗi API
- Kiểm tra API key có đúng không
- Kiểm tra free tier còn quota không
- Xem log lỗi chi tiết trong terminal

## Ví dụ sử dụng

### Chuyển đổi một file text
```bash
# Với gTTS
python3 text_to_mp3.py --file intro.txt --output intro.mp3 --backend gtts

# Với FPT.AI (cần API key trong config hoặc env)
python3 text_to_mp3.py --file intro.txt --output intro.mp3 --backend fpt-ai
```

### Chuyển đổi batch với run.py
```bash
# Sử dụng gTTS
python3 run.py --config config.json --tts-backend gtts --tts-concurrency 4

# Sử dụng FPT.AI
python3 run.py --config config.json --tts-backend fpt-ai --fpt-api-key YOUR_KEY
```

