// Entity Field Annotation Templates for @Dict
// Copy and modify as needed for your entity classes

// ========================================
// Template 1: Normal Dictionary
// Use for status, type, enum fields
// ========================================

@Data
@TableName("your_table_name")
public class YourEntity {

    @TableId(type = IdType.ASSIGN_ID)
    private String id;

    /**
     * Status field - normal dictionary translation
     * Dictionary code must exist in sys_dict table
     */
    @Excel(name = "Status", width = 15, dicCode = "your_dict_code")
    @Dict(dicCode = "your_dict_code")
    private Integer status;

    /**
     * Type field - normal dictionary translation
     */
    @Excel(name = "Type", width = 15, dicCode = "your_type_dict")
    @Dict(dicCode = "your_type_dict")
    private String type;
}

// ========================================
// Template 2: Table Dictionary
// Use for foreign key translation
// ========================================

@Data
@TableName("your_table_name")
public class YourEntity {

    /**
     * Creator field - table dictionary translation
     * Translates username to realname from sys_user table
     */
    @Excel(name = "Creator", width = 15)
    @Dict(dicCode = "username", dicText = "realname", dictTable = "sys_user")
    private String createBy;

    /**
     * Department field - table dictionary translation
     * Translates dept_id to dept_name from sys_depart table
     */
    @Excel(name = "Department", width = 15)
    @Dict(dicCode = "id", dicText = "depart_name", dictTable = "sys_depart")
    private String deptId;

    /**
     * User field - table dictionary translation
     * Translates user_id to realname from sys_user table
     */
    @Excel(name = "User Name", width = 15)
    @Dict(dicCode = "id", dicText = "realname", dictTable = "sys_user")
    private String userId;
}

// ========================================
// Template 3: Multi-Value Translation
// Supports comma-separated values
// ========================================

@Data
@TableName("your_table_name")
public class YourEntity {

    /**
     * Role IDs field - multi-value translation
     * Input: "1,2,3" → Output: "Admin,User,Guest"
     */
    @Excel(name = "Roles", width = 15)
    @Dict(dicCode = "id", dicText = "role_name", dictTable = "sys_role")
    private String roleIds;

    /**
     * Category IDs - multi-value translation
     */
    @Excel(name = "Categories", width = 15)
    @Dict(dicCode = "id", dicText = "category_name", dictTable = "sys_category")
    private String categoryIds;
}

// ========================================
// Template 4: Combined Example
// ========================================

@Data
@TableName("biz_order")
public class BizOrder {

    @TableId(type = IdType.ASSIST_ID)
    private String id;

    @Excel(name = "Order No", width = 20)
    private String orderNo;

    /** Normal dictionary - order status */
    @Excel(name = "Status", width = 15, dicCode = "order_status")
    @Dict(dicCode = "order_status")
    private Integer status;

    /** Normal dictionary - payment method */
    @Excel(name = "Payment Method", width = 15, dicCode = "payment_method")
    @Dict(dicCode = "payment_method")
    private String paymentMethod;

    /** Table dictionary - creator name */
    @Excel(name = "Creator", width = 15)
    @Dict(dicCode = "username", dicText = "realname", dictTable = "sys_user")
    private String createBy;

    /** Table dictionary - department name */
    @Excel(name = "Department", width = 15)
    @Dict(dicCode = "id", dicText = "depart_name", dictTable = "sys_depart")
    private String deptId;
}
