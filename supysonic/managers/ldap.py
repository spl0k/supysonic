import logging


import ldap3


logger = logging.getLogger(__name__)


class LdapManager:

    def __init__(self, ldap_server, base_dn, user_filter, admin_filter, bind_dn, bind_password, username_attr, email_attr):
        self.ldap_server=ldap_server
        self.base_dn=base_dn
        self.user_filter=user_filter
        self.admin_filter=admin_filter
        self.bind_dn=bind_dn
        self.bind_password=bind_password
        self.username_attr=username_attr
        self.email_attr=email_attr
        if not self.ldap_server:
            raise ValueError("No LDAP configured")
        self.server = ldap3.Server(self.ldap_server, get_info="ALL")

    def try_auth(self,user, password):
        admin= False
        if self.admin_filter:
            entrie = self.search_user(user, self.admin_filter)
            if entrie:
                logger.debug("{0} is admin".format(user))
                admin = True
        if not admin:
            entrie = self.search_user(user, self.user_filter)
            if not entrie:
                return False
        try:
            with ldap3.Connection(
                self.server, entrie.entry_dn, password, read_only=True
            ) as conn:
                return {
                    "uid": entrie[self.username_attr],
                    "mail": entrie[self.email_attr],
                    "admin": admin,
                }
        except ldap3.core.exceptions.LDAPBindError:
            logger.warning("wrong password for user {0}".format(user))
            return False

    def search_user(self,user, filter):

        try:
            with ldap3.Connection(
                self.server, self.bind_dn, self.bind_password, read_only=True
            ) as conn:
                conn.search(
                    self.base_dn,
                    filter,
                    attributes=[self.email_attr, self.username_attr],
                )
                entries = conn.entries
        except ldap3.core.exceptions.LDAPBindError:
            logger.warning(
                "wrong can't bind LDAP with {0}".format(self.bind_dn))

        for entrie in entries:
            if entrie[self.username_attr] == user:
                return entrie
        return False
