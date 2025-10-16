from flask import Flask, request, jsonify, g
from flask_cors import CORS
import asyncio
from database import PersistentDB

# Create the Flask app at the top level
app = Flask(__name__)
CORS(app)

def run_api_server(bot):
    # Attach the bot object to the app's context
    app.bot = bot

    @app.before_request
    async def before_request_func():
        g.db = PersistentDB()
        await g.db.connect()

    @app.after_request
    async def after_request_func(response):
        if 'db' in g:
            await g.db.close()
        return response

    @app.route('/api/guilds', methods=['GET'])
    def get_guilds():
        guilds_list = [{
            'id': str(guild.id),
            'name': guild.name,
            'icon': guild.icon.url if guild.icon else None
        } for guild in app.bot.guilds]
        return jsonify(guilds_list)

    @app.route('/api/automod_settings/<int:guild_id>', methods=['GET', 'POST'])
    async def automod_settings(guild_id):
        db = g.db
        if request.method == 'POST':
            data = request.json
            await db.set_automod_settings(
                guild_id,
                data.get('profanityFilter'),
                data.get('warningLimit'),
                data.get('limitAction'),
                data.get('muteDuration')
            )
            return jsonify({'message': 'Settings updated successfully'})
        else:
            settings = await db.get_automod_settings(guild_id)
            return jsonify(settings)

    @app.route('/api/buildserver', methods=['POST'])
    async def build_server():
        data = request.json
        guild_id = data.get('guildId')
        prompt = data.get('prompt')
        reset_server = data.get('resetServer', False)

        guild = app.bot.get_guild(int(guild_id))
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404

        ai_cog = app.bot.get_cog('AICommands')
        if not ai_cog:
            return jsonify({'error': 'AICommands cog not loaded'}), 500

        result = await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            ai_cog.handle_api_build_request(guild, prompt, reset_server), app.bot.loop
        ))
        
        return jsonify(result)
        
    @app.route('/api/serveredit', methods=['POST'])
    async def server_edit():
        data = request.json
        guild_id = data.get('guildId')
        prompt = data.get('prompt')

        guild = app.bot.get_guild(int(guild_id))
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404
        
        edit_cog = app.bot.get_cog('AIEditCommands')
        if not edit_cog:
            return jsonify({'error': 'AIEditCommands cog not loaded'}), 500
        
        result = await asyncio.wrap_future(asyncio.run_coroutine_threadsafe(
            edit_cog.handle_api_edit_request(guild, prompt), app.bot.loop
        ))
        
        return jsonify(result)

    # Note: We don't call app.run() here anymore. The bot.py file will handle it.

