import redis
import json
import os
from dotenv import load_dotenv
load_dotenv()

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_DB   = int(os.getenv("REDIS_DB", 0))

# ── Connect to Redis ──────────────────────────────────────────
def get_redis():
    """Return a Redis connection. Raises clear error if Redis not running."""
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=REDIS_DB,
                        decode_responses=True)
        r.ping()  # Will raise if Redis is not available
        return r
    except redis.ConnectionError:
        print(" Redis not running! Start it with: docker run -d -p 6379:6379 redis")
        raise

# ── Publish a message to an agent's channel ───────────────────
def publish_message(message: dict):
    """
    Send a structured JSON message to the recipient agent's Redis channel.
    Also appends to the global 'log' list for full history.
    """
    r = get_redis()
    recipient = message.get("to_agent")
    payload   = json.dumps(message)

    # Publish to recipient's pub/sub channel
    r.publish(f"channel:{recipient}", payload)

    # Also push to recipient's queue (list) so agents can poll
    r.rpush(f"queue:{recipient}", payload)

    # Append to global log list
    r.rpush("log", payload)

    print(f"[BUS] {message['from_agent'].upper()} → {recipient.upper()} "
          f"| type: {message['message_type']}")

# ── Read all messages for an agent (from queue) ───────────────
def read_messages(agent_name: str) -> list:
    """
    Return all messages in an agent's queue and clear the queue.
    Use this for polling (non-blocking).
    """
    r = get_redis()
    key = f"queue:{agent_name}"
    messages = []
    while True:
        raw = r.lpop(key)
        if raw is None:
            break
        try:
            messages.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return messages

# ── Subscribe to an agent's channel (blocking) ────────────────
def subscribe_and_listen(agent_name: str, callback, timeout=10):
    """
    Subscribe to agent's Redis channel and call callback(message) for each message.
    Blocks for `timeout` seconds waiting for messages.
    Used for real-time listening (optional, advanced usage).
    """
    r = get_redis()
    pubsub = r.pubsub()
    pubsub.subscribe(f"channel:{agent_name}")
    print(f"[BUS] 👂 {agent_name.upper()} subscribed to channel:{agent_name}")

    for raw_message in pubsub.listen():
        if raw_message["type"] == "message":
            try:
                msg = json.loads(raw_message["data"])
                callback(msg)
            except json.JSONDecodeError:
                pass

# ── Get full message history (for demo) ──────────────────────
def get_full_log() -> list:
    """Return all messages ever sent — shown in demo to evaluator."""
    r = get_redis()
    raw_list = r.lrange("log", 0, -1)
    messages = []
    for raw in raw_list:
        try:
            messages.append(json.loads(raw))
        except json.JSONDecodeError:
            pass
    return messages

# ── Clear all queues (for fresh run) ─────────────────────────
def clear_all():
    """Clear all agent queues and log. Call at start of main.py for clean run."""
    r = get_redis()
    agents = ["ceo", "product", "engineer", "marketing", "qa", "log"]
    for agent in agents:
        r.delete(f"queue:{agent}")
        r.delete(f"channel:{agent}")
    r.delete("log")
    print("[BUS]  All queues and log cleared for fresh run.")

# ── Fallback: dict-based bus (used if Redis unavailable) ──────
_fallback_bus = {
    "ceo": [], "product": [], "engineer": [],
    "marketing": [], "qa": [], "log": []
}

class MessageBus:
    """
    Smart Message Bus — tries Redis first, falls back to dict.
    Import this class in all agents instead of the raw dict.

    Usage:
        from Message_Bus import MessageBus
        bus = MessageBus()
        bus.send(message)
        msgs = bus.receive("ceo")
        log  = bus.get_log()
    """

    def __init__(self):
        self.use_redis = False
        try:
            self._r = get_redis()
            self.use_redis = True
            print("[BUS]  Redis connected — using pub/sub message bus")
        except Exception:
            print("[BUS]   Redis unavailable — falling back to dict message bus")
            self._r = None

    def send(self, message: dict):
        """Send a message. Uses Redis if available, else dict."""
        if self.use_redis:
            publish_message(message)
        else:
            recipient = message.get("to_agent")
            _fallback_bus.setdefault(recipient, []).append(message)
            _fallback_bus.setdefault("log", []).append(message)
            print(f"[BUS]  {message['from_agent'].upper()} → {recipient.upper()} "
                  f"| type: {message['message_type']}")

    def receive(self, agent_name: str) -> list:
        """Get all pending messages for an agent."""
        if self.use_redis:
            return read_messages(agent_name)
        else:
            msgs = list(_fallback_bus.get(agent_name, []))
            _fallback_bus[agent_name] = []
            return msgs

    def peek(self, agent_name: str) -> list:
        """Read messages WITHOUT removing them (for CEO review loops)."""
        if self.use_redis:
            r = self._r
            raw_list = r.lrange(f"queue:{agent_name}", 0, -1)
            msgs = []
            for raw in raw_list:
                try:
                    msgs.append(json.loads(raw))
                except:
                    pass
            return msgs
        else:
            return list(_fallback_bus.get(agent_name, []))

    def get_log(self) -> list:
        """Get full message history for demo."""
        if self.use_redis:
            return get_full_log()
        else:
            return list(_fallback_bus.get("log", []))

    def clear(self):
        """Clear everything for a fresh run."""
        if self.use_redis:
            clear_all()
        else:
            for key in _fallback_bus:
                _fallback_bus[key] = []
            print("[BUS]  Dict bus cleared.")

    def get_all_queues(self) -> dict:
        """Show all queues — for debugging."""
        if self.use_redis:
            r = self._r
            agents = ["ceo", "product", "engineer", "marketing", "qa"]
            result = {}
            for agent in agents:
                raw_list = r.lrange(f"queue:{agent}", 0, -1)
                result[agent] = [json.loads(x) for x in raw_list]
            return result
        else:
            return dict(_fallback_bus)


# ── Backwards compatibility: dict-style message_bus ──────────
# Old code that does message_bus["ceo"].append(...) still works
message_bus = _fallback_bus
