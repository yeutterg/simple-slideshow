#!/usr/bin/env python3
"""Serve a simple, dependency-free browser slideshow from a photo folder."""

from __future__ import annotations

import argparse
import json
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import quote

IMAGE_EXTENSIONS = {".jpg", ".jpeg", ".png", ".webp", ".JPG", ".JPEG", ".PNG", ".WEBP"}
DEFAULT_CONFIG = Path("config.json")


def page(photos: list[Path]) -> bytes:
    urls = [quote(path.name) for path in photos]
    photo_json = json.dumps(urls)
    return f"""<!doctype html>
<meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Simple Slideshow</title>
<style>
  :root {{ color-scheme: dark; }} * {{ box-sizing: border-box; }} body {{ margin:0; background:#111; color:#eee; font:16px system-ui,sans-serif; }}
  main {{ height:100vh; display:grid; place-items:center; position:relative; }} img {{ max-width:96vw; max-height:90vh; object-fit:contain; }}
  button {{ border:0; border-radius:999px; padding:.6rem 1rem; background:#333; color:#fff; cursor:pointer; }} nav {{ position:fixed; bottom:1rem; display:flex; gap:.75rem; align-items:center; }}
</style>
<main><img id="photo" alt="Slideshow photo"><nav><button id="previous">Previous</button><button id="toggle">Pause</button><button id="next">Next</button><span id="count"></span></nav></main>
<script>
const photos={photo_json}; let index=0, playing=true;
const image=document.querySelector('#photo'), count=document.querySelector('#count'), toggle=document.querySelector('#toggle');
function show() {{ image.src='/photos/'+photos[index]; count.textContent=`${{index+1}} / ${{photos.length}}`; }}
function step(delta) {{ index=(index+delta+photos.length)%photos.length; show(); }}
function setPlaying(value) {{ playing=value; toggle.textContent=playing?'Pause':'Play'; }}
document.querySelector('#previous').onclick=()=>step(-1); document.querySelector('#next').onclick=()=>step(1); toggle.onclick=()=>setPlaying(!playing);
document.addEventListener('keydown', event=>{{ if(event.key===' '){{event.preventDefault();setPlaying(!playing)}} if(event.key==='ArrowLeft')step(-1); if(event.key==='ArrowRight')step(1); if(event.key.toLowerCase()==='f')document.documentElement.requestFullscreen?.(); }});
setInterval(()=>{{if(playing&&photos.length>1)step(1)}},5000); show();
</script>""".encode()


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--config", type=Path, default=DEFAULT_CONFIG)
    parser.add_argument("--photos", type=Path, help="Override the photos folder from the config")
    parser.add_argument("--port", type=int, help="Override the port from the config")
    args = parser.parse_args()
    settings = {"photos": "photos", "port": 8765}
    if args.config.exists():
        with args.config.open(encoding="utf-8") as config_file:
            settings.update(json.load(config_file))
    photos_dir = Path(args.photos or settings["photos"])
    port = int(args.port or settings["port"])
    photos_dir.mkdir(parents=True, exist_ok=True)
    photos = sorted(path for path in photos_dir.iterdir() if path.is_file() and path.suffix in IMAGE_EXTENSIONS)

    class Handler(SimpleHTTPRequestHandler):
        def do_GET(self):  # noqa: N802
            if self.path == "/" or self.path.startswith("/?"):
                body = page(photos)
                self.send_response(200)
                self.send_header("Content-Type", "text/html; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)
                return
            if self.path.startswith("/photos/"):
                self.directory = str(photos_dir.parent)
            super().do_GET()

    print(f"Serving {len(photos)} photos at http://127.0.0.1:{port}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()


if __name__ == "__main__":
    main()
