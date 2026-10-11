import functools
import mimetypes
import http.server
import os
import threading
from pathlib import Path

import pytest

ROOT = Path(__file__).parent.parent
FIXTURES = Path(__file__).parent / "fixtures"
# Optional local copies of CDN files, laid out as tests/.cdn-cache/<package@version>/<path>.
# Used when the CDN isn't reachable (e.g. sandboxed environments); CI uses the real CDN.
CDN_CACHE = Path(__file__).parent / ".cdn-cache"


@pytest.fixture(scope="session")
def browser_type_launch_args(browser_type_launch_args):
    # Set CHROMIUM_EXECUTABLE to use a preinstalled browser instead of `playwright install`
    executable = os.environ.get("CHROMIUM_EXECUTABLE")
    if executable:
        return {**browser_type_launch_args, "executable_path": executable}
    return browser_type_launch_args


@pytest.fixture(scope="session")
def server():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT))
    httpd = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
    thread = threading.Thread(target=httpd.serve_forever, daemon=True)
    thread.start()
    yield f"http://127.0.0.1:{httpd.server_address[1]}"
    httpd.shutdown()


@pytest.fixture
def page(page):
    def serve_cdn(route):
        path = route.request.url.split("/npm/", 1)[-1].split("?")[0]
        local = CDN_CACHE / path
        if local.is_file():
            route.fulfill(path=str(local), content_type=mimetypes.guess_type(local.name)[0] or "application/javascript")
        else:
            route.continue_()

    page.route("https://cdn.jsdelivr.net/npm/**", serve_cdn)
    return page


@pytest.fixture
def fixture_html():
    return lambda name: (FIXTURES / name).read_text()
