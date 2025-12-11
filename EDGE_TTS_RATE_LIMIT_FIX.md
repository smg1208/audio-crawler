# Giải pháp khi Edge TTS bị Block/Rate Limit

## Tình trạng hiện tại

Edge TTS có thể bị **rate limiting** hoặc **blocking** từ Microsoft server khi:
- Gọi API quá nhiều trong thời gian ngắn
- Gọi từ cùng một IP address
- Vượt quá giới hạn requests không rõ ràng của Microsoft

**Dấu hiệu:**
- Lỗi `NoAudioReceived: No audio was received`
- Tất cả requests đều thất bại
- Không có audio file được tạo

## Các giải pháp đã được cập nhật trong code

### 1. ✅ Retry với Exponential Backoff
- Code tự động retry 3 lần với delay tăng dần: 2s → 4s → 8s
- Tự động phát hiện lỗi rate limiting và thêm delay

### 2. ✅ Delay giữa các Chunks
- Tự động thêm 1 giây delay giữa các text chunks
- Giúp tránh gọi API quá nhanh

### 3. ✅ Giảm Concurrency mặc định
- Edge TTS tự động giảm concurrency xuống tối đa 2
- Tránh gửi quá nhiều requests cùng lúc

### 4. ✅ Random Delay trong Workers
- Thêm delay ngẫu nhiên (0-1s) giữa các workers
- Giúp phân tán requests theo thời gian

## Các giải pháp khác

### Giải pháp 1: Giảm Concurrency thủ công
```bash
python3 run.py --config config.json --tts-backend edge-tts --tts-concurrency 1
```

### Giải pháp 2: Chuyển sang Azure TTS (Khuyến nghị)
**Azure TTS** là dịch vụ chính thức của Microsoft:
- ✅ Cùng giọng nói với Edge TTS
- ✅ Có SLA 99.9%
- ✅ Ít bị rate limit hơn
- ✅ Có free tier (0-500K ký tự/tháng)
- 💰 Trả phí sau free tier (~$15/1M ký tự)

```bash
python3 run.py --config config.json --tts-backend azure
```

**Cấu hình:**
- Cần Azure subscription key và region
- Thêm vào `stories/38060.json`:
  ```json
  "tts_backend": "azure",
  "azure_subscription_key": "your-key-here",
  "azure_region": "eastus",
  "azure_voice_name": "vi-VN-NamMinhNeural"
  ```

### Giải pháp 3: Chuyển sang Google Cloud TTS
**Google Cloud TTS:**
- ✅ Rất ổn định
- ✅ Có free tier (0-4M ký tự/tháng)
- ✅ Hỗ trợ concurrency cao (10-20)
- 💰 Trả phí sau free tier (~$4/1M ký tự)

```bash
python3 run.py --config config.json --tts-backend google-cloud --tts-concurrency 10
```

### Giải pháp 4: Sử dụng macOS TTS (Offline)
**macOS TTS:**
- ✅ Hoàn toàn offline, không bị block
- ✅ Miễn phí
- ⚠️  Chất lượng thấp hơn
- ⚠️  Chỉ hoạt động trên macOS

```bash
python3 run.py --config config.json --tts-backend macos
```

### Giải pháp 5: Chờ và thử lại
- Đợi **10-30 phút** để Microsoft reset rate limit
- Sau đó thử lại với concurrency thấp (1-2)

### Giải pháp 6: Sử dụng VPN/Proxy
- Thay đổi IP address bằng VPN
- Có thể giúp bypass rate limit tạm thời

## So sánh các backends

| Backend | Miễn phí | Ổn định | Rate Limit | Chất lượng |
|---------|----------|---------|------------|------------|
| Edge TTS | ✅ | ⭐⭐⭐ | ⚠️  Dễ bị | ⭐⭐⭐⭐⭐ |
| Azure TTS | 💰 Free tier | ⭐⭐⭐⭐⭐ | ✅ Ít | ⭐⭐⭐⭐⭐ |
| Google Cloud | 💰 Free tier | ⭐⭐⭐⭐⭐ | ✅ Rất ít | ⭐⭐⭐⭐⭐ |
| macOS TTS | ✅ | ⭐⭐⭐⭐ | ✅ Không | ⭐⭐⭐ |

## Khuyến nghị

1. **Ngắn hạn:** Sử dụng Azure TTS hoặc Google Cloud TTS
2. **Dài hạn:** Đăng ký Azure TTS subscription (free tier đủ dùng cho nhiều dự án)
3. **Offline:** Sử dụng macOS TTS nếu cần miễn phí hoàn toàn

## Cách test xem Edge TTS có còn bị block không

```bash
python3 test_edge_tts_blocked.py
```

Script này sẽ test và đưa ra kết quả chi tiết.

