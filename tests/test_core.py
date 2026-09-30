import random
import unittest

from guildperm.core import Guild, PermError


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


class InheritanceTest(unittest.TestCase):
    def test_rule_inherited_from_parent(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("member", "guest", {})
        guild.set_role("p", "member")
        self.assertTrue(guild.can("p", "chat"))

    def test_rule_inherited_through_three_levels(self):
        guild = Guild()
        guild.add_role("root", None, {"chat": True})
        guild.add_role("mid", "root", {})
        guild.add_role("leaf", "mid", {})
        guild.set_role("p", "leaf")
        self.assertTrue(guild.can("p", "chat"))

    def test_child_rule_overrides_parent_allow(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("member", "guest", {"chat": False})
        guild.set_role("p", "member")
        self.assertFalse(guild.can("p", "chat"))

    def test_child_allow_does_not_override_parent_deny(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": False})
        guild.add_role("member", "guest", {"chat": True})
        guild.set_role("p", "member")
        self.assertFalse(guild.can("p", "chat"))

    def test_deny_anywhere_on_chain_wins(self):
        guild = Guild()
        guild.add_role("root", None, {"chat": True})
        guild.add_role("muted", "root", {"chat": False})
        guild.add_role("member", "muted", {"chat": True})
        guild.set_role("p", "member")
        self.assertFalse(guild.can("p", "chat"))

    def test_unknown_member_and_role_are_false(self):
        guild = Guild()
        guild.set_role("p", "ghost")
        self.assertFalse(guild.can("p", "chat"))
        self.assertFalse(guild.can("nobody", "chat"))


class CacheTest(unittest.TestCase):
    def test_set_role_invalidates_cache(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("mute", None, {"chat": False})
        guild.set_role("p", "guest")
        self.assertTrue(guild.can("p", "chat"))
        guild.set_role("p", "mute")
        self.assertFalse(guild.can("p", "chat"))

    def test_add_role_invalidates_cache(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.set_role("p", "guest")
        self.assertTrue(guild.can("p", "chat"))
        guild.add_role("mute", "guest", {"chat": False})
        guild.set_role("p", "mute")
        self.assertFalse(guild.can("p", "chat"))

    def test_cached_false_is_not_treated_as_missing(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": False})
        guild.set_role("p", "guest")
        self.assertFalse(guild.can("p", "chat"))
        self.assertFalse(guild.can("p", "chat"))


class CycleTest(unittest.TestCase):
    def test_two_role_cycle_raises(self):
        guild = Guild()
        guild.add_role("a", "b", {})
        with self.assertRaises(PermError):
            guild.add_role("b", "a", {})

    def test_self_cycle_raises(self):
        guild = Guild()
        with self.assertRaises(PermError):
            guild.add_role("a", "a", {})

    def test_three_role_cycle_raises_and_state_unchanged(self):
        guild = Guild()
        guild.add_role("a", None, {})
        guild.add_role("b", "a", {})
        with self.assertRaises(PermError):
            guild.add_role("a", "b", {})
        self.assertIsNone(guild.roles["a"]["parent"])

    def test_repeated_sequence_is_deterministic(self):
        def run():
            guild = Guild()
            out = []
            guild.add_role("a", "b", {})
            try:
                guild.add_role("b", "a", {})
                out.append("ok")
            except PermError:
                out.append("cycle")
            guild.add_role("b", None, {"chat": True})
            guild.set_role("p", "a")
            out.append(guild.can("p", "chat"))
            return out
        self.assertEqual(run(), run())


class ScaleTest(unittest.TestCase):
    def test_scanned_is_chain_length_not_role_count(self):
        guild = Guild()
        for index in range(2000):
            guild.add_role("r-%d" % index, None, {"chat": True})
        guild.set_role("p", "r-1999")
        for _ in range(2000):
            guild.cache.clear()
            guild.can("p", "chat")
        self.assertLessEqual(guild.scanned_count(), 6000)


class ReferenceModel:
    """参考实现：独立存状态，每次判定都沿链重算（不缓存）。"""

    def __init__(self):
        self.roles = {}
        self.members = {}

    @staticmethod
    def _would_cycle(roles, name, parent):
        current, seen = parent, set()
        while current is not None:
            if current == name or current in seen:
                return True
            seen.add(current)
            node = roles.get(current)
            current = node[0] if node is not None else None
        return False

    def add_role(self, name, parent, rules):
        if parent is not None and self._would_cycle(self.roles, name, parent):
            raise PermError("cycle")
        self.roles[name] = (parent, dict(rules))

    def set_role(self, member, role):
        self.members[member] = role

    def can(self, member, perm):
        role, allowed, seen = self.members.get(member), False, set()
        while role is not None and role not in seen:
            seen.add(role)
            node = self.roles.get(role)
            if node is None:
                break
            rule = node[1].get(perm)
            if rule is False:
                return False
            if rule is True:
                allowed = True
            role = node[0]
        return allowed


class DifferentialTest(unittest.TestCase):
    def test_random_sequences_match_reference(self):
        rng = random.Random(20260930)
        perms = ["chat", "ban", "kick", "invite"]
        for _ in range(200):
            guild, ref = Guild(), ReferenceModel()
            names, members = [], []
            for _ in range(rng.randint(10, 40)):
                action = rng.random()
                if action < 0.45 or not names:
                    reconfigure = bool(names) and rng.random() < 0.3
                    if reconfigure:
                        name = names[rng.randrange(len(names))]
                    else:
                        name = "role-%d" % len(names)
                    parent = rng.choice([None] + names + [name])
                    rules = {
                        perm: rng.choice([True, False])
                        for perm in perms
                        if rng.random() < 0.4
                    }
                    expect_cycle = ReferenceModel._would_cycle(ref.roles, name, parent)
                    if expect_cycle:
                        with self.assertRaises(PermError):
                            guild.add_role(name, parent, rules)
                        with self.assertRaises(PermError):
                            ref.add_role(name, parent, rules)
                    else:
                        guild.add_role(name, parent, rules)
                        ref.add_role(name, parent, rules)
                        if not reconfigure and name not in names:
                            names.append(name)
                elif action < 0.75:
                    member = "m-%d" % rng.randrange(6)
                    role = rng.choice(names)
                    guild.set_role(member, role)
                    ref.set_role(member, role)
                    if member not in members:
                        members.append(member)
                else:
                    member = rng.choice(members) if members else "m-x"
                    perm = rng.choice(perms)
                    guild.can(member, perm)
                    self.assertEqual(
                        guild.can(member, perm),
                        ref.can(member, perm),
                        (names, member, perm),
                    )


if __name__ == "__main__":
    unittest.main()
