import discord
from discord.ext import commands, tasks
from core import Cog, Context, zyrox
from utils.Tools import *
import aiosqlite
import random
import string
import datetime
from typing import Optional

SUPPORT_SERVER_ID = 1554479885760856076
APPROVAL_CHANNEL_ID = 1560600589237358692
FOUNDER_ID = 1181221352393420856

async def is_bot_staff_or_founder(ctx: Context) -> bool:
    if ctx.author.id == FOUNDER_ID or ctx.author.id in ctx.bot.owner_ids:
        return True
    try:
        async with aiosqlite.connect('bot/db/staff.db') as db:
            async with db.execute('SELECT role, status, expires_at FROM staff_members WHERE user_id = ?', (str(ctx.author.id),)) as cursor:
                row = await cursor.fetchone()
                if row and row[1] == 'active':
                    return True
    except Exception:
        pass
    return False

async def is_guild_premium(guild_id: int) -> bool:
    if guild_id == SUPPORT_SERVER_ID:
        return True
    try:
        async with aiosqlite.connect('bot/db/staff.db') as db:
            async with db.execute('SELECT tier, expires_at FROM guild_premium WHERE guild_id = ?', (str(guild_id),)) as cursor:
                row = await cursor.fetchone()
                if row:
                    tier, expires_at = row
                    if tier == 'lifetime':
                        return True
                    if datetime.datetime.fromisoformat(expires_at) > datetime.datetime.utcnow():
                        return True
    except Exception:
        pass
    return False

class StaffHelpSelect(discord.ui.Select):
    def __init__(self):
        options = [
            discord.SelectOption(label='Staff & Contract System', description='Appoint, join, renew and manage staff contracts', emoji='📜', value='staff_contract'),
            discord.SelectOption(label='Premium Management', description='Generate, redeem, grant, revoke premium codes & 24/7', emoji='💎', value='premium'),
            discord.SelectOption(label='Owner & Server Control', description='Mutuals, leaveserver, getinvite, reload, sync', emoji='👑', value='owner_control'),
            discord.SelectOption(label='Global Moderation & Blacklist', description='Global bans, unbans, guild bans, blacklist management', emoji='🛡️', value='global_mod'),
            discord.SelectOption(label='No-Prefix & Badges', description='No-prefix system, auto-np, badge management', emoji='⚡', value='np_badges'),
        ]
        super().__init__(placeholder='Select a Staff/Owner Command Category...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        cat = self.values[0]
        if cat == 'staff_contract':
            embed = discord.Embed(
                title='📜 Staff & Contract Commands',
                description=(
                    '• `.staff appoint <member> <role> [days]` - Appoints a staff member and DMs single-use contract activation code\n'
                    '• `.staff remove <member>` - Revokes staff member status\n'
                    '• `.staff list` - Lists all currently active and pending staff\n'
                    '• `.staffjoin <code>` - Must be run in [Support Server](https://discord.gg/q4ybG2DUay) to activate contract\n'
                    '• `.contractrenew` - Requests contract renewal and notifies approval channel in support server'
                ),
                color=0x2b2d31
            )
        elif cat == 'premium':
            embed = discord.Embed(
                title='💎 Premium Management Commands',
                description=(
                    '• `.premium gen <tier> <duration_days|lifetime>` - Generates a redeemable premium key\n'
                    '• `.premium redeem <code>` - Redeems premium code for current guild\n'
                    '• `.premium add <guild_id> <tier> <days|lifetime>` - Directly grants premium to a guild\n'
                    '• `.premium remove <guild_id>` - Revokes premium from a guild\n'
                    '• `.premium check [guild_id]` - Checks premium status and expiry of a guild\n'
                    '• `.premium list` - Lists all guilds with active premium\n'
                    '• `.247` - Toggles 24/7 music voice channel persistence mode'
                ),
                color=0x2b2d31
            )
        elif cat == 'owner_control':
            embed = discord.Embed(
                title='👑 Owner & Server Control Commands',
                description=(
                    '• `.reload` - Restarts and reloads the bot client\n'
                    '• `.sync` - Syncs database tables and command trees\n'
                    '• `.mutuals <user>` - Shows all mutual servers shared with a user\n'
                    '• `.getinvite <guild_id>` - Generates an instant invite link to a guild\n'
                    '• `.leaveguild <guild_id>` - Forces the bot to leave a specified guild\n'
                    '• `.guildinfo <guild_id>` - Inspects detailed statistics of a guild\n'
                    '• `.owners` - Displays all configured bot owners'
                ),
                color=0x2b2d31
            )
        elif cat == 'global_mod':
            embed = discord.Embed(
                title='🛡️ Global Moderation & Blacklist Commands',
                description=(
                    '• `.ownerban <user> [reason]` - Globally bans a user across mutual guilds\n'
                    '• `.ownerunban <user>` - Lifts global ban on a user\n'
                    '• `.guildban <guild_id>` - Globally blacklists and bans a guild\n'
                    '• `.guildunban <guild_id>` - Unbans a blacklisted guild\n'
                    '• `.blacklist add/remove <user>` - Adds or removes user from global blacklist\n'
                    '• `.block add/remove <guild>` - Blocks guild from using bot'
                ),
                color=0x2b2d31
            )
        elif cat == 'np_badges':
            embed = discord.Embed(
                title='⚡ No-Prefix & Badge Commands',
                description=(
                    '• `.np add <user>` - Grants no-prefix mode to a user\n'
                    '• `.np remove <user>` - Revokes no-prefix mode from a user\n'
                    '• `.np list` - Lists all no-prefix users\n'
                    '• `.autonp add/remove <guild>` - Toggles auto-np for boosters in partner guilds\n'
                    '• `.badge add <user> <badge>` - Awards custom badge to a user profile\n'
                    '• `.badge remove <user> <badge>` - Removes badge from a user profile'
                ),
                color=0x2b2d31
            )
        embed.set_footer(text='Zenith Staff Panel • Authorized Personnel Only', icon_url=interaction.client.user.avatar.url if interaction.client.user.avatar else None)
        await interaction.response.edit_message(embed=embed, view=self.view)

class StaffHelpView(discord.ui.View):
    def __init__(self, ctx):
        super().__init__(timeout=180)
        self.ctx = ctx
        self.add_item(StaffHelpSelect())

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if interaction.user.id != self.ctx.author.id:
            await interaction.response.send_message('❌ This panel is not for you.', ephemeral=True)
            return False
        return True

class StaffAndPremium(Cog):
    def __init__(self, bot: zyrox):
        self.bot = bot
        self.db_path = 'bot/db/staff.db'
        self.init_db()
        self.contract_expiry_task.start()

    def cog_unload(self):
        self.contract_expiry_task.cancel()

    def init_db(self):
        import sqlite3, os
        os.makedirs('bot/db', exist_ok=True)
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
            redeemed INTEGER DEFAULT 0,
            redeemed_by TEXT,
            redeemed_guild TEXT,
            created_at TEXT
        )''')
        c.execute('''CREATE TABLE IF NOT EXISTS guild_premium (
            guild_id TEXT PRIMARY KEY,
            tier TEXT,
            expires_at TEXT,
            granted_by TEXT
        )''')
        conn.commit()
        conn.close()

    @tasks.loop(hours=6)
    async def contract_expiry_task(self):
        try:
            now = datetime.datetime.utcnow().isoformat()
            async with aiosqlite.connect(self.db_path) as db:
                async with db.execute('SELECT user_id, role FROM staff_members WHERE status = ? AND expires_at < ?', ('active', now)) as cursor:
                    rows = await cursor.fetchall()
                    for user_id, role in rows:
                        await db.execute('UPDATE staff_members SET status = ? WHERE user_id = ?', ('expired', user_id))
                        await db.commit()
                        try:
                            user = await self.bot.fetch_user(int(user_id))
                            if user:
                                await user.send(f'⚠️ **Your Zenith Bot Staff contract ({role.upper()}) has expired.**\\nYour global staff perks have been suspended. Use `.contractrenew` to request renewal.')
                        except Exception:
                            pass
        except Exception as e:
            print(f'Contract expiry check error: {e}')

    @contract_expiry_task.before_loop
    async def before_expiry(self):
        await self.bot.wait_until_ready()

    # --- STAFF COMMANDS ---
    @commands.group(name='botstaff', aliases=['staff'], invoke_without_subcommand=True)
    async def botstaff(self, ctx: Context):
        await ctx.send_help(ctx.command)

    @botstaff.command(name='appoint', help='Appoint a staff member and send contract onboarding code.')
    async def staff_appoint(self, ctx: Context, member: discord.Member, role: str, duration_days: int = 30):
        if not (ctx.author.id == FOUNDER_ID or ctx.author.id in self.bot.owner_ids):
            await ctx.reply('❌ Only Founder and Owners can appoint staff.')
            return

        role_clean = role.lower()
        if role_clean not in ['owner', 'co-owner', 'admin', 'moderator', 'staff']:
            await ctx.reply('❌ Invalid role tier. Options: `owner`, `co-owner`, `admin`, `moderator`, `staff`.')
            return

        code = 'STAFF-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))
        expires = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO staff_members (user_id, role, code, expires_at, status) VALUES (?, ?, ?, ?, ?)',
                             (str(member.id), role_clean, code, expires, 'pending'))
            await db.commit()

        try:
            embed = discord.Embed(
                title='🛡️ Zenith Bot Staff Appointment & Contract',
                description=(
                    f'Congratulations! You have been appointed as **{role_clean.upper()}** for Zenith Bot.\\n\\n'
                    f'**To activate your staff status & global perks:**\\n'
                    f'1. Join our [Support Server](https://discord.gg/q4ybG2DUay)\\n'
                    f'2. Run the command: `.staffjoin {code}`\\n\\n'
                    f'**Contract Term:** {duration_days} Days\\n'
                    f'**Expires:** `{expires}`'
                ),
                color=0x00FF00
            )
            await member.send(embed=embed)
            await ctx.reply(f'✅ Appointed {member.mention} as `{role_clean.upper()}` ({duration_days} days). Activation code sent via DM.')
        except Exception as e:
            await ctx.reply(f'⚠️ Appointed in database, but DM failed: {e}. Code is `{code}`')

    @botstaff.command(name='remove', help='Remove a staff member.')
    async def staff_remove(self, ctx: Context, member: discord.User):
        if not (ctx.author.id == FOUNDER_ID or ctx.author.id in self.bot.owner_ids):
            await ctx.reply('❌ Only Founder and Owners can remove staff.')
            return
        if member.id == FOUNDER_ID:
            await ctx.reply('❌ The Founder is immutable and cannot be removed.')
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM staff_members WHERE user_id = ?', (str(member.id),))
            await db.commit()
        await ctx.reply(f'✅ Removed {member.mention} from staff.')

    @botstaff.command(name='list', help='List all registered staff members.')
    async def staff_list(self, ctx: Context):
        if not await is_bot_staff_or_founder(ctx):
            await ctx.reply('❌ You do not have permission to view this.')
            return

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT user_id, role, expires_at, status FROM staff_members') as cursor:
                rows = await cursor.fetchall()

        if not rows:
            await ctx.reply('ℹ️ No appointed staff members found.')
            return

        desc = f'👑 **Founder:** <@{FOUNDER_ID}> (`{FOUNDER_ID}`) - [IMMUTABLE]\\n\\n'
        for uid, role, exp, status in rows:
            icon = '🟢' if status == 'active' else ('🟡' if status == 'pending' else '🔴')
            desc += f'{icon} <@{uid}> (`{uid}`) - **{role.upper()}** [{status.upper()}] (Expires: `{exp[:10]}`)\\n'

        embed = discord.Embed(title='🛡️ Zenith Bot Staff Directory', description=desc, color=0x2b2d31)
        await ctx.reply(embed=embed)

    @commands.command(name='staffjoin', help='Activate your staff contract inside the official support server.')
    async def staff_join(self, ctx: Context, code: str):
        if not ctx.guild or ctx.guild.id != SUPPORT_SERVER_ID:
            await ctx.reply(f'❌ This command can ONLY be executed inside the official [Support Server](https://discord.gg/q4ybG2DUay).', delete_after=10)
            return

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT user_id, role, expires_at, status FROM staff_members WHERE code = ?', (code,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await ctx.reply('❌ Invalid staff activation code.', delete_after=8)
                    return
                user_id, role, expires_at, status = row
                if str(ctx.author.id) != user_id:
                    await ctx.reply('❌ This code does not belong to you.', delete_after=8)
                    return
                if status == 'active':
                    await ctx.reply('ℹ️ Your contract is already active.', delete_after=8)
                    return

                await db.execute('UPDATE staff_members SET status = ? WHERE code = ?', ('active', code))
                await db.commit()

        embed = discord.Embed(
            title='🎉 Staff Contract Activated!',
            description=(
                f'Welcome to the Zenith Staff Team, {ctx.author.mention}!\\n\\n'
                f'• **Role:** `{role.upper()}`\\n'
                f'• **Expires At:** `{expires_at}`\\n'
                f'• **Activated Perks:** Global Whitelist, Anti-Nuke Bypass, Global Moderation Powers & Staff Panel Access.\\n\\n'
                f'Use `.staffhelp` to view all available commands.'
            ),
            color=0x00FF00
        )
        await ctx.reply(embed=embed)

    @commands.command(name='contractrenew', help='Request a contract renewal from upper management.')
    async def contract_renew(self, ctx: Context):
        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT role, expires_at, status FROM staff_members WHERE user_id = ?', (str(ctx.author.id),)) as cursor:
                row = await cursor.fetchone()
                if not row and ctx.author.id != FOUNDER_ID:
                    await ctx.reply('❌ You do not have an active or expired staff record to renew.', delete_after=8)
                    return
                role = row[0] if row else 'founder'
                expires_at = row[1] if row else 'lifetime'

        channel = self.bot.get_channel(APPROVAL_CHANNEL_ID)
        if not channel:
            await ctx.reply('❌ Approval channel not found. Please contact the Founder directly.', delete_after=8)
            return

        view = RenewalApprovalView(ctx.author.id, role)
        embed = discord.Embed(
            title='📜 Staff Contract Renewal Request',
            description=(
                f'**Staff Member:** {ctx.author.mention} (`{ctx.author.id}`)\\n'
                f'**Role Tier:** `{role.upper()}`\\n'
                f'**Last Expiry:** `{expires_at}`\\n\\n'
                f'Click below to approve for 30 days or deny.'
            ),
            color=0xFFA500
        )
        await channel.send(embed=embed, view=view)
        await ctx.reply('📨 Your contract renewal request has been submitted to upper management for review!', delete_after=10)

    # --- PREMIUM COMMANDS ---
    @commands.group(name='premium', invoke_without_subcommand=True)
    async def premium_grp(self, ctx: Context):
        embed = discord.Embed(
            title='💎 Zenith Premium System',
            description=(
                '• `.premium redeem <code>` - Redeem a premium code for this server\\n'
                '• `.premium check [guild_id]` - Check premium status and expiry\\n'
                '• `.premium gen <tier> <duration_days|lifetime>` - (Staff) Generate code\\n'
                '• `.premium add <guild_id> <tier> <duration_days|lifetime>` - (Staff) Grant premium\\n'
                '• `.premium remove <guild_id>` - (Staff) Revoke premium\\n'
                '• `.premium list` - (Staff) List all premium guilds'
            ),
            color=0x2b2d31
        )
        await ctx.reply(embed=embed)

    @premium_grp.command(name='gen', aliases=['generate'])
    async def premium_gen(self, ctx: Context, tier: str = 'pro', duration: str = '30'):
        if not await is_bot_staff_or_founder(ctx):
            await ctx.reply('❌ You do not have permission to generate premium codes.')
            return

        tier_clean = tier.lower()
        if tier_clean not in ['pro', 'vip', 'lifetime']:
            tier_clean = 'pro'

        duration_days = 9999 if duration.lower() == 'lifetime' or tier_clean == 'lifetime' else (int(duration) if duration.isdigit() else 30)
        code = 'ZENITH-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=10))
        now = datetime.datetime.utcnow().isoformat()

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT INTO premium_codes (code, tier, duration_days, redeemed, created_at) VALUES (?, ?, ?, 0, ?)',
                             (code, tier_clean, duration_days, now))
            await db.commit()

        embed = discord.Embed(
            title='💎 Premium Code Generated',
            description=(
                f'**Code:** `{code}`\\n'
                f'**Tier:** `{tier_clean.upper()}`\\n'
                f'**Duration:** `{duration_days if duration_days != 9999 else "Lifetime"}` Days\\n\\n'
                f'Redeem with: `.premium redeem {code}`'
            ),
            color=0x00FF00
        )
        await ctx.reply(embed=embed)

    @premium_grp.command(name='redeem')
    async def premium_redeem(self, ctx: Context, code: str):
        if not ctx.guild:
            await ctx.reply('❌ This command can only be used in a server.')
            return
        if not (ctx.author.guild_permissions.administrator or ctx.author.id == ctx.guild.owner_id or await is_bot_staff_or_founder(ctx)):
            await ctx.reply('❌ You must be a server administrator or bot staff to redeem premium.')
            return

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT tier, duration_days, redeemed FROM premium_codes WHERE code = ?', (code,)) as cursor:
                row = await cursor.fetchone()
                if not row:
                    await ctx.reply('❌ Invalid premium code.')
                    return
                tier, duration_days, redeemed = row
                if redeemed == 1:
                    await ctx.reply('❌ This premium code has already been redeemed.')
                    return

                expires = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat() if duration_days != 9999 else 'lifetime'
                await db.execute('INSERT OR REPLACE INTO guild_premium (guild_id, tier, expires_at, granted_by) VALUES (?, ?, ?, ?)',
                                 (str(ctx.guild.id), tier, expires, str(ctx.author.id)))
                await db.execute('UPDATE premium_codes SET redeemed = 1, redeemed_by = ?, redeemed_guild = ? WHERE code = ?',
                                 (str(ctx.author.id), str(ctx.guild.id), code))
                await db.commit()

        embed = discord.Embed(
            title='💎 Premium Activated!',
            description=(
                f'**Server:** {ctx.guild.name}\\n'
                f'**Tier:** `{tier.upper()}`\\n'
                f'**Expires At:** `{expires if expires == "lifetime" else expires[:10]}`\\n\\n'
                f'**Unlocked Perks:**\\n'
                f'• 24/7 Voice Channel Persistence (`.247`)\\n'
                f'• Advanced Multi-Panels (Up to 6 multi-panels & 15 standard panels)\\n'
                f'• Maximum ticket support hours configurations'
            ),
            color=0x00FF00
        )
        await ctx.reply(embed=embed)

    @premium_grp.command(name='add', aliases=['grant'])
    async def premium_add(self, ctx: Context, guild_id: int, tier: str = 'pro', duration: str = '30'):
        if not await is_bot_staff_or_founder(ctx):
            await ctx.reply('❌ You do not have permission to grant premium.')
            return

        tier_clean = tier.lower()
        duration_days = 9999 if duration.lower() == 'lifetime' or tier_clean == 'lifetime' else (int(duration) if duration.isdigit() else 30)
        expires = (datetime.datetime.utcnow() + datetime.timedelta(days=duration_days)).isoformat() if duration_days != 9999 else 'lifetime'

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('INSERT OR REPLACE INTO guild_premium (guild_id, tier, expires_at, granted_by) VALUES (?, ?, ?, ?)',
                             (str(guild_id), tier_clean, expires, str(ctx.author.id)))
            await db.commit()

        await ctx.reply(f'✅ Granted `{tier_clean.upper()}` premium to Guild `{guild_id}` until `{expires[:10] if expires != "lifetime" else "Lifetime"}`.')

    @premium_grp.command(name='remove', aliases=['revoke'])
    async def premium_remove(self, ctx: Context, guild_id: int):
        if not await is_bot_staff_or_founder(ctx):
            await ctx.reply('❌ You do not have permission to revoke premium.')
            return
        if guild_id == SUPPORT_SERVER_ID:
            await ctx.reply('❌ The official support server has permanent Lifetime Premium.')
            return

        async with aiosqlite.connect(self.db_path) as db:
            await db.execute('DELETE FROM guild_premium WHERE guild_id = ?', (str(guild_id),))
            await db.commit()
        await ctx.reply(f'✅ Revoked premium status from Guild `{guild_id}`.')

    @premium_grp.command(name='check')
    async def premium_check(self, ctx: Context, guild_id: Optional[int] = None):
        target_id = guild_id or (ctx.guild.id if ctx.guild else None)
        if not target_id:
            await ctx.reply('❌ Specify a guild ID or use in a server.')
            return

        if target_id == SUPPORT_SERVER_ID:
            embed = discord.Embed(
                title='💎 Premium Status: Active',
                description=f'**Guild ID:** `{target_id}`\\n**Tier:** `LIFETIME (OFFICIAL SUPPORT SERVER)`\\n**Expires:** Never',
                color=0x00FF00
            )
            await ctx.reply(embed=embed)
            return

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT tier, expires_at, granted_by FROM guild_premium WHERE guild_id = ?', (str(target_id),)) as cursor:
                row = await cursor.fetchone()

        if not row:
            embed = discord.Embed(
                title='💎 Premium Status: Inactive',
                description=f'Guild `{target_id}` does not currently have active premium.\\nUpgrade using `.premium redeem <code>`.',
                color=0xFF0000
            )
        else:
            tier, expires_at, granted_by = row
            embed = discord.Embed(
                title='💎 Premium Status: Active',
                description=f'**Guild ID:** `{target_id}`\\n**Tier:** `{tier.upper()}`\\n**Expires At:** `{expires_at[:10] if expires_at != "lifetime" else "Lifetime"}`',
                color=0x00FF00
            )
        await ctx.reply(embed=embed)

    @premium_grp.command(name='list')
    async def premium_list(self, ctx: Context):
        if not await is_bot_staff_or_founder(ctx):
            await ctx.reply('❌ You do not have permission to view this.')
            return

        async with aiosqlite.connect(self.db_path) as db:
            async with db.execute('SELECT guild_id, tier, expires_at FROM guild_premium') as cursor:
                rows = await cursor.fetchall()

        desc = f'💎 **Official Support Server:** `{SUPPORT_SERVER_ID}` [LIFETIME]\\n\\n'
        for gid, tier, exp in rows:
            g = self.bot.get_guild(int(gid))
            name = g.name if g else 'Unknown Guild'
            desc += f'• **{name}** (`{gid}`) - `{tier.upper()}` (Expires: `{exp[:10] if exp != "lifetime" else "Lifetime"}`)\\n'

        embed = discord.Embed(title='💎 Zenith Premium Guilds', description=desc, color=0x2b2d31)
        await ctx.reply(embed=embed)

    # --- 24/7 MUSIC MODE ---
    @commands.command(name='247', aliases=['24/7'], help='Toggle 24/7 voice channel persistence.')
    async def toggle_247(self, ctx: Context):
        if not ctx.guild:
            await ctx.reply('❌ This command can only be used in a server.')
            return

        is_premium = await is_guild_premium(ctx.guild.id) or await is_bot_staff_or_founder(ctx)
        if not is_premium:
            await ctx.reply('❌ **24/7 Mode is a Premium Feature.** Upgrade this server via `.premium redeem` to unlock.')
            return

        if not ctx.author.voice:
            await ctx.reply('❌ You must be connected to a voice channel to enable 24/7 mode.')
            return

        async with aiosqlite.connect('bot/db/247.db') as db:
            await db.execute('CREATE TABLE IF NOT EXISTS mode_247 (guild_id TEXT PRIMARY KEY, channel_id TEXT)')
            async with db.execute('SELECT channel_id FROM mode_247 WHERE guild_id = ?', (str(ctx.guild.id),)) as cursor:
                row = await cursor.fetchone()
                if row:
                    await db.execute('DELETE FROM mode_247 WHERE guild_id = ?', (str(ctx.guild.id),))
                    await db.commit()
                    await ctx.reply('🔴 **24/7 Mode has been disabled.** The bot will now disconnect when idle.')
                else:
                    await db.execute('INSERT INTO mode_247 (guild_id, channel_id) VALUES (?, ?)',
                                     (str(ctx.guild.id), str(ctx.author.voice.channel.id)))
                    await db.commit()
                    await ctx.reply(f'🟢 **24/7 Mode has been enabled for {ctx.author.voice.channel.mention}!** The bot will remain connected.')

    # --- STAFFHELP CONSOLIDATION ---
    @commands.command(name='staffhelp', help='Open the consolidated staff and administration panel.')
    async def staff_help(self, ctx: Context):
        if not await is_bot_staff_or_founder(ctx):
            await ctx.reply('❌ **Access Denied.** The `.staffhelp` console is strictly restricted to active Bot Staff and Founders.', delete_after=8)
            return

        embed = discord.Embed(
            title='🛡️ Zenith Staff & Administration Control Panel',
            description=(
                f'Welcome, **{ctx.author}**!\\n\\n'
                f'Select a category from the dropdown menu below to view full syntax and options for all staff, management, and owner commands.'
            ),
            color=0x2b2d31
        )
        embed.set_footer(text='Zenith Multi-System Panel • Select a category below', icon_url=self.bot.user.avatar.url if self.bot.user.avatar else None)
        view = StaffHelpView(ctx)
        await ctx.reply(embed=embed, view=view)

class RenewalApprovalView(discord.ui.View):
    def __init__(self, user_id: int, role: str):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.role = role

    @discord.ui.button(label='Approve Renewal (30d)', style=discord.ButtonStyle.green, custom_id='staff_renew_approve')
    async def approve(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.id == FOUNDER_ID or interaction.user.id in interaction.client.owner_ids):
            await interaction.response.send_message('❌ Only the Founder and Owners can approve renewals.', ephemeral=True)
            return

        new_expires = (datetime.datetime.utcnow() + datetime.timedelta(days=30)).isoformat()
        new_code = 'STAFF-' + ''.join(random.choices(string.ascii_uppercase + string.digits, k=8))

        async with aiosqlite.connect('bot/db/staff.db') as db:
            await db.execute('UPDATE staff_members SET expires_at = ?, code = ?, status = ? WHERE user_id = ?',
                             (new_expires, new_code, 'active', str(self.user_id)))
            await db.commit()

        try:
            user = await interaction.client.fetch_user(self.user_id)
            if user:
                await user.send(f'✅ **Your staff contract has been renewed for 30 days!**\\nYour new activation code is: `{new_code}`\\nRun `.staffjoin {new_code}` in the support server to finalize.')
        except Exception:
            pass

        await interaction.response.edit_message(content=f'✅ Contract renewal approved for <@{self.user_id}> by {interaction.user.mention}.', view=None)

    @discord.ui.button(label='Deny Renewal', style=discord.ButtonStyle.red, custom_id='staff_renew_deny')
    async def deny(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not (interaction.user.id == FOUNDER_ID or interaction.user.id in interaction.client.owner_ids):
            await interaction.response.send_message('❌ Only the Founder and Owners can deny renewals.', ephemeral=True)
            return

        async with aiosqlite.connect('bot/db/staff.db') as db:
            await db.execute('UPDATE staff_members SET status = ? WHERE user_id = ?', ('denied', str(self.user_id)))
            await db.commit()

        try:
            user = await interaction.client.fetch_user(self.user_id)
            if user:
                await user.send('❌ **Your staff contract renewal request was denied by upper management.**')
        except Exception:
            pass

        await interaction.response.edit_message(content=f'❌ Renewal denied for <@{self.user_id}> by {interaction.user.mention}.', view=None)

async def setup(bot: zyrox):
    await bot.add_cog(StaffAndPremium(bot))
