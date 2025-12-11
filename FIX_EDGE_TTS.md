# Hướng dẫn sửa lỗi edge-tts "No audio was received"

## Vấn đề
edge-tts không thể nhận audio từ dịch vụ Microsoft, báo lỗi "No audio was received" ngay cả khi:
- Kết nối đến service thành công (có thể list voices)
- Python 3.11 với OpenSSL 3.6.0 đã được cài
- urllib3 đã được downgrade về v1.x

## Nguyên nhân có thể
1. **Dịch vụ Microsoft tạm thời có vấn đề** - Service có thể đang maintenance hoặc overload
2. **Rate limiting** - IP có thể bị rate limit do quá nhiều requests
3. **Network/Firewall blocking** - Firewall hoặc VPN có thể chặn WebSocket connections đến edge-tts service
4. **IP bị block tạm thời** - Microsoft có thể tạm thời block IP do suspicious activity

## Giải pháp đã thử

### ✅ Option 1: Cài Python 3.11 từ Homebrew (Đã làm)
```bash
brew install python@3.11
python3.11 -m venv venv_py311
source venv_py311/bin/activate
pip install edge-tts requests beautifulsoup4
```
**Kết quả**: Vẫn lỗi "No audio was received"

### ✅ Option 2: Downgrade urllib3 (Đã làm)
```bash
pip install "urllib3<2.0"
```
**Kết quả**: Không giải quyết được vấn đề

### ✅ Option 3: Thử với voice khác (Đã làm)
```bash
python3 text_to_mp3.py --text "Xin chào" --output test.mp3 --voice vi-VN-HoaiMyNeural
```
**Kết quả**: Vẫn lỗi

## Giải pháp đề xuất

### Option A: Đợi và thử lại sau (Khuyến nghị)
- Đợi 15-30 phút và thử lại
- Có thể là rate limiting tạm thời
- Audio files đã được tạo thành công trước đó (Chapter_0201.mp3 = 2.6MB)

### Option B: Đổi mạng/VPN
```bash
# Tắt VPN/Proxy nếu có
# Hoặc đổi sang mạng khác (4G/hotspot)
# Sau đó thử lại
python3 text_to_mp3.py --text "Xin chào" --output test.mp3
```

### Option C: Sử dụng converter trong run.py
Script `run.py` có retry logic tốt hơn và có thể hoạt động khi service recover:

```bash
# Sử dụng venv_py311 với Python 3.11
source venv_py311/bin/activate

# Chạy với dry-run để test
python3 run.py --config config.json --tts-backend edge-tts --dry-run

# Chạy thực tế khi service hoạt động
python3 run.py --config config.json --tts-backend edge-tts --tts-concurrency 4
```

### Option D: Kiểm tra kết nối đến edge-tts service
```bash
python3 -c "
import asyncio
import edge_tts

async def test():
    voices = await edge_tts.list_voices()
    print(f'✓ Connected! Found {len(voices)} voices')
    vi_voices = [v for v in voices if v['Locale'].startswith('vi')]
    print(f'Vietnamese voices: {len(vi_voices)}')

asyncio.run(test())
"
```

## Lưu ý
- Audio files đã được tạo thành công trước đó, nghĩa là edge-tts đã hoạt động
- Vấn đề có thể là tạm thời do Microsoft service
- Nếu vẫn lỗi sau khi đợi và đổi mạng, có thể cần liên hệ Microsoft support hoặc tìm alternative TTS service

