# JeecgBoot 3.9.x 缓存常量核对指南

## 适用边界

本文件不复制一份“完整常量接口”。`CacheConstant` 通常来自 `jeecg-boot-common` 依赖，具体字段和值可能随版本变化；复制接口只会制造第二份会过期的真相。

使用任何缓存常量前按以下优先级核对：

1. 当前项目源码中的 import 和既有调用。
2. 构建工具解析出的实际 `jeecg-boot-common` 版本及其 class/Jar。
3. 当前 profile 使用的 Redis、CacheManager 和认证配置。
4. 本文件只用于帮助定位，不覆盖前三项。

## 当前 3.9.x 常见常量

项目代码中常见以下 `CacheConstant` 名称：

```java
CacheConstant.SYS_DICT_CACHE
CacheConstant.SYS_ENABLE_DICT_CACHE
CacheConstant.SYS_DICT_TABLE_CACHE
CacheConstant.SYS_DICT_TABLE_BY_KEYS_CACHE
CacheConstant.SYS_USERS_CACHE
CacheConstant.SYS_DEPARTS_CACHE
CacheConstant.SYS_DEPART_IDS_CACHE
CacheConstant.SYS_DATA_PERMISSIONS_CACHE
CacheConstant.SYS_DYNAMICDB_CACHE
CacheConstant.GATEWAY_ROUTES
```

不要仅凭此列表判断某个常量存在。先在当前仓库搜索使用点；若类来自依赖，再检查实际解析到的 Jar：

```bash
rg -n "CacheConstant\." jeecg-boot --glob "*.java" --glob "!**/target/**"
javap -classpath /absolute/path/to/jeecg-boot-common.jar org.jeecg.common.constant.CacheConstant
```

当前项目源码中的 `CommonConstant` 可见以下认证和字典相关名称：

```java
CommonConstant.PREFIX_USER_TOKEN
CommonConstant.PREFIX_USER_SHIRO_CACHE
CommonConstant.DICT_TEXT_SUFFIX
CommonConstant.DICT_COLOR_SUFFIX
CommonConstant.DEPART_NAME_REDIS_KEY_PRE
```

`PREFIX_USER_TOKEN` 和 `PREFIX_USER_SHIRO_CACHE` 只属于仍启用 Shiro/JWT 的认证链路。启用 Sa-Token profile 时，不得拿这些常量另造一套认证缓存。

## Spring Cache Key 规则

Spring Cache 的物理 Redis key 由 CacheManager、cache name、key expression 和序列化器共同决定。不要手工假设一定是某个字符串格式。

处理失效时优先复用项目现有写法：

```java
@CacheEvict(value = CacheConstant.SYS_DICT_CACHE, allEntries = true)
```

必须按前缀清理且当前依赖确实提供 `RedisUtil.removeAll` 时，传前缀本身，不附加星号：

```java
redisUtil.removeAll(CacheConstant.SYS_DICT_CACHE + "::" + dictCode);
```

在已核对的实现中，`removeAll` 内部会追加 `*` 并扫描匹配键。升级依赖后仍需重新核对实现。

## 自定义业务 Key

使用稳定、短小、分层的命名：

```text
{应用}:{模块}:{业务}:{标识}
```

示例：

```java
String key = "myapp:order:detail:" + orderId;
String lockKey = "myapp:order:lock:" + orderId;
```

禁止把用户输入、密码、Token 明文或超长 JSON 拼进 key。批量失效需求应在设计 key 时确定公共前缀，不要事后依赖全库 `KEYS`。

## TTL

- 框架缓存 TTL：读取当前项目的 CacheManager / RedisConfig，禁止引用旧版本固定值。
- 业务缓存 TTL：按数据生命周期确定并显式设置。
- 验证码、幂等标记、临时状态必须有短 TTL。
- 分布式锁的 leaseTime 不是普通缓存 TTL；两者不要混用。
- 永久缓存必须有明确业务理由和失效路径。

## 版本核对清单

- `pom.xml` 的 JeecgBoot 版本是 3.9.x。
- Redis 配置键是 `spring.data.redis`。
- `RedisUtil` 方法签名已从实际依赖核对。
- `CacheConstant` 名称已从实际依赖核对。
- 当前认证 profile 是 Shiro/JWT 还是 Sa-Token 已确认。
- CacheManager 的 TTL 和序列化策略已确认。
