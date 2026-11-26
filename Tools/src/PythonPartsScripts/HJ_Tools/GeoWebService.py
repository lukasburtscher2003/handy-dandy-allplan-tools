"""Host the approved GeoIMPORT backend in ALLPLAN's own Python runtime."""
from pathlib import Path
import importlib
import os
import re
import shutil
import sys
import tempfile
import threading


DEPENDENCIES = (
    "flask", "werkzeug", "requests", "numpy", "scipy", "shapely", "pyproj",
    "rasterio", "laspy", "lazrs", "ezdxf", "reportlab", "PIL",
)
_window_lock = threading.Lock()
_backend = None


def _missing_dependencies():
    failures = []
    for module in DEPENDENCIES:
        try:
            importlib.import_module(module)
        except Exception as exc:
            failures.append(f"{module}: {exc}")
    return failures


def dependency_report():
    failures = _missing_dependencies()
    version = sys.version.split()[0]
    if failures:
        for failure in failures:
            print("[GeoIMPORT] " + failure)
        return f"Allplan Python {version}: {len(failures)} fehlende/inkompatible Pakete. Details im Python-Trace."
    return f"Allplan Python {version}: GIS-Bibliotheken verfügbar."


def _get_backend():
    global _backend
    if _backend is not None:
        return _backend
    failures = _missing_dependencies()
    if failures:
        for failure in failures:
            print("[GeoIMPORT] " + failure)
        raise RuntimeError("GIS-Bibliotheken fehlen oder sind inkompatibel. Umgebung prüfen; IT-freigegebene ALLEP-Installation erforderlich.")
    from HJ_Tools.geo_web import server
    root = Path(os.environ.get("LOCALAPPDATA", tempfile.gettempdir())) / "HJ_Tools" / "GeoIMPORT"
    root.mkdir(parents=True, exist_ok=True)
    folder = Path(tempfile.mkdtemp(prefix="native-", dir=root))
    shutil.copytree(server.RESOURCE / "data", folder / "data")
    server.HERE = folder
    server.CACHE = folder / "cache"
    server.OUTPUT = folder / "exports"
    server.CACHE.mkdir()
    server.OUTPUT.mkdir()
    _backend = server
    return server


class GeoWebService:
    def __init__(self):
        self.http = None
        self.thread = None
        self.backend = None
        self.locked = False

    def __enter__(self):
        if not _window_lock.acquire(blocking=False):
            raise RuntimeError("GeoIMPORT ist bereits geöffnet.")
        self.locked = True
        try:
            self.backend = _get_backend()
            with self.backend.LOCK:
                if any(j["state"] in ("queued", "running") for j in self.backend.JOBS.values()):
                    raise RuntimeError("Ein vorheriger Export wird noch beendet. Bitte kurz warten.")
            from werkzeug.serving import make_server
            # Standard local web interface for the approved extension; no fallback
            # or attempt to change firewall or enterprise settings if binding fails.
            try:
                self.http = make_server("127.0.0.1", 0, self.backend.app, threaded=True)
            except SystemExit as exc:
                raise RuntimeError("Lokaler Kartenserver konnte nicht gestartet werden. Bitte IT-Freigabe prüfen.") from exc
            port = self.http.server_port
            self.url = f"http://127.0.0.1:{port}/"
            self.backend.app.config["LOCAL_HOSTS"] = [f"127.0.0.1:{port}"]
            self.backend.app.config["LOCAL_ORIGINS"] = [self.url.rstrip("/")]
            self.thread = threading.Thread(
                target=self.http.serve_forever, name="GeoIMPORT-HTTP", daemon=True
            )
            self.thread.start()
            return self
        except BaseException:
            self.close()
            raise

    def import_file(self, job):
        if not re.fullmatch(r"[a-f0-9]{32}", job):
            raise ValueError("Ungültiger Exportauftrag.")
        entry = self.backend.JOBS.get(job)
        if not entry or entry.get("state") != "done" or "metadaten.json" not in entry.get("files", []):
            raise ValueError("Kein abgeschlossener Geodatenexport.")
        path = self.backend.OUTPUT / job / "metadaten.json"
        if not path.is_file():
            raise ValueError("Metadaten fehlen.")
        return path

    def close(self):
        try:
            # Only stop jobs if this instance actually opened the HTTP server.
            if self.http is not None:
                if self.thread is not None and self.thread.is_alive():
                    self.http.shutdown()
                    self.thread.join(timeout=5)
                self.http.server_close()
                self.http = None
                with self.backend.LOCK:
                    for job in self.backend.JOBS.values():
                        if job["state"] in ("queued", "running"):
                            job["cancel"].set()
        finally:
            if self.locked:
                self.locked = False
                _window_lock.release()

    def __exit__(self, *_args):
        self.close()
