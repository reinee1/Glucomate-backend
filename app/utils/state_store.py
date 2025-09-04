# app/utils/state_store.py
import json, os, time, threading
from contextlib import suppress

class _InMemoryTTL:
    def __init__(self):
        self._d = {}
        self._lock = threading.Lock()

    def get(self, k):
        now = time.time()
        with self._lock:
            v = self._d.get(k)
            if not v: return None
            exp, payload = v
            if exp and now > exp:
                self._d.pop(k, None)
                return None
            return payload

    def set(self, k, payload, ttl=None):
        exp = time.time() + ttl if ttl else None
        with self._lock:
            self._d[k] = (exp, payload)

class StateStore:
    """
    Simple namespaced state store:
      - Uses REDIS_URL if available (recommended for multi-worker)
      - Else falls back to process-local in-memory TTL cache
      - Optional file cache for dev (STATE_FILE_CACHE=1)
    """
    def __init__(self, namespace="glucomate", default_ttl_secs=14*24*3600):
        self.ns = namespace
        self.default_ttl = default_ttl_secs

        self._redis = None
        url = os.getenv("REDIS_URL") or os.getenv("REDIS_CONNECTION_STRING")
        if url:
            try:
                import redis  # pip install redis
                self._redis = redis.Redis.from_url(url, decode_responses=True)
                # quick ping
                self._redis.ping()
            except Exception:
                self._redis = None

        self._mem = _InMemoryTTL()
        self._file_cache = os.getenv("STATE_FILE_CACHE", "0") == "1"
        self._file_dir = os.getenv("STATE_FILE_DIR", "/tmp/glucomate_state")
        if self._file_cache:
            os.makedirs(self._file_dir, exist_ok=True)

    def _key(self, user_id, suffix="state"):
        return f"{self.ns}:{user_id}:{suffix}"

    def get_json(self, user_id, suffix="state"):
        key = self._key(user_id, suffix)
        if self._redis:
            raw = self._redis.get(key)
            return json.loads(raw) if raw else None

        if self._file_cache:
            path = os.path.join(self._file_dir, key.replace(":", "_") + ".json")
            with suppress(FileNotFoundError):
                with open(path, "r") as f:
                    return json.load(f)

        return self._mem.get(key)

    def set_json(self, user_id, payload, suffix="state", ttl=None):
        key = self._key(user_id, suffix)
        ttl = ttl or self.default_ttl
        raw = json.dumps(payload, ensure_ascii=False)

        if self._redis:
            # setex ensures TTL
            self._redis.setex(key, ttl, raw)
            return

        if self._file_cache:
            path = os.path.join(self._file_dir, key.replace(":", "_") + ".json")
            tmp = path + ".tmp"
            with open(tmp, "w") as f:
                f.write(raw)
            os.replace(tmp, path)
            return

        self._mem.set(key, payload, ttl=ttl)
