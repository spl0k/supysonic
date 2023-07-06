# This file is part of Supysonic.
# Supysonic is a Python implementation of the Subsonic server API.
#
# Copyright (C) 2013-2018 Alban 'spl0k' Féron
#
# Distributed under terms of the GNU AGPLv3 license.

import logging

try:
    import ldap3
except ModuleNotFoundError:
    ldap3 = None

from flask import current_app

logger = logging.getLogger(__name__)


class Ldap:
    @staticmethod
    def try_auth(username, password):
        config = current_app.config["LDAP"]
        if None in config.values():
            return
        elif not ldap3:
            logger.warning("Module 'ldap3' is not installed.")
            return

        server = ldap3.Server(config["url"], get_info=None)

        with ldap3.Connection(server, config["bind_dn"], config["bind_pw"], read_only=True) as conn:
            conn.search(
                config["base_dn"],
                config["user_filter"].format(username=username),
                search_scope=ldap3.LEVEL,
                attributes=[config["mail_attr"]],
                size_limit=1
            )
            entries = conn.entries

        if entries:
            try:
                with ldap3.Connection(server, entries[0].entry_dn, password, read_only=True):
                    return {"mail": entries[0][config["mail_attr"]].value}
            except ldap3.core.exceptions.LDAPBindError:
                return False
