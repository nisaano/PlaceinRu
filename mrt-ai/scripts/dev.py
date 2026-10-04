"""Run the MRT-AI local API and Misha developer chat in one terminal."""
import argparse
from contextlib import contextmanager
from pathlib import Path
import socket
import threading
import time
import webbrowser

import uvicorn

from app.main import create_app
from fastapi.responses import FileResponse


@contextmanager
def local_api(port=0, database: Path | None = None):
    # Reserve our own socket: never attach to or stop someone else's server.
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as listener:
        listener.bind(("127.0.0.1", port))
        app = create_app(database=database, enable_intent_test=True)

        @app.get("/", include_in_schema=False)
        def developer_chat():
            return FileResponse(Path(__file__).parent / "developer-chat.html", headers={"Cache-Control": "no-store"})

        config = uvicorn.Config(app, log_level="error", access_log=False)
        server = uvicorn.Server(config)
        failures = []

        def serve():
            try:
                server.run(sockets=[listener])
            except BaseException as error:
                failures.append(error)

        thread = threading.Thread(target=serve, name="mrt-ai-local-api", daemon=True)
        thread.start()
        try:
            deadline = time.monotonic() + 15
            while not server.started:
                if not thread.is_alive() or time.monotonic() >= deadline:
                    raise RuntimeError(f"API не запустился: {failures or 'истёк срок ожидания'}")
                time.sleep(0.05)
            yield listener.getsockname()[1]
        finally:
            server.should_exit = True
            thread.join(timeout=10)
            if thread.is_alive():
                server.force_exit = True
                thread.join(timeout=2)


def main():
    parser = argparse.ArgumentParser(description="mrt-ai · Миша: локальный тестовый чат в браузере")
    parser.add_argument("--port", type=int, default=0, help="Порт API; 0 — свободный порт автоматически")
    parser.add_argument("--no-browser", action="store_true", help="Не открывать браузер автоматически")
    args = parser.parse_args()
    if not 0 <= args.port <= 65535:
        parser.error("Порт должен быть от 0 до 65535")
    try:
        print("Запуск локального бота…")
        with local_api(args.port) as port:
            url = f"http://127.0.0.1:{port}/"
            print(f"Чат готов: {url}", flush=True)
            print("Оставьте терминал открытым. Остановка — Ctrl+C.", flush=True)
            if not args.no_browser:
                try:
                    if not webbrowser.open(url):
                        print("Откройте ссылку выше вручную.")
                except webbrowser.Error:
                    print("Откройте ссылку выше вручную.")
            while True:
                time.sleep(0.5)
    except KeyboardInterrupt:
        return 0
    except (OSError, RuntimeError) as error:
        print(f"Не удалось запустить бота: {error}")
        print("Если порт занят, запустите start.cmd без номера порта.")
        return 1
    finally:
        print("Тестовый стенд остановлен.")


if __name__ == "__main__":
    raise SystemExit(main())
