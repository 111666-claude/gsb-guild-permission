# guild-permission

公会权限：角色继承、否决优先、缓存失效，只用 Python 标准库。

```
python3 -m guildperm.cli --sample inherit
python3 -m guildperm.cli --sample deny
python3 -m guildperm.cli --sample cache
python3 -m guildperm.cli --sample cycle
python3 -m unittest discover -s tests -v
```

## 口径（README 为准）

- **沿继承链找规则**：成员角色没有这条规则时沿 `parent` 向上找，子角色的规则优先。
- **否决优先**：链上任意角色显式 `deny` 该权限时，最终结果必须是否决（`False`），
  `allow` 不许覆盖它。
- **缓存必须失效**：`set_role` 与 `add_role` 之后，之前的判定结果不许继续生效。
- **继承环要报错**：`add_role` 发现继承环时抛 `PermError`。
- **查询代价**：`can` 只在继承链上走，`scanned_count()` 不随角色总数线性增长。
- **规模**：2000 个角色、每秒 10 万次权限判定，单次 O(链长)，内存 O(角色数)。

## 输出契约（不改格式）

```
allowed=true
allowed=false
first=true second=false
cycle=true
scanned<=6000
```

## 目录

```
guildperm/core.py   角色继承、否决与缓存
guildperm/cli.py    命令行入口
tests/              unittest 用例
```
