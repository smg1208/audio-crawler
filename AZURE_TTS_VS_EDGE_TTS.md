# So sánh Azure TTS và Edge TTS

## Tổng quan

Cả **Azure TTS** và **Edge TTS** đều là dịch vụ TTS từ Microsoft, nhưng có những khác biệt quan trọng:

| Tính năng | Edge TTS | Azure TTS |
|-----------|----------|-----------|
| **Miễn phí** | ✅ Hoàn toàn miễn phí | 💰 Trả phí (có free tier) |
| **API Key** | ❌ Không cần | ✅ Cần Azure subscription |
| **Chất lượng** | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **Ổn định** | ⭐⭐⭐ (có thể lỗi) | ⭐⭐⭐⭐⭐ (rất ổn định) |
| **Giọng nói** | Giống nhau | Giống nhau |
| **Rate limiting** | ⚠️ Không rõ ràng | ✅ Rõ ràng, có SLA |
| **Support** | ❌ Không có | ✅ Có support |
| **SLA** | ❌ Không có | ✅ 99.9% uptime |

## Giống nhau

1. **Cùng giọng nói**: Cả hai đều sử dụng cùng các giọng nói Microsoft (ví dụ: `vi-VN-HoaiMyNeural`, `vi-VN-NamMinhNeural`)
2. **Cùng chất lượng**: Chất lượng audio giống nhau
3. **Cùng format**: Hỗ trợ MP3, WAV, OGG
4. **Cùng ngôn ngữ**: Hỗ trợ tiếng Việt tốt

## Khác nhau

### 1. Edge TTS (Miễn phí)
- ✅ **Hoàn toàn miễn phí**, không cần API key
- ✅ **Dễ sử dụng**, không cần setup phức tạp
- ⚠️ **Không ổn định**, có thể gặp lỗi "No audio was received"
- ⚠️ **Không có SLA**, không đảm bảo uptime
- ⚠️ **Rate limiting không rõ ràng**, có thể bị block tạm thời

### 2. Azure TTS (Trả phí)
- 💰 **Trả phí** (có free tier: 0-500K ký tự/tháng)
- ✅ **Rất ổn định**, ít lỗi
- ✅ **Có SLA**, đảm bảo 99.9% uptime
- ✅ **Rate limiting rõ ràng**, không bị block bất ngờ
- ✅ **Có support** từ Microsoft
- ⚠️ **Cần setup** Azure account và API key

## Khi nào nên dùng?

### Dùng Edge TTS khi:
- ✅ Cần miễn phí hoàn toàn
- ✅ Dự án nhỏ, không quan trọng về uptime
- ✅ Chấp nhận rủi ro lỗi tạm thời
- ✅ Không muốn setup Azure account

### Dùng Azure TTS khi:
- ✅ Cần ổn định cao, không thể chấp nhận lỗi
- ✅ Dự án production, cần SLA
- ✅ Có ngân sách (free tier đủ cho nhiều trường hợp)
- ✅ Cần support từ Microsoft
- ✅ Cần rate limiting rõ ràng

## Free Tier của Azure TTS

Azure TTS có **free tier**:
- **0-500,000 ký tự/tháng**: Miễn phí
- **Sau 500K**: $15.00 / 1 triệu ký tự (Standard voices)
- **Neural voices**: $16.00 / 1 triệu ký tự

**Ví dụ:**
- 100,000 ký tự/tháng: **Miễn phí** (trong free tier)
- 1 triệu ký tự/tháng: ~$15 (sau free tier)

## Kết luận

**Azure TTS và Edge TTS giống nhau về giọng nói và chất lượng**, nhưng:
- **Edge TTS**: Miễn phí nhưng không ổn định
- **Azure TTS**: Trả phí nhưng rất ổn định, có free tier

**Khuyến nghị:**
- Nếu **edge-tts đang lỗi** và bạn cần giải pháp ổn định → **Dùng Azure TTS**
- Nếu muốn **miễn phí hoàn toàn** và chấp nhận rủi ro → **Đợi edge-tts hoạt động lại**
- Nếu có **ngân sách nhỏ** và cần ổn định → **Azure TTS với free tier**

