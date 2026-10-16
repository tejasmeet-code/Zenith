import discord
from discord.ext import commands
from core import Cog, Context, zyrox
from utils.Tools import *
import aiosqlite
import random
import string
import datetime

SUPPORT_SERVER_ID = 1554479885760856076
APPROVAL_CHANNEL_ID = 1560600589237358692

class BotStaff(Cog):
    def __init__(self, bot: zyrox):
        self.bot = bot
        self.db_path = 'bot/db/staff.db'
        self.init_db()

    def init_db(self):
        import os
        os.makedirs('bot/db', exist_ok=True)
        import sqlite3
        conn = sqlite3.connect(self.db_path)
        c = conn.cursor()
        c.execute('''CREATE TABLE IF NOT EXISTS staff_members (
            user_id TEXT PRIMARY KEY,
            role TEXT,
            code TEXT,
            expires_at TEXT,
            status TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS premium_codes (
            code TEXT PRIMARY KEY,
            tier TEXT,
            duration_days INTEGER,
            redeemed INTEGER DEFAULT 0
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS guild_premium (
            guild_id TEXT PRIMARY KEY,
            tier TEXT,
            expires_at TEXT
        )''')
        conn.commit()
        conn.close()

    @commands.group(name='botstaff', aliases=['staff'], invoke_without_subcommand=True)
    async def botstaff(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @botstaff.command(name='appoint')
    async def staff_appoint(self, ctx: Context, member: discord.Member, role: str, duration_days: int = 30):
        if not (ctx.author.id in self.bot.owner_ids or str(ctx.author.id) == '1181221352393420856'):
            await ctx.reply('❌ You do not have permission to appoint staff.')
            return
        code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expires = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat()
        
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO staff_members (user_id, role, code, expires_at, status) VALUES (?, ?, ?, ?, ?)',
                             (str(member.id), role.lower(), code, expires, 'pending'))
            await db.commit()

        try:
            embed = discord.Embed(
                title='🛡️ Staff Appointment & Contract',
                description=f'You have been appointed as **{role.upper()}** for Zenith Bot!\n\n'
                            f'To activate your staff status and benefits, please join our [Support Server](https://discord.gg/q4ybG2DUay) and run the following command:\n\n'
                            f'```.staffjoin {code}```\n\n'
                            f'Your contract duration is **{duration_days} days**.',
                color=0x00FF00
            )
            await member.send(embed=embed)
            await ctx.reply(f'✅ Successfully appointed {member.mention} as {role}. Appointment DM sent with code.')
        except Exception as e:
            await ctx.reply(f'⚠️ Appointed in database, but failed to send DM: {e}. Code is `{code}`')

    @commands.command(name='staffjoin')
    async def staff_join(self, ctx: Context, code: str):
        if ctx.guild.id != SUPPORT_SERVER_ID:
            await ctx.reply(f'❌ Please run this command in the official support server: https://discord.gg/q4ybG2DUay', delete_after=10)
            return
        
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT user_id, role, expires_at, status FROM staff_members WHERE code = ?', (code,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await ctx.reply('❌ Invalid staff code.', delete_after=8)
                    return
                user_id, role, expires_at, status = row
                if str(ctx.author.id) != user_id:
                    await ctx.reply('❌ This code does not belong to you.', delete_after=8)
                    return
                
                await db.execute('UPDATE staff_members SET status = ? WHERE code = ?', ('active', code))
                await db.commit()

        await ctx.reply(f'🎉 **Congratulations {ctx.author.mention}!** Your staff status (`{role.upper()}`) is now active with global benefits!', delete_after=15)

    @commands.command(name='contractrenew')
    async def contract_renew(self, ctx: Context):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT role, expires_at FROM staff_members WHERE user_id = ?', (str(ctx.author.id),)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await ctx.reply('❌ You are not registered as a staff member.', delete_after=8)
                    return
                role, expires_at = row

        channel = self.bot.get_channel(APPROVAL_CHANNEL_ID)
        if not channel:
            await ctx.reply('❌ Approval channel not found. Please contact the founder.', delete_after=8)
            return

        view = RenewalApprovalView(ctx.author.id, role)
        embed = discord.Embed(
            title='📜 Staff Contract Renewal Request',
            description=f'Staff Member: {ctx.author.mention} (`{ctx.author.id}`)\nRole: **{role.upper()}**\nCurrent Expiry: `{expires_at}`',
            color=0xFFA500
        )
        await channel.send(embed=embed, view=view)
        await ctx.reply('📨 Contract renewal request sent to upper management for approval!', delete_after=10)

class RenewalApprovalView(discord.ui.View):
    def __init__(self, user_id: int, role: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.role = role

    @discord.ui.button(label='Approve Renewal', style=discord.ButtonStyle.green, custom_id='staff_renew_approve')
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.id in [1181221352393420856, 870179991462236170]):
            await interaction.response.send_message('❌ Only founders/owners can approve renewals.', ephemeral=True)
            return
        
        new_expires = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
        new_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        
        async with aiosqlite.connect('bot/db/staff.db') as db:
            await db.execute('UPDATE staff_members SET expires_at = ?, code = ?, status = ? WHERE user_id = ?',
                             (new_expires, new_code, 'active', str(self.user_id)))
            await db.commit()

        try:
            user = await interaction.client.fetch_user(self.user_id)
            await user.send(f'✅ Your staff contract has been renewed for 30 days! Your new activation code is: `{new_code}`')
        except Exception:
            pass

        await interaction.response.edit_message(content=f'✅ Renewal approved by {interaction.user.mention}. New code generated.', view=None)

    @discord.ui.button(label='Deny Renewal', style=discord.ButtonStyle.red, custom_id='staff_renew_deny')
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.id in [1181221352393420856, 870179991462236170]):
            await interaction.response.send_message('❌ Only founders/owners can deny renewals.', ephemeral=True)
            return
        await interaction.response.edit_message(content=f'❌ Renewal denied by {interaction.user.mention}.', view=None)

def setup(bot):
    bot.add_cog(BotStaff(bot))
