# jeecg-boot Redis 常见问题排查

> 适用边界：仅用于已确认的 JeecgBoot 3.9.x / Spring Boot 3 项目。命令和 Java 片段执行前必须与当前 profile 配置、项目源码及实际依赖 API 对照。

## 目录
1. [连接问题](#连接问题)
2. [序列化问题](#序列化问题)
3. [缓存一致性问题](#缓存一致性问题)
4. [性能问题](#性能问题)
5. [内存问题](#内存问题)
6. [分布式锁问题](#分布式锁问题)

---

## 连接问题

### 问题：Redis 连接超时

**症状**：
```
redis.connection.TimeoutException: Command timed out
io.lettuce.core.RedisConnectionTimeoutException: Command timed out
```

**排查步骤**：

1. **检查 Redis 服务状态**
```bash
# 检查 Redis 是否运行
redis-cli ping

# 检查 Redis 端口
netstat -an | grep 6379
```

2. **检查配置**
```yaml
# application-dev.yml
spring:
  data:
    redis:
      host: 127.0.0.1  # 确认 IP 正确
      port: 6379        # 确认端口正确
      password: ''      # 如果设置了密码，必须配置
      database: 0
      timeout: 3000ms   # 增加超时时间

# Lettuce 连接池配置
spring:
  data:
    redis:
      lettuce:
        pool:
          max-active: 8   # 最大连接数
          max-idle: 8     # 最大空闲连接
          min-idle: 0     # 最小空闲连接
          max-wait: -1ms  # 获取连接最大等待时间
```

3. **检查防火墙**
```bash
# 云服务器需要开放安全组
# 本地防火墙检查
sudo iptables -L | grep 6379
```

### 问题：Redis 连接被拒绝

**症状**：
```
io.lettuce.core.RedisConnectionException: Unable to connect to localhost:6379
```

**解决方案**：

1. 启动 Redis 服务
```bash
# Linux/Mac
redis-server

# Windows
redis-server.exe

# Docker
docker run -d -p 6379:6379 redis:latest
```

2. 检查 Redis 配置文件
```conf
# redis.conf
bind 127.0.0.1 0.0.0.0  # 允许远程连接
protected-mode yes      # 生产环境开启
requirepass yourpassword # 设置密码后需在 application.yml 中配置
```

### 问题：连接池耗尽

**症状**：
```
redis.connectionpool.TimeoutException: No available connection
```

**解决方案**：

```yaml
spring:
  data:
    redis:
      lettuce:
        pool:
          max-active: 20   # 增加最大连接数
          max-idle: 10
          min-idle: 5
          max-wait: 3000ms # 设置等待超时
        shutdown-timeout: 100ms
```

---

## 序列化问题

### 问题：反序列化失败 ClassCastException

**症状**：
```java
java.lang.ClassCastException: java.util.LinkedHashMap cannot be cast to com.example.User
```

**原因**：jeecg-boot 使用 Jackson2JsonRedisSerializer，存储对象被序列化为 JSON，取出时默认转为 LinkedHashMap。

**解决方案**：

1. **确保实体类有 getter/setter**
```java
public class User {
    private String id;
    private String name;

    // 必须提供 getter/setter
    public String getId() { return id; }
    public void setId(String id) { this.id = id; }
    public String getName() { return name; }
    public void setName(String name) { this.name = name; }
}
```

2. **使用 RedisTemplate 指定类型**
```java
// 不推荐：直接强转
User user = (User) redisUtil.get("user:1"); // 可能抛异常

// 推荐：用 ObjectMapper 转换
ObjectMapper mapper = new ObjectMapper();
User user = mapper.convertValue(redisUtil.get("user:1"), User.class);

// 或使用 RedisTemplate 的序列化配置
redisTemplate.setValueSerializer(new Jackson2JsonRedisSerializer<>(User.class));
```

3. **存储 JSON 字符串**
```java
// 存储
String json = JSON.toJSONString(user);
redisUtil.set("user:1", json);

// 获取
String json = (String) redisUtil.get("user:1");
User user = JSON.parseObject(json, User.class);
```

### 问题：日期序列化异常

**症状**：
```
com.fasterxml.jackson.databind.exc.InvalidDefinitionException:
Java 8 date/time type `java.time.LocalDateTime` not supported by default
```

**解决方案**：

```java
// 全局配置 Jackson（已存在于 RedisConfig）
@Configuration
public class RedisConfig {
    @Bean
    public RedisTemplate<String, Object> redisTemplate(RedisConnectionFactory factory) {
        Jackson2JsonRedisSerializer<Object> serializer = new Jackson2JsonRedisSerializer<>(Object.class);

        ObjectMapper om = new ObjectMapper();
        om.setVisibility(PropertyAccessor.ALL, JsonAutoDetect.Visibility.ANY);
        // 关键：支持 Java 8 日期类型
        om.registerModule(new JavaTimeModule());
        om.disable(SerializationFeature.WRITE_DATES_AS_TIMESTAMPS);

        serializer.setObjectMapper(om);

        RedisTemplate<String, Object> template = new RedisTemplate<>();
        template.setConnectionFactory(factory);
        template.setKeySerializer(new StringRedisSerializer());
        template.setValueSerializer(serializer);
        template.setHashKeySerializer(new StringRedisSerializer());
        template.setHashValueSerializer(serializer);
        template.afterPropertiesSet();
        return template;
    }
}
```

### 问题：枚举序列化问题

**症状**：枚举值存储为数字或名称不一致。

**解决方案**：

```java
// 方案1：使用 @JsonValue
public enum Status {
    ACTIVE(1, "激活"),
    INACTIVE(0, "禁用");

    private final int code;
    private final String desc;

    @JsonValue
    public int getCode() { return code; }
}

// 方案2：自定义序列化器
public class EnumSerializer extends JsonSerializer<Enum<?>> {
    @Override
    public void serialize(Enum<?> value, JsonGenerator gen, SerializerProvider serializers) throws IOException {
        gen.writeString(value.name());
    }
}
```

---

## 缓存一致性问题

### 问题：更新数据库后缓存未清除

**症状**：修改数据后，接口仍返回旧数据。

**原因**：忘记清除缓存或缓存注解使用不当。

**解决方案**：

```java
// 1. 查询时使用 @Cacheable
@Cacheable(value = CacheConstant.SYS_DICT_CACHE, key = "#code", unless = "#result == null")
public List<DictModel> queryDictItemsByCode(String code) {
    return sysDictMapper.queryDictItemsByCode(code);
}

// 2. 更新/删除时必须清除缓存
@CacheEvict(value = CacheConstant.SYS_DICT_CACHE, allEntries = true)
public void updateDict(SysDict dict) {
    sysDictMapper.updateById(dict);
}

// 3. 精确清除指定 key
@CacheEvict(value = "userCache", key = "#user.id")
public void updateUser(User user) {
    userMapper.updateById(user);
}

// 4. 手动清除缓存（无法使用注解时）
public void updateData(Data data) {
    dataMapper.updateById(data);
    // 手动清除相关缓存
    redisUtil.del("data:" + data.getId());
    redisUtil.removeAll("data:list:");
}
```

### 问题：多服务实例缓存不一致

**场景**：多台服务器部署，A 服务更新数据，B 服务缓存未清除。

**解决方案**：

1. **使用 Redis 发布订阅**
```java
// 更新服务
@Service
public class UpdateService {
    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    public void updateData(Data data) {
        dataMapper.updateById(data);
        // 发布缓存清除消息
        redisTemplate.convertAndSend("cache:invalidate", "data:" + data.getId());
    }
}

// 订阅服务
@Component
public class CacheInvalidationListener implements MessageListener {
    @Autowired
    private RedisUtil redisUtil;

    @Override
    public void onMessage(Message message, byte[] pattern) {
        String key = new String(message.getBody());
        redisUtil.del(key);
    }
}
```

2. **直接用 Redis 共享缓存**
```java
// 多服务实例共享同一 Redis，缓存自动一致
@Cacheable(value = "sharedCache", key = "#id")
public Data getData(String id) {
    return dataMapper.selectById(id);
}
```

### 问题：缓存穿透（查询不存在的数据）

**症状**：大量查询不存在的数据，每次都打到数据库。

**解决方案**：

```java
// 1. 缓存空值（unless = "#result == null" 的反面）
@Cacheable(value = "userCache", key = "#id")
public User getUser(String id) {
    User user = userMapper.selectById(id);
    if (user == null) {
        // 缓存一个特殊标记，短期过期
        redisUtil.set("user:" + id, "NULL", 60);
    }
    return user;
}

// 2. 使用布隆过滤器
@Component
public class UserBloomFilter {
    @Autowired
    private RedissonClient redissonClient;

    @PostConstruct
    public void init() {
        RBloomFilter<String> filter = redissonClient.getBloomFilter("user:bloom");
        filter.tryInit(1000000, 0.01);

        // 预加载所有用户 ID
        List<String> allIds = userMapper.selectAllIds();
        for (String id : allIds) {
            filter.add(id);
        }
    }

    public boolean mightContain(String id) {
        return filter.contains(id);
    }
}

// 使用
public User getUser(String id) {
    if (!bloomFilter.mightContain(id)) {
        return null; // 一定不存在
    }
    return userMapper.selectById(id);
}
```

### 问题：缓存雪崩（大量 key 同时过期）

**症状**：某个时刻大量缓存失效，数据库压力骤增。

**解决方案**：

```java
// 1. 设置随机过期时间
public void cacheWithRandomTTL(String key, Object value) {
    int baseTTL = 3600; // 1小时
    int randomTTL = ThreadLocalRandom.current().nextInt(300, 900); // 5-15分钟随机
    redisUtil.set(key, value, baseTTL + randomTTL);
}

// 2. 使用多级缓存
@Cacheable(value = "l1Cache", key = "#id") // 本地缓存（Caffeine）
public User getUserFromL1(String id) {
    return getUserFromL2(id);
}

@Cacheable(value = "l2Cache", key = "#id") // Redis 缓存
public User getUserFromL2(String id) {
    return userMapper.selectById(id);
}

// 3. 缓存预热（定时刷新）
@Scheduled(cron = "0 */10 * * * ?") // 每10分钟
public void warmupCache() {
    // 提前刷新即将过期的热点数据
    List<String> hotKeys = getHotKeys();
    for (String key : hotKeys) {
        Object value = redisUtil.get(key);
        if (value != null) {
            redisUtil.set(key, value, 3600); // 刷新 TTL
        }
    }
}
```

---

## 性能问题

### 问题：keys 命令阻塞

**症状**：使用 `keys` 命令时 Redis 卡顿。

**原因**：`keys` 是 O(N) 复杂度，会阻塞 Redis。

**解决方案**：

```java
// ❌ 错误用法
Set<String> keys = redisTemplate.keys("sys:cache:dict*");
redisTemplate.delete(keys);

// ✅ 正确用法（批量删除）
redisUtil.removeAll("sys:cache:dict");

// ✅ 正确用法（SCAN 命令）
public Set<String> scanKeys(String pattern) {
    Set<String> keys = new HashSet<>();
    RedisConnection connection = redisTemplate.getConnectionFactory().getConnection();
    ScanOptions options = ScanOptions.scanOptions().match(pattern).count(100).build();
    Cursor<byte[]> cursor = connection.scan(options);
    while (cursor.hasNext()) {
        keys.add(new String(cursor.next()));
    }
    return keys;
}
```

### 问题：大 key 导致性能下降

**症状**：某个 key 操作特别慢。

**原因**：存储了过大的对象（如大 List、大 Hash）。

**解决方案**：

```java
// 1. 拆分大 key
// ❌ 错误：存储大 List
List<Object> bigList = fetchData(100000); // 10万条数据
redisUtil.set("big:list", bigList);

// ✅ 正确：分片存储
for (int i = 0; i < 100; i++) {
    int from = i * 1000;
    int to = Math.min(from + 1000, 100000);
    List<Object> chunk = fetchData(from, to);
    redisTemplate.opsForList().rightPush("big:list:" + i, chunk);
}

// 2. 使用 Hash 代替大 String
// ❌ 错误
String bigJson = JSON.toJSONString(largeObject);
redisUtil.set("big:object", bigJson);

// ✅ 正确
redisUtil.hset("object:" + id, "field1", value1);
redisUtil.hset("object:" + id, "field2", value2);

// 3. 监控 key 大小
public void checkKeySize(String key) {
    Long size = redisTemplate.execute((RedisCallback<Long>) connection -> {
        return connection.dbSize().longValue();
    });
    if (size > 1024 * 1024) { // 大于 1MB
        log.warn("Large key detected: {}, size: {}", key, size);
    }
}
```

### 问题：慢查询堆积

**症状**：Redis CPU 使用率高，响应变慢。

**排查**：

```bash
# 1. 查看 Redis 慢查询
redis-cli slowlog get 10

# 2. 监控命令
redis-cli monitor

# 3. 查看客户端连接
redis-cli client list
```

**优化**：

```java
// 1. 使用 Pipeline 批量操作
public void batchSet(Map<String, Object> data) {
    redisTemplate.executePipelined((RedisCallback<Object>) connection -> {
        data.forEach((key, value) -> {
            connection.set(key.getBytes(), serialize(value));
        });
        return null;
    });
}

// 2. 避免在循环中操作 Redis
// ❌ 错误
for (String id : ids) {
    redisUtil.get("user:" + id);
}

// ✅ 正确
List<String> keys = ids.stream().map(id -> "user:" + id).collect(Collectors.toList());
List<Object> users = redisTemplate.opsForValue().multiGet(keys);

// 3. 使用 Lua 脚本减少网络往返
String luaScript =
    "local results = {} " +
    "for i, key in ipairs(KEYS) do " +
    "    table.insert(results, redis.call('GET', key)) " +
    "end " +
    "return results";

List<Object> results = redisTemplate.execute(
    new DefaultRedisScript<>(luaScript, List.class),
    keys
);
```

---

## 内存问题

### 问题：Redis 内存溢出

**症状**：
```
OOM command not allowed when used memory > 'maxmemory'
```

**解决方案**：

```bash
# 1. 查看 Redis 内存使用
redis-cli info memory

# 2. 配置最大内存和淘汰策略
# redis.conf
maxmemory 2gb
maxmemory-policy allkeys-lru  # LRU 淘汰
```

**Java 代码优化**：

```java
// 1. 为所有缓存设置 TTL
redisUtil.set("key", value);  // ❌ 没有过期时间
redisUtil.set("key", value, 3600);  // ✅ 设置过期时间

// 2. 监控内存使用
@Component
public class RedisMemoryMonitor {
    @Autowired
    private RedisConnectionFactory connectionFactory;

    @Scheduled(cron = "0 */5 * * * ?")
    public void checkMemory() {
        RedisConnection connection = connectionFactory.getConnection();
        Properties info = connection.info("memory");
        String usedMemory = info.getProperty("used_memory_human");
        String maxMemory = info.getProperty("maxmemory_human");

        log.info("Redis memory: {} / {}", usedMemory, maxMemory);

        // 超过 80% 告警
        long used = Long.parseLong(info.getProperty("used_memory"));
        long max = Long.parseLong(info.getProperty("maxmemory"));
        if (used > max * 0.8) {
            log.error("Redis memory usage exceeds 80%");
        }
    }
}

// 3. 不要伪造 RedisUtil.execute 等不存在的方法来“清理过期 key”
// Redis 自己负责过期键回收；业务侧负责给缓存设置 TTL，并监控 maxmemory 与淘汰策略。
```

### 问题：内存碎片严重

**症状**：`used_memory_rss` 远大于 `used_memory`

**解决方案**：

```bash
# 执行内存整理
redis-cli memory purge

# 重启 Redis（慎用）
redis-cli shutdown
redis-server
```

---

## 分布式锁问题

### 问题：锁无法释放

**症状**：加锁后异常退出，导致死锁。

**解决方案**：

```java
public void safeLockMethod(String id) {
    RLock lock = redissonClient.getLock("lock:" + id);
    try {
        // 使用 tryLock 而非 lock
        if (lock.tryLock(10, 30, TimeUnit.SECONDS)) {
            try {
                doBusiness();
            } finally {
                // 检查锁是否为自己持有
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

### 问题：锁超时导致业务未完成

**症状**：业务执行超过 lock leaseTime，锁被释放。

**解决方案**：

```java
// 使用不带 leaseTime 的重载才能启用默认看门狗续期；具体重载以当前 Redisson 版本为准
if (lock.tryLock(10, TimeUnit.SECONDS)) {
    try {
        // 业务逻辑
    } finally {
        if (lock.isHeldByCurrentThread()) {
            lock.unlock();
        }
    }
}

// 或设置足够长的 leaseTime
if (lock.tryLock(10, 300, TimeUnit.SECONDS)) { // 5分钟
    // 业务逻辑
}
```

### 问题：主从切换导致锁丢失

**症状**：Redis 主节点宕机，从节点升级为主节点，锁信息丢失。

**解决方案**：

```java
// 使用 RedissonRedLock（红锁）- 跨多个 Redis 实例
@Autowired
private RedissonClient redisson1;
private RedissonClient redisson2;
private RedissonClient redisson3;

public void redLockMethod() {
    RLock lock1 = redisson1.getLock("lock:resource");
    RLock lock2 = redisson2.getLock("lock:resource");
    RLock lock3 = redisson3.getLock("lock:resource");

    RedissonRedLock redLock = new RedissonRedLock(lock1, lock2, lock3);

    try {
        if (redLock.tryLock(10, 30, TimeUnit.SECONDS)) {
            try {
                doBusiness();
            } finally {
                redLock.unlock();
            }
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}
```

---

## 监控与诊断

### 监控指标

```java
@Component
public class RedisHealthIndicator implements HealthIndicator {

    @Autowired
    private RedisConnectionFactory connectionFactory;

    @Override
    public Health health() {
        try {
            RedisConnection connection = connectionFactory.getConnection();

            // 1. Ping 测试
            String pong = connection.ping();
            if (!"PONG".equals(pong)) {
                return Health.down().withDetail("ping", pong).build();
            }

            // 2. 获取信息
            Properties info = connection.info();
            Properties memory = connection.info("memory");

            return Health.up()
                .withDetail("version", info.getProperty("redis_version"))
                .withDetail("used_memory", memory.getProperty("used_memory_human"))
                .withDetail("connected_clients", info.getProperty("connected_clients"))
                .withDetail("uptime_in_days", info.getProperty("uptime_in_days"))
                .build();
        } catch (Exception e) {
            return Health.down().withException(e).build();
        }
    }
}
```

### 诊断工具类

```java
@Component
public class RedisDiagnostics {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    /**
     * 分析 key 的内存使用
     */
    public void analyzeKey(String key) {
        Long size = redisTemplate.execute((RedisCallback<Long>) connection -> {
            return connection.strLen(key.getBytes());
        });

        Long ttl = redisTemplate.getExpire(key, TimeUnit.SECONDS);

        log.info("Key: {}, Size: {} bytes, TTL: {} seconds", key, size, ttl);
    }

    /**
     * 扫描大 key
     */
    public List<String> findLargeKeys(String pattern, long threshold) {
        List<String> largeKeys = new ArrayList<>();
        RedisConnection connection = redisTemplate.getConnectionFactory().getConnection();
        ScanOptions options = ScanOptions.scanOptions().match(pattern).count(100).build();

        Cursor<byte[]> cursor = connection.scan(options);
        while (cursor.hasNext()) {
            byte[] key = cursor.next();
            Long size = connection.strLen(key);
            if (size > threshold) {
                largeKeys.add(new String(key));
            }
        }

        return largeKeys;
    }

    /**
     * 分析数据库大小
     */
    public Map<String, Object> analyzeDatabase() {
        RedisConnection connection = redisTemplate.getConnectionFactory().getConnection();

        Properties info = connection.info("memory");

        Map<String, Object> result = new HashMap<>();
        result.put("used_memory", info.getProperty("used_memory_human"));
        result.put("used_memory_peak", info.getProperty("used_memory_peak_human"));
        result.put("used_memory_rss", info.getProperty("used_memory_rss_human"));
        result.put("mem_fragmentation_ratio", info.getProperty("mem_fragmentation_ratio"));
        result.put("dbSize", connection.dbSize());

        return result;
    }
}
```

---

## 最佳实践总结

1. **所有缓存必须设置 TTL**
2. **使用缓存常量，避免硬编码**
3. **更新数据时清除缓存**
4. **使用 RedisUtil.removeAll 代替 keys + del**
5. **避免存储大 key，必要时拆分**
6. **分布式锁必须放在 finally 中释放**
7. **生产环境配置密码和防火墙**
8. **监控 Redis 内存和性能指标**
