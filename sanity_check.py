"""Quick sanity check for the project.

Run this to verify basic functions work (dry-run friendly).

Usage: python3 sanity_check.py
"""
from crawler.config_manager import ConfigManager
from crawler.parser import HTMLParser

def main():
    print('Running a small sanity check...')

    # parser check
    sample = '<div id="chapter-content"><p>Line 1</p><p>Line 2</p></div>'
    p = HTMLParser()
    print('Parsed text:', p.parse_main_text(sample))

    # config manager check — ensure we surface helpful error if config missing
    try:
        cfg = ConfigManager('config.json')
        print('Loaded config.story_id =', cfg.get('story_id'))
    except FileNotFoundError:
        print('No config.json found in current folder (this is ok for sanity check).')

if __name__ == '__main__':
    main()
