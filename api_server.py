import asyncio
import concurrent.futures
import ipaddress
import os
import secrets
import threading
import time
import uuid

import google.api_core.exceptions as google_exceptions
from dotenv import load_dotenv
from flask import Flask, g, jsonify, redirect, request, session
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask_session import Session

from utils.auth import (
    discord_oauth_url,
    exchange_code,
    get_discord_guilds,
    get_discord_user,
    has_valid_api_key,
    require_guild_admin,
)
from utils.logger import log
from utils.sanitize import sanitize_prompt

load_dotenv()


def _get_env_int(name: str, default: int, minimum: int = 0) -> int:
    raw_value = os.getenv(name, str(default)).strip()
    try:
        parsed = int(raw_value)
    except ValueError:
        log.warning("Invalid integer for %s: %s. Falling back to %s.", name, raw_value, default)
        return default
    return max(minimum, parsed)


def _get_env_bool(name: str, default: bool = False) -> bool:
    raw_value = os.getenv(name, "true" if default else "false").strip().lower()
    return raw_value in {"1", "true", "yes", "on"}


def _parse_ip_allowlist(raw_value: str):
    networks = []
    for chunk in raw_value.split(","):
        candidate = chunk.strip()
        if not candidate:
            continue
        try:
            networks.append(ipaddress.ip_network(candidate, strict=False))
        except ValueError:
            log.warning("Ignoring invalid ALLOWED_DASHBOARD_IPS entry: %s", candidate)
    return networks


def _parse_guild_allowlist(raw_value: str):
    guild_ids = set()
    for chunk in raw_value.split(","):
        candidate = chunk.strip()
        if not candidate:
            continue
        if candidate.isdigit():
            guild_ids.add(int(candidate))
        else:
            log.warning("Ignoring invalid ALLOWED_GUILD_IDS entry: %s", candidate)
    return guild_ids


FLASK_DEBUG = os.getenv("FLASK_ENV", "production") == "development"
FORCE_HTTPS = _get_env_bool("FORCE_HTTPS", False)
HSTS_MAX_AGE = _get_env_int("HSTS_MAX_AGE", 31536000, minimum=0)
MAX_PENDING_PLANS = _get_env_int("MAX_PENDING_PLANS", 100, minimum=1)
AI_PREVIEW_ROUTE_CONCURRENCY = _get_env_int("AI_PREVIEW_ROUTE_CONCURRENCY", 2, minimum=1)
SERVER_EDIT_ROUTE_CONCURRENCY = _get_env_int("SERVER_EDIT_ROUTE_CONCURRENCY", 2, minimum=1)
BUILD_EXECUTE_ROUTE_CONCURRENCY = _get_env_int("BUILD_EXECUTE_ROUTE_CONCURRENCY", 1, minimum=1)
BUILD_PREVIEW_TIMEOUT_SECONDS = _get_env_int("BUILD_PREVIEW_TIMEOUT_SECONDS", 75, minimum=30)
ALLOWED_DASHBOARD_NETWORKS = _parse_ip_allowlist(os.getenv("ALLOWED_DASHBOARD_IPS", ""))
ALLOWED_GUILD_IDS = _parse_guild_allowlist(os.getenv("ALLOWED_GUILD_IDS", ""))
AUTH_EXEMPT_PATHS = {
    "/health",
    "/auth/login",
    "/auth/callback",
    "/auth/me",
    "/auth/logout",
}
BOT_READY_EXEMPT_PREFIXES = (
    "/api/buildserver/status/",
    "/api/feedback",
)
_PLAN_TTL_SECONDS = 300
_pending_plans = {}
_pending_plans_lock = threading.Lock()
_operation_tracking_lock = threading.Lock()
_preview_slots = threading.BoundedSemaphore(AI_PREVIEW_ROUTE_CONCURRENCY)
_server_edit_slots = threading.BoundedSemaphore(SERVER_EDIT_ROUTE_CONCURRENCY)
_build_execute_slots = threading.BoundedSemaphore(BUILD_EXECUTE_ROUTE_CONCURRENCY)

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 16 * 1024
app.config["DEBUG"] = FLASK_DEBUG
app.config["SECRET_KEY"] = os.getenv("FLASK_SECRET_KEY", secrets.token_hex(32))
app.config["SESSION_TYPE"] = "filesystem"
app.config["SESSION_PERMANENT"] = False
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = FORCE_HTTPS
Session(app)

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]
CORS(app, origins=allowed_origins, supports_credentials=True)

upstash_url = os.getenv("UPSTASH_REDIS_REST_URL", "")
upstash_token = os.getenv("UPSTASH_REDIS_REST_TOKEN", "")
if upstash_url and upstash_token:
    # TODO: Replace memory:// with Upstash-backed storage once flask-limiter supports
    # the Upstash HTTP API natively. Track issue at github.com/alisaifee/flask-limiter.
    storage_uri = "memory://"
else:
    storage_uri = "memory://"

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["600 per day", "120 per hour"],
    storage_uri=storage_uri,
    headers_enabled=True,
)


def run_api_server(bot):
    app.bot = bot


def _bot_ready_for_api() -> bool:
    bot = getattr(app, "bot", None)
    if bot is None:
        return False

    bot_loop = getattr(bot, "loop", None)
    if bot_loop is None or not bot_loop.is_running():
        return False

    if bot.is_closed():
        return False

    return bot.is_ready()


def _run_on_bot_loop(coro, timeout=10):
    future = asyncio.run_coroutine_threadsafe(coro, app.bot.loop)
    try:
        return future.result(timeout=timeout)
    except concurrent.futures.TimeoutError:
        future.cancel()
        raise TimeoutError("Bot loop did not respond within timeout.")


def _evict_expired_plans():
    now = time.monotonic()
    with _pending_plans_lock:
        expired = [key for key, value in _pending_plans.items() if value["expires_at"] < now]
        for key in expired:
            del _pending_plans[key]


def _parse_bool(value, *, field_name: str, default: bool = False) -> bool:
    if value is None:
        return default
    if isinstance(value, bool):
        return value
    if isinstance(value, (int, float)):
        return bool(value)
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in {"true", "1", "yes", "on"}:
            return True
        if lowered in {"false", "0", "no", "off", ""}:
            return False
    raise ValueError(f"{field_name} must be a boolean.")


def _parse_bounded_int(value, *, field_name: str, default: int, minimum: int, maximum: int) -> int:
    if value is None or value == "":
        return default
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        raise ValueError(f"{field_name} must be an integer.")
    return max(minimum, min(parsed, maximum))


def _require_json_body():
    if not request.is_json:
        return None, (jsonify({"error": "Content-Type must be application/json"}), 415)

    data = request.get_json(silent=True)
    if not isinstance(data, dict):
        return None, (jsonify({"error": "Invalid JSON body"}), 400)

    return data, None


def _is_ip_allowed(remote_addr: str) -> bool:
    if not ALLOWED_DASHBOARD_NETWORKS:
        return True
    if not remote_addr:
        return False
    try:
        ip_addr = ipaddress.ip_address(remote_addr)
    except ValueError:
        return False
    return any(ip_addr in network for network in ALLOWED_DASHBOARD_NETWORKS)


def _is_guild_allowed(guild_id: int) -> bool:
    if not ALLOWED_GUILD_IDS:
        return True
    return guild_id in ALLOWED_GUILD_IDS


def _session_manageable_guild_ids() -> set[int]:
    guild_ids = set()
    for guild in session.get("discord_guilds", []):
        try:
            perms = int(guild.get("permissions", guild.get("permissions_new", 0)) or 0)
        except (TypeError, ValueError):
            continue
        if perms & 0x8 or perms & 0x20:
            guild_id = guild.get("id")
            if str(guild_id).isdigit():
                guild_ids.add(int(guild_id))
    return guild_ids


def _session_has_guild_access(guild_id: int) -> bool:
    return guild_id in _session_manageable_guild_ids()


def _guild_operation_in_progress(guild_id: int) -> bool:
    with _operation_tracking_lock:
        pending_guilds = getattr(app.bot, "dashboard_operations_in_progress", set())
        if guild_id in pending_guilds:
            return True
    locks = getattr(app.bot, "guild_operation_locks", {})
    lock = locks.get(guild_id)
    return bool(lock and lock.locked())


async def _run_guarded_guild_operation(guild_id: int, coro):
    try:
        await coro
    finally:
        with _operation_tracking_lock:
            app.bot.dashboard_operations_in_progress.discard(guild_id)


def _submit_guild_operation(guild_id: int, coro):
    with _operation_tracking_lock:
        app.bot.dashboard_operations_in_progress.add(guild_id)
    return asyncio.run_coroutine_threadsafe(
        _run_guarded_guild_operation(guild_id, coro),
        app.bot.loop,
    )


def _get_guild_from_id(guild_id_raw):
    if not str(guild_id_raw).isdigit():
        return None, (jsonify({"error": "Invalid guild ID"}), 400)

    guild_id = int(guild_id_raw)
    if not _is_guild_allowed(guild_id):
        return None, (jsonify({"error": "Guild is not allowed for dashboard control"}), 403)

    guild = app.bot.get_guild(guild_id)
    if not guild:
        return None, (jsonify({"error": "Guild not found"}), 404)

    return guild, None


def _get_build_request_context(data):
    guild, guild_error = _get_guild_from_id(data.get("guildId", ""))
    if guild_error:
        return None, None, None, None, guild_error

    prompt = sanitize_prompt(data.get("prompt", ""))
    if not prompt:
        return None, None, None, None, (jsonify({"error": "Prompt is required"}), 400)

    try:
        reset_server = _parse_bool(data.get("resetServer", False), field_name="resetServer")
    except ValueError as error:
        return None, None, None, None, (jsonify({"error": str(error)}), 400)

    ai_cog = app.bot.get_cog("AICommands")
    if not ai_cog:
        return None, None, None, None, (jsonify({"error": "AICommands cog not loaded"}), 500)

    return guild, ai_cog, prompt, reset_server, None


def _serialize_build_preview(setup_plan):
    categories = []
    categories_by_name = {}

    for task in setup_plan.get("plan", []):
        if task.get("task") != "create_category":
            continue

        category_name = task.get("name")
        category_entry = {"name": category_name, "channels": []}
        categories.append(category_entry)
        categories_by_name[category_name] = category_entry

    uncategorized_channels = []
    for task in setup_plan.get("plan", []):
        if task.get("task") != "create_channel":
            continue

        channel_entry = {
            "name": task.get("name"),
            "type": task.get("channel_type", "text"),
            "permissions": task.get("permissions", "public"),
            "topic": task.get("topic"),
            "message": task.get("message"),
        }
        category_name = task.get("category")
        category = categories_by_name.get(category_name)
        if category:
            category["channels"].append(channel_entry)
        else:
            uncategorized_channels.append(channel_entry)

    if uncategorized_channels:
        categories.append({"name": "Uncategorized", "channels": uncategorized_channels})

    return {
        "roles": setup_plan.get("roles", []),
        "categories": categories,
    }


def _acquire_slot(semaphore: threading.BoundedSemaphore, busy_message: str):
    if semaphore.acquire(blocking=False):
        return None
    return jsonify({"error": busy_message}), 503


def _is_bot_ready_exempt_path(path: str) -> bool:
    if path in AUTH_EXEMPT_PATHS:
        return True
    return any(path.startswith(prefix) for prefix in BOT_READY_EXEMPT_PREFIXES)


def _resolve_build_execution_request(data):
    setup_plan = data.get("setupPlan")
    if setup_plan is not None:
        guild, ai_cog, prompt, reset_server, error_response = _get_build_request_context(data)
        if error_response:
            return None, None, None, None, None, error_response

        try:
            validated_plan = ai_cog._validate_build_plan(setup_plan)
        except ValueError as error:
            return None, None, None, None, None, (jsonify({"error": str(error)}), 400)

        return guild, ai_cog, prompt, reset_server, validated_plan, None

    plan_token = str(data.get("planToken", "")).strip()
    guild_id_raw = str(data.get("guildId", "")).strip()
    if not plan_token or not guild_id_raw.isdigit():
        return None, None, None, None, None, (
            jsonify({"error": "setupPlan or planToken with a valid guildId is required"}),
            400,
        )

    guild_id = int(guild_id_raw)
    if not _is_guild_allowed(guild_id):
        return None, None, None, None, None, (
            jsonify({"error": "Guild is not allowed for dashboard control"}),
            403,
        )

    with _pending_plans_lock:
        entry = _pending_plans.get(plan_token)
    if not entry:
        return None, None, None, None, None, (
            jsonify({"error": "Plan token not found or expired."}),
            404,
        )

    if time.monotonic() > entry["expires_at"]:
        with _pending_plans_lock:
            _pending_plans.pop(plan_token, None)
        return None, None, None, None, None, (
            jsonify({"error": "Plan token has expired. Please generate a new preview."}),
            410,
        )

    if entry["guild_id"] != guild_id:
        return None, None, None, None, None, (
            jsonify({"error": "Guild ID does not match the plan token."}),
            403,
        )

    guild = app.bot.get_guild(entry["guild_id"])
    if not guild:
        return None, None, None, None, None, (jsonify({"error": "Guild not found"}), 404)

    ai_cog = app.bot.get_cog("AICommands")
    if not ai_cog:
        return None, None, None, None, None, (
            jsonify({"error": "AICommands cog not loaded"}),
            500,
        )

    with _pending_plans_lock:
        _pending_plans.pop(plan_token, None)

    return guild, ai_cog, entry["prompt"], entry["reset"], entry["plan"], None


@app.before_request
def require_auth_or_key():
    if request.method == "OPTIONS":
        return

    if request.path in AUTH_EXEMPT_PATHS:
        return

    if not hasattr(app, "bot"):
        g.api_request_error = (jsonify({"error": "Bot backend is not ready"}), 503)
        return

    if FORCE_HTTPS and not request.is_secure:
        g.api_request_error = (jsonify({"error": "HTTPS is required"}), 400)
        return

    if not _is_ip_allowed(request.remote_addr):
        g.api_request_error = (jsonify({"error": "Forbidden"}), 403)
        return

    if has_valid_api_key():
        return

    if session.get("discord_user_id"):
        return

    g.api_request_error = (jsonify({"error": "Unauthorized"}), 401)


@app.before_request
def log_request():
    if request.path == "/health":
        return

    guild_id = None
    if request.is_json and request.content_length and request.content_length < 1024:
        try:
            body = request.get_json(silent=True, cache=True) or {}
            guild_id = body.get("guildId")
        except Exception:
            pass

    log.info(
        "API %s %s | ip=%s guild=%s",
        request.method,
        request.path,
        request.remote_addr,
        guild_id or "none",
    )

    request_error = getattr(g, "api_request_error", None)
    if request_error:
        return request_error


@app.before_request
def ensure_bot_ready():
    if request.method == "OPTIONS" or _is_bot_ready_exempt_path(request.path):
        return

    if not _bot_ready_for_api():
        return jsonify(
            {
                "error": "Bot backend is starting up or reconnecting to Discord. Please retry shortly.",
                "botReady": False,
            }
        ), 503


@app.after_request
def apply_security_headers(response):
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "no-referrer"
    response.headers["Cross-Origin-Resource-Policy"] = "same-site"
    response.headers["Cache-Control"] = "no-store"
    if FORCE_HTTPS or request.is_secure:
        response.headers["Strict-Transport-Security"] = f"max-age={HSTS_MAX_AGE}; includeSubDomains"
    return response


@app.errorhandler(413)
def handle_request_too_large(_error):
    return jsonify({"error": "Request body too large"}), 413


@app.errorhandler(429)
def handle_rate_limit(_error):
    return jsonify({"error": "Rate limit exceeded. Please slow down."}), 429


@limiter.limit("120 per minute")
@app.route("/health", methods=["GET"])
def health_check():
    bot = getattr(app, "bot", None)
    bot_loop = getattr(bot, "loop", None) if bot is not None else None
    return (
        jsonify(
            {
                "status": "ok",
                "bot_ready": bot.is_ready() if bot is not None else False,
                "loop_running": bot_loop.is_running() if bot_loop is not None else False,
            }
        ),
        200,
    )


@app.route("/auth/login")
def auth_login():
    state = secrets.token_urlsafe(16)
    session["oauth_state"] = state
    return redirect(discord_oauth_url(state))


@app.route("/auth/callback")
def auth_callback():
    if request.args.get("state") != session.pop("oauth_state", None):
        return jsonify({"error": "Invalid state"}), 400

    code = request.args.get("code")
    if not code:
        return jsonify({"error": "No code"}), 400

    try:
        tokens = exchange_code(code)
        user = get_discord_user(tokens["access_token"])
        guilds = get_discord_guilds(tokens["access_token"])
        session["discord_user_id"] = user["id"]
        session["discord_username"] = user["username"]
        session["discord_guilds"] = guilds
        session["access_token"] = tokens["access_token"]
        frontend_url = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173").split(",")[0].strip()
        return redirect(f"{frontend_url}/dashboard")
    except Exception as error:
        log.error("OAuth callback error: %s", error)
        return jsonify({"error": "Authentication failed"}), 500


@app.route("/auth/me")
def auth_me():
    if not session.get("discord_user_id"):
        return jsonify({"authenticated": False}), 200
    return jsonify(
        {
            "authenticated": True,
            "user_id": session["discord_user_id"],
            "username": session["discord_username"],
        }
    )


@app.route("/auth/logout", methods=["POST"])
def auth_logout():
    session.clear()
    return jsonify({"ok": True})


@limiter.limit("30 per minute")
@app.route("/api/guilds", methods=["GET"])
def get_guilds():
    allowed_session_guilds = _session_manageable_guild_ids()
    guilds_list = []
    for guild in app.bot.guilds:
        if not _is_guild_allowed(guild.id):
            continue
        if not has_valid_api_key() and guild.id not in allowed_session_guilds:
            continue
        guilds_list.append(
            {
                "id": str(guild.id),
                "name": guild.name,
                "icon": guild.icon.url if guild.icon else None,
            }
        )
    guilds_list.sort(key=lambda item: item["name"].lower())
    return jsonify(guilds_list)


@limiter.limit("60 per minute")
@app.route("/api/guilds/<int:guild_id>/info", methods=["GET"])
@require_guild_admin
def get_guild_info(guild_id):
    if not _is_guild_allowed(guild_id):
        return jsonify({"error": "Guild is not allowed for dashboard control"}), 403

    guild = app.bot.get_guild(guild_id)
    if not guild:
        return jsonify({"error": "Guild not found"}), 404

    info = {
        "member_count": guild.member_count,
        "premium_tier": guild.premium_tier,
        "premium_subscription_count": guild.premium_subscription_count,
        "channels": len(guild.text_channels) + len(guild.voice_channels),
        "roles": len(guild.roles),
    }
    return jsonify(info)


@limiter.limit("60 per minute")
@app.route("/api/guilds/<int:guild_id>/members", methods=["GET"])
@require_guild_admin
def get_guild_members(guild_id):
    guild = app.bot.get_guild(guild_id)
    if not guild:
        return jsonify({"error": "Guild not found"}), 404

    members = [
        {
            "id": str(member.id),
            "name": member.display_name,
            "username": str(member),
        }
        for member in guild.members
        if not member.bot
    ]
    members.sort(key=lambda item: item["name"].lower())
    return jsonify(members)


@limiter.limit("30 per minute")
@app.route("/api/automod_settings/<int:guild_id>", methods=["GET", "POST"])
@require_guild_admin
def automod_settings(guild_id):
    if not _is_guild_allowed(guild_id):
        return jsonify({"error": "Guild is not allowed for dashboard control"}), 403

    db = app.bot.db
    try:
        if request.method == "POST":
            data, error_response = _require_json_body()
            if error_response:
                return error_response

            warning_limit = _parse_bounded_int(
                data.get("warningLimit", 3),
                field_name="warningLimit",
                default=3,
                minimum=1,
                maximum=20,
            )
            profanity_filter = _parse_bool(
                data.get("profanityFilter", False),
                field_name="profanityFilter",
                default=False,
            )
            limit_action = str(data.get("limitAction", "kick")).strip().lower()
            if limit_action not in ("kick", "ban"):
                limit_action = "kick"

            _run_on_bot_loop(
                db.set_automod_settings(
                    guild_id,
                    profanity_filter,
                    warning_limit,
                    limit_action,
                )
            )
            return jsonify({"message": "Settings updated successfully"})

        settings = _run_on_bot_loop(db.get_automod_settings(guild_id))
        return jsonify(settings)
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except TimeoutError:
        return jsonify({"error": "Request timed out. Bot may be busy."}), 504


@limiter.limit("20 per hour")
@app.route("/api/automod_settings/<int:guild_id>/warnings/reset", methods=["POST"])
@app.route("/api/guilds/<int:guild_id>/warnings/reset", methods=["POST"])
@require_guild_admin
def reset_member_warnings(guild_id):
    data = request.get_json(silent=True) or {}
    user_id_raw = data.get("userId", "")
    if not str(user_id_raw).isdigit():
        return jsonify({"error": "Invalid user ID"}), 400

    try:
        _run_on_bot_loop(app.bot.db.reset_warnings(guild_id, int(user_id_raw)))
    except TimeoutError:
        return jsonify({"error": "Request timed out. Bot may be busy."}), 504

    return jsonify({"message": "Warnings reset successfully!"})


@limiter.limit("20 per minute")
@app.route("/api/feedback", methods=["POST"])
def submit_feedback():
    data = request.get_json(silent=True) or {}
    message = data.get("message", "").strip()
    if not message:
        return jsonify({"error": "Message is required"}), 400
    if len(message) > 2000:
        return jsonify({"error": "Message too long"}), 400
    log.info("FEEDBACK: %s", message)
    return jsonify({"message": "Feedback received. Thank you!"})


@limiter.limit("5 per minute")
@app.route("/api/buildserver/preview", methods=["POST"])
@require_guild_admin
def build_server_preview():
    data, error_response = _require_json_body()
    if error_response:
        return error_response

    guild, ai_cog, prompt, reset_server, context_error = _get_build_request_context(data)
    if context_error:
        return context_error

    variation_hint = sanitize_prompt(str(data.get("variationHint", "")), max_length=80)

    _evict_expired_plans()
    with _pending_plans_lock:
        if len(_pending_plans) >= MAX_PENDING_PLANS:
            log.warning("Rejecting build preview because pending plan store is full.")
            return jsonify({"error": "Server is busy. Please try again shortly."}), 503

    busy_response = _acquire_slot(
        _preview_slots,
        "AI preview capacity is full right now. Please try again shortly.",
    )
    if busy_response:
        return busy_response

    try:
        started_at = time.monotonic()
        setup_plan = _run_on_bot_loop(
            ai_cog.generate_build_plan(prompt, variation_hint),
            timeout=BUILD_PREVIEW_TIMEOUT_SECONDS,
        )
        log.info(
            "Generated build preview for guild %s in %.2fs",
            guild.id,
            time.monotonic() - started_at,
        )
    except TimeoutError:
        log.warning(
            "Build preview timed out for guild %s after %ss",
            guild.id,
            BUILD_PREVIEW_TIMEOUT_SECONDS,
        )
        return jsonify(
            {
                "error": (
                    "AI request timed out. Gemini 3 can take longer on the free tier. "
                    "Please try again in a moment."
                )
            }
        ), 504
    except google_exceptions.ResourceExhausted:
        return jsonify({"error": "AI service rate-limited. Wait 60s."}), 429
    except google_exceptions.GoogleAPICallError as error:
        return jsonify({"error": f"AI error: {getattr(error, 'message', str(error))}"}), 502
    except ValueError as error:
        return jsonify({"error": str(error)}), 400
    except Exception:
        log.exception("Failed to generate build preview for guild %s", guild.id)
        return jsonify({"error": "Failed to generate a server preview."}), 500
    finally:
        _preview_slots.release()

    token = str(uuid.uuid4())
    with _pending_plans_lock:
        _pending_plans[token] = {
            "plan": setup_plan,
            "guild_id": guild.id,
            "prompt": prompt,
            "reset": reset_server,
            "expires_at": time.monotonic() + _PLAN_TTL_SECONDS,
        }

    return jsonify(
        {
            "message": "Preview generated successfully.",
            "planToken": token,
            "prompt": prompt,
            "resetServer": reset_server,
            "preview": _serialize_build_preview(setup_plan),
        }
    )


@limiter.limit("10 per minute")
@app.route("/api/buildserver/execute", methods=["POST"])
@require_guild_admin
def build_server_execute():
    data, error_response = _require_json_body()
    if error_response:
        return error_response

    guild, ai_cog, prompt, reset_server, setup_plan, context_error = _resolve_build_execution_request(data)
    if context_error:
        return context_error

    if _guild_operation_in_progress(guild.id):
        return jsonify({"error": "A server operation is already running for this guild."}), 409

    busy_response = _acquire_slot(
        _build_execute_slots,
        "Build execution capacity is full right now. Please try again shortly.",
    )
    if busy_response:
        return busy_response

    job_id = str(uuid.uuid4())

    try:
        try:
            _run_on_bot_loop(app.bot.db.create_build_job(job_id, guild.id))
        except TimeoutError:
            return jsonify({"error": "Request timed out while creating the job."}), 504

        try:
            _submit_guild_operation(
                guild.id,
                ai_cog.execute_api_build_plan(
                    guild,
                    setup_plan,
                    reset_server,
                    prompt,
                    job_id,
                ),
            )
        except Exception:
            with _operation_tracking_lock:
                app.bot.dashboard_operations_in_progress.discard(guild.id)
            try:
                _run_on_bot_loop(
                    app.bot.db.update_build_job(
                        job_id,
                        "failed",
                        "Failed to schedule the build execution.",
                    )
                )
            except Exception:
                log.exception("Failed to mark build job %s as failed after scheduling error", job_id)
            log.exception("Failed to submit build execution for guild %s", guild.id)
            return jsonify({"error": "Failed to schedule the build execution."}), 503

        return jsonify({"message": "Build started.", "jobId": job_id}), 202
    finally:
        _build_execute_slots.release()


@limiter.limit("30 per minute")
@app.route("/api/buildserver/status/<job_id>", methods=["GET"])
def build_job_status(job_id):
    try:
        row = _run_on_bot_loop(app.bot.db.get_build_job(job_id))
    except TimeoutError:
        return jsonify({"error": "Request timed out. Bot may be busy."}), 504

    if not row:
        return jsonify({"error": "Job not found"}), 404

    if not has_valid_api_key() and not _session_has_guild_access(int(row["guild_id"])):
        return jsonify({"error": "Insufficient permissions"}), 403

    return jsonify({"status": row["status"], "message": row["result_message"]})


@limiter.limit("10 per minute")
@app.route("/api/buildserver", methods=["POST"])
@require_guild_admin
def build_server_compat():
    data, error_response = _require_json_body()
    if error_response:
        return error_response
    if data.get("setupPlan") is not None or data.get("planToken"):
        return build_server_execute()
    return build_server_preview()


@limiter.limit("5 per minute")
@app.route("/api/serveredit", methods=["POST"])
@require_guild_admin
def server_edit():
    data, error_response = _require_json_body()
    if error_response:
        return error_response

    guild, guild_error = _get_guild_from_id(data.get("guildId", ""))
    if guild_error:
        return guild_error

    prompt = sanitize_prompt(data.get("prompt", ""))
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    edit_cog = app.bot.get_cog("AIEditCommands")
    if not edit_cog:
        return jsonify({"error": "AIEditCommands cog not loaded"}), 500

    if _guild_operation_in_progress(guild.id):
        return jsonify({"error": "A server operation is already running for this guild."}), 409

    busy_response = _acquire_slot(
        _server_edit_slots,
        "Server edit capacity is full right now. Please try again shortly.",
    )
    if busy_response:
        return busy_response

    try:
        try:
            _submit_guild_operation(
                guild.id,
                edit_cog.handle_api_edit_request(guild, prompt),
            )
        except Exception:
            with _operation_tracking_lock:
                app.bot.dashboard_operations_in_progress.discard(guild.id)
            log.exception("Failed to submit server edit for guild %s", guild.id)
            return jsonify({"error": "Failed to schedule the server edit."}), 503
        return jsonify({"message": "Server edit command sent successfully!"})
    finally:
        _server_edit_slots.release()
