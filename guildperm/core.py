"""公会权限：角色继承、否决优先、缓存失效。

缺陷：只看成员的直接角色不看继承链、allow 会覆盖父角色的 deny、角色改动后缓存不失效、
权限查询全扫所有角色、继承环不检测。
"""


class PermError(ValueError):
    """权限配置不合法。"""


class Guild:
    """公会权限表。"""

    def __init__(self):
        self.roles = {}
        self.members = {}
        self.cache = {}
        self.scanned = 0

    def add_role(self, name, parent=None, rules=None):
        """加一个角色。缺陷：不检测继承环。"""
        self.roles[name] = {"parent": parent, "rules": dict(rules or {})}
        self.cache.clear()

    def set_role(self, member, role):
        """给成员换角色。缺陷：忘了清缓存，旧权限还会生效。"""
        self.members[member] = role

    def can(self, member, perm):
        """权限判定。缺陷：只看直接角色、allow 覆盖 deny、每次全扫所有角色。"""
        cached = self.cache.get((member, perm))
        if cached is not None:
            return cached
        self.scanned += len(self.roles)
        role = self.members.get(member)
        allowed = False
        if role in self.roles and perm in self.roles[role]["rules"]:
            allowed = self.roles[role]["rules"][perm]
        self.cache[(member, perm)] = allowed
        return allowed

    def scanned_count(self):
        return self.scanned
