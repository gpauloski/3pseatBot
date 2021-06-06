"""Error classes for the soundboard service"""


class BaseError(Exception):
    """Base exception class for soundboard errors"""

    def __init__(self, message):
        super(BaseError, self).__init__(self)
        self.message = message
        self.error_code = 400


class UserNotFound(BaseError):
    """Raised when a Discord user cannot be found by ID"""

    def __init__(self, message):
        super(UserNotFound, self).__init__(message)


class MemberNotFound(BaseError):
    """Raised when a Guild member cannot be found by ID"""

    def __init__(self, message):
        super(MemberNotFound, self).__init__(message)


class UserHasNoMutualGuilds(BaseError):
    """Raised when a user is not in any mutual guilds with the bot"""

    def __init__(self, message):
        super(UserHasNoMutualGuilds, self).__init__(message)


class UserNotMemberOfGuild(BaseError):
    """Raised when a user is not a member of the guild"""

    def __init__(self, message):
        super(UserNotMemberOfGuild, self).__init__(message)


class MemberNotInVoiceChannel(BaseError):
    """Raised when issuing a command requiring being in a voice channel"""

    def __init__(self, message):
        super(MemberNotInVoiceChannel, self).__init__(message)


class FailedToPlaySound(BaseError):
    """Raised when an unknown error prevents a sound from being played"""

    def __init__(self, message):
        super(FailedToPlaySound, self).__init__(message)


class NoSoundsInGuild(BaseError):
    """Raised when a sound command is issued but there are no sounds"""

    def __init__(self, message):
        super(NoSoundsInGuild, self).__init__(message)


class SoundNotFound(BaseError):
    """Raised when a specific sound cannot be found in the guild"""

    def __init__(self, message):
        super(SoundNotFound, self).__init__(message)
