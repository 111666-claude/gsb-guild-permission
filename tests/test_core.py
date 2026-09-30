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


class InheritChainTest(unittest.TestCase):
    def test_empty_rule_uses_parent_allow(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("member", "guest", {})
        guild.set_role("p", "member")
        self.assertTrue(guild.can("p", "chat"))

    def test_deep_chain_walks_to_ancestor(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("member", "guest", {})
        guild.add_role("officer", "member", {"kick": True})
        guild.add_role("leader", "officer", {})
        guild.set_role("p", "leader")
        self.assertTrue(guild.can("p", "chat"))
        self.assertTrue(guild.can("p", "kick"))
        self.assertFalse(guild.can("p", "ban"))

    def test_child_allow_takes_effect_without_deny(self):
        guild = Guild()
        guild.add_role("guest", None, {})
        guild.add_role("member", "guest", {"chat": True})
        guild.set_role("p", "member")
        self.assertTrue(guild.can("p", "chat"))

    def test_missing_role_or_member_is_false(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.set_role("p", "ghost")
        self.assertFalse(guild.can("p", "chat"))
        self.assertFalse(guild.can("nobody", "chat"))


class DenyPriorityTest(unittest.TestCase):
    def test_parent_deny_beats_child_allow(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": False})
        guild.add_role("member", "guest", {"chat": True})
        guild.set_role("p", "member")
        self.assertFalse(guild.can("p", "chat"))

    def test_child_deny_beats_parent_allow(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.add_role("muted", "guest", {"chat": False})
        guild.set_role("p", "muted")
        self.assertFalse(guild.can("p", "chat"))

    def test_deny_anywhere_on_chain_wins(self):
        guild = Guild()
        guild.add_role("root", None, {"chat": True})
        guild.add_role("a", "root", {})
        guild.add_role("b", "a", {"chat": False})
        guild.add_role("c", "b", {"chat": True})
        guild.set_role("p", "c")
        self.assertFalse(guild.can("p", "chat"))


class CacheInvalidationTest(unittest.TestCase):
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
        guild.add_role("guest", None, {})
        guild.add_role("member", "guest", {})
        guild.set_role("p", "member")
        self.assertFalse(guild.can("p", "chat"))
        guild.add_role("guest", None, {"chat": True})
        self.assertTrue(guild.can("p", "chat"))

    def test_same_sequence_replays_identically(self):
        def run():
            guild = Guild()
            results = []
            guild.add_role("guest", None, {"chat": True})
            guild.add_role("member", "guest", {"chat": False})
            guild.set_role("p", "member")
            results.append(guild.can("p", "chat"))
            guild.add_role("member", "guest", {})
            results.append(guild.can("p", "chat"))
            guild.set_role("p", "guest")
            results.append(guild.can("p", "chat"))
            return results
        self.assertEqual(run(), run())


class CycleTest(unittest.TestCase):
    def test_two_node_cycle_raises(self):
        guild = Guild()
        guild.add_role("a", "b", {})
        with self.assertRaises(PermError):
            guild.add_role("b", "a", {})

    def test_self_parent_raises(self):
        guild = Guild()
        with self.assertRaises(PermError):
            guild.add_role("a", "a", {})

    def test_long_cycle_raises(self):
        guild = Guild()
        guild.add_role("a", "b", {})
        guild.add_role("b", "c", {})
        with self.assertRaises(PermError):
            guild.add_role("c", "a", {})

    def test_reparent_into_cycle_raises(self):
        guild = Guild()
        guild.add_role("a", None, {})
        guild.add_role("b", "a", {})
        with self.assertRaises(PermError):
            guild.add_role("a", "b", {})

    def test_failed_add_keeps_old_role(self):
        guild = Guild()
        guild.add_role("a", None, {"chat": True})
        guild.add_role("b", "a", {})
        with self.assertRaises(PermError):
            guild.add_role("a", "b", {"chat": False})
        guild.set_role("p", "a")
        self.assertTrue(guild.can("p", "chat"))

    def test_dangling_parent_is_allowed(self):
        guild = Guild()
        guild.add_role("a", "not-yet", {"chat": True})
        guild.set_role("p", "a")
        self.assertTrue(guild.can("p", "chat"))


class ScaleTest(unittest.TestCase):
    def test_scanned_independent_of_role_count(self):
        guild = Guild()
        for index in range(2000):
            guild.add_role("r-%d" % index, None, {"chat": True})
        guild.set_role("p", "r-1999")
        for _ in range(2000):
            guild.cache.clear()
            guild.can("p", "chat")
        self.assertLessEqual(guild.scanned_count(), 6000)

    def test_scanned_grows_only_with_chain_length(self):
        guild = Guild()
        depth = 10
        guild.add_role("r0", None, {"chat": True})
        for index in range(1, depth):
            guild.add_role("r%d" % index, "r%d" % (index - 1), {})
        for index in range(2000):
            guild.add_role("noise-%d" % index, None, {})
        guild.set_role("p", "r%d" % (depth - 1))
        before = guild.scanned_count()
        guild.can("p", "chat")
        self.assertEqual(guild.scanned_count() - before, depth)

    def test_cache_hits_do_not_scan(self):
        guild = Guild()
        guild.add_role("guest", None, {"chat": True})
        guild.set_role("p", "guest")
        guild.can("p", "chat")
        scanned = guild.scanned_count()
        for _ in range(100000):
            guild.can("p", "chat")
        self.assertEqual(guild.scanned_count(), scanned)


PERMS = ("chat", "ban", "kick", "invite")


def reference_can(roles, members, member, perm):
    """沿链判定 + 否决优先，不做缓存。"""
    role = members.get(member)
    allowed = False
    visited = set()
    while role is not None and role in roles and role not in visited:
        visited.add(role)
        value = roles[role]["rules"].get(perm)
        if value is not None:
            if not value:
                return False
            allowed = True
        role = roles[role]["parent"]
    return allowed


def reference_has_cycle(roles, name, parent):
    node = parent
    visited = set()
    while node is not None and node not in visited:
        if node == name:
            return True
        visited.add(node)
        entry = roles.get(node)
        node = entry["parent"] if entry is not None else None
    return False


class DifferentialTest(unittest.TestCase):
    def test_random_sequences_match_reference(self):
        rng = random.Random(20260930)
        mismatches = 0
        for _ in range(200):
            guild = Guild()
            roles = {}
            members = {}
            for _ in range(40):
                op = rng.choice(("add", "set", "can", "can"))
                if op == "add":
                    name = "r%d" % rng.randrange(8)
                    parent = rng.choice(
                        (None, "r%d" % rng.randrange(8), "dangling")
                    )
                    rules = {
                        perm: rng.random() < 0.5
                        for perm in PERMS
                        if rng.random() < 0.5
                    }
                    if reference_has_cycle(roles, name, parent):
                        with self.assertRaises(PermError):
                            guild.add_role(name, parent, rules)
                    else:
                        guild.add_role(name, parent, rules)
                        roles[name] = {"parent": parent, "rules": dict(rules)}
                elif op == "set":
                    member = "p%d" % rng.randrange(4)
                    role = rng.choice(("r%d" % rng.randrange(8), "ghost"))
                    guild.set_role(member, role)
                    members[member] = role
                else:
                    member = "p%d" % rng.randrange(4)
                    perm = rng.choice(PERMS + ("unseen",))
                    expected = reference_can(roles, members, member, perm)
                    if guild.can(member, perm) != expected:
                        mismatches += 1
        self.assertEqual(mismatches, 0)


if __name__ == "__main__":
    unittest.main()
