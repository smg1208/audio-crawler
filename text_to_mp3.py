#!/usr/bin/env python3
"""Simple CLI tool to convert text to MP3 using edge-tts.

Usage:
    python3 text_to_mp3.py --text "Xin chào" --output hello.mp3 --voice "vi-VN-NamMinhNeural"
    python3 text_to_mp3.py --file chapter.txt --output chapter.mp3 --voice "vi-VN-HoaiMyNeural"
"""
import argparse
import asyncio
import os
import sys
from pathlib import Path

try:
    import edge_tts
except ImportError:
    print("Error: edge-tts not installed. Install it with:")
    print("  pip install edge-tts")
    sys.exit(1)


async def text_to_speech(text: str, output_path: str, voice: str = "vi-VN-NamMinhNeural", rate: float = 1.0) -> None:
    """Convert text to MP3 using edge-tts.

    Args:
        text: Text to convert
        output_path: Output MP3 file path
        voice: Edge-tts voice name (default: vi-VN-NamMinhNeural for Vietnamese male)
        rate: Speech rate (0.5 to 2.0, default 1.0)
    """
    if not text.strip():
        print("Error: Text is empty")
        sys.exit(1)

    try:
        # Convert rate to edge-tts format (+X% or -X%)
        if rate == 1.0:
            rate_str = "+0%"
        elif rate > 1.0:
            rate_str = f"+{int((rate - 1.0) * 100)}%"
        else:
            rate_str = f"{int((rate - 1.0) * 100)}%"

        # Create communicate object
        communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate_str)
        
        # Save to file
        print(f"Converting text to speech...")
        print(f"  Voice: {voice}")
        print(f"  Rate: {rate}x")
        print(f"  Output: {output_path}")
        
        await communicate.save(output_path)
        
        # Verify file was created
        if os.path.exists(output_path):
            size_mb = os.path.getsize(output_path) / (1024 * 1024)
            print(f"✓ Success! Created {output_path} ({size_mb:.2f} MB)")
        else:
            print("Error: Output file was not created")
            sys.exit(1)

    except Exception as e:
        print(f"Error during conversion: {e}")
        sys.exit(1)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description="Convert text to MP3 using edge-tts",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  # Convert text directly
  python3 text_to_mp3.py --text "Xin chào" --output hello.mp3

  # Convert from file
  python3 text_to_mp3.py --file chapter.txt --output chapter.mp3

  # Use different voice
  python3 text_to_mp3.py --text "Hello" --output hello.mp3 --voice "vi-VN-HoaiMyNeural"

  # Adjust speech rate (0.5 = slower, 1.5 = faster)
  python3 text_to_mp3.py --text "Hello" --output hello.mp3 --rate 0.8

Available Vietnamese voices:
  - vi-VN-NamMinhNeural (male, default)
  - vi-VN-HoaiMyNeural (female)
"""
    )

    parser.add_argument('--text', help='Text to convert (or use --file)')
    parser.add_argument('--file', help='Text file to convert (alternative to --text)')
    parser.add_argument('--output', '-o', required=True, help='Output MP3 file path')
    parser.add_argument('--voice', default='vi-VN-NamMinhNeural', help='Edge-tts voice name (default: vi-VN-NamMinhNeural)')
    parser.add_argument('--rate', type=float, default=1.0, help='Speech rate 0.5-2.0 (default: 1.0)')

    args = parser.parse_args(argv)

    # Get text from either --text or --file
    if args.text:
        text = args.text
    elif args.file:
        if not os.path.exists(args.file):
            print(f"Error: File not found: {args.file}")
            sys.exit(1)
        with open(args.file, 'r', encoding='utf-8') as fh:
            text = fh.read()
    else:
        parser.print_help()
        print("\nError: Provide either --text or --file")
        sys.exit(1)

    # Run async conversion
    asyncio.run(text_to_speech(text, args.output, voice=args.voice, rate=args.rate))


if __name__ == '__main__':
    main()
