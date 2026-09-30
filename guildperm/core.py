"""公会权限：角色继承、否决优先、缓存失效。

规则：
- 成员角色没有该规则时沿 ``parent`` 向上找，子角色的规则优先。
- 链上任意角色显式 ``deny``（规则值为 ``False``）时结果必为否决。
- ``set_role`` / ``add_role`` 后缓存整体失效。
- ``add_role`` 形成继承环时抛 :class:`PermError`。
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
        """加一个角色；若新边会形成继承环则抛 ``PermError``。"""
        if parent is not None and self._would_cycle(name, parent):
            raise PermError("继承环: %r -> %r" % (name, parent))
        self.roles[name] = {"parent": parent, "rules": dict(rules or {})}
        self.cache.clear()

    def set_role(self, member, role):
        """给成员换角色，并让旧判定缓存失效。"""
        self.members[member] = role
        self.cache.clear()

    def _would_cycle(self, name, parent):
        """加入 ``name -> parent`` 这条边后是否成环（允许父角色尚未注册）。"""
        current = parent
        seen = set()
        while current is not None:
            if current == name or current in seen:
                return True
            seen.add(current)
            node = self.roles.get(current)
            current = node["parent"] if node is not None else None
        return False

    def can(self, member, perm):
        """沿继承链判定；单次 O(链长)，结果缓存到下次变更前。"""
        key = (member, perm)
        if key in self.cache:
            return self.cache[key]
        allowed = False
        role = self.members.get(member)
        seen = set()
        while role is not None and role not in seen:
            seen.add(role)
            node = self.roles.get(role)
            if node is None:
                break
            self.scanned += 1
            rule = node["rules"].get(perm)
            if rule is False:
                allowed = False
                break
            if rule is True:
                allowed = True
            role = node["parent"]
        self.cache[key] = allowed
        return allowed

    def scanned_count(self):
        return self.scanned
