#!/usr/bin/env python3
from __future__ import annotations

import json
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))


class BolaoHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def do_POST(self):
        if self.path == "/api/import-bets":
            self.import_bets()
            return
        self.send_error(404, "Endpoint não encontrado")

    def import_bets(self):
        try:
            from import_bets import build_data, load_base_data

            output = ROOT / "data" / "bolao-data.js"
            data = build_data(ROOT / "apostas", load_base_data(output))
            output.parent.mkdir(parents=True, exist_ok=True)
            output.write_text(
                "window.BOLAO_DATA = " + json.dumps(data, ensure_ascii=False, indent=2) + ";\n",
                encoding="utf-8",
            )
            self.respond_json({"ok": True, "data": data})
        except Exception as exc:
            self.respond_json({"ok": False, "error": str(exc)}, status=500)

    def respond_json(self, payload, status=200):
        body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)


def main():
    port = int(os.environ.get("PORT", "8000"))
    last_error = None
    for candidate_port in range(port, port + 20):
        try:
            server = ThreadingHTTPServer(("127.0.0.1", candidate_port), BolaoHandler)
            port = candidate_port
            break
        except OSError as exc:
            last_error = exc
    else:
        raise SystemExit(f"Não foi possível iniciar o servidor local: {last_error}")

    print(f"Dashboard do Bolão Mundo Real em http://127.0.0.1:{port}/index.html")
    print("Use Ctrl+C para parar.")
    server.serve_forever()


if __name__ == "__main__":
    main()
