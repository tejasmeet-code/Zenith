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

from __future__ import annotations

from discord.ext import commands
import discord
import functools
from typing import Optional, Any
import asyncio

__all__ = ("Context", )


class Context(commands.Context):

    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs)

    def __repr__(self):
        return "<core.Context>"

    @property
    async def session(self):
        return self.bot.session

    @discord.utils.cached_property
    def replied_reference(self) -> Optional[discord.Message]:
        ref = self.message.reference
        if ref and isinstance(ref.resolved, discord.Message):
            return ref.resolved.to_reference()
        return None

    def with_type(func):

        @functools.wraps(func)
        async def wrapped(self, *args, **kwargs):
            context = args[0] if isinstance(args[0],
                                            commands.Context) else args[1]
            try:
                async with context.typing():
                    await func(*args, **kwargs)
            except discord.Forbidden:  
                await func(*args, **kwargs)

        return wrapped

    async def show_help(self, command: str = None) -> Any:
        cmd = self.bot.get_command('help')
        command = command or self.command.qualified_name
        await self.invoke(cmd, command=command)

    async def send(self,
                   content: Optional[str] = None,
                   **kwargs) -> Optional[discord.Message]:
        if self.guild:
            me = self.guild.me or self.guild.get_member(self.bot.user.id if self.bot and self.bot.user else 0)
            if me and hasattr(self.channel, "permissions_for"):
                try:
                    perms = self.channel.permissions_for(me)
                    if hasattr(perms, "send_messages") and not perms.send_messages:
                        try:
                            await self.author.send("Bot does not have permissions to send messages in that channel.")
                        except Exception:
                            pass
                        return None
                except Exception:
                    pass
        try:
            return await super().send(content, **kwargs)
        except discord.HTTPException as err:
            view = kwargs.get("view")
            embed = kwargs.get("embed")
            if view and not content and not embed:
                title_str = getattr(view, "_title", None) or "Zenith Bot Response"
                desc_str = getattr(view, "_description", None) or ""
                if not desc_str and hasattr(view, "children"):
                    desc_str = getattr(view, "title", str(view))
                fallback_embed = discord.Embed(
                    title=str(title_str),
                    description=str(desc_str) if desc_str else None,
                    color=0x2b2d31
                )
                kwargs_copy = {k: v for k, v in kwargs.items() if k != "view"}
                try:
                    return await super().send(embed=fallback_embed, **kwargs_copy)
                except Exception:
                    pass
            raise err

    async def reply(self,
                    content: Optional[str] = None,
                    **kwargs) -> Optional[discord.Message]:
        if self.guild:
            me = self.guild.me or self.guild.get_member(self.bot.user.id if self.bot and self.bot.user else 0)
            if me and hasattr(self.channel, "permissions_for"):
                try:
                    perms = self.channel.permissions_for(me)
                    if hasattr(perms, "send_messages") and not perms.send_messages:
                        try:
                            await self.author.send("Bot does not have permissions to send messages in that channel.")
                        except Exception:
                            pass
                        return None
                except Exception:
                    pass
        try:
            return await super().reply(content, **kwargs)
        except discord.HTTPException:
            return await self.send(content, **kwargs)

    async def release(self, delay: Optional[int] = None) -> None:
        delay = delay or 0
        await asyncio.sleep(delay)
