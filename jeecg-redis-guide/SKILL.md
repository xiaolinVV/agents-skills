---
name: jeecg-redis-guide
description: jeecg-boot 低代码平台 Redis 使用指南。涵盖三种使用方式（Jeecg RedisUtil 工具类、Spring Cache 注解、RedisTemplate 原生操作）、分布式锁、缓存策略最佳实践。使用场景：在 jeecg-boot 项目中需要使用 Redis 缓存、分布式锁、会话管理、验证码等功能时；遇到 Redis 相关问题时；需要了解 jeecg-boot 缓存机制和配置时。
---

# jeecg-boot Redis 使用指南

## Overview

在 jeecg-boot 低代码平台中使用 Redis 实现缓存、分布式锁、会话管理等功能。

## Redis 配置

### 基本配置

```yaml
# application-dev.yml
spring:
  redis:
    database: 0
    host: 127.0.0.1
    port: 6379
    password: ''
    timeout: 3000ms
    lettuce:
      pool:
        max-active: 8
        max-idle: 8
        min-idle: 0
        max-wait: -1ms

# Redisson 分布式锁配置
jeecg:
  redisson:
    address: 127.0.0.1:6379
    password:
    type: STANDALONE
```

### 连接验证

```bash
# 测试 Redis 连接
redis-cli ping
# 应返回: PONG

# 查看 Redis 信息
redis-cli info
```

---

## 三种使用方式

### 方式选择指南

| 场景 | 推荐方式 | 说明 |
|------|---------|------|
| 简单 KV 操作 | **RedisUtil** | Jeecg 封装，最简单 |
| 方法级查询缓存 | **Spring Cache** | 声明式，自动管理 |
| 复杂操作/自定义 | **RedisTemplate** | 原生 API，灵活控制 |
| 分布式协调 | **Redisson** | 分布式锁、高级结构 |

### 方式一：RedisUtil 工具类（推荐用于简单操作）

```java
@Autowired
private RedisUtil redisUtil;

// String 操作
redisUtil.set("key", value);
redisUtil.set("key", value, 3600);  // 带过期时间（秒）
Object result = redisUtil.get("key");
redisUtil.del("key");

// Hash 操作
redisUtil.hset("hashKey", "field", value);
Object field = redisUtil.hget("hashKey", "field");
redisUtil.hdel("hashKey", "field1", "field2");

// Set/List 操作
redisUtil.sSet("setKey", value1, value2);
redisUtil.lSet("listKey", value);

// 通用操作
redisUtil.hasKey("key");
redisUtil.expire("key", 1800);
redisUtil.removeAll("prefix:*");  // 批量删除（推荐）
```

### 方式二：Spring Cache 注解（推荐用于方法缓存）

```java
// 查询缓存
@Cacheable(value = CacheConstant.SYS_DICT_CACHE, key = "#code", unless = "#result == null")
public List<DictModel> queryDictItemsByCode(String code) {
    return sysDictMapper.queryDictItemsByCode(code);
}

// 清除缓存
@CacheEvict(value = CacheConstant.SYS_DICT_CACHE, allEntries = true)
public void deleteDict(String id) {
    sysDictMapper.deleteById(id);
}

// 更新缓存
@CachePut(value = "userCache", key = "#result.id")
public User updateUser(User user) {
    userMapper.updateById(user);
    return user;
}
```

**重要**：数据更新/删除时必须使用 `@CacheEvict` 清除缓存。

### 方式三：RedisTemplate 原生操作（灵活控制）

```java
@Autowired
private RedisTemplate<String, Object> redisTemplate;
@Autowired
private StringRedisTemplate stringRedisTemplate;

// Value 操作
redisTemplate.opsForValue().set("key", value, 5, TimeUnit.MINUTES);
Object value = redisTemplate.opsForValue().get("key");

// Hash 操作
redisTemplate.opsForHash().put("hashKey", "field", value);
Map<Object, Object> map = redisTemplate.opsForHash().entries("hashKey");

// List 操作
redisTemplate.opsForList().rightPush("queue", item);
Object item = redisTemplate.opsForList().leftPop("queue");

// 发布订阅
redisTemplate.convertAndSend("channel", message);
```

---

## 分布式锁（Redisson）

```java
@Autowired
private RedissonClient redissonClient;

public void businessMethod(String id) {
    RLock lock = redissonClient.getLock("business:lock:" + id);
    try {
        if (lock.tryLock(10, 30, TimeUnit.SECONDS)) { // 等待10s，锁30s
            try {
                // 业务逻辑
            } finally {
                if (lock.isHeldByCurrentThread()) {
                    lock.unlock();
                }
            }
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}
```

---

## 缓存常量规范

使用 `CacheConstant` 中定义的常量，避免硬编码：

```java
import org.jeecg.common.constant.CacheConstant;

CacheConstant.SYS_DICT_CACHE            // sys:cache:dict
CacheConstant.SYS_ENABLE_DICT_CACHE     // sys:cache:dictEnable
CacheConstant.SYS_DICT_TABLE_CACHE      // sys:cache:dictTable
CacheConstant.SYS_USERS_CACHE           // sys:cache:encrypt:user
CacheConstant.SYS_DEPARTS_CACHE         // sys:cache:depart:alldata
CacheConstant.SYS_DATA_PERMISSIONS_CACHE // sys:cache:permission:datarules
```

更多常量定义详见 [references/constants.md](references/constants.md)

---

## 常见场景

### 验证码缓存

```java
// 存储（5分钟）
String key = Md5Util.md5Encode(captcha + uuid + secret, "utf-8");
redisUtil.set(key, captcha, 300);

// 校验
Object cached = redisUtil.get(key);
if (cached == null || !cached.toString().equals(input)) {
    return Result.error("验证码错误");
}
redisUtil.del(key);  // 校验成功后删除
```

### 用户 Token 管理

```java
// 登录
String token = JwtUtil.sign(username, password);
redisUtil.set(CommonConstant.PREFIX_USER_TOKEN + token, token, 7200);

// 退出
redisUtil.del(CommonConstant.PREFIX_USER_TOKEN + token);
redisUtil.del(CommonConstant.PREFIX_USER_SHIRO_CACHE + userId);
```

### 防重复提交

```java
@Around("@annotation(preventDuplicateSubmit)")
public Object around(ProceedingJoinPoint point, PreventDuplicateSubmit preventDuplicateSubmit) {
    String key = "duplicate:submit:" + request.getRequestURI() + ":" + sessionId;
    if (redisUtil.hasKey(key)) {
        throw new RuntimeException("请勿重复提交");
    }
    redisUtil.set(key, "1", preventDuplicateSubmit.time());
    try {
        return point.proceed();
    } catch (Throwable e) {
        redisUtil.del(key);  // 失败则删除标记
        throw e;
    }
}
```

---

## Key 命名规范

```
{系统}:{模块}:{业务}:{参数}
```

示例：
- `sys:cache:dict:sex` - 字典缓存
- `prefix_user_token:eyJhbGc...` - 用户 Token
- `myapp:data:user:1001` - 自定义业务数据

---

## 最佳实践

1. **所有缓存必须设置 TTL**，避免内存泄漏
2. **使用 CacheConstant 常量**，避免 key 硬编码
3. **更新数据时清除缓存**，使用 `@CacheEvict` 或手动删除
4. **使用 `redisUtil.removeAll(prefix)`** 代替 `keys + del`
5. **分布式锁必须在 finally 中释放**
6. **存储对象需要 getter/setter**（Jackson 序列化要求）

---

## 故障排查

| 问题 | 原因 | 解决方案 |
|------|------|---------|
| 连接超时 | Redis 未启动/配置错误 | 检查 host/port/password |
| ClassCastException | 反序列化类型错误 | 使用 JSON 字符串或提供 getter/setter |
| 缓存未生效 | 忘记清除缓存 | 更新时使用 @CacheEvict |
| keys 命令卡顿 | 阻塞 Redis | 使用 removeAll 或 SCAN |

详细排查指南见 [references/troubleshooting.md](references/troubleshooting.md)

---

## 资源

### [examples.md](references/examples.md)
完整代码示例，包括：
- RedisUtil 所有方法用法
- Spring Cache 所有注解
- RedisTemplate 各种数据结构操作
- Redisson 分布式锁、读写锁、信号量
- 常见业务场景代码模板

### [constants.md](references/constants.md)
缓存常量参考，包括：
- CacheConstant 完整定义
- CommonConstant 缓存常量
- Key 命名规范
- TTL 建议

### [troubleshooting.md](references/troubleshooting.md)
问题排查指南，包括：
- 连接问题排查
- 序列化问题解决
- 缓存一致性问题
- 性能优化建议
- 分布式锁问题
- 监控与诊断工具

---

## jeecg-boot 相关源码位置

| 文件 | 路径 |
|------|------|
| Redis 配置 | `application-dev.yml` (第 171-177 行) |
| RedisUtil | `org.jeecg.common.util.RedisUtil` |
| CacheConstant | `org.jeecg.common.constant.CacheConstant` |
| RedisConfig | `org.jeecg.common.modules.redis.config.RedisConfig` |
| 字典缓存示例 | `SysDictServiceImpl.java` |
| DictAspect | `org.jeecg.common.aspect.DictAspect` |
| Shiro Redis | `org.jeecg.config.shiro.ShiroRealm` |
