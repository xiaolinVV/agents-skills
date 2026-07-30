-- SQL Templates for Dictionary Setup
-- Copy and modify as needed to create new dictionaries

-- ========================================
-- Template 1: Basic Dictionary Setup
-- ========================================

-- Step 1: Generate unique IDs
SET @dict_id = REPLACE(UUID(), '-', '');
SET @item_id_1 = REPLACE(UUID(), '-', '');
SET @item_id_2 = REPLACE(UUID(), '-', '');
SET @item_id_3 = REPLACE(UUID(), '-', '');

-- Step 2: Create dictionary type
INSERT INTO `sys_dict` (
    `id`,
    `dict_code`,
    `dict_name`,
    `description`,
    `del_flag`,
    `type`,
    `create_by`,
    `create_time`,
    `update_by`,
    `update_time`
) VALUES (
    @dict_id,                    -- Generated ID
    'your_dict_code',            -- TODO: Dictionary code (must be unique)
    'Your Dictionary Name',      -- TODO: Dictionary display name
    'Dictionary description',    -- TODO: Description
    0,                           -- del_flag: 0=active
    0,                           -- type: 0=string, 1=number
    'admin',                     -- create_by
    NOW(),                       -- create_time
    'admin',                     -- update_by
    NOW()                        -- update_time
);

-- Step 3: Create dictionary items
INSERT INTO `sys_dict_item` (
    `id`,
    `dict_id`,
    `item_text`,
    `item_value`,
    `item_color`,
    `description`,
    `sort_order`,
    `status`,
    `create_by`,
    `create_time`,
    `update_by`,
    `update_time`
) VALUES
(
    @item_id_1,                  -- Generated ID
    @dict_id,                    -- FK to sys_dict
    'Option Text 1',             -- TODO: Display text
    'value1',                    -- TODO: Actual value
    '#00CC00',                   -- TODO: Color code
    'Description for option 1',  -- TODO: Description
    1,                           -- Sort order (lower = first)
    1,                           -- status: 1=enabled, 0=disabled
    'admin',
    NOW(),
    'admin',
    NOW()
),
(
    @item_id_2,
    @dict_id,
    'Option Text 2',             -- TODO: Display text
    'value2',                    -- TODO: Actual value
    '#FF0000',                   -- TODO: Color code
    'Description for option 2',  -- TODO: Description
    2,                           -- Sort order
    1,                           -- status: 1=enabled, 0=disabled
    'admin',
    NOW(),
    'admin',
    NOW()
),
(
    @item_id_3,
    @dict_id,
    'Option Text 3',             -- TODO: Display text
    'value3',                    -- TODO: Actual value
    '#0000CC',                   -- TODO: Color code
    'Description for option 3',  -- TODO: Description
    3,                           -- Sort order
    1,                           -- status: 1=enabled, 0=disabled
    'admin',
    NOW(),
    'admin',
    NOW()
);

-- ========================================
-- Example: User Status Dictionary
-- ========================================

SET @dict_id = REPLACE(UUID(), '-', '');
SET @item_1 = REPLACE(UUID(), '-', '');
SET @item_2 = REPLACE(UUID(), '-', '');

INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `type`, `create_by`, `create_time`)
VALUES (@dict_id, 'user_status', 'User Status', 'User account status', 0, 1, 'admin', NOW());

INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `sort_order`, `status`, `create_by`, `create_time`)
VALUES
    (@item_1, @dict_id, 'Normal', '1', '#00CC00', 1, 1, 'admin', NOW()),
    (@item_2, @dict_id, 'Disabled', '0', '#FF0000', 2, 1, 'admin', NOW());

-- ========================================
-- Example: Order Status Dictionary
-- ========================================

SET @dict_id = REPLACE(UUID(), '-', '');
SET @item_1 = REPLACE(UUID(), '-', '');
SET @item_2 = REPLACE(UUID(), '-', '');
SET @item_3 = REPLACE(UUID(), '-', '');
SET @item_4 = REPLACE(UUID(), '-', '');
SET @item_5 = REPLACE(UUID(), '-', '');

INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `type`, `create_by`, `create_time`)
VALUES (@dict_id, 'order_status', 'Order Status', 'Order processing status', 0, 1, 'admin', NOW());

INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `sort_order`, `status`, `create_by`, `create_time`)
VALUES
    (@item_1, @dict_id, 'Pending', '0', '#FF9900', 1, 1, 'admin', NOW()),
    (@item_2, @dict_id, 'Processing', '1', '#0099FF', 2, 1, 'admin', NOW()),
    (@item_3, @dict_id, 'Shipped', '2', '#00CC00', 3, 1, 'admin', NOW()),
    (@item_4, @dict_id, 'Completed', '3', '#00CC00', 4, 1, 'admin', NOW()),
    (@item_5, @dict_id, 'Cancelled', '4', '#FF0000', 5, 1, 'admin', NOW());

-- ========================================
-- Example: Payment Method Dictionary
-- ========================================

SET @dict_id = REPLACE(UUID(), '-', '');
SET @item_1 = REPLACE(UUID(), '-', '');
SET @item_2 = REPLACE(UUID(), '-', '');
SET @item_3 = REPLACE(UUID(), '-', '');
SET @item_4 = REPLACE(UUID(), '-', '');

INSERT INTO `sys_dict` (`id`, `dict_code`, `dict_name`, `description`, `del_flag`, `type`, `create_by`, `create_time`)
VALUES (@dict_id, 'payment_method', 'Payment Method', 'Payment methods', 0, 0, 'admin', NOW());

INSERT INTO `sys_dict_item` (`id`, `dict_id`, `item_text`, `item_value`, `item_color`, `sort_order`, `status`, `create_by`, `create_time`)
VALUES
    (@item_1, @dict_id, 'Alipay', 'alipay', '#00AAEE', 1, 1, 'admin', NOW()),
    (@item_2, @dict_id, 'WeChat Pay', 'wechat', '#09BB07', 2, 1, 'admin', NOW()),
    (@item_3, @dict_id, 'Bank Card', 'bank', '#FF0000', 3, 1, 'admin', NOW()),
    (@item_4, @dict_id, 'Cash', 'cash', '#CCCCCC', 4, 1, 'admin', NOW());

-- ========================================
-- Useful Queries for Dictionary Management
-- ========================================

-- Check if a dictionary code exists
SELECT * FROM sys_dict WHERE dict_code = 'your_dict_code';

-- Get all dictionary items for a dictionary
SELECT di.* FROM sys_dict_item di
INNER JOIN sys_dict d ON di.dict_id = d.id
WHERE d.dict_code = 'your_dict_code'
ORDER BY di.sort_order;

-- Check enabled dictionary items
SELECT di.* FROM sys_dict_item di
INNER JOIN sys_dict d ON di.dict_id = d.id
WHERE d.dict_code = 'your_dict_code' AND di.status = 1
ORDER BY di.sort_order;

-- Disable a dictionary item (soft delete)
UPDATE sys_dict_item SET status = 0 WHERE id = 'item_id';

-- Delete a dictionary (use with caution)
DELETE FROM sys_dict_item WHERE dict_id = 'dict_id';
DELETE FROM sys_dict WHERE id = 'dict_id';
