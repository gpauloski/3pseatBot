class BaseError(Exception):
    def __init__(self, message):
        super(BaseError, self).__init__(self)
        self.message = message
        self.error_code = 400

class UserNotFound(BaseError):
    def __init__(self, message):
        super(UserNotFound, self).__init__(message)
    
class MemberNotFound(BaseError):
    def __init__(self, message):
        super(MemberNotFound, self).__init__(message)

class UserHasNoMutualGuilds(BaseError):
    def __init__(self, message):
        super(UserHasNoMutualGuilds, self).__init__(message)

class UserNotMemberOfGuild(BaseError):
    def __init__(self, message):
        super(UserNotMemberOfGuild, self).__init__(message)

class MemberNotInVoiceChannel(BaseError):
    def __init__(self, message):
        super(MemberNotInVoiceChannel, self).__init__(message)

class FailedToPlaySound(BaseError):
    def __init__(self, message):
        super(FailedToPlaySound, self).__init__(message)

class NoSoundsInGuild(BaseError):
    def __init__(self, message):
        super(NoSoundsInGuild, self).__init__(message)

class SoundNotFound(BaseError):
    def __init__(self, message):
        super(SoundNotFound, self).__init__(message)
