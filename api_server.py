import asyncio
import os

import google.api_core.exceptions as google_exceptions
from dotenv import load_dotenv
from flask import Flask, jsonify, request
from flask_cors import CORS
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

from utils.logger import log
from utils.sanitize import sanitize_prompt

load_dotenv()

FLASK_DEBUG = os.getenv("FLASK_ENV", "production") == "development"

app = Flask(__name__)
app.config["DEBUG"] = FLASK_DEBUG

allowed_origins_raw = os.getenv("ALLOWED_ORIGINS", "http://localhost:5173")
allowed_origins = [origin.strip() for origin in allowed_origins_raw.split(",") if origin.strip()]
CORS(app, origins=allowed_origins, supports_credentials=False)

limiter = Limiter(
    get_remote_address,
    app=app,
    default_limits=["200 per day", "60 per hour"],
    storage_uri="memory://",
)


def run_api_server(bot):
    app.bot = bot


def _run_on_bot_loop(coro):
    future = asyncio.run_coroutine_threadsafe(coro, app.bot.loop)
    return future.result()


def _get_build_request_context(data):
    guild_id_raw = data.get("guildId", "")
    if not str(guild_id_raw).isdigit():
        return None, None, None, None, (jsonify({"error": "Invalid guild ID"}), 400)

    prompt = sanitize_prompt(data.get("prompt", ""))
    if not prompt:
        return None, None, None, None, (jsonify({"error": "Prompt is required"}), 400)

    reset_server = bool(data.get("resetServer", False))
    guild = app.bot.get_guild(int(guild_id_raw))
    if not guild:
        return None, None, None, None, (jsonify({"error": "Guild not found"}), 404)

    ai_cog = app.bot.get_cog("AICommands")
    if not ai_cog:
        return None, None, None, None, (jsonify({"error": "AICommands cog not loaded"}), 500)

    return guild, ai_cog, prompt, reset_server, None


def _is_valid_setup_plan(setup_plan):
    return (
        isinstance(setup_plan, dict)
        and isinstance(setup_plan.get("plan"), list)
        and bool(setup_plan.get("plan"))
    )


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
        "rawPlan": setup_plan.get("plan", []),
    }


@app.before_request
def require_api_key():
    if request.method == "OPTIONS" or request.path == "/health":
        return

    key = request.headers.get("X-API-Key")
    expected = os.getenv("API_SECRET_KEY")
    if not key or key != expected:
        return jsonify({"error": "Unauthorized"}), 401


@app.route("/health", methods=["GET"])
def health_check():
    return (
        jsonify(
            {
                "status": "ok",
                "bot_ready": app.bot.is_ready() if hasattr(app, "bot") else False,
            }
        ),
        200,
    )


@app.route("/api/guilds", methods=["GET"])
def get_guilds():
    guilds_list = [
        {
            "id": str(guild.id),
            "name": guild.name,
            "icon": guild.icon.url if guild.icon else None,
        }
        for guild in app.bot.guilds
    ]
    return jsonify(guilds_list)


@app.route("/api/guilds/<int:guild_id>/info", methods=["GET"])
def get_guild_info(guild_id):
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


@app.route("/api/automod_settings/<int:guild_id>", methods=["GET", "POST"])
def automod_settings(guild_id):
    db = app.bot.db
    if request.method == "POST":
        data = request.get_json(silent=True) or {}
        _run_on_bot_loop(
            db.set_automod_settings(
                guild_id,
                data.get("profanityFilter"),
                data.get("warningLimit"),
                data.get("limitAction"),
            )
        )
        return jsonify({"message": "Settings updated successfully"})

    settings = _run_on_bot_loop(db.get_automod_settings(guild_id))
    return jsonify(settings)


@limiter.limit("5 per minute")
@app.route("/api/buildserver/preview", methods=["POST"])
def build_server_preview():
    data = request.get_json(silent=True) or {}
    guild, ai_cog, prompt, reset_server, error_response = _get_build_request_context(data)
    if error_response:
        return error_response

    variation_hint = str(data.get("variationHint", "")).strip()

    try:
        setup_plan = _run_on_bot_loop(ai_cog.generate_build_plan(prompt, variation_hint))
    except google_exceptions.ResourceExhausted:
        return (
            jsonify(
                {
                    "error": (
                        "The AI service is currently rate-limited. "
                        "Please wait 60 seconds and try again."
                    )
                }
            ),
            429,
        )
    except google_exceptions.GoogleAPICallError as e:
        return (
            jsonify(
                {
                    "error": f"AI service returned an error: {getattr(e, 'message', str(e))}"
                }
            ),
            502,
        )
    except ValueError as e:
        return jsonify({"error": str(e)}), 400
    except Exception:
        log.exception("Failed to generate build preview for guild %s", guild.id)
        return jsonify({"error": "Failed to generate a server preview."}), 500

    return jsonify(
        {
            "message": "Preview generated successfully.",
            "prompt": prompt,
            "resetServer": reset_server,
            "setupPlan": setup_plan,
            "preview": _serialize_build_preview(setup_plan),
        }
    )


@limiter.limit("10 per minute")
@app.route("/api/buildserver/execute", methods=["POST"])
def build_server_execute():
    data = request.get_json(silent=True) or {}
    guild, ai_cog, prompt, reset_server, error_response = _get_build_request_context(data)
    if error_response:
        return error_response

    setup_plan = data.get("setupPlan")
    if not _is_valid_setup_plan(setup_plan):
        return jsonify({"error": "Invalid build preview payload"}), 400

    asyncio.run_coroutine_threadsafe(
        ai_cog.execute_api_build_plan(guild, setup_plan, reset_server, prompt),
        app.bot.loop,
    )
    return jsonify({"message": "Approved build sent successfully!"}), 202


@limiter.limit("5 per minute")
@app.route("/api/buildserver", methods=["POST"])
def build_server():
    data = request.get_json(silent=True) or {}
    guild, ai_cog, prompt, reset_server, error_response = _get_build_request_context(data)
    if error_response:
        return error_response

    asyncio.run_coroutine_threadsafe(
        ai_cog.handle_api_build_request(guild, prompt, reset_server),
        app.bot.loop,
    )
    return jsonify({"message": "Build command sent successfully!"})


@limiter.limit("5 per minute")
@app.route("/api/serveredit", methods=["POST"])
def server_edit():
    data = request.get_json(silent=True) or {}
    guild_id_raw = data.get("guildId", "")
    if not str(guild_id_raw).isdigit():
        return jsonify({"error": "Invalid guild ID"}), 400

    prompt = sanitize_prompt(data.get("prompt", ""))
    if not prompt:
        return jsonify({"error": "Prompt is required"}), 400

    guild = app.bot.get_guild(int(guild_id_raw))
    if not guild:
        return jsonify({"error": "Guild not found"}), 404

    edit_cog = app.bot.get_cog("AIEditCommands")
    if not edit_cog:
        return jsonify({"error": "AIEditCommands cog not loaded"}), 500

    feedback_channel = None
    for channel in guild.text_channels:
        if channel.permissions_for(guild.me).send_messages:
            feedback_channel = channel
            break

    if not feedback_channel:
        log.error("No channel found to send server edit feedback for guild %s", guild.id)
        return jsonify({"error": "No channel found to send feedback"}), 500

    asyncio.run_coroutine_threadsafe(
        edit_cog.handle_api_edit_request(guild, feedback_channel, prompt),
        app.bot.loop,
    )
    return jsonify({"message": "Server edit command sent successfully!"})
