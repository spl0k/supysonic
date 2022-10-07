from ..db import User
import ldap3
from ..config import get_current_config

LDAPConfig = get_current_config().LDAP


class LdapManager:

    @staticmethod
    def try_auth(user, password):
        pass
