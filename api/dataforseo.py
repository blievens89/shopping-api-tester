import base64
import time
from typing import Dict, Optional, Callable
import requests
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

DEFAULT_BASE = "https://api.dataforseo.com/v3"
DEFAULT_TIMEOUT = (10, 60)  # (connect, read)

class DataForSEOError(Exception):
    pass

class DataForSEOClient:
    """Minimal client for DataForSEO Google Shopping API."""

    def __init__(self, login: str, password: str, base_url: str = DEFAULT_BASE):
        if not login or not password:
            raise ValueError("Missing DataForSEO credentials.")
        self.base_url = base_url.rstrip("/")
        creds = f"{login}:{password}"
        encoded = base64.b64encode(creds.encode()).decode()
        self.headers = {
            "Authorization": f"Basic {encoded}",
            "Content-Type": "application/json",
            "Accept": "application/json",
            "User-Agent": "shopping-api-tester/2.0"
        }
        self.session = requests.Session()

    @retry(
        retry=retry_if_exception_type((requests.RequestException, DataForSEOError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(5),
        reraise=True,
    )
    def _post(self, path: str, payload) -> Dict:
        url = f"{self.base_url}{path}"
        r = self.session.post(url, headers=self.headers, json=payload, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("status_code") not in (20000, 20100, 40500):
            raise DataForSEOError(f"API status: {data.get('status_code')} {data.get('status_message')}")
        return data

    @retry(
        retry=retry_if_exception_type((requests.RequestException, DataForSEOError)),
        wait=wait_exponential(multiplier=1, min=1, max=8),
        stop=stop_after_attempt(7),
        reraise=True,
    )
    def _get(self, path: str) -> Dict:
        url = f"{self.base_url}{path}"
        r = self.session.get(url, headers=self.headers, timeout=DEFAULT_TIMEOUT)
        r.raise_for_status()
        data = r.json()
        if data.get("status_code") not in (20000,):
            raise DataForSEOError(f"API status: {data.get('status_code')} {data.get('status_message')}")
        return data

    def _wait_for_result(
        self,
        get_path: str,
        max_wait_sec: int = 180,
        poll_every: float = 2.0,
        on_tick: Optional[Callable[[int, int], None]] = None,
    ) -> Dict:
        start = time.time()
        last = {}
        while True:
            last = self._get(get_path)
            tasks = last.get("tasks") or []
            if tasks and tasks[0].get("result"):
                return last
            elapsed = int(time.time() - start)
            if on_tick:
                on_tick(elapsed, int(max_wait_sec))
            if elapsed >= max_wait_sec:
                raise DataForSEOError("Timed out waiting for task result.")
            time.sleep(poll_every)

    def search_products(
        self,
        keyword: str,
        location_code: int = 2826,
        language_code: str = "en",
        depth: int = 100,
        on_tick: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        payload = [{
            "keyword": keyword,
            "location_code": location_code,
            "language_code": language_code,
            "depth": max(10, min(depth, 100))
        }]
        post = self._post("/merchant/google/products/task_post", payload)
        task_id = post["tasks"][0]["id"]
        return self._wait_for_result(f"/merchant/google/products/task_get/advanced/{task_id}", on_tick=on_tick)

    def get_product_info(
        self,
        product_id: str,
        location_code: int = 2826,
        language_code: str = "en",
        on_tick: Optional[Callable[[int, int], None]] = None
    ) -> Dict:
        payload = [{
            "product_id": product_id,
            "location_code": location_code,
            "language_code": language_code
        }]
        post = self._post("/merchant/google/product_info/task_post", payload)
        task_id = post["tasks"][0]["id"]
        return self._wait_for_result(f"/merchant/google/product_info/task_get/advanced/{task_id}", on_tick=on_tick)
