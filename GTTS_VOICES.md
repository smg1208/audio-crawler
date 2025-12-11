# gTTS (Google Text-to-Speech) - Danh sách Giọng Đọc

## Tổng quan

**gTTS** (Google Text-to-Speech) là thư viện Python miễn phí sử dụng Google Translate TTS API. 

**Đặc điểm quan trọng:**
- ✅ Miễn phí, không cần API key
- ✅ Hỗ trợ 69 ngôn ngữ
- ⚠️ **Mỗi ngôn ngữ chỉ có 1 giọng đọc mặc định** (không thể chọn giọng nam/nữ, chất lượng cao/thấp)
- ⚠️ Không thể tùy chỉnh giọng đọc như Google Cloud TTS hay Edge TTS

## Tiếng Việt

**Mã ngôn ngữ:** `vi`  
**Tên:** Vietnamese  
**Giọng đọc:** Chỉ có 1 giọng đọc mặc định (không thể chọn)

### Ví dụ sử dụng:

```python
from gtts import gTTS

# Tạo TTS với tiếng Việt
tts = gTTS(text="Xin chào, tôi đang thử giọng", lang='vi')
tts.save("output.mp3")
```

## Danh sách đầy đủ 69 ngôn ngữ

| Mã | Ngôn ngữ |
|---|---|
| `af` | Afrikaans |
| `sq` | Albanian |
| `am` | Amharic |
| `ar` | Arabic |
| `eu` | Basque |
| `bn` | Bengali |
| `bs` | Bosnian |
| `bg` | Bulgarian |
| `yue` | Cantonese |
| `ca` | Catalan |
| `zh` | Chinese (Mandarin) |
| `zh-TW` | Chinese (Mandarin/Taiwan) |
| `zh-CN` | Chinese (Simplified) |
| `hr` | Croatian |
| `cs` | Czech |
| `da` | Danish |
| `nl` | Dutch |
| `en` | English |
| `et` | Estonian |
| `tl` | Filipino |
| `fi` | Finnish |
| `fr` | French |
| `fr-CA` | French (Canada) |
| `gl` | Galician |
| `de` | German |
| `el` | Greek |
| `gu` | Gujarati |
| `ha` | Hausa |
| `iw` | Hebrew |
| `hi` | Hindi |
| `hu` | Hungarian |
| `is` | Icelandic |
| `id` | Indonesian |
| `it` | Italian |
| `ja` | Japanese |
| `jw` | Javanese |
| `kn` | Kannada |
| `km` | Khmer |
| `ko` | Korean |
| `la` | Latin |
| `lv` | Latvian |
| `lt` | Lithuanian |
| `ms` | Malay |
| `ml` | Malayalam |
| `mr` | Marathi |
| `my` | Myanmar (Burmese) |
| `ne` | Nepali |
| `no` | Norwegian |
| `pl` | Polish |
| `pt` | Portuguese (Brazil) |
| `pt-PT` | Portuguese (Portugal) |
| `pa` | Punjabi (Gurmukhi) |
| `ro` | Romanian |
| `ru` | Russian |
| `sr` | Serbian |
| `si` | Sinhala |
| `sk` | Slovak |
| `es` | Spanish |
| `su` | Sundanese |
| `sw` | Swahili |
| `sv` | Swedish |
| `ta` | Tamil |
| `te` | Telugu |
| `th` | Thai |
| `tr` | Turkish |
| `uk` | Ukrainian |
| `ur` | Urdu |
| **`vi`** | **Vietnamese** |
| `cy` | Welsh |

## So sánh với các TTS engine khác

| Tính năng | gTTS | Google Cloud TTS | Edge TTS |
|---|---|---|---|
| **Số giọng đọc tiếng Việt** | 1 | 40+ | 10+ |
| **Chọn giọng nam/nữ** | ❌ | ✅ | ✅ |
| **Chất lượng** | Trung bình | Cao | Cao |
| **Miễn phí** | ✅ | ❌ (có billing) | ✅ |
| **Cần API key** | ❌ | ✅ | ❌ |
| **Offline** | ❌ | ❌ | ❌ |

## Lưu ý

1. **gTTS chỉ có 1 giọng đọc cho mỗi ngôn ngữ** - không thể chọn giọng nam/nữ hay chất lượng
2. **Chất lượng giọng đọc** của gTTS thấp hơn Google Cloud TTS và Edge TTS
3. **Phù hợp cho:** Test nhanh, demo, hoặc khi không cần chất lượng cao
4. **Không phù hợp cho:** Production với yêu cầu chất lượng cao, cần nhiều giọng đọc

## Cách sử dụng trong project

Trong file `config.json`:

```json
{
  "tts_backend": "gtts",
  "tts_voice": "vi"
}
```

Trong code:

```python
from crawler.converter import TextToAudioConverter

converter = TextToAudioConverter(backend='gtts')
converter.convert('input.txt', 'output.mp3')
```

## Tài liệu tham khảo

- [gTTS GitHub](https://github.com/pndurette/gTTS)
- [gTTS Documentation](https://gtts.readthedocs.io/)

