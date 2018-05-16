# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2017)
#
# This file is part of GWpy.
#
# GWpy is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# GWpy is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with GWpy.  If not, see <http://www.gnu.org/licenses/>.

"""I/O utilities for reading `TimeSeries` from a `list` of file paths.
"""

from six import string_types

from ...io.cache import (FILE_LIKE, read_cache, sieve)
from ...segments import Segment

__author__ = "Duncan Macleod <duncan.macleod@ligo.org>"


def preformat_cache(cache, start=None, end=None):
    """Preprocess a `list` of file paths for reading.

    - read the cache from the file (if necessary)
    - sieve the cache to only include data we need

    Parameters
    ----------
    cache : `list`, `str`
        List of file paths, or path to a LAL-format cache file on disk.

    start : `~gwpy.time.LIGOTimeGPS`, `float`, `str`, optional
        GPS start time of required data, defaults to start of data found;
        any input parseable by `~gwpy.time.to_gps` is fine.

    end : `~gwpy.time.LIGOTimeGPS`, `float`, `str`, optional
        GPS end time of required data, defaults to end of data found;
        any input parseable by `~gwpy.time.to_gps` is fine.

    Returns
    -------
    modcache : `list`
        A parsed, sieved list of paths based on the input arguments.
    """
    # format cache file
    if isinstance(cache, FILE_LIKE + string_types):  # open cache file
        cache = read_cache(cache)
    cache = type(cache)(cache)  # copy cache
    cache.sort(key=lambda e: e.segment)  # sort

    # get timing
    if start is None:  # start time of earliest file
        start = cache[0].segment[0]
    if end is None:  # end time of latest file
        end = cache[-1].segment[-1]

    return sieve(cache, segment=Segment(start, end))  # sieve
