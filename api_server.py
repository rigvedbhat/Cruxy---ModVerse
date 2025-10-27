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

    @app.route('/api/guilds/<int:guild_id>/info', methods=['GET'])
    def get_guild_info(guild_id):
        guild = app.bot.get_guild(guild_id)
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404

        info = {
            'member_count': guild.member_count,
            'premium_tier': guild.premium_tier,
            'premium_subscription_count': guild.premium_subscription_count,
            'channels': len(guild.text_channels) + len(guild.voice_channels),
            'roles': len(guild.roles),
        }
        return jsonify(info)

    @app.route('/api/automod_settings/<int:guild_id>', methods=['GET', 'POST'])
    async def automod_settings(guild_id):
        db = g.db
        if request.method == 'POST':
            data = request.json
            await db.set_automod_settings(
                guild_id,
                data.get('profanityFilter'),
                data.get('warningLimit'),
                data.get('limitAction')
            )
            return jsonify({'message': 'Settings updated successfully'})
        else:
            settings = await db.get_automod_settings(guild_id)
            return jsonify(settings)

    @app.route('/api/buildserver', methods=['POST'])
    def build_server():
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

        # Schedule the coroutine to run on the bot's event loop
        asyncio.run_coroutine_threadsafe(
            ai_cog.handle_api_build_request(guild, prompt, reset_server),
            app.bot.loop
        )
        
        return jsonify({'message': 'Build command sent successfully!'})
        
    @app.route('/api/serveredit', methods=['POST'])
    def server_edit():
        data = request.json
        guild_id = data.get('guildId')
        prompt = data.get('prompt')

        guild = app.bot.get_guild(int(guild_id))
        if not guild:
            return jsonify({'error': 'Guild not found'}), 404
        
        edit_cog = app.bot.get_cog('AIEditCommands')
        if not edit_cog:
            return jsonify({'error': 'AIEditCommands cog not loaded'}), 500
        
        # Find a channel to post the results to
        feedback_channel = None
        for channel in guild.text_channels:
            if channel.permissions_for(guild.me).send_messages:
                feedback_channel = channel
                break
        
        if not feedback_channel:
            return jsonify({'error': 'No channel found to send feedback'}), 500

        # Schedule the coroutine to run on the bot's event loop
        asyncio.run_coroutine_threadsafe(
            edit_cog.handle_api_edit_request(guild, feedback_channel, prompt),
            app.bot.loop
        )
        
        return jsonify({'message': 'Server edit command sent successfully!'})