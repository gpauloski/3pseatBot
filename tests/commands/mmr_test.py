from __future__ import annotations

import time
from typing import Any
from unittest import mock

import pytest

from testing.mock import MockInteraction
from testing.utils import extract
from threepseat.commands.mmr import days_since
from threepseat.commands.mmr import GameMode
from threepseat.commands.mmr import get_stats
from threepseat.commands.mmr import mmr
from threepseat.commands.mmr import split_strings
from threepseat.commands.mmr import Stats
from threepseat.commands.mmr import Status


class _MockResponse:
    def __init__(self, status_code: int, json: dict[str, Any]) -> None:
        self.status_code = status_code
        self._json = json

    def json(self) -> dict[str, Any]:
        return self._json


def test_days_since() -> None:
    assert days_since(1658098829, 1658098829) == 0
    assert days_since(int(time.time())) == 0
    assert days_since(int(time.time()) - (60 * 60 * 26)) == 1
    assert days_since(1657494029, 1658098989) == 7


def test_split_strings() -> None:
    assert split_strings('') == []
    assert split_strings('     ') == []
    assert split_strings('abc') == ['abc']
    assert split_strings(' abc, def ') == ['abc', 'def']
    assert split_strings('axbxcx', delimiter='x') == ['a', 'b', 'c']


def test_get_stats_404() -> None:
    with mock.patch(
        'requests.get',
        return_value=_MockResponse(404, {'error': {'code': 101}}),
    ):
        stats = get_stats('foo', GameMode.ARAM)
        assert stats.summoner == 'foo'
        assert stats.status == Status.UNAVAILABLE
        assert stats.gamemode == GameMode.ARAM

    with mock.patch('requests.get', return_value=_MockResponse(404, {})):
        stats = get_stats('foo', GameMode.ARAM)
        assert stats.summoner == 'foo'
        assert stats.status == Status.UNKNOWN
        assert stats.gamemode == GameMode.ARAM


def test_get_stats_not_200() -> None:
    with mock.patch('requests.get', return_value=_MockResponse(400, {})):
        stats = get_stats('foo', GameMode.ARAM)
        assert stats.summoner == 'foo'
        assert stats.status == Status.ERROR
        assert stats.gamemode == GameMode.ARAM


def test_get_stats_missing_gamemode() -> None:
    with mock.patch(
        'requests.get',
        return_value=_MockResponse(200, {'ARAM': {'avg': None}}),
    ):
        stats = get_stats('foo', GameMode.ARAM)
        assert stats.summoner == 'foo'
        assert stats.status == Status.UNAVAILABLE
        assert stats.gamemode == GameMode.ARAM


def test_get_stats_success() -> None:
    t = time.time()
    with mock.patch(
        'requests.get',
        return_value=_MockResponse(
            200,
            {
                'ARAM': {
                    'avg': 2500,
                    'err': 50,
                    'percentile': 99.0,
                    'closestRank': 'Platinum II',
                    'timestamp': t,
                },
            },
        ),
    ):
        stats = get_stats('foo', GameMode.ARAM)
        assert stats.summoner == 'foo'
        assert stats.status == Status.AVAILABLE
        assert stats.gamemode == GameMode.ARAM
        assert stats.mmr == 2500
        assert stats.err == 50
        assert stats.percentile == 99.0
        assert stats.rank == 'Platinum II'
        assert stats.time == t


@pytest.mark.asyncio
async def test_mmr() -> None:
    mmr_ = extract(mmr)

    interaction = MockInteraction(mmr, user='calling-user')

    stats = [
        Stats(
            summoner='foo',
            status=Status.AVAILABLE,
            gamemode=GameMode.ARAM,
        ),
        Stats(
            summoner='bar',
            status=Status.UNAVAILABLE,
            gamemode=GameMode.ARAM,
        ),
    ]

    with mock.patch('threepseat.commands.mmr.get_stats', side_effect=stats):
        await mmr_(interaction, 'foo, bar', GameMode.ARAM)

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'foo' in interaction.followup_message
        and 'bar' in interaction.followup_message
        and 'aram' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_mmr_error() -> None:
    mmr_ = extract(mmr)

    interaction = MockInteraction(mmr, user='calling-user')

    stats = Stats(
        summoner='foo',
        status=Status.ERROR,
        gamemode=GameMode.ARAM,
    )

    with mock.patch('threepseat.commands.mmr.get_stats', return_value=stats):
        await mmr_(interaction, 'foo, bar', GameMode.ARAM)

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'API error' in interaction.followup_message
    )


@pytest.mark.asyncio
async def test_mmr_summoner_does_not_exist() -> None:
    mmr_ = extract(mmr)

    interaction = MockInteraction(mmr, user='calling-user')

    stats = Stats(
        summoner='foo',
        status=Status.UNKNOWN,
        gamemode=GameMode.ARAM,
    )

    with mock.patch('threepseat.commands.mmr.get_stats', return_value=stats):
        await mmr_(interaction, 'foo, bar', GameMode.ARAM)

    assert interaction.followed
    assert (
        interaction.followup_message is not None
        and 'does not exist' in interaction.followup_message
    )
