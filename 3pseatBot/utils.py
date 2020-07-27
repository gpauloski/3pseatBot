import emoji
import re

EMOJI_RE = r'<:\w*:\d*>'

def is_emoji(text):
    """Returns True if string is just whitespace and Discord emojis"""
    # remove unicode emojis from text
    text = emoji.get_emoji_regexp().sub(r'', text)
    # remove discord emojis from text
    text = re.sub(EMOJI_RE, '', text)
    
    # at this point, the string has all emojis removed so if the string
    # is just whitespace then we know it was only emojis
    return text.strip() == ''
