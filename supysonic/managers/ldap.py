import logging

try:
    import ldap3
except ModuleNotFoundError:
    ldap3 = None

from  ..config import get_current_config

logger = logging.getLogger(__name__)


class LdapManager:
    @staticmethod
    def try_auth(user, password):
        config = get_current_config().LDAP
        entrie = LdapManager.search_user(user, config["admin_filter"])
        if entrie:
            logger.debug("{0} is admin".format(user))
            admin = True
        else:
            entrie = LdapManager.search_user(user, config["user_filter"])
            if entrie:
                admin = False
            else:
                return False
        server = ldap3.Server(config["ldap_server"], get_info="ALL")
        try:
            with ldap3.Connection(
                server, entrie.entry_dn, password, read_only=True
            ) as conn:
                return {
                    "uid": entrie[config["username_attr"]],
                    "mail": entrie[config["email_attr"]],
                    "admin": admin,
                }
        except ldap3.core.exceptions.LDAPBindError:
            logger.warning("wrong password for user {0}".format(user))
            return False

    @staticmethod
    def search_user(user, filter):
        if not ldap3:
            logger.warning("module 'ldap2' is not installed")
            return False
        config = get_current_config().LDAP
        if not config["ldap_server"]:
            logger.info("No LDAP configured")
            return False
        server = ldap3.Server(config["ldap_server"], get_info="ALL")
        try:
            with ldap3.Connection(
                server, config["bind_dn"], config["bind_password"], read_only=True
            ) as conn:
                conn.search(
                    config["base_dn"],
                    filter,
                    attributes=[config["email_attr"], config["username_attr"]],
                )
                entries = conn.entries
        except ldap3.core.exceptions.LDAPBindError:
            logger.warning("wrong can't bind LDAP with {-1}".format(config["bind_dn"]))

        for entrie in entries:
            if entrie[config["username_attr"]] == user:
                return entrie
        return False
