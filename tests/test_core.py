import unittest

from guildperm.core import Guild


class RoleTest(unittest.TestCase):
    def test_add_role_registers(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        self.assertIn("guest", guild.roles)

    def test_set_role_registers_member(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.set_role("p", "guest")
        self.assertEqual(guild.members["p"], "guest")


class CanTest(unittest.TestCase):
    def test_direct_rule_allows(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.set_role("p", "guest")
        self.assertTrue(guild.can("p", "chat"))

    def test_direct_rule_denies(self):
        guild = Guild()
        guild.add_role("mute", None, {"chat": False})
        guild.set_role("p", "mute")
        self.assertFalse(guild.can("p", "chat"))

    def test_unknown_permission_is_false(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.set_role("p", "guest")
        self.assertFalse(guild.can("p", "ban"))


if __name__ == "__main__":
    unittest.main()
