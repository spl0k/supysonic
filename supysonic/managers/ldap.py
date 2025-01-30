import logging
try:
    import ldap3
except ModuleNotFoundError:
    ldap3 = None

logger = logging.getLogger(__name__)

class LdapManager:
    def __init__(self, **config):
        if not config["server_url"]:
            logger.debug("LDAP 'server_url' is not configured.")
            raise ValueError
        elif not ldap3:
            logger.error("Module 'ldap3' is not installed.")
            raise ValueError
        elif None in config.values():
            logger.error("Some required LDAP parameters are missing.")
            raise ValueError

        self.server = ldap3.Server(config["server_url"], get_info=None)
        self.config = config

    def try_auth(self, username, password):
        admin = False

        if self.config["admin_filter"]:
            entry = self.search_user(username, self.config["admin_filter"])
            if entry:
                logger.info(f"User '{username}' is admin.")
                admin = True

        if not admin:
            entry = self.search_user(username, self.config["user_filter"])

        if entry:
            try:
                with ldap3.Connection(self.server, entry.entry_dn, password, read_only=True):
                    return {
                        "mail": entry[self.config["email_attr"]],
                        "admin": admin
                    }
            except ldap3.core.exceptions.LDAPBindError:
                logger.error(f"Bind failed for '{entry.entry_dn}'.")
            except Exception as e:
                logger.error(f"LDAP error: {e}")

    def search_user(self, username, _filter):
        try:
            with ldap3.Connection(self.server, self.config["bind_dn"], self.config["bind_pw"], read_only=True) as conn:
                conn.search(
                    self.config["base_dn"],
                    _filter.format(username=username),
                    attributes=[self.config["username_attr"], self.config["email_attr"]],
                    size_limit=1
                )
                entries = conn.entries
                if entries and entries[0][self.config["username_attr"]] == username:
                    return entries[0]
                else:
                    logger.info(f"User '{username}' not found in LDAP database.")
        except ldap3.core.exceptions.LDAPBindError:
            logger.error(f"Bind failed for '{self.config['bind_dn']}'.")
        except Exception as e:
            logger.error(f"LDAP error: {e}")
