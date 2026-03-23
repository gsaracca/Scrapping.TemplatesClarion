# -*- coding: utf-8 -*-
import os
import re
import sys
import time
import pathlib
import urllib.parse
from typing import List, Optional, Tuple

import requests
from bs4 import BeautifulSoup

BASE_PAGE = "https://templatesclarion.com/downloads/"
BASE_DOMAIN = "https://templatesclarion.com/"

UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) PythonDownloader/1.1"

def is_download_url(url: str) -> bool:
    """
    True si la URL es del dominio templatesclarion.com y contiene:
      - sdm_process_download=1
      - download_id=<número>
    en cualquier orden.
    """
    try:
        u = urllib.parse.urlparse(url)
        if u.netloc and u.netloc != "templatesclarion.com":
            return False
        qs = urllib.parse.parse_qs(u.query)
        if qs.get("sdm_process_download", ["0"])[0] != "1":
            return False
        did = qs.get("download_id", [None])[0]
        return did is not None and str(did).isdigit()
    except Exception:
        return False


def extract_download_links(html: str) -> List[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()

    # 1) Por anchors
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href:
            continue
        abs_url = urllib.parse.urljoin(BASE_DOMAIN, href)
        if is_download_url(abs_url):
            links.add(abs_url)

    # 2) Fallback por regex amplio (cualquier orden)
    # Nota: luego se valida con is_download_url()
    for m in re.finditer(r'https?://templatesclarion\.com/\?[^"\s<>]+', html):
        candidate = m.group(0)
        if is_download_url(candidate):
            links.add(candidate)

    return sorted(links)


def filename_from_cd(content_disposition: Optional[str]) -> Optional[str]:
    if not content_disposition:
        return None

    m = re.search(r"filename\*\s*=\s*([^']*)''([^;]+)", content_disposition, flags=re.IGNORECASE)
    if m:
        enc = m.group(1).strip() or "utf-8"
        raw = m.group(2).strip().strip('"')
        try:
            return urllib.parse.unquote(raw, encoding=enc, errors="replace")
        except Exception:
            return urllib.parse.unquote(raw)

    m = re.search(r'filename\s*=\s*"([^"]+)"', content_disposition, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip()

    m = re.search(r"filename\s*=\s*([^;]+)", content_disposition, flags=re.IGNORECASE)
    if m:
        return m.group(1).strip().strip('"')

    return None


def safe_name(name: str) -> str:
    name = name.replace("\\", "_").replace("/", "_").strip()
    name = re.sub(r"[<>:\"|?*\x00-\x1F]", "_", name)
    name = name.strip(". ")
    return name or "download.bin"


def head_for_name_and_size(session: requests.Session, url: str, timeout: int = 30) -> Tuple[Optional[str], Optional[int]]:
    try:
        r = session.head(url, allow_redirects=True, timeout=timeout)
        cd = r.headers.get("Content-Disposition")
        cl = r.headers.get("Content-Length")
        name = filename_from_cd(cd) or None
        size = int(cl) if cl and cl.isdigit() else None
        return name, size
    except Exception:
        pass

    try:
        r = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
        cd = r.headers.get("Content-Disposition")
        cl = r.headers.get("Content-Length")
        name = filename_from_cd(cd) or None
        size = int(cl) if cl and cl.isdigit() else None
        r.close()
        return name, size
    except Exception:
        return None, None


def download_with_resume(session: requests.Session, url: str, out_dir: pathlib.Path, timeout: int = 60) -> pathlib.Path:
    out_dir.mkdir(parents=True, exist_ok=True)

    name, size = head_for_name_and_size(session, url)

    # Fallback a nombre basado en download_id
    if not name:
        q = urllib.parse.parse_qs(urllib.parse.urlparse(url).query)
        did = q.get("download_id", ["file"])[0]
        name = f"download_{did}.bin"

    name = safe_name(name)
    target = out_dir / name

    if target.exists() and size is not None and target.stat().st_size == size:
        print(f"OK (ya estaba): {target.name}")
        return target

    headers = {}
    mode = "wb"
    existing = target.stat().st_size if target.exists() else 0
    if existing > 0:
        headers["Range"] = f"bytes={existing}-"
        mode = "ab"

    with session.get(url, allow_redirects=True, stream=True, timeout=timeout, headers=headers) as r:
        r.raise_for_status()

        if "Range" in headers and r.status_code == 200:
            existing = 0
            mode = "wb"

        cd2 = r.headers.get("Content-Disposition")
        name2 = filename_from_cd(cd2)
        if name2:
            name2 = safe_name(name2)
            if name2 != target.name:
                new_target = out_dir / name2
                if target.exists() and not new_target.exists():
                    target.rename(new_target)
                target = new_target

        total_written = existing
        chunk = 1024 * 256

        with open(target, mode) as f:
            for part in r.iter_content(chunk_size=chunk):
                if part:
                    f.write(part)
                    total_written += len(part)

    print(f"DESCARGADO: {target.name} ({total_written} bytes)")
    return target


def main():
    out_dir = pathlib.Path(sys.argv[1]) if len(sys.argv) > 1 else pathlib.Path("TC_Downloads")

    session = requests.Session()
    session.headers.update({"User-Agent": UA})

    print(f"Leyendo pagina: {BASE_PAGE}")
    resp = session.get(BASE_PAGE, timeout=30)
    resp.raise_for_status()

    links = extract_download_links(resp.text)
    print(f"Encontrados {len(links)} links de descarga.")

    if not links:
        print("No se encontraron links. Puede haber cambiado el HTML o requerir sesion/cookies.")
        return 2

    failed = 0
    for i, url in enumerate(links, 1):
        print(f"\n[{i}/{len(links)}] {url}")
        try:
            download_with_resume(session, url, out_dir)
            time.sleep(0.2)
        except Exception as e:
            failed += 1
            print(f"FALLO: {e}")

    print(f"\nListo. OK: {len(links) - failed} | Fallos: {failed} | Carpeta: {out_dir.resolve()}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
