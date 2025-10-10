# database.py
import aiosqlite

class PersistentDB:
    def __init__(self, path="bot_data.db"):
        self.path = path
        self.conn = None

    async def connect(self):
        self.conn = await aiosqlite.connect(self.path)
        
        # Table for storing user warnings
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS warnings (
                guild_id INTEGER,
                user_id INTEGER,
                count INTEGER,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        
        # NEW: Table for storing user XP and levels
        await self.conn.execute('''
            CREATE TABLE IF NOT EXISTS user_data (
                guild_id INTEGER,
                user_id INTEGER,
                xp INTEGER DEFAULT 0,
                level INTEGER DEFAULT 0,
                PRIMARY KEY (guild_id, user_id)
            )
        ''')
        
        await self.conn.commit()

    async def close(self):
        if self.conn:
            await self.conn.close()

    # --- Methods for Warnings (existing functionality) ---
    async def get_warnings(self, guild_id, user_id):
        async with self.conn.execute("SELECT count FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return row[0] if row else 0

    async def add_warning(self, guild_id, user_id):
        current = await self.get_warnings(guild_id, user_id)
        if current:
            await self.conn.execute("UPDATE warnings SET count=? WHERE guild_id=? AND user_id=?", (current + 1, guild_id, user_id))
        else:
            await self.conn.execute("INSERT INTO warnings VALUES (?, ?, 1)", (guild_id, user_id))
        await self.conn.commit()

    async def reset_warnings(self, guild_id, user_id):
        await self.conn.execute("DELETE FROM warnings WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()

    # --- NEW: Methods for XP and Levels ---
    async def get_user_data(self, guild_id, user_id):
        async with self.conn.execute("SELECT xp, level FROM user_data WHERE guild_id=? AND user_id=?", (guild_id, user_id)) as cursor:
            row = await cursor.fetchone()
            return {"xp": row[0], "level": row[1]} if row else {"xp": 0, "level": 0}

    async def add_xp(self, guild_id, user_id, xp_to_add):
        user_data = await self.get_user_data(guild_id, user_id)
        new_xp = user_data["xp"] + xp_to_add
        new_level = user_data["level"]
        
        # Check for level up
        required_xp_for_next_level = 100 * (new_level + 1)
        if new_xp >= required_xp_for_next_level:
            new_level += 1
        
        # Insert or update the user's data
        await self.conn.execute(
            "INSERT OR REPLACE INTO user_data (guild_id, user_id, xp, level) VALUES (?, ?, ?, ?)",
            (guild_id, user_id, new_xp, new_level)
        )
        await self.conn.commit()
        return new_level

    async def get_xp_and_level(self, guild_id, user_id):
        data = await self.get_user_data(guild_id, user_id)
        return data["xp"], data["level"]

    async def reset_levels(self, guild_id, user_id):
        await self.conn.execute("UPDATE user_data SET xp=0, level=0 WHERE guild_id=? AND user_id=?", (guild_id, user_id))
        await self.conn.commit()