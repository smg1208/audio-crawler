import unittest
from crawler.llm_wrapper import LLMClient


class TestLLMWrapper(unittest.TestCase):
    def test_api_key_is_stored(self):
        client = LLMClient(api_key='sk-test-123')
        self.assertEqual(client.api_key, 'sk-test-123')

    def test_available_without_openai(self):
        # if openai is not installed or no key, available should be False
        client = LLMClient(api_key=None)
        self.assertFalse(client.available())


if __name__ == '__main__':
    unittest.main()
