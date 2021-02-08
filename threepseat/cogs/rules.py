import discord
import logging

from discord.ext import commands
from typing import Union, Optional, List

from threepseat.constants import F_EMOTE
from threepseat.bans import Bans
from threepseat.utils import is_admin, is_emoji, is_booster, is_url

logger = logging.getLogger()


class Rules(commands.Cog):
    """Extension for enforcing guild rules"""
    def __init__(self,
                 bot: commands.Bot,
                 database_path: str,
                 message_prefix: Optional[Union[str, List[str]]] = None,
                 whitelist_prefix: Union[str, List[str]] = [],
                 max_offenses: int = 3,
                 allow_deletes: bool = True,
                 allow_edits: bool = True,
                 allow_wrong_commands: bool = True,
                 booster_exception: bool = True,
                 invite_after_kick: bool = True
        ) -> None:
        """Create Rules cog

        Args:
            bot: bot object this cog is attached to
            database_path: path to file storing database of strikes
            message_prefix: valid prefixes for messages. If None, no
                message prefix checking is done.
            whitelist_prefix: messages starting with these prefixes will
                be ignored. Useful for ignoring the command prefixes of
                other bots.
            max_offenses: maximum strikes before being kicked
            allow_deletes: if false, the bot will notify the channel if
                a message is deleted
            allow_edits: if false, the bot will notify the channel if 
                a message is edited
            allow_wrong_commands: if false, members will be given a strike
                for trying to use invalid commands
            booster_exception: boosters are exempt from rules
            invite_after_kick: send invite link if member is kicked
        """
        self.bot = bot
        if isinstance(message_prefix, str):
            message_prefix = [message_prefix]
        self.message_prefix = message_prefix
        if isinstance(whitelist_prefix, str):
            message_prefix = [whitelist_prefix]
        self.whitelist_prefix = whitelist_prefix
        self.max_offenses = max_offenses
        self.allow_deletes = allow_deletes
        self.allow_edits = allow_edits
        self.allow_wrong_commands = allow_wrong_commands
        self.booster_exception = booster_exception
        self.invite_after_kick = invite_after_kick

        if self.message_prefix is not None:
            self.bot.guild_message_prefix = self.message_prefix[0]

        # TODO
        self.db = Bans(database_path)


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
            await self._add_strike(message.author, message.channel, 
                    message.guild)


    @commands.Cog.listener()
    async def on_message_delete(self, message: discord.Message) -> None:
        """Called when message is deleted"""
        if message.author.bot or self.should_ignore(message):
            return
        msg = '{}, where did your message go? It was: \"{}\"'.format(
              message.author.mention, message.clean_content)
        await self.bot.message_guild(msg, message.channel)


    @commands.Cog.listener()
    async def on_message_edit(self, 
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
            await self._add_strike(after.author, after.channel, 
                    after.guild)


    @commands.Cog.listener()
    async def on_command_error(self, 
                               ctx: commands.Context,
                               error: commands.CommandError
        ) -> None:
        """Called when a command is invalid"""
        if (isinstance(error, commands.CommandNotFound) and
                not self.allow_wrong_commands):
            await self._add_strike(ctx.message.author, ctx.channel, ctx.guild)


    @commands.group(pass_context=True, brief='?help strikes for more info', 
                    description='Manage strikes. By default, '
                                'lists all strikes in the guild.')
    async def strikes(self, ctx: commands.Context) -> None:
        """Command to list strikes in guild"""
        if ctx.invoked_subcommand is None:
            self.list(ctx)


    @strikes.command(pass_context=True, brief='add strike to user')
    async def list(self, ctx: commands.Context) -> None:
        """Command to list strikes for the guild""" 
        msg = '{}, here are the strikes:```'.format(
                ctx.message.author.mention)
        serverCount = 0
        for user in self.db.get_table(ctx.guild.name):
            if user['name'] != 'server':
                msg = msg + '\n{}: {}/{}'.format(
                      user['name'], user['count'], self.max_offenses)
            else:
                serverCount = user['count']
        msg = msg + '```Total offenses to date: {}'.format(serverCount)
        await self.bot.message_guild(msg, ctx.channel)


    @strikes.command(pass_context=True, brief='add strike to user')
    async def add(self, 
                  ctx: commands.Context,
                  member: discord.Member
        ) -> None:
        """Command to add a strike to a user

        Requires being a bot admin
        """
        if self.bot.is_bot_admin(ctx.message.author):
            await self._add_strike(member, ctx.channel, ctx.guild)
        else:
            await self.bot.message_server('you lack permission, {}'.format(
                    ctx.message.author.mention))


    @strikes.command(pass_context=True, brief='remove strike from user')
    async def remove(self, 
                     ctx: commands.Context,
                     member: discord.Member
        ) -> None:
        """Command to remove a strike to a user

        Requires being a bot admin
        """
        if self.bot.is_bot_admin(ctx.message.author):
            self._remove_strike(member, ctx.guild)
            count = self.db.get_value(ctx.guild.name, member.name)
            await self.bot.message_guild(
                    'removed strike for {}. New strike count is {}.'.format(
                    member.mention, count),
                    ctx.message.channel)
        else:
            await self.bot.message_server('you lack permission, {}'.format(
                    ctx.message.author.mention))


    def should_ignore(self, message: discord.Message) -> bool:
        """Returns true if the message should be ignored for rules"""
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
        """Verifies a message passes the rules"""
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


    async def check_strikes(self,
                            member: discord.Member, 
                            channel: discord.TextChannel,
                            guild: discord.Guild
        ) -> None:
        """Handles what to do when user recieves a strike

        If the user has fewer that `self.max_offenses` strikes,
        a warning is sent. Otherwise, the bot attempts to kick
        the user and send them a invite link if
        `self.invite_after_kick`.

        Warning: in general, this function should only be called
            by `self._add_strike()`.
        """
        count = self.db.get_value(guild.name, member.name)

        if count < self.max_offenses:
            msg = '{}! You\'ve disturbed the spirits ({}/{})'.format(
                  member.mention, count, self.max_offenses)
            await self.bot.message_guild(msg, channel)
        else:
            self._clear_strikes(member, guild)
            msg = ('That\'s {} strikes, {}. I\'m sorry but your time as come. '
                   'RIP.\n'.format(self.max_offenses, member.mention))
            success = await self.kick(member, channel, guild, msg)
            if self.invite_after_kick and success:
                msg = ('Sorry we had to kick you. Here is a link to rejoin: '
                       '{link}')
                await self.invite(member, channel, msg)


    async def invite(self,
                     user: Union[discord.User, discord.Member], 
                     channel: discord.TextChannel,
                     message: str
        ) -> None:
        """Send guild invite link to user"""
        try:
            link = await channel.create_invite(max_uses=1)
            msg = message.format(link=link)
            await self.bot.message_user(msg, user)
        except Exception as e:
            logger.warning('Failed to send rejoin message to {}.'
                    'Caught exception: {}'.format(user, e))


    async def kick(self,
                   member: discord.Member, 
                   channel: discord.TextChannel,
                   guild: discord.Guild,
                   message: str = None
        ) -> bool:
        """Kick user from guild

        Args:
            member: member to kick
            channel: channel to send notification messages to
            guild: guild member belongs to to be kicked from
            message: optional message to sent to channel when
                the member is kicked
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


    async def _add_strike(self,
                    member: discord.Member, 
                    channel: discord.TextChannel,
                    guild: discord.Guild
        ) -> None:
        """Add a strike to the `member` of `guild`"""
        self.db.up(guild.name, member.name)
        await self.check_strikes(member, channel, guild)


    def _remove_strike(self,
                       member: discord.Member, 
                       guild: discord.Guild
        ) -> None:
        """Remove a strike from the `member` of `guild`"""
        self.db.down(guild.name, member.name)


    def _clear_strikes(self,
                       member: discord.Member, 
                       guild: discord.Guild
        ) -> None:
        """Reset strikes for the `member` of `guild`"""
        self.db.clear(guild.name, member.name)