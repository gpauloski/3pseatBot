"""Test utility functions"""
from threepseat.utils import is_emoji, is_url, keys_to_int


def test_is_emoji():
    """Test is_emoji function"""
    assert not is_emoji('not an emoji')
    # Check unicode emoji
    assert is_emoji('😁')
    # Check discord emoji
    assert is_emoji('<:skelepls:>')
    assert is_emoji('<:skelepls:12345>')
    # Check multiple
    assert is_emoji('😁 <:skelepls:>')
    assert not is_emoji('')


def test_is_url():
    """Test is_url function"""
    assert is_url('github.com/')
    assert is_url('https://github.com/')
    assert is_url('www.github.com')
    assert not is_url('not a url')
    assert not is_url('')


def test_keys_to_int():
    """Test keys_to_int function"""
    d = {'1': 1, '2': 2, '3': 3}
    d_out = keys_to_int(d)
    for key in d_out:
        assert isinstance(key, int)
        assert key == d_out[key]
