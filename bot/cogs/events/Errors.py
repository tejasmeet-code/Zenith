# ╔══════════════════════════════════════════════════════════════════╗
# ║                                                                  ║
# ║   ░█▀▀░█▀█░█▀▄░█▀▀░█░█   ░█▀▄░█▀▀░█░█░█▀▀                     ║
# ║   ░█░░░█░█░█░█░█▀▀░▄▀▄   ░█░█░█▀▀░▀▄▀░▀▀█                     ║
# ║   ░▀▀▀░▀▀▀░▀▀░░▀▀▀░▀░▀   ░▀▀░░▀▀▀░░▀░░▀▀▀                     ║
# ║                                                                  ║
# ║            © 2026 CodeX Devs — All Rights Reserved              ║
# ║                                                                  ║
# ║   discord  ──  https://discord.gg/codexdev                      ║
# ║   youtube  ──  https://youtube.com/@CodeXDevs                   ║
# ║   github   ──  https://github.com/RayExo                        ║
# ║                                                                  ║
# ╚══════════════════════════════════════════════════════════════════╝

import discord
import json
import aiosqlite
from discord.ext import commands
from utils.config import serverLink
from core import zyrox, Cog, Context
from utils.Tools import get_ignore_data

class Errors(Cog):
  def __init__(self, client: zyrox):
    self.client = client

  @commands.Cog.listener()
  async def on_command_error(self, ctx: Context, error):
    if ctx.command is None:
      return
    

    if isinstance(error, commands.CommandNotFound):
      return

    if isinstance(error, commands.MissingRequiredArgument):
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.CheckFailure):
      if ctx.guild:
        try:
          data = await get_ignore_data(ctx.guild.id)
          ch = data.get("channel", set())
          iuser = data.get("user", set())
          cmd = data.get("command", set())
          buser = data.get("bypassuser", set())

          if str(ctx.author.id) in buser:
            return

          if str(ctx.channel.id) in ch:
            await ctx.reply(f"{ctx.author.mention} **This channel is in the ignored list.**", delete_after=8)
            return

          if str(ctx.author.id) in iuser:
            await ctx.reply(f"{ctx.author.mention} **You are set as an ignored user in this guild.**", delete_after=8)
            return

          if ctx.command.name in cmd or any(alias in cmd for alias in ctx.command.aliases):
            await ctx.reply(f"{ctx.author.mention} **This command is ignored in this guild.**", delete_after=8)
            return
        except Exception:
          pass
      await ctx.reply(f"{ctx.author.mention} **You do not have permission or access to execute this command.**", delete_after=8)
      return

    if isinstance(error, commands.NoPrivateMessage):
      embed = discord.Embed(color=0xFF0000, description="You can't use my commands in DMs.")
      embed.set_author(name=ctx.author, icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      embed.set_thumbnail(url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(embed=embed, delete_after=20)
      return

    if isinstance(error, commands.TooManyArguments):
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.CommandOnCooldown):
      embed = discord.Embed(color=0xFF0000, description=f"**{ctx.author.mention} Cooldown active. Try again in {error.retry_after:.1f}s**.")
      embed.set_author(name="Cooldown", icon_url=self.client.user.avatar.url if self.client.user and self.client.user.avatar else None)
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(embed=embed, delete_after=10)
      return

    if isinstance(error, commands.MaxConcurrencyReached):
      embed = discord.Embed(color=0xFF0000, description=f"{ctx.author.mention} This command is already in progress. Please wait for it to finish.")
      embed.set_author(name="Command in Progress", icon_url=self.client.user.avatar.url if self.client.user and self.client.user.avatar else None)
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(embed=embed, delete_after=10)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.MissingPermissions):
      missing = [perm.replace("_", " ").replace("guild", "server").title() for perm in error.missing_permissions]
      fmt = "{}, and {}".format(", ".join(missing[:-1]), missing[-1]) if len(missing) > 2 else " and ".join(missing)
      embed = discord.Embed(color=0xFF0000, description=f"**You need `{fmt}` permission(s) to run `{ctx.command.name}`!**")
      embed.set_author(name="Missing Permissions", icon_url=self.client.user.avatar.url if self.client.user and self.client.user.avatar else None)
      embed.set_footer(text=f"Requested by {ctx.author}", icon_url=ctx.author.avatar.url if ctx.author.avatar else ctx.author.default_avatar.url)
      await ctx.reply(embed=embed, delete_after=7)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.BadArgument):
      await ctx.send_help(ctx.command)
      ctx.command.reset_cooldown(ctx)
      return

    if isinstance(error, commands.BotMissingPermissions):
      missing = ", ".join(error.missing_permissions)
      await ctx.reply(f'**I need `{missing}` permission(s) to execute `{ctx.command.qualified_name}`.**', delete_after=7)
      return

    if isinstance(error, discord.HTTPException):
      print(f"[ERROR] HTTPException in {ctx.command}: {error}")
      try:
        await ctx.reply(f"❌ **HTTP Error:** Failed to process response (`{error.status}`).", delete_after=8)
      except Exception:
        pass
      return

    if isinstance(error, commands.CommandInvokeError):
      orig = getattr(error, 'original', error)
      print(f"[ERROR] CommandInvokeError in {ctx.command}: {error} | Original: {orig}")
      try:
        await ctx.reply(f"⚠️ **Error executing `{ctx.command.name}`:** `{orig}`", delete_after=10)
      except Exception:
        pass
      return

