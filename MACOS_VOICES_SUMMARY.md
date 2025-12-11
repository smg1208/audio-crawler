# Tóm tắt giọng đọc macOS cho TTS

## Giọng đọc tiếng Việt

**Chỉ có 1 giọng đọc tiếng Việt chính thức:**

1. **Linh** (`vi_VN`)
   - Giới tính: Nữ
   - Vùng miền: Miền Bắc
   - Mô tả: "Xin chào! Tên tôi là Linh."
   - **Đây là giọng mặc định được khuyến nghị cho macOS TTS**

## Cách sử dụng trong config

```json
{
  "tts_backend": "macos",
  "macos_voice": "Linh"
}
```

## Lưu ý

- macOS chỉ có **1 giọng đọc tiếng Việt** là "Linh"
- Không có giọng "Nam" chính thức cho tiếng Việt
- Nếu bạn muốn giọng nam, có thể thử các giọng đa ngôn ngữ khác, nhưng chất lượng sẽ không tốt bằng Linh

## Danh sách đầy đủ

Xem file `MACOS_VOICES.md` để xem danh sách đầy đủ 177 giọng đọc.

## Test giọng đọc

```bash
# Test giọng Linh
say -v "Linh" "Xin chào các bạn"

# Lưu thành file
say -v "Linh" -o test.m4a "Xin chào các bạn"
```

## Sử dụng trong code

```python
from crawler.tts_engines import MacOSTTS
import asyncio

macos = MacOSTTS(voice='Linh')
asyncio.run(macos.speak('Xin chào', 'output.m4a'))
```

