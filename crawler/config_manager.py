import json
import os
from typing import Any


class ConfigManager:
    """Simple JSON config manager that reads/write a file path.

    Minimal validation is performed; the object behaves like a dict with load/save.
    """

    def __init__(self, path: str):
        self.path = path
        self._data = {}
        self._load()

    def _load(self):
        if not os.path.exists(self.path):
            raise FileNotFoundError(f'Config file not found: {self.path}')
        with open(self.path, 'r', encoding='utf-8') as fh:
            self._data = json.load(fh)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        with open(self.path, 'w', encoding='utf-8') as fh:
            json.dump(self._data, fh, ensure_ascii=False, indent=2)

    def raw(self):
        return self._data


class StoryConfigStore:
    """Manage per-story configuration files using a global template.

    Usage:
        store = StoryConfigStore(global_config_path)
        story_cfg = store.load_story(story_id)

    Per-story files are stored in ./stories/<story_id>.json
    """

    def __init__(self, global_config_path: str, stories_dir: str = 'stories'):
        self.global_path = global_config_path
        self.stories_dir = stories_dir
        self.global_cfg = ConfigManager(global_config_path)
        os.makedirs(self.stories_dir, exist_ok=True)

    def _story_path(self, story_id: str) -> str:
        safe = str(story_id).strip()
        return os.path.join(self.stories_dir, f"{safe}.json")

    def has_story(self, story_id: str) -> bool:
        return os.path.exists(self._story_path(story_id))

    def load_story(self, story_id: str) -> ConfigManager:
        path = self._story_path(story_id)
        if not os.path.exists(path):
            # create per-story config using global template
            template = dict(self.global_cfg.raw())
            # ensure important keys are present: story_id, base_url, chapters_api, last_downloaded_chapter, batch_size
            template['story_id'] = story_id
            template.setdefault('base_url', self.global_cfg.get('base_url'))
            template.setdefault('chapters_api', self.global_cfg.get('chapters_api'))
            template.setdefault('last_downloaded_chapter', 0)
            template.setdefault('batch_size', self.global_cfg.get('batch_size', 15))
            # write to file
            with open(path, 'w', encoding='utf-8') as fh:
                json.dump(template, fh, ensure_ascii=False, indent=2)
        return ConfigManager(path)

