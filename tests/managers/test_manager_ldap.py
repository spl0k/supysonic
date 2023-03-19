import ldap3
from supysonic import db
from supysonic.managers.ldap import LdapManager
import unittest
from unittest.mock import patch

LDAP = {
    "ldap_server": "fakeServer",
    "base_dn": "ou=test,o=lab",
    "user_filter": "(&(objectClass=inetOrgPerson))",
    "admin_filter": None,
    "bind_dn": "cn=my_user,ou=test,o=lab",
    "bind_password": 'my_password',
    "username_attr": "uid",
    "email_attr": "mail",
}


class LdapManagerTestCase(unittest.TestCase):

    def setUp(self):
        # Create an empty sqlite database in memory
        pass

    def tearDown(self):
        pass

    @patch('supysonic.managers.ldap.ldap3.Connection')
    def test_ldapManager_searchUser(self, mock_object):
        mock_object.return_value.__enter__.return_value.entries = [
            {LDAP["username_attr"]:"toto"}]
        ldap = LdapManager(**LDAP)
        ldap_user = ldap.search_user("toto", LDAP["user_filter"])
        self.assertEqual(ldap_user[LDAP["username_attr"]], "toto")
        ldap_user = ldap.search_user("tata", LDAP["user_filter"])
        self.assertFalse(ldap_user)

    @patch('supysonic.managers.ldap.ldap3.Connection')
    def test_ldapManager_try_auth(self, mock_object):
        mock_object.return_value.__enter__.return_value.entries = [
            {LDAP["username_attr"]:"toto", "entry_dn":"cn=toto", "mail":"toto@example.com"}]
        ldap = LdapManager(**LDAP)
        ldap_user = ldap.try_auth("toto", "toto")
        self.assertFalse(ldap_user["admin"])
        self.assertEqual(ldap_user[LDAP["username_attr"]], "toto")
        self.assertEqual(ldap_user[LDAP["email_attr"]], "toto@example.com")
        ldap_user = ldap.try_auth("tata", "tata")
        self.assertFalse(ldap_user)
