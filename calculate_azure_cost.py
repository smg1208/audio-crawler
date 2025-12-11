#!/usr/bin/env python3
"""
Script tính toán chi phí Azure TTS cho một truyện.

Usage:
    python3 calculate_azure_cost.py --story-id 38060
"""

import argparse
import os
from pathlib import Path


def calculate_azure_cost(story_id: str, verbose: bool = False):
    """Tính toán chi phí Azure TTS cho một truyện.
    
    Args:
        story_id: ID của truyện
        verbose: Nếu True, hiển thị chi tiết từng file
    """
    text_dir = f'./{story_id} - Text'
    
    if not os.path.exists(text_dir):
        print(f'❌ Thư mục không tồn tại: {text_dir}')
        return None
    
    # Tìm tất cả text files
    text_files = sorted(Path(text_dir).glob('Chapter_*.txt'))
    total_files = len(text_files)
    
    if total_files == 0:
        print(f'❌ Không tìm thấy text files trong {text_dir}')
        return None
    
    print(f'📁 Tìm thấy {total_files:,} text files')
    print(f'📊 Đang đếm ký tự...\n')
    
    total_chars = 0
    total_bytes = 0
    file_stats = []
    
    for text_file in text_files:
        try:
            with open(text_file, 'r', encoding='utf-8') as f:
                content = f.read()
                chars = len(content)
                bytes_count = len(content.encode('utf-8'))
                total_chars += chars
                total_bytes += bytes_count
                file_stats.append((text_file.name, chars, bytes_count))
        except Exception as e:
            print(f'⚠️  Lỗi đọc {text_file.name}: {e}')
    
    # Sắp xếp theo số ký tự
    file_stats.sort(key=lambda x: x[1], reverse=True)
    
    # Hiển thị kết quả
    print('=' * 70)
    print(f'📊 TỔNG KẾT')
    print('=' * 70)
    print(f'Số file: {total_files:,}')
    print(f'Tổng ký tự (UTF-8): {total_chars:,}')
    print(f'Tổng bytes: {total_bytes:,}')
    print(f'Trung bình mỗi file: {total_chars // total_files:,} ký tự')
    print()
    
    # Top 10 files lớn nhất
    print('📈 Top 10 files lớn nhất:')
    for i, (name, chars, bytes_count) in enumerate(file_stats[:10], 1):
        print(f'  {i:2d}. {name}: {chars:,} ký tự')
    
    if verbose:
        print()
        print('📋 Chi tiết tất cả files:')
        for name, chars, bytes_count in file_stats:
            print(f'  {name}: {chars:,} ký tự')
    
    print()
    print('=' * 70)
    print(f'💰 CHI PHÍ AZURE TTS')
    print('=' * 70)
    
    # Azure TTS pricing
    free_tier = 500_000  # 500K characters/month free
    standard_price_per_million = 15.0  # $15 per 1M characters (Standard)
    neural_price_per_million = 16.0  # $16 per 1M characters (Neural)
    
    if total_chars <= free_tier:
        print(f'✅ Trong FREE TIER! ({total_chars:,} / {free_tier:,} ký tự)')
        print(f'💰 Chi phí: $0.00 (miễn phí)')
        remaining = free_tier - total_chars
        print(f'📉 Còn lại trong free tier: {remaining:,} ký tự')
        cost_standard = 0.0
        cost_neural = 0.0
    else:
        paid_chars = total_chars - free_tier
        cost_standard = (paid_chars / 1_000_000) * standard_price_per_million
        cost_neural = (paid_chars / 1_000_000) * neural_price_per_million
        
        print(f'📊 Tổng: {total_chars:,} ký tự')
        print(f'🆓 Free tier: {free_tier:,} ký tự (miễn phí)')
        print(f'💳 Phải trả: {paid_chars:,} ký tự')
        print()
        print(f'💰 Chi phí Standard voices: ${cost_standard:.2f}')
        print(f'💰 Chi phí Neural voices: ${cost_neural:.2f}')
        print()
        print(f'💡 Khuyến nghị: Dùng Neural voices (${cost_neural:.2f}) cho chất lượng tốt hơn')
    
    print()
    print('=' * 70)
    print(f'📝 LƯU Ý')
    print('=' * 70)
    print('• Azure TTS tính phí theo số ký tự (characters), không phải tokens')
    print('• Free tier: 0-500,000 ký tự/tháng (miễn phí)')
    print('• Sau free tier: ~$15-16 / 1 triệu ký tự')
    print('• Pricing có thể thay đổi, xem: https://azure.microsoft.com/pricing/details/cognitive-services/speech-services/')
    print()
    
    # So sánh với Google Cloud TTS
    print('=' * 70)
    print(f'🔄 SO SÁNH VỚI GOOGLE CLOUD TTS')
    print('=' * 70)
    
    google_free_tier = 0  # Google Cloud không có free tier cho TTS
    google_price_per_million = 16.0  # $16 per 1M characters (Neural2)
    
    google_cost = (total_chars / 1_000_000) * google_price_per_million
    
    print(f'📊 Google Cloud TTS: ${google_cost:.2f}')
    print(f'📊 Azure TTS (Neural): ${cost_neural:.2f}')
    print()
    
    if cost_neural < google_cost:
        diff = google_cost - cost_neural
        print(f'✅ Azure TTS rẻ hơn ${diff:.2f} (có free tier)')
    elif cost_neural > google_cost:
        diff = cost_neural - google_cost
        print(f'✅ Google Cloud TTS rẻ hơn ${diff:.2f}')
    else:
        print('💰 Chi phí tương đương')
    
    return {
        'story_id': story_id,
        'total_files': total_files,
        'total_chars': total_chars,
        'total_bytes': total_bytes,
        'cost_standard': cost_standard,
        'cost_neural': cost_neural,
        'cost_google': google_cost
    }


def main():
    parser = argparse.ArgumentParser(description='Tính toán chi phí Azure TTS cho một truyện')
    parser.add_argument('--story-id', required=True, help='ID của truyện (ví dụ: 38060)')
    parser.add_argument('--verbose', '-v', action='store_true', help='Hiển thị chi tiết từng file')
    args = parser.parse_args()
    
    result = calculate_azure_cost(args.story_id, args.verbose)
    
    if result:
        print()
        print('=' * 70)
        print('✅ Hoàn thành!')
        print('=' * 70)


if __name__ == '__main__':
    main()

