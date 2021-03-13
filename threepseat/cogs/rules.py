"""Cog for enforcing 3pseat rules"""
import asyncio
import discord
import logging
import random

from discord.ext import commands, tasks
from typing import Union, Optional, List

from threepseat.bot import Bot
from threepseat.utils import is_admin, is_emoji, is_booster, is_url
from threepseat.utils import GuildDatabase


logger = logging.getLogger()

F_EMOTE = '\U0001F1EB'


class Rules(commands.Cog):
    """Extension for enforcing guild rules

    This cog enforces a long running meme on our Discord server that
    all messages have to start with '3pseat'. This cog enforces a more
    general version of that concept and tracks the number of infractions
    a user has. If they get too many, they will be kicked.

    Adds the following commands:
      - `?strikes`: aliases `?strikes list`
      - `?strikes list`: list strike count for members
      - `?strikes add @member`: add strike to member
      - `?strikes remove @member`: remove strike from member
    """
    def __init__(
        self,
        bot: Bot,
        database_path: str,
        message_prefix: Optional[Union[str, List[str]]] = None,
        whitelist_prefix: Union[str, List[str]] = [],
        max_offenses: int = 3,
        max_booster_offenses: int = 3,
        allow_deletes: bool = True,
        allow_edits: bool = True,
        allow_wrong_commands: bool = True,
        booster_exception: bool = True,
        invite_after_kick: bool = True,
        freedom_mode_default_time: int = 30,
        freedom_mode_event_prob: float = 0.0029
    ) -> None:
        """Init Rules

        Args:
            bot (Bot): bot object this cog is attached to
            database_path (str): path to file storing database of strikes
            message_prefix (str, list[str]): valid prefixes for messages. If None, no
                message prefix checking is done.
            whitelist_prefix (str, list[str]): messages starting with these prefixes will
                be ignored. Useful for ignoring the command prefixes of
                other bots.
            max_offenses (int): maximum strikes before being kicked
            max_booster_offenses (int): maximum strikes before a booster is kicked
            allow_deletes (bool): if false, the bot will notify the channel if
                a message is deleted
            allow_edits (bool): if false, the bot will notify the channel if
                a message is edited
            allow_wrong_commands (bool): if false, members will be given a strike
                for trying to use invalid commands
            booster_exception (bool): boosters are exempt from rules
            invite_after_kick (bool): send invite link if member is kicked
            freedom_mode_default_time (int): default length in minutes for freedom mode
            freedom_mode_event_prob (float): probability every hour that freedom mode
                is started. No rules are enforced in freedom mode
        """
        self.bot = bot
        if isinstance(message_prefix, str):
            message_prefix = [message_prefix]
        self.message_prefix = message_prefix
        if isinstance(whitelist_prefix, str):
            message_prefix = [whitelist_prefix]
        self.whitelist_prefix = whitelist_prefix
        self.max_offenses = max_offenses
        self.max_booster_offenses = max_booster_offenses
        self.allow_deletes = allow_deletes
        self.allow_edits = allow_edits
        self.allow_wrong_commands = allow_wrong_commands
        self.booster_exception = booster_exception
        self.invite_after_kick = invite_after_kick
        self.freedom_mode_default_time = freedom_mode_default_time
        self.freedom_mode_event_prob = freedom_mode_event_prob

        # List of guild IDs that have freedom mode enabled
        self.freedom_mode_guilds = []

        if self.freedom_mode_event_prob > 1 or self.freedom_mode_event_prob < 0:
            raise ValueError('freedom_mode_event_prob must be in [0,1]')

        if self.message_prefix is not None:
            self.bot.guild_message_prefix = self.message_prefix[0]

        self.db = GuildDatabase(database_path)

        self._freedom_event.start()

    async def list(self, ctx: commands.Context) -> None:
        """List strikes for members in `ctx.guild`

        Args:
            ctx (Context): context from command call
        """
        msg = '{}, here are the strikes:'.format(
            ctx.message.author.mention)
        serverCount = 0
        strikes = self.db.table(ctx.guild)
        if len(strikes) > 0:
            msg += '```'
            for uid in strikes:
                if int(uid) != ctx.guild.id:
                    if strikes[uid] == 0:
                        continue
                    user = ctx.guild.get_member(int(uid))
                    max_offenses = self.get_max_offenses(user)
                    msg = msg + '\n{}: {}/{}'.format(
                        user.name, strikes[uid], max_offenses)
                else:
                    serverCount = strikes[uid]
            msg += '```'
        else:
            msg += ' there are none!\n'
        msg += 'Total offenses to date: {}'.format(serverCount)
        await self.bot.message_guild(msg, ctx.channel)

    async def add(self, ctx: commands.Context, member: discord.Member) -> None:
        """Adds a strike to `member`

        Requires `ctx.message.author` to be a bot admin (not guild admin).

        Args:
            ctx (Context): context from command call
            member (Member): member to add strike to
        """
        if self.bot.is_bot_admin(ctx.message.author):
            await self.add_strike(member, ctx.channel)
        else:
            raise commands.MissingPermissions

    async def remove(self, ctx: commands.Context, member: discord.Member) -> None:
        """Removes a strike from `member`

        Requires `ctx.message.author` to be a bot admin (not guild admin).

        Args:
            ctx (Context): context from command call
            member (Member): member to remove strike from
        """
        if self.bot.is_bot_admin(ctx.message.author):
            self.remove_strike(member)
            msg = 'removed strike for {}. New strike count is {}.'.format(
                member.mention, self.get_strikes(member))
            await self.bot.message_guild(msg, ctx.message.channel)
        else:
            raise commands.MissingPermissions

    def should_ignore(self, message: discord.Message) -> bool:
        """Returns true if the message should be ignored

        Many types of messages are exempt from the message prefix rules
        including: pin messages, member join messages, guild boosters
        if `booster_exception`, messages that start with `whitelist_prefix`,
        and bot commands.

        Args:
            message (Message): message to parse

        Returns:
            `bool`
        """
        if message.guild.id in self.freedom_mode_guilds:
            return True
        if message.type is discord.MessageType.pins_add:
            return True
        if message.type is discord.MessageType.new_member:
            return True
        if self.booster_exception and is_booster(message.author):
            return True
        text = message.content.strip().lower()
        for keyword in self.whitelist_prefix:
            if text.startswith(keyword.lower()):
                return True
        if text.startswith(self.bot.command_prefix):
            return True
        return False

    def is_verified(self, message: discord.Message) -> bool:
        """Verifies a message passes the rules

        A message is verified if it: start with `message_prefix`, is
        just emojis, is a single attachment with no text, is a single
        url with no text, is quoted, or is code.

        Args:
            message (Message): message to parse

        Returns:
            `bool`
        """
        text = message.content.strip().lower()

        # Check if starts with 3pseat, 3pfeet, etc
        if self.message_prefix is not None:
            for keyword in self.message_prefix:
                if text.startswith(keyword):
                    return True
            # Check if just emoji
        if is_emoji(text):
            return True
        # Check if just images
        if text == '' and message.attachments:
            return True
        # Check if single link
        if is_url(text):
            return True
        # Check if quoted message
        if text.startswith('>'):
            return True
        # Check if code
        if text.startswith('```'):
            return True

        return False

    def get_max_offenses(self, member: discord.Member) -> int:
        """Returns the max offenses a member can get

        Args:
            member (Member): member to check max offenses for

        Returns:
            max allowable offenses
        """
        if is_booster(member):
            return self.max_booster_offenses
        return self.max_offenses

    async def check_strikes(
        self,
        member: discord.Member,
        channel: discord.TextChannel,
        guild: discord.Guild
    ) -> None:
        """Handles what to do when user recieves a strike

        If the user has fewer that `self.max_offenses` strikes,
        a warning is sent. Otherwise, the bot attempts to kick
        the user and send them a invite link if
        `self.invite_after_kick`.

        Warning:
            In general, this function should only be called
            by `add_strike()`.

        Args:
            member (Member): member to check strikes of
            channel (Channel): channel to send message in
            guild (Guild): guild to kick user from if needed
        """
        count = self.get_strikes(member)
        max_offenses = self.get_max_offenses(member)

        if count < max_offenses:
            msg = '{}! You\'ve disturbed the spirits ({}/{})'.format(
                  member.mention, count, max_offenses)
            await self.bot.message_guild(msg, channel)
        else:
            self.clear_strikes(member)
            msg = ('That\'s {} strikes, {}. I\'m sorry but your time as come. '
                   'RIP.\n'.format(max_offenses, member.mention))
            success = await self.kick(member, channel, guild, msg)
            if self.invite_after_kick and success:
                msg = ('Sorry we had to kick you. Here is a link to rejoin: '
                       '{link}')
                await self.invite(member, channel, msg)

    async def invite(
        self,
        user: Union[discord.User, discord.Member],
        channel: discord.TextChannel,
        message: str
    ) -> None:
        """Send guild invite link to user

        Args:
            user (Member, User): user to direct message link
            channel (Channel): channel to create invite for
            message (str): optional message to include with invite link
        """
        try:
            link = await channel.create_invite(max_uses=1)
            msg = message.format(link=link)
            await self.bot.message_user(msg, user)
        except Exception as e:
            logger.warning('Failed to send rejoin message to {}.'
                           'Caught exception: {}'.format(user, e))

    async def kick(
        self,
        member: discord.Member,
        channel: discord.TextChannel,
        guild: discord.Guild,
        message: str = None
    ) -> bool:
        """Kick member from guild

        Args:
            member (Member): member to kick
            channel (Channel): channel to send notification messages to
            guild (Guild): guild member belongs to to be kicked from
            message (str): optional message to sent to channel when
                the member is kicked

        Returns:
            `True` if kick was successful
        """
        if is_admin(member):
            if message is None:
                message = ''
            message += ('Failed to kick {}. Your cognizance is highly '
                        'acknowledged.'.format(member.mention))
            await self.bot.message_guild(message, channel)
            return False

        try:
            await guild.kick(member)
        except Exception as e:
            logger.warning('Failed to kick {}. Caught exception: '
                           '{}'.format(member, e))
            return False

        if message is not None:
            message += 'Press F to pay respects.'
            await self.bot.message_guild(message, channel, react=F_EMOTE)
        return True

    async def add_strike(
        self,
        member: discord.Member,
        channel: discord.TextChannel
    ) -> None:
        """Add a strike to the `member` of `guild` in the database

        Calls `check_strikes()`

        Args:
            member (Member): member
            channel (Channel): channel to send message in
        """
        count = self.get_strikes(member)
        self.db.set(member.guild, str(member.id), count + 1)
        server_count = self.get_global_strikes(member.guild)
        self.db.set(member.guild, str(member.guild.id), server_count + 1)
        await self.check_strikes(member, channel, member.guild)

    def clear_strikes(self, member: discord.Member) -> None:
        """Reset strikes for the `member` in the database"""
        self.db.set(member.guild, str(member.id), 0)

    def get_strikes(self, member: discord.Member) -> int:
        """Get strike count for `member`"""
        value = self.db.value(member.guild, str(member.id))
        if value is None:
            return 0
        return value

    def get_global_strikes(self, guild: discord.Guild) -> int:
        """Get global strike count for guild"""
        value = self.db.value(guild, str(guild.id))
        if value is None:
            return 0
        return value

    def remove_strike(self, member: discord.Member) -> None:
        """Remove a strike from the `member` in the database"""
        count = self.get_strikes(member)
        if count > 0:
            self.db.set(member.guild, str(member.id), count - 1)
        server_count = self.get_global_strikes(member.guild)
        if server_count > 0:
            self.db.set(member.guild, str(member.guild.id), server_count + 1)

    async def freedom_start(self, ctx: commands.Context, minutes: float = None) -> None:
        """Start freedom mode

        No rules are enforced in freedom mode. Freedom mode will
        last for `minutes` if specified, otherwise freedom mode will
        last for `self.freedom_mode_default_time`.

        Args:
            ctx (commands.Context): invoking context
            minutes (float): duration of freedom mode
        """
        if not self.bot.is_bot_admin(ctx.message.author):
            raise commands.MissingPermissions

        if ctx.guild.id in self.freedom_mode_guilds:
            await self.bot.message_guild(
                'freedom mode is already enabled', ctx.channel)
            return

        await self._freedom_start(ctx.channel, minutes)

    async def freedom_stop(self, ctx: commands.Context) -> None:
        """Stop freedom mode"""
        if not self.bot.is_bot_admin(ctx.message.author):
            raise commands.MissingPermissions

        if ctx.guild.id not in self.freedom_mode_guilds:
            await self.bot.message_guild(
                'freedom mode is already disabled', ctx.channel)
            return

        await self.bot.message_guild(
            'your freedom has ended', ctx.channel)
        self.freedom_mode_guilds.remove(ctx.guild.id)

    async def _freedom_start(
        self,
        channel: commands.Context,
        minutes: float = None
    ) -> None:
        """Freedom mode start helper"""
        if channel.guild.id in self.freedom_mode_guilds:
            return

        self.freedom_mode_guilds.append(channel.guild.id)
        minutes = self.freedom_mode_default_time if minutes is None else minutes
        minutes = max(minutes, 1 / 60)
        await self.bot.message_guild(
            'starting freedom mode for {} {}'.format(
                int(minutes) if minutes >= 1 else int(minutes * 60),
                'minutes' if minutes >= 1 else 'seconds'),
            channel, react='\U0001F1FA\U0001F1F8')
        await asyncio.sleep(60 * minutes)
        await self.bot.message_guild(
            'your freedom has ended', channel)
        if channel.guild.id in self.freedom_mode_guilds:
            self.freedom_mode_guilds.remove(channel.guild.id)

    @tasks.loop(hours=1)
    async def _freedom_event(self) -> None:
        """Task that randomly starts freedom events"""
        for guild_id in self.db.tables():
            rng = random.uniform(0, 1)
            if rng < self.freedom_mode_event_prob:
                try:
                    guild = self.bot.get_guild(guild_id)
                    channel = guild.text_channels[0]
                except Exception as e:
                    logger.error('{}: unable to get channel in guild {}'.format(e, guild_id))
                await self._freedom_start(channel)

    @commands.Cog.listener()
    async def on_message(self, message: discord.Message) -> None:
        """Called when message is created and sent"""
        if message.author.bot:
            return
        if message.guild is None:
            await self.bot.message_user(
                'Hi there, I cannot reply to direct messages.',
                message.author)
            return

        if self.should_ignore(message):
            return

        if not self.is_verified(message):
            await self.add_strike(message.author, message.channel)

    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Called when message is deleted"""
        if self.allow_deletes or message.author.bot or self.should_ignore(message):
            return
        msg = '{}, where did your message go? It was: \"{}\"'.format(
              message.author.mention, message.clean_content)
        await self.bot.message_guild(msg, message.channel)

    @commands.Cog.listener()
    async def on_message_edit(
        self,
        before: discord.Message,
        after: discord.Message
    ) -> None:
        """Called when message is edited"""
        if self.allow_edits or before.author.bot or self.should_ignore(after):
            return
        # ignore message with embeds because it counts as editing a message
        if after.embeds:
            return
        # ignore message being edited because it was pinned
        if not before.pinned and after.pinned:
            return
        msg = '{}, what did you do to your message? It was: \"{}\"'.format(
              before.author.mention, before.clean_content)
        await self.bot.message_guild(msg, before.channel)

        # confirm new message still passes rules
        if not self.is_verified(after):
            await self.add_strike(after.author, after.channel)

    @commands.Cog.listener()
    async def on_command_error(
        self,
        ctx: commands.Context,
        error: commands.CommandError
    ) -> None:
        """Called when a command is invalid"""
        if (
            isinstance(error, commands.CommandNotFound)
            and not self.allow_wrong_commands
        ):
            for prefix in self.whitelist_prefix:
                if ctx.message.content.startswith(prefix):
                    return
            await self.add_strike(ctx.message.author, ctx.channel)

    @commands.group(
        name='strikes',
        pass_context=True,
        brief='?help strikes for more info',
        description='Manage Guild member strikes'
    )
    async def _strikes(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.list(ctx)

    @_strikes.command(
        name='add',
        pass_context=True,
        brief='add strike to user',
        ignore_extra=False
    )
    async def _add(self, ctx: commands.Context, member: discord.Member) -> None:
        await self.add(ctx, member)

    @_strikes.command(
        name='list',
        pass_context=True,
        brief='add strike to user',
        ignore_extra=False
    )
    async def _list(self, ctx: commands.Context) -> None:
        await self.list(ctx)

    @_strikes.command(
        name='remove',
        pass_context=True,
        brief='remove strike from user',
        ignore_extra=False
    )
    async def _remove(self, ctx: commands.Context, member: discord.Member) -> None:
        await self.remove(ctx, member)

    @commands.group(
        name='freedom',
        pass_context=True,
        brief='?help freedom for more info',
        description='Start/stop freedom mode for the guild'
    )
    async def _freedom(self, ctx: commands.Context) -> None:
        if ctx.invoked_subcommand is None:
            await self.bot.message_guild(
                'use the `start` or `stop` subcommands. See `{}help {}` for '
                'more info'.format(self.bot.command_prefix, ctx.invoked_with),
                ctx.channel)

    @_freedom.command(
        name='start',
        pass_context=True,
        brief='start freedom mode for [float] minutes',
        ignore_extra=False
    )
    async def _start(self, ctx: commands.Context, minutes: float = None) -> None:
        await self.freedom_start(ctx, minutes)

    @_freedom.command(
        name='stop',
        pass_context=True,
        brief='stop freedom mode',
        ignore_extra=False
    )
    async def _stop(self, ctx: commands.Context) -> None:
        await self.freedom_stop(ctx)
