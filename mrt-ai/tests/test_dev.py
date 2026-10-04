import json
from pathlib import Path
import socket
import tempfile
import unittest
from urllib.request import ProxyHandler, build_opener

from scripts.dev import local_api


class DeveloperLauncherTests(unittest.TestCase):
    def test_browser_chat_and_shutdown(self):
        root = Path(__file__).resolve().parents[1] / ".test-tmp"
        root.mkdir(exist_ok=True)
        with tempfile.TemporaryDirectory(dir=root) as temp:
            with local_api(database=Path(temp) / "sessions.sqlite3") as port:
                opener = build_opener(ProxyHandler({}))
                with opener.open(f"http://127.0.0.1:{port}/", timeout=5) as response:
                    page = response.read().decode("utf-8")
                self.assertIn("<title>mrt-ai · тест intent-модели</title>", page)
                self.assertIn("RuBERT intent classifier сравнивается с rules-v1", page)
                self.assertIn("api('/v1/dev/intent',probe)", page)
                self.assertIn("Параметры поездки, выделенные rules-v1", page)
                self.assertIn("Локальный API недоступен.", page)
                self.assertIn("start.cmd", page)
                self.assertIn('type="date" required', page)
                self.assertIn("updates,", page)
                self.assertIn("Собрать поездку по форме", page)
                self.assertIn('rows="2" disabled', page)
                self.assertIn("!formSubmitted||!message", page)
                self.assertIn('id="budget"', page)
                self.assertIn("Свободный текст используется только для правок после отправки формы", page)
                with opener.open(f"http://127.0.0.1:{port}/health", timeout=5) as response:
                    self.assertEqual(json.load(response)["status"], "ok")
            with socket.socket() as probe:
                self.assertNotEqual(probe.connect_ex(("127.0.0.1", port)), 0)

    def test_occupied_port_is_not_reused(self):
        with socket.socket() as occupied:
            occupied.bind(("127.0.0.1", 0))
            occupied.listen()
            with self.assertRaises(OSError):
                with local_api(occupied.getsockname()[1]):
                    self.fail("Occupied port should not be used")


if __name__ == "__main__":
    unittest.main()
