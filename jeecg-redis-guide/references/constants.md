# jeecg-boot 缓存常量参考

## CacheConstant 常量

完整路径：`org.jeecg.common.constant.CacheConstant`

```java
public interface CacheConstant {
    // ==================== 字典缓存 ====================
    /**
     * 所有字典缓存（含禁用的字典项）
     * Key 格式: sys:cache::dict:{code}
     * TTL: 6小时（默认）
     */
    String SYS_DICT_CACHE = "sys:cache:dict";

    /**
     * 有效字典缓存（只包含启用的字典项）
     * Key 格式: sys:cache::dictEnable:{code}
     * TTL: 6小时（默认）
     */
    String SYS_ENABLE_DICT_CACHE = "sys:cache:dictEnable";

    /**
     * 表字典缓存
     * Key 格式: sys:cache::dictTable::{table,text,code}
     * TTL: 10分钟
     */
    String SYS_DICT_TABLE_CACHE = "sys:cache:dictTable";

    // ==================== 用户缓存 ====================
    /**
     * 用户信息加密缓存
     * Key 格式: sys:cache:encrypt:user:{username}
     * TTL: 6小时（默认）
     */
    String SYS_USERS_CACHE = "sys:cache:encrypt:user";

    // ==================== 部门缓存 ====================
    /**
     * 全部部门数据缓存
     * Key: sys:cache:depart:alldata
     * TTL: 6小时（默认）
     */
    String SYS_DEPARTS_CACHE = "sys:cache:depart:alldata";

    /**
     * 部门 ID 列表缓存
     * Key: sys:cache:depart:allids
     * TTL: 6小时（默认）
     */
    String SYS_DEPART_IDS_CACHE = "sys:cache:depart:allids";

    /**
     * 子部门缓存
     * Key 格式: sys:cache:depart:parentId:{parentId}
     * TTL: 6小时（默认）
     */
    String SYS_DEPART_PARENTID_CACHE = "sys:cache:depart:parentId";

    /**
     * 部门名称缓存
     * Key 格式: sys:cache:depart:name:{departName}
     * TTL: 6小时（默认）
     */
    String SYS_DEPART_NAME_CACHE = "sys:cache:depart:name";

    // ==================== 权限缓存 ====================
    /**
     * 数据权限规则缓存
     * Key: sys:cache:permission:datarules
     * TTL: 6小时（默认）
     */
    String SYS_DATA_PERMISSIONS_CACHE = "sys:cache:permission:datarules";

    // ==================== 网关路由缓存 ====================
    /**
     * 网关路由配置缓存
     * Key: sys:cache:cloud:gateway_routes
     * TTL: 永久
     */
    String GATEWAY_ROUTES = "sys:cache:cloud:gateway_routes";

    // ==================== Online 报表缓存 ====================
    /**
     * Online 列表缓存
     */
    String ONLINE_LIST = "sys:cache:online:list";

    /**
     * Online 表单缓存
     */
    String ONLINE_FORM = "sys:cache:online:form";

    /**
     * Online 报表缓存
     */
    String ONLINE_RP = "sys:cache:online:rp";

    /**
     * Online 图表缓存
     */
    String ONLINE_GRAPH = "sys:cache:online:graph";

    // ==================== 动态数据源缓存 ====================
    /**
     * 动态数据源连接缓存
     * Key 格式: sys:cache:dbconnect:dynamic:{dbSourceCode}
     * TTL: 6小时（默认）
     */
    String SYS_DYNAMICDB_CACHE = "sys:cache:dbconnect:dynamic:";
}
```

## CommonConstant 常量

完整路径：`org.jeecg.common.constant.CommonConstant`

```java
public interface CommonConstant {
    // ==================== 用户 Token 相关 ====================
    /**
     * 登录用户 Token 缓存 KEY 前缀
     * Key 格式: prefix_user_token:{token}
     * TTL: 2小时
     */
    String PREFIX_USER_TOKEN = "prefix_user_token:";

    /**
     * 登录用户 Shiro 权限缓存 KEY 前缀
     * Key 格式: shiro:cache:org.jeecg.config.shiro.ShiroRealm.authorizationCache:{userId}
     * TTL: 2小时
     */
    String PREFIX_USER_SHIRO_CACHE = "shiro:cache:org.jeecg.config.shiro.ShiroRealm.authorizationCache:";
}
```

## 缓存 Key 设计规范

### 命名格式

jeecg-boot 使用冒号分隔的层级结构：

```
{系统标识}:{模块}:{业务}:{参数}
```

### 示例

| 缓存类型 | Key 模式 | 示例 |
|---------|---------|------|
| 字典缓存 | `sys:cache:dict:{code}` | `sys:cache:dict:sex` |
| 表字典 | `sys:cache:dictTable::{table,text,code}` | `sys:cache:dictTable::SimpleKey [sys_user,realname,username]` |
| 用户 Token | `prefix_user_token:{token}` | `prefix_user_token:eyJhbGciOiJIUzI1NiJ9...` |
| Shiro 权限 | `shiro:cache:...:{userId}` | `shiro:cache:org.jeecg.config.shiro.ShiroRealm.authorizationCache:user001` |
| 部门 | `sys:cache:depart:alldata` | `sys:cache:depart:alldata` |
| 数据源 | `sys:cache:dbconnect:dynamic:{code}` | `sys:cache:dbconnect:dynamic:oracle1` |

## 自定义缓存 Key 建议

### 推荐模式

```java
// 1. 使用前缀常量
public interface MyCacheConstant {
    String MY_DATA_PREFIX = "myapp:data:";
    String MY_LIST_PREFIX = "myapp:list:";
}

// 2. Key 构建
String key = MyCacheConstant.MY_DATA_PREFIX + id;
String listKey = MyCacheConstant.MY_LIST_PREFIX + type + ":" + page;

// 3. Hash Key
String hashKey = "myapp:user:" + userId;
String hashField = "profile";
```

### 避免的模式

```java
// ❌ 避免硬编码
redisUtil.set("user_1001", data);

// ❌ 避免过长的 Key
redisUtil.set("very:long:namespace:com:company:project:module:user:1001:detail:info", data);

// ❌ 避免特殊字符
redisUtil.set("user:1001:info/name", data); // "/" 可能被误解析

// ✅ 推荐
String key = String.format("app:module:user:%s", userId);
redisUtil.set(key, data);
```

## 缓存 TTL 建议

| 数据类型 | 建议 TTL | 原因 |
|---------|---------|------|
| 验证码 | 5分钟 | 防止暴力破解 |
| 用户 Token | 2小时 | 平衡安全与体验 |
| 字典数据 | 6小时 | 变更频率低 |
| 表字典 | 10分钟 | 可能动态变化 |
| 部门架构 | 6小时 | 组织架构相对稳定 |
| 热点数据 | 1小时 | 根据业务调整 |
| 临时状态 | 15分钟 | 短期状态存储 |

## Spring Cache 配置

jeecg-boot 默认 CacheManager 配置（RedisConfig）：

```java
// 默认 TTL: 6小时
// 字典表 TTL: 10分钟
// 测试缓存 TTL: 5分钟

@Cacheable(value = "myCache", key = "#id")  // 使用默认 TTL
@Cacheable(value = "dictTableCache", key = "#id")  // 使用 10分钟 TTL
```

自定义 TTL 可在 RedisConfig 中添加新缓存配置。
