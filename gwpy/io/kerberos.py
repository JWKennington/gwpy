# -*- coding: utf-8 -*-
# Copyright (C) Duncan Macleod (2013)
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

"""Utility module to initialise a kerberos ticket for NDS2 connections

This module provides a lazy-mans python version of the 'kinit'
command-line tool, with internal guesswork using keytabs

See the documentation of the `kinit` function for example usage
"""

import getpass
import os
import re
import subprocess
import sys

from six.moves import input

from ..utils.shell import which

__author__ = "Duncan Macleod <duncan.macleod@ligo.org>"

__all__ = ['kinit']


class KerberosError(RuntimeError):
    """Kerberos (krb5) operation failed
    """
    pass


def kinit(username=None, password=None, realm=None, exe=None, keytab=None,
          krb5ccname=None, verbose=None):
    """Initialise a kerberos (krb5) ticket.

    This allows authenticated connections to, amongst others, NDS2
    services.

    Parameters
    ----------
    username : `str`, optional
        name of user, will be prompted for if not given.

    password : `str`, optional
        cleartext password of user for given realm, will be prompted for
        if not given.

    realm : `str`, optional
        name of realm to authenticate against, read from keytab if available,
        defaults to ``'LIGO.ORG'``.

    exe : `str`, optional
        path to kinit executable.

    keytab : `str`, optional
        path to keytab file. If not given this will be read from the
        ``KRB5_KTNAME`` environment variable. See notes for more details.

    krb5ccname : `str`, optional
        path to Kerberos credentials cache.

    verbose : `bool`, optional
        print verbose output (if `True`), or not (`False)`; default is `True`
        if any user-prompting is needed, otherwise `False`.

    Notes
    -----
    If a keytab is given, or is read from the KRB5_KTNAME environment
    variable, this will be used to guess the username and realm, if it
    contains only a single credential

    Examples
    --------
    Example 1: standard user input, with password prompt::

        >>> kinit('albert.einstein')
        Password for albert.einstein@LIGO.ORG:
        Kerberos ticket generated for albert.einstein@LIGO.ORG

    Example 2: extract username and realm from keytab, and use that
    in authentication::

        >>> kinit(keytab='~/.kerberos/ligo.org.keytab')
        Kerberos ticket generated for albert.einstein@LIGO.ORG
    """
    # get kinit path
    if exe is None:
        exe = which('kinit')

    # get keytab
    if keytab is None:
        keytab = os.environ.get('KRB5_KTNAME', None)
        if keytab is None or not os.path.isfile(keytab):
            keytab = None
    if keytab:
        try:
            principals = parse_keytab(keytab)
        except KerberosError:
            pass
        else:
            # is there's only one entry in the keytab, use that
            if username is None and len(principals) == 1:
                username = principals[0][0]
            # or if the given username is in the keytab, find the realm
            if username in list(zip(*principals))[0]:
                idx = list(zip(*principals))[0].index(username)
                realm = principals[idx][1]
            # otherwise this keytab is useless, so remove it
            else:
                keytab = None

    # refuse to prompt if we can't get an answer
    if not sys.stdout.isatty() and (
            username is None or
            (not keytab and password is None)
    ):
        raise KerberosError("cannot generate kerberos ticket in a "
                            "non-interactive session, please manually create "
                            "a ticket, or consider using a keytab file")

    # get credentials
    if realm is None:
        realm = 'LIGO.ORG'
    if username is None:
        username = input("Please provide username for the {} kerberos "
                         "realm: ".format(realm))
    identity = '{}@{}'.format(username, realm)
    if not keytab and password is None:
        password = getpass.getpass(prompt="Password for {}: ".format(identity),
                                   stream=sys.stdout)

    # format kinit command
    if keytab:
        cmd = [exe, '-k', '-t', keytab, identity]
    else:
        cmd = [exe, identity]
    if krb5ccname:
        krbenv = {'KRB5CCNAME': krb5ccname}
    else:
        krbenv = None

    # execute command
    kget = subprocess.Popen(cmd, env=krbenv, stdout=subprocess.PIPE,
                            stdin=subprocess.PIPE)
    if not keytab:
        kget.communicate(password.encode('utf-8'))
    kget.wait()
    retcode = kget.poll()
    if retcode:
        raise subprocess.CalledProcessError(kget.returncode, ' '.join(cmd))
    if verbose:
        print("Kerberos ticket generated for {}".format(identity))


def parse_keytab(keytab):
    """Read the contents of a KRB5 keytab file, returning a list of
    credentials listed within

    Parameters
    ----------
    keytab : `str`
        path to keytab file
    """
    try:
        out = subprocess.check_output(['klist', '-k', keytab],
                                      stderr=subprocess.PIPE)
    except OSError:
        raise KerberosError("Failed to locate klist, cannot read keytab")
    except subprocess.CalledProcessError:
        raise KerberosError("Cannot read keytab {!r}".format(keytab))
    principals = []
    for line in out.splitlines():
        if isinstance(line, bytes):
            line = line.decode('utf-8')
        try:
            num, principal, = re.split(r'\s+', line.strip(' '), 1)
        except ValueError:
            continue
        else:
            if not num.isdigit():
                continue
            principals.append(principal.split('@'))
    return principals
