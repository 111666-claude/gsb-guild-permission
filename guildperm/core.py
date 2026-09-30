"""公会权限：角色继承、否决优先、缓存失效。

判定沿成员角色的 ``parent`` 链进行：成员角色没有该规则时沿链向上找；链上
任意角色显式 ``deny``（False）时结果即否决，任何 ``allow`` 都不许覆盖它。
``set_role`` 与 ``add_role`` 都会让旧缓存失效；``add_role`` 发现继承环时
抛 :class:`PermError`。``can`` 单次代价 O(链长)，不随角色总数线性增长。
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
        """加一个角色；发现继承环时抛 PermError，并失效全部缓存。"""
        node = parent
        visited = set()
        while node is not None and node not in visited:
            if node == name:
                raise PermError("角色继承存在环: %s" % name)
            visited.add(node)
            entry = self.roles.get(node)
            node = entry["parent"] if entry is not None else None
        self.roles[name] = {"parent": parent, "rules": dict(rules or {})}
        self.cache.clear()

    def set_role(self, member, role):
        """给成员换角色，并失效全部缓存。"""
        self.members[member] = role
        self.cache.clear()

    def can(self, member, perm):
        """权限判定：沿继承链找规则，链上显式 deny 优先于任何 allow。"""
        key = (member, perm)
        cached = self.cache.get(key)
        if cached is not None:
            return cached
        allowed = False
        role = self.members.get(member)
        visited = set()
        while role is not None and role not in visited:
            entry = self.roles.get(role)
            if entry is None:
                break
            visited.add(role)
            self.scanned += 1
            value = entry["rules"].get(perm)
            if value is not None:
                if not value:
                    allowed = False
                    break
                allowed = True
            role = entry["parent"]
        self.cache[key] = allowed
        return allowed

    def scanned_count(self):
        return self.scanned
