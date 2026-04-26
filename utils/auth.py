import hmac
import json
import os
import urllib.parse
import urllib.request
from functools import wraps

from flask import jsonify, request, session

DISCORD_CLIENT_ID = os.getenv("DISCORD_CLIENT_ID", "")
DISCORD_CLIENT_SECRET = os.getenv("DISCORD_CLIENT_SECRET", "")
DISCORD_REDIRECT_URI = os.getenv(
    "DISCORD_REDIRECT_URI",
    "http://localhost:5000/auth/callback",
)
DISCORD_API = "https://discord.com/api/v10"


def has_valid_api_key() -> bool:
    provided = request.headers.get("X-API-Key", "")
    expected = os.getenv("API_SECRET_KEY", "")
    if not provided or not expected:
        return False
    return hmac.compare_digest(
        provided.encode("utf-8"),
        expected.encode("utf-8"),
    )


def discord_oauth_url(state: str) -> str:
    params = urllib.parse.urlencode(
        {
            "client_id": DISCORD_CLIENT_ID,
            "redirect_uri": DISCORD_REDIRECT_URI,
            "response_type": "code",
            "scope": "identify guilds",
            "state": state,
        }
    )
    return f"https://discord.com/oauth2/authorize?{params}"


def exchange_code(code: str) -> dict:
    data = urllib.parse.urlencode(
        {
            "client_id": DISCORD_CLIENT_ID,
            "client_secret": DISCORD_CLIENT_SECRET,
            "grant_type": "authorization_code",
            "code": code,
            "redirect_uri": DISCORD_REDIRECT_URI,
        }
    ).encode()
    req = urllib.request.Request(
        f"{DISCORD_API}/oauth2/token",
        data=data,
        headers={"Content-Type": "application/x-www-form-urlencoded"},
        method="POST",
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def get_discord_user(access_token: str) -> dict:
    req = urllib.request.Request(
        f"{DISCORD_API}/users/@me",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def get_discord_guilds(access_token: str) -> list:
    req = urllib.request.Request(
        f"{DISCORD_API}/users/@me/guilds",
        headers={"Authorization": f"Bearer {access_token}"},
    )
    with urllib.request.urlopen(req) as response:
        return json.loads(response.read())


def require_auth(f):
    """Decorator: require a valid Discord OAuth2 session or internal API key."""

    @wraps(f)
    def decorated(*args, **kwargs):
        if session.get("discord_user_id") or has_valid_api_key():
            return f(*args, **kwargs)
        return jsonify({"error": "Unauthorized — please log in"}), 401

    return decorated


def require_guild_admin(f):
    """
    Decorator: require the logged-in user to have ADMINISTRATOR or MANAGE_GUILD
    in the target guild, while still allowing trusted internal API key callers.
    """

    @wraps(f)
    def decorated(*args, **kwargs):
        if has_valid_api_key():
            return f(*args, **kwargs)

        guild_id = (
            kwargs.get("guild_id")
            or request.args.get("guild_id")
            or (request.get_json(silent=True) or {}).get("guildId")
        )
        if not guild_id:
            return jsonify({"error": "guild_id required"}), 400

        user_guilds = session.get("discord_guilds", [])
        for guild in user_guilds:
            if str(guild.get("id")) != str(guild_id):
                continue
            perms = int(guild.get("permissions", guild.get("permissions_new", 0)) or 0)
            if perms & 0x8 or perms & 0x20:
                return f(*args, **kwargs)
            return jsonify({"error": "Insufficient permissions"}), 403

        return jsonify({"error": "Guild not found in your account"}), 403

    return decorated
