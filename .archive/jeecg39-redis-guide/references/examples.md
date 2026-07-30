# jeecg-boot Redis 代码示例

> 适用边界：这些是 JeecgBoot 3.9.x 的模式示例，不是可直接粘贴的完整实现。使用前必须核对当前项目解析到的 `RedisUtil`、`CacheConstant`、Spring Data Redis 和 Redisson API。Token/在线用户示例仅适用于仍启用 Shiro/JWT 的 profile，不适用于 Sa-Token profile。

## 目录
1. [RedisUtil 工具类](#redisutil-工具类)
2. [Spring Cache 注解](#spring-cache-注解)
3. [RedisTemplate 原生操作](#redistemplate-原生操作)
4. [Redisson 分布式锁](#redisson-分布式锁)
5. [常见业务场景](#常见业务场景)

---

## RedisUtil 工具类

### String 操作

```java
@Autowired
private RedisUtil redisUtil;

// 基本存储
redisUtil.set("user:1001", userObj);
redisUtil.set("user:1001", userObj, 3600); // 1小时过期

// 获取
User user = (User) redisUtil.get("user:1001");

// 删除
redisUtil.del("user:1001");

// 计数器
long count = redisUtil.incr("view:count", 1);
redisUtil.decr("stock:1001", 1);

// 判断是否存在
boolean exists = redisUtil.hasKey("user:1001");

// 设置过期时间
redisUtil.expire("user:1001", 1800); // 30分钟
```

### Hash 操作

```java
// 存储 Hash
redisUtil.hset("user:1001:info", "name", "张三");
redisUtil.hset("user:1001:info", "age", "25");
redisUtil.hset("user:1001:info", "city", "北京");

// 获取 Hash 值
String name = (String) redisUtil.hget("user:1001:info", "name");

// 获取整个 Hash（使用 RedisTemplate）
Map<Object, Object> userInfo = redisTemplate.opsForHash().entries("user:1001:info");

// 删除 Hash 字段
redisUtil.hdel("user:1001:info", "age", "city");

// 判断 Hash 字段存在
boolean hasField = redisTemplate.opsForHash().hasKey("user:1001:info", "name");
```

### Set 操作

```java
// 添加元素
redisUtil.sSet("tags:article:1001", "java", "spring", "redis");

// 获取所有元素
Set<Object> tags = redisUtil.sGet("tags:article:1001");

// 获取集合大小（使用 RedisTemplate）
Long size = redisTemplate.opsForSet().size("tags:article:1001");

// 判断元素是否存在
boolean isMember = redisTemplate.opsForSet().isMember("tags:article:1001", "java");

// 移除元素
redisTemplate.opsForSet().remove("tags:article:1001", "redis");
```

### List 操作

```java
// 右侧添加（队列）
redisUtil.lSet("queue:task", taskId);

// 左侧添加（栈）
redisTemplate.opsForList().leftPush("stack:action", actionData);

// 获取范围列表
List<Object> tasks = redisUtil.lGet("queue:task", 0, 9); // 前10个

// 获取列表大小
Long size = redisTemplate.opsForList().size("queue:task");

// 左侧弹出（队列消费）
Object task = redisTemplate.opsForList().leftPop("queue:task");
```

### 批量操作

```java
// 批量删除（推荐）
redisUtil.removeAll("sys:cache:dict"); // 传前缀；框架实现会追加 *

// 批量设置过期
List<String> keys = Arrays.asList("key1", "key2", "key3");
for (String key : keys) {
    redisUtil.expire(key, 3600);
}
```

---

## Spring Cache 注解

### @Cacheable - 查询缓存

```java
@Service
public class UserServiceImpl {

    // 基本用法
    @Cacheable(value = "userCache", key = "#id")
    public User getUserById(String id) {
        return userMapper.selectById(id);
    }

    // 复合 key
    @Cacheable(value = "userCache", key = "#userId + ':' + #type")
    public User getUserByType(String userId, String type) {
        return userMapper.selectByType(userId, type);
    }

    // 条件缓存
    @Cacheable(value = "userCache", key = "#id", unless = "#result == null")
    public User getUserById(String id) {
        return userMapper.selectById(id);
    }

    // 条件缓存（只缓存特定条件）
    @Cacheable(value = "activeUserCache", key = "#id", condition = "#id.length() > 3")
    public User getActiveUser(String id) {
        return userMapper.selectById(id);
    }

    // 使用 CacheConstant
    @Cacheable(value = CacheConstant.SYS_DICT_CACHE, key = "#code", unless = "#result == null")
    public List<DictModel> queryDictItemsByCode(String code) {
        return sysDictMapper.queryDictItemsByCode(code);
    }
}
```

### @CacheEvict - 清除缓存

```java
// 删除后清除整个缓存
@CacheEvict(value = "userCache", allEntries = true)
public void deleteUser(String id) {
    userMapper.deleteById(id);
}

// 删除后清除指定 key
@CacheEvict(value = "userCache", key = "#user.id")
public void updateUser(User user) {
    userMapper.updateById(user);
}

// 清除多个缓存
@CacheEvict(value = {
    CacheConstant.SYS_DICT_CACHE,
    CacheConstant.SYS_ENABLE_DICT_CACHE
}, allEntries = true)
public Result<SysDict> delete(String id) {
    sysDictMapper.deleteById(id);
    return Result.OK();
}

// 方法执行前清除
@CacheEvict(value = "userCache", key = "#id", beforeInvocation = true)
public void updateUserWithPreClear(String id, User user) {
    userMapper.updateById(user);
}
```

### @CachePut - 更新缓存

```java
// 方法执行后更新缓存
@CachePut(value = "userCache", key = "#result.id")
public User createUser(User user) {
    userMapper.insert(user);
    return user; // 返回值会更新到缓存
}

@CachePut(value = "userCache", key = "#user.id")
public User updateAndRefresh(User user) {
    userMapper.updateById(user);
    return user;
}
```

### @Caching - 组合注解

```java
@Caching(
    cacheable = {
        @Cacheable(value = "userCache", key = "#id")
    },
    evict = {
        @CacheEvict(value = "userListCache", allEntries = true)
    }
)
public User getUser(String id) {
    return userMapper.selectById(id);
}
```

### @CacheConfig - 类级别配置

```java
@Service
@CacheConfig(cacheNames = "userCache")
public class UserServiceImpl {

    @Cacheable(key = "#id")
    public User getUser(String id) {
        return userMapper.selectById(id);
    }

    @CacheEvict(key = "#user.id")
    public void updateUser(User user) {
        userMapper.updateById(user);
    }
}
```

---

## RedisTemplate 原生操作

### ValueOperations - 字符串操作

```java
@Autowired
private RedisTemplate<String, Object> redisTemplate;

// 基本操作
redisTemplate.opsForValue().set("key", value);
redisTemplate.opsForValue().set("key", value, 5, TimeUnit.MINUTES);
redisTemplate.opsForValue().set("key", value, Duration.ofMinutes(5));

// 获取
Object value = redisTemplate.opsForValue().get("key");

// 批量获取
List<String> keys = Arrays.asList("key1", "key2", "key3");
List<Object> values = redisTemplate.opsForValue().multiGet(keys);

// 追加
redisTemplate.opsForValue().append("key", " suffix");

// 自增（仅数值类型）
Long newValue = redisTemplate.opsForValue().increment("counter");
Long increment = redisTemplate.opsForValue().increment("counter", 5);

// 自减
Long decrement = redisTemplate.opsForValue().decrement("counter", 2);
```

### HashOperations - Hash 操作

```java
HashOperations<String, Object, Object> hashOps = redisTemplate.opsForHash();

// 设置
hashOps.put("user:1001", "name", "张三");
hashOps.put("user:1001", "age", 25);

// 批量设置
Map<String, Object> map = new HashMap<>();
map.put("name", "李四");
map.put("age", 30);
hashOps.putAll("user:1002", map);

// 获取
Object name = hashOps.get("user:1001", "name");

// 获取所有
Map<Object, Object> all = hashOps.entries("user:1001");

// 删除
hashOps.delete("user:1001", "age", "city");

// 判断存在
Boolean hasField = hashOps.hasKey("user:1001", "name");

// 获取所有字段
Set<Object> keys = hashOps.keys("user:1001");

// 获取所有值
List<Object> values = hashOps.values("user:1001");

// 大小
Long size = hashOps.size("user:1001");
```

### SetOperations - Set 操作

```java
SetOperations<String, Object> setOps = redisTemplate.opsForSet();

// 添加
setOps.add("tags", "java", "spring", "redis");

// 获取所有
Set<Object> members = setOps.members("tags");

// 判断存在
Boolean isMember = setOps.isMember("tags", "java");

// 获取大小
Long size = setOps.size("tags");

// 移除
setOps.remove("tags", "redis");

// 随机获取
Object random = setOps.randomMember("tags");
List<Object> randoms = setOps.distinctRandomMembers("tags", 2);

// 集合运算
setOps.union("set1", "set2"); // 并集
setOps.intersect("set1", "set2"); // 交集
setOps.difference("set1", "set2"); // 差集
```

### ListOperations - List 操作

```java
ListOperations<String, Object> listOps = redisTemplate.opsForList();

// 右侧添加（队列）
listOps.rightPush("queue", task1);
listOps.rightPushAll("queue", task1, task2, task3);

// 左侧添加（栈）
listOps.leftPush("stack", action);

// 获取范围
List<Object> list = listOps.range("queue", 0, 9); // 前10个

// 索引获取
Object first = listOps.index("queue", 0);

// 弹出
Object left = listOps.leftPop("queue"); // 左侧弹出（队列）
Object right = listOps.rightPop("queue"); // 右侧弹出

// 大小
Long size = listOps.size("queue");

// 修剪（保留指定范围）
listOps.trim("queue", 0, 99); // 只保留前100个
```

### ZSetOperations - 有序集合

```java
@Autowired
private StringRedisTemplate stringRedisTemplate;
private ZSetOperations<String, String> zSetOps = stringRedisTemplate.opsForZSet();

// 添加
zSetOps.add("ranking", "user1", 100);
zSetOps.add("ranking", "user2", 200);

// 获取范围（按分数）
Set<String> set = zSetOps.range("ranking", 0, 9); // 前10名

// 获取范围（按分数+分数）
Set<TypedTuple<String>> setWithScores = zSetOps.rangeWithScores("ranking", 0, 9);

// 按分数范围获取
Set<String> setByScore = zSetOps.rangeByScore("ranking", 100, 200);

// 获取排名
Long rank = zSetOps.rank("ranking", "user1"); // 从0开始
Long reverseRank = zSetOps.reverseRank("ranking", "user1"); // 倒序排名

// 获取分数
Double score = zSetOps.score("ranking", "user1");

// 增加分数
Double newScore = zSetOps.incrementScore("ranking", "user1", 10);

// 移除
zSetOps.remove("ranking", "user1");

// 大小
Long size = zSetOps.size("ranking");
```

### 发布订阅

```java
// 发布消息
redisTemplate.convertAndSend("channel:notification", message);

// 配置监听器（在配置类中）
@Bean
RedisMessageListenerContainer container(RedisConnectionFactory connectionFactory,
                                        MessageListener listener) {
    RedisMessageListenerContainer container = new RedisMessageListenerContainer();
    container.setConnectionFactory(connectionFactory);
    container.addMessageListener(listener, new PatternTopic("channel:*"));
    return container;
}
```

---

## Redisson 分布式锁

### 基本用法

```java
@Autowired
private RedissonClient redissonClient;

public void businessMethod(String id) {
    // 获取锁
    RLock lock = redissonClient.getLock("business:lock:" + id);
    try {
        // 尝试加锁：最多等待10秒，锁30秒后自动释放
        if (lock.tryLock(10, 30, TimeUnit.SECONDS)) {
            try {
                // 业务逻辑
                doBusiness(id);
            } finally {
                // 释放锁
                lock.unlock();
            }
        } else {
            throw new RuntimeException("获取锁失败，请稍后重试");
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
        throw new RuntimeException("锁等待被中断");
    }
}
```

### 公平锁

```java
public void fairLockMethod() {
    RLock lock = redissonClient.getFairLock("fair:lock:resource");
    try {
        if (lock.tryLock(10, 30, TimeUnit.SECONDS)) {
            try {
                // 业务逻辑
            } finally {
                lock.unlock();
            }
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}
```

### 读写锁

```java
public void writeMethod() {
    RReadWriteLock rwLock = redissonClient.getReadWriteLock("rw:lock:resource");
    RLock lock = rwLock.writeLock();
    try {
        lock.lock();
        // 写操作
    } finally {
        lock.unlock();
    }
}

public void readMethod() {
    RReadWriteLock rwLock = redissonClient.getReadWriteLock("rw:lock:resource");
    RLock lock = rwLock.readLock();
    try {
        lock.lock();
        // 读操作（多个读锁可以同时持有）
    } finally {
        lock.unlock();
    }
}
```

### 信号量

```java
public void rateLimitMethod() {
    RSemaphore semaphore = redissonClient.getSemaphore("semaphore:api");
    try {
        // 尝试获取许可（非阻塞）
        if (semaphore.tryAcquire()) {
            try {
                // 业务逻辑
            } finally {
                semaphore.release();
            }
        } else {
            throw new RuntimeException("达到并发限制");
        }
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}

// 初始化信号量（在应用启动时）
@PostConstruct
public void initSemaphore() {
    RSemaphore semaphore = redissonClient.getSemaphore("semaphore:api");
    semaphore.trySetPermits(10); // 最多10个并发
}
```

### 倒计时门锁

```java
public void awaitMethod() {
    RCountDownLatch latch = redissonClient.getCountDownLatch("latch:deploy");
    latch.trySetCount(1); // 设置计数

    try {
        latch.await(); // 等待计数归零
        // 业务逻辑
    } catch (InterruptedException e) {
        Thread.currentThread().interrupt();
    }
}

public void countDownMethod() {
    RCountDownLatch latch = redissonClient.getCountDownLatch("latch:deploy");
    latch.countDown(); // 计数减1
}
```

---

## 常见业务场景

### 验证码缓存

```java
@Service
public class CaptchaService {

    @Autowired
    private RedisUtil redisUtil;
    @Value("${jeecg.signatureSecret}")
    private String secret;

    // 生成验证码
    public void generateCaptcha(String uuid, String code) {
        String key = Md5Util.md5Encode(code + uuid + secret, "utf-8");
        redisUtil.set(key, code, 300); // 5分钟过期
    }

    // 验证验证码
    public boolean verifyCaptcha(String uuid, String inputCode) {
        String key = Md5Util.md5Encode(inputCode + uuid + secret, "utf-8");
        Object cachedCode = redisUtil.get(key);
        if (cachedCode == null || !cachedCode.toString().equals(inputCode)) {
            return false;
        }
        // 验证成功后删除
        redisUtil.del(key);
        return true;
    }
}
```

### 用户 Token 管理

```java
@Service
public class TokenService {

    @Autowired
    private RedisUtil redisUtil;

    private static final String TOKEN_PREFIX = "prefix_user_token:";
    private static final String SHIRO_CACHE_PREFIX = "shiro:cache:org.jeecg.config.shiro.ShiroRealm.authorizationCache:";

    // 登录成功存储 Token
    public void saveToken(String token, String userId, Object userInfo) {
        redisUtil.set(TOKEN_PREFIX + token, token, 7200); // 2小时
        redisUtil.set(SHIRO_CACHE_PREFIX + userId, userInfo, 7200);
    }

    // 验证 Token
    public boolean verifyToken(String token) {
        String key = TOKEN_PREFIX + token;
        return redisUtil.hasKey(key);
    }

    // 刷新 Token
    public void refreshToken(String token) {
        String key = TOKEN_PREFIX + token;
        redisUtil.expire(key, 7200);
    }

    // 退出登录
    public void logout(String token, String userId) {
        redisUtil.del(TOKEN_PREFIX + token);
        redisUtil.del(SHIRO_CACHE_PREFIX + userId);
    }

    // 强制退出用户
    public void forceLogout(String userId) {
        // 需要先通过反向查找 token
        Collection<String> keys = redisTemplate.keys(TOKEN_PREFIX + "*");
        for (String key : keys) {
            // 检查是否为该用户的 token
            // 实际项目中需要建立 userId -> token 的映射
        }
    }
}
```

### 字典缓存

```java
@Service
public class DictServiceImpl {

    @Autowired
    private SysDictMapper sysDictMapper;

    // 查询字典项（缓存）
    @Cacheable(value = CacheConstant.SYS_DICT_CACHE, key = "#code", unless = "#result == null")
    public List<DictModel> queryDictItemsByCode(String code) {
        return sysDictMapper.queryDictItemsByCode(code);
    }

    // 查询有效字典项（缓存）
    @Cacheable(value = CacheConstant.SYS_ENABLE_DICT_CACHE, key = "#code", unless = "#result == null")
    public List<DictModel> queryEnableDictItemsByCode(String code) {
        return sysDictMapper.queryDictItemsByCode(code);
    }

    // 字典翻译（缓存）
    @Cacheable(value = CacheConstant.SYS_DICT_CACHE, key = "#code + ':' + #key", unless = "#result == null")
    public String queryDictTextByKey(String code, String key) {
        return sysDictMapper.queryDictTextByKey(code, key);
    }

    // 添加字典（清除缓存）
    @CacheEvict(value = {
        CacheConstant.SYS_DICT_CACHE,
        CacheConstant.SYS_ENABLE_DICT_CACHE
    }, allEntries = true)
    public void addDict(SysDict dict) {
        sysDictMapper.insert(dict);
    }

    // 更新字典（清除缓存）
    @CacheEvict(value = {
        CacheConstant.SYS_DICT_CACHE,
        CacheConstant.SYS_ENABLE_DICT_CACHE
    }, allEntries = true)
    public void updateDict(SysDict dict) {
        sysDictMapper.updateById(dict);
    }

    // 删除字典（清除缓存）
    @CacheEvict(value = {
        CacheConstant.SYS_DICT_CACHE,
        CacheConstant.SYS_ENABLE_DICT_CACHE
    }, allEntries = true)
    public void deleteDict(String id) {
        sysDictMapper.deleteById(id);
    }
}
```

### 在线用户管理

```java
@Service
public class OnlineUserService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;
    @Autowired
    private RedisUtil redisUtil;

    private static final String TOKEN_PREFIX = "prefix_user_token:";

    // 获取所有在线用户
    public List<SysUserOnlineVO> getOnlineUsers() {
        Collection<String> keys = redisTemplate.keys(TOKEN_PREFIX + "*");
        List<SysUserOnlineVO> onlineList = new ArrayList<>();

        for (String key : keys) {
            String token = (String) redisUtil.get(key);
            if (StringUtils.isNotEmpty(token)) {
                // 解析 token 获取用户信息
                String username = JwtUtil.getUsername(token);
                Date expireTime = JwtUtil.getExpiryDate(token);

                SysUserOnlineVO online = new SysUserOnlineVO();
                online.setUsername(username);
                online.setToken(token);
                online.setExpireTime(expireTime);
                onlineList.add(online);
            }
        }
        return onlineList;
    }

    // 强制退出
    public void forceLogout(String token) {
        String username = JwtUtil.getUsername(token);
        String userId = getUserIdByUsername(username);

        redisUtil.del(TOKEN_PREFIX + token);
        redisUtil.del("shiro:cache:org.jeecg.config.shiro.ShiroRealm.authorizationCache:" + userId);
    }

    // 批量强制退出
    public void batchForceLogout(List<String> tokens) {
        for (String token : tokens) {
            forceLogout(token);
        }
    }
}
```

### 防重复提交

```java
@Aspect
@Component
public class PreventDuplicateSubmitAspect {

    @Autowired
    private RedisUtil redisUtil;

    @Around("@annotation(preventDuplicateSubmit)")
    public Object around(ProceedingJoinPoint point, PreventDuplicateSubmit preventDuplicateSubmit) throws Throwable {
        HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.currentRequestAttributes()).getRequest();
        String key = "duplicate:submit:" + request.getRequestURI() + ":" + request.getSession().getId();

        // 检查是否已提交
        if (redisUtil.hasKey(key)) {
            throw new RuntimeException("请勿重复提交");
        }

        // 设置标记（过期时间根据注配置）
        long expireTime = preventDuplicateSubmit.time();
        redisUtil.set(key, "1", expireTime);

        try {
            return point.proceed();
        } catch (Throwable e) {
            // 执行失败，删除标记
            redisUtil.del(key);
            throw e;
        }
    }
}

// 使用
@PostMapping("/submit")
@PreventDuplicateSubmit(time = 5) // 5秒内不可重复提交
public Result<?> submit(@RequestBody FormData formData) {
    // 业务逻辑
    return Result.OK();
}
```

### 接口限流

```java
@Aspect
@Component
public class RateLimitAspect {

    @Autowired
    private RedisUtil redisUtil;

    @Around("@annotation(rateLimit)")
    public Object around(ProceedingJoinPoint point, RateLimit rateLimit) throws Throwable {
        HttpServletRequest request = ((ServletRequestAttributes) RequestContextHolder.currentRequestAttributes()).getRequest();
        String key = "rate:limit:" + request.getRequestURI();

        // 获取当前计数
        Object count = redisUtil.get(key);
        if (count == null) {
            // 首次访问，设置计数和过期时间
            redisUtil.set(key, 1, rateLimit.time());
        } else {
            int current = Integer.parseInt(count.toString());
            if (current >= rateLimit.count()) {
                throw new RuntimeException("访问过于频繁，请稍后再试");
            }
            redisUtil.incr(key, 1);
        }

        return point.proceed();
    }
}

// 使用
@PostMapping("/api/data")
@RateLimit(count = 10, time = 60) // 60秒内最多10次
public Result<?> getData() {
    return Result.OK();
}
```

### 网关路由缓存

```java
@Service
public class GatewayRouteService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String GATEWAY_ROUTES_KEY = "sys:cache:cloud:gateway_routes";

    // 刷新路由到 Redis
    public void refreshRoutes() {
        List<SysGatewayRoute> routes = gatewayRouteMapper.selectList(null);
        redisTemplate.opsForValue().set(GATEWAY_ROUTES_KEY, JSON.toJSONString(routes));
    }

    // 发布路由变更消息
    public void publishRouteChange(String params) {
        redisTemplate.convertAndSend("redisson:gateway", params);
    }

    // 获取所有路由
    public List<SysGatewayRoute> getRoutes() {
        String json = (String) redisTemplate.opsForValue().get(GATEWAY_ROUTES_KEY);
        return JSON.parseArray(json, SysGatewayRoute.class);
    }
}
```

### 数据库查询结果缓存

```java
@Service
public class DataReportService {

    @Autowired
    private RedisUtil redisUtil;

    public List<ReportData> generateReport(String reportId, LocalDate date) {
        String cacheKey = String.format("report:%s:%s", reportId, date);

        // 先查缓存
        Object cached = redisUtil.get(cacheKey);
        if (cached != null) {
            return JSON.parseArray(cached.toString(), ReportData.class);
        }

        // 缓存未命中，查询数据库
        List<ReportData> data = queryFromDatabase(reportId, date);

        // 存入缓存（1小时过期）
        redisUtil.set(cacheKey, JSON.toJSONString(data), 3600);

        return data;
    }

    public void invalidateReport(String reportId) {
        redisUtil.removeAll("report:" + reportId + ":");
    }
}
```

### 分布式 ID 生成

```java
@Component
public class DistributedIdGenerator {

    @Autowired
    private RedisUtil redisUtil;

    private static final String ID_KEY_PREFIX = "distributed:id:";

    public Long generateId(String bizType) {
        String key = ID_KEY_PREFIX + bizType;
        Long id = redisUtil.incr(key, 1);
        // 设置过期时间（可根据业务调整）
        if (id == 1) {
            redisUtil.expire(key, 86400); // 24小时
        }
        return id;
    }

    // 生成订单号示例
    public String generateOrderNo() {
        Long id = generateId("order");
        LocalDate now = LocalDate.now();
        return String.format("ORD%04d%02d%02d%06d",
            now.getYear(), now.getMonthValue(), now.getDayOfMonth(), id);
    }
}
```

### 会话共享

```java
@Service
public class SessionService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String SESSION_PREFIX = "session:";

    // 保存会话
    public void saveSession(String sessionId, SessionData data) {
        String key = SESSION_PREFIX + sessionId;
        redisTemplate.opsForHash().put(key, "userId", data.getUserId());
        redisTemplate.opsForHash().put(key, "username", data.getUsername());
        redisTemplate.opsForHash().put(key, "lastAccess", System.currentTimeMillis());
        redisTemplate.expire(key, 30, TimeUnit.MINUTES);
    }

    // 获取会话
    public SessionData getSession(String sessionId) {
        String key = SESSION_PREFIX + sessionId;
        Map<Object, Object> map = redisTemplate.opsForHash().entries(key);
        if (map.isEmpty()) {
            return null;
        }
        SessionData data = new SessionData();
        data.setUserId((String) map.get("userId"));
        data.setUsername((String) map.get("username"));
        return data;
    }

    // 刷新会话
    public void refreshSession(String sessionId) {
        String key = SESSION_PREFIX + sessionId;
        redisTemplate.expire(key, 30, TimeUnit.MINUTES);
        redisTemplate.opsForHash().put(key, "lastAccess", System.currentTimeMillis());
    }

    // 销毁会话
    public void destroySession(String sessionId) {
        redisTemplate.delete(SESSION_PREFIX + sessionId);
    }
}
```

### 消息队列（轻量级）

```java
@Service
public class MessageQueueService {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String QUEUE_PREFIX = "mq:";

    // 发送消息
    public void sendMessage(String queueName, Object message) {
        String key = QUEUE_PREFIX + queueName;
        redisTemplate.opsForList().rightPush(key, message);
    }

    // 消费消息
    public Object consumeMessage(String queueName) {
        String key = QUEUE_PREFIX + queueName;
        return redisTemplate.opsForList().leftPop(key);
    }

    // 批量消费
    public List<Object> consumeMessages(String queueName, int count) {
        String key = QUEUE_PREFIX + queueName;
        List<Object> messages = new ArrayList<>();
        for (int i = 0; i < count; i++) {
            Object message = redisTemplate.opsForList().leftPop(key);
            if (message == null) {
                break;
            }
            messages.add(message);
        }
        return messages;
    }

    // 获取队列大小
    public long getQueueSize(String queueName) {
        String key = QUEUE_PREFIX + queueName;
        Long size = redisTemplate.opsForList().size(key);
        return size != null ? size : 0;
    }
}
```

### 热点数据缓存预热

```java
@Component
public class CacheWarmupService {

    @Autowired
    private RedisUtil redisUtil;
    @Autowired
    private DictService dictService;
    @Autowired
    private DepartService departService;

    @PostConstruct
    public void warmupCache() {
        log.info("开始缓存预热...");

        // 预热字典缓存
        warmupDictCache();

        // 预热部门缓存
        warmupDepartCache();

        log.info("缓存预热完成");
    }

    private void warmupDictCache() {
        List<SysDict> allDicts = dictService.list();
        Set<String> dictCodes = allDicts.stream()
            .map(SysDict::getDictCode)
            .collect(Collectors.toSet());

        for (String code : dictCodes) {
            // 触发 @Cacheable 注解
            dictService.queryDictItemsByCode(code);
        }
    }

    private void warmupDepartCache() {
        // 触发部门缓存加载
        departService.getAllDeparts();
        departService.getAllDepartIds();
    }
}
```

### 缓存击穿防护

```java
@Service
public class CachePenetrationService {

    @Autowired
    private RedisUtil redisUtil;
    @Autowired
    private RedissonClient redissonClient;

    private static final String LOCK_PREFIX = "lock:";

    public User getUserWithLock(String userId) {
        String cacheKey = "user:" + userId;

        // 先查缓存
        Object cached = redisUtil.get(cacheKey);
        if (cached != null) {
            return (User) cached;
        }

        // 缓存未命中，使用分布式锁防止击穿
        String lockKey = LOCK_PREFIX + cacheKey;
        RLock lock = redissonClient.getLock(lockKey);

        try {
            if (lock.tryLock(5, 30, TimeUnit.SECONDS)) {
                try {
                    // 再次检查缓存（双重检查）
                    cached = redisUtil.get(cacheKey);
                    if (cached != null) {
                        return (User) cached;
                    }

                    // 查询数据库
                    User user = userMapper.selectById(userId);

                    // 缓存结果（包括空值，防止缓存穿透）
                    if (user != null) {
                        redisUtil.set(cacheKey, user, 3600);
                    } else {
                        redisUtil.set(cacheKey, NULL_VALUE, 60); // 空值缓存1分钟
                    }

                    return user;
                } finally {
                    lock.unlock();
                }
            }
        } catch (InterruptedException e) {
            Thread.currentThread().interrupt();
        }

        // 获取锁失败，直接查数据库
        return userMapper.selectById(userId);
    }
}
```

### 布隆过滤器（防缓存穿透）

```java
@Component
public class BloomFilterService {

    @Autowired
    private RedissonClient redissonClient;

    private RBloomFilter<String> bloomFilter;

    @PostConstruct
    public void init() {
        bloomFilter = redissonClient.getBloomFilter("user:bloom");
        bloomFilter.tryInit(1000000, 0.01); // 预计100万数据，误判率1%

        // 预加载所有有效 ID
        List<String> allIds = loadAllUserIds();
        for (String id : allIds) {
            bloomFilter.add(id);
        }
    }

    public boolean isUserExists(String userId) {
        return bloomFilter.contains(userId);
    }

    public User getUser(String userId) {
        // 先用布隆过滤器判断
        if (!isUserExists(userId)) {
            return null; // 直接返回，避免查询数据库
        }

        // 正常查询流程
        return userMapper.selectById(userId);
    }
}
```

### 地理位置存储

```java
@Service
public class GeoLocationService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;
    private GeoOperations<String, String> geoOps = stringRedisTemplate.opsForGeo();

    private static final String GEO_KEY = "geo:locations";

    // 添加位置
    public void addLocation(String userId, double longitude, double latitude) {
        Point point = new Point(longitude, latitude);
        geoOps.add(GEO_KEY, point, userId);
    }

    // 获取位置
    public Point getLocation(String userId) {
        List<Point> points = geoOps.position(GEO_KEY, userId);
        return points.isEmpty() ? null : points.get(0);
    }

    // 计算距离
    public Double getDistance(String user1, String user2) {
        Distance distance = geoOps.distance(GEO_KEY, user1, user2, RedisGeoCommands.DistanceUnit.KILOMETERS);
        return distance.getValue();
    }

    // 查找附近的人
    public Map<String, Double> getNearbyUsers(double longitude, double latitude, double radius) {
        Point point = new Point(longitude, latitude);
        Circle circle = new Circle(point, new Distance(radius, RedisGeoCommands.DistanceUnit.KILOMETERS));

        GeoResults<RedisGeoCommands.GeoLocation<String>> results = geoOps.radius(GEO_KEY, circle);

        Map<String, Double> nearby = new HashMap<>();
        for (GeoResult<RedisGeoCommands.GeoLocation<String>> result : results) {
            nearby.put(result.getContent().getName(),
                result.getDistance().getValue());
        }
        return nearby;
    }
}
```

### HyperLogLog 统计

```java
@Service
public class StatisticsService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    // 添加访问记录
    public void recordVisit(String date, String userId) {
        String key = "stats:uv:" + date;
        stringRedisTemplate.opsForHyperLogLog().add(key, userId);
    }

    // 获取 UV（独立访客数）
    public long getUniqueVisitors(String date) {
        String key = "stats:uv:" + date;
        Long size = stringRedisTemplate.opsForHyperLogLog().size(key);
        return size != null ? size : 0;
    }

    // 合并多天的统计
    public long getUniqueVisitors(String... dates) {
        String[] keys = Arrays.stream(dates)
            .map(d -> "stats:uv:" + d)
            .toArray(String[]::new);
        String destKey = "stats:uv:merged:" + System.currentTimeMillis();
        stringRedisTemplate.opsForHyperLogLog().union(destKey, keys);
        Long size = stringRedisTemplate.opsForHyperLogLog().size(destKey);
        stringRedisTemplate.delete(destKey);
        return size != null ? size : 0;
    }
}
```

### 位图统计

```java
@Service
public class BitmapService {

    @Autowired
    private StringRedisTemplate stringRedisTemplate;

    // 记录签到（按年）
    public void signIn(String userId, int dayOfYear) {
        String key = "signin:" + LocalDate.now().getYear() + ":" + userId;
        stringRedisTemplate.opsForValue().setBit(key, dayOfYear, true);
    }

    // 检查是否签到
    public boolean hasSignedIn(String userId, int dayOfYear) {
        String key = "signin:" + LocalDate.now().getYear() + ":" + userId;
        Boolean signed = stringRedisTemplate.opsForValue().getBit(key, dayOfYear);
        return signed != null && signed;
    }

    // 统计签到次数
    public long getSignInCount(String userId) {
        String key = "signin:" + LocalDate.now().getYear() + ":" + userId;
        BitSet set = BitSet.valueOf(stringRedisTemplate.opsForValue().get(key).getBytes());
        return set.cardinality();
    }
}
```

### 限流令牌桶

```java
@Service
public class TokenBucketRateLimiter {

    @Autowired
    private RedisTemplate<String, Object> redisTemplate;

    private static final String TOKEN_BUCKET_PREFIX = "token:bucket:";

    public boolean tryConsume(String api, int tokens) {
        String key = TOKEN_BUCKET_PREFIX + api;

        // 使用 Lua 脚本保证原子性
        String luaScript =
            "local key = KEYS[1] " +
            "local capacity = tonumber(ARGV[1]) " +
            "local tokens = tonumber(ARGV[2]) " +
            "local interval = tonumber(ARGV[3]) " +
            "local current = redis.call('HMGET', key, 'tokens', 'last_refill') " +
            "local token_count = tonumber(current[1]) or capacity " +
            "local last_refill = tonumber(current[2]) or 0 " +
            "local now = tonumber(ARGV[4]) " +
            "local elapsed = math.max(0, now - last_refill) " +
            "local new_tokens = math.min(capacity, token_count + elapsed * capacity / interval) " +
            "if new_tokens >= tokens then " +
            "    redis.call('HMSET', key, 'tokens', new_tokens - tokens, 'last_refill', now) " +
            "    redis.call('EXPIRE', key, interval * 2) " +
            "    return 1 " +
            "else " +
            "    redis.call('HMSET', key, 'tokens', new_tokens, 'last_refill', now) " +
            "    return 0 " +
            "end";

        DefaultRedisScript<Long> script = new DefaultRedisScript<>(luaScript, Long.class);

        Long result = redisTemplate.execute(
            script,
            Collections.singletonList(key),
            100, // capacity 容量
            tokens, // tokens 消费令牌数
            60, // interval 补充间隔(秒)
            System.currentTimeMillis() / 1000 // now 当前时间
        );

        return result != null && result == 1;
    }
}
```

---

## 总结

以上代码示例涵盖了 jeecg-boot 平台中使用 Redis 的主要场景，包括：

1. **RedisUtil** - Jeecg 封装的简单工具类
2. **Spring Cache** - 方法级缓存注解
3. **RedisTemplate** - Spring Data Redis 原生操作
4. **Redisson** - 分布式锁和高级数据结构

选择使用方式时：
- 简单 KV 操作 → **RedisUtil**
- 方法级查询缓存 → **Spring Cache**
- 复杂操作/自定义需求 → **RedisTemplate**
- 分布式协调 → **Redisson**
