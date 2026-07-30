// Frontend Column Templates for @Dict Translation
// Copy and modify as needed for your table columns

// ========================================
// Template 1: Normal Dictionary Column
// ========================================

export const columns = [
  {
    title: 'User Name',
    align: 'center',
    dataIndex: 'username',
    width: 120
  },
  {
    title: 'Status',           // Column header
    align: 'center',
    width: 100,
    dataIndex: 'status_dictText'  // IMPORTANT: Use fieldName + '_dictText'
  },
  {
    title: 'Gender',
    align: 'center',
    width: 80,
    dataIndex: 'sex_dictText'     // IMPORTANT: Use fieldName + '_dictText'
  }
];

// ========================================
// Template 2: Table Dictionary Column
// ========================================

export const columns = [
  {
    title: 'File Name',
    align: 'center',
    dataIndex: 'fileName',
    width: 200
  },
  {
    title: 'Creator',           // Shows translated creator name
    align: 'center',
    width: 120,
    dataIndex: 'createBy_dictText'  // Translated from sys_user.realname
  },
  {
    title: 'Department',        // Shows translated department name
    align: 'center',
    width: 150,
    dataIndex: 'deptId_dictText'    // Translated from sys_depart.depart_name
  }
];

// ========================================
// Template 3: Combined Original + Translated
// ========================================

export const columns = [
  {
    title: 'Order No',
    align: 'center',
    dataIndex: 'orderNo',
    width: 180
  },
  {
    title: 'Status',
    align: 'center',
    width: 100,
    customRender: ({ text, record }) => {
      // Show both code and translated text
      return `${record.status} - ${record.status_dictText}`;
    }
  },
  {
    title: 'Payment Method',
    align: 'center',
    dataIndex: 'paymentMethod_dictText',
    width: 120
  },
  {
    title: 'Creator',
    align: 'center',
    dataIndex: 'createBy_dictText',
    width: 120
  }
];

// ========================================
// Template 4: With Custom Rendering
// ========================================

export const columns = [
  {
    title: 'User Name',
    align: 'center',
    dataIndex: 'username',
    width: 120
  },
  {
    title: 'Status',
    align: 'center',
    width: 100,
    dataIndex: 'status_dictText',
    customRender: ({ text }) => {
      // Custom rendering with color badge
      const colorMap = {
        '正常': 'green',
        '禁用': 'red'
      };
      return <a-tag color={colorMap[text] || 'blue'}>{text}</a-tag>;
    }
  },
  {
    title: 'Gender',
    align: 'center',
    width: 80,
    dataIndex: 'sex_dictText',
    customRender: ({ text }) => {
      const iconMap = {
        '男': <UserOutlined />,
        '女': <WomanOutlined />
      };
      return <span>{iconMap[text]} {text}</span>;
    }
  }
];

// ========================================
// Template 5: Search Form with Dictionary
// ========================================

export const searchForm = {
  labelCol: { span: 6 },
  wrapperCol: { span: 16 },
  fields: [
    {
      label: 'User Name',
      field: 'username',
      component: 'a-input',
      placeholder: 'Please enter username'
    },
    {
      label: 'Status',
      field: 'status',
      component: 'a-select',
      placeholder: 'Please select status',
      options: [
        { label: 'Normal', value: '1' },
        { label: 'Disabled', value: '0' }
      ]
      // Note: For search, use original value (not _dictText)
    },
    {
      label: 'Gender',
      field: 'sex',
      component: 'a-select',
      placeholder: 'Please select gender',
      options: [
        { label: 'Male', value: '1' },
        { label: 'Female', value: '2' }
      ]
    }
  ]
};

// ========================================
// Vue 2 Template (Ant Design Vue)
// ========================================

/*
<template>
  <a-table
    :columns="columns"
    :data-source="dataSource"
    :pagination="ipagination"
  >
    <template #status="{ text, record }">
      <a-tag :color="getStatusColor(record.status)">
        {{ record.status_dictText }}
      </a-tag>
    </template>
  </a-table>
</template>

<script>
export default {
  data() {
    return {
      columns: [
        {
          title: 'User Name',
          align: 'center',
          dataIndex: 'username',
          width: 120
        },
        {
          title: 'Status',
          align: 'center',
          width: 100,
          scopedSlots: { customRender: 'status' }
          // Use slot for custom rendering
        }
      ],
      dataSource: []
    };
  },
  methods: {
    getStatusColor(status) {
      const colors = {
        1: 'green',
        0: 'red'
      };
      return colors[status] || 'blue';
    }
  }
};
</script>
*/

// ========================================
// Common Pattern: Custom Cell Renderer
// ========================================

// Function to create status badge
export const renderStatusBadge = (text, record, colorMap = {}) => {
  const statusText = record[record.field + '_dictText'] || text;
  const color = colorMap[text] || 'blue';
  return <a-tag color={color}>{statusText}</a-tag>;
};

// Usage in columns
export const columns = [
  {
    title: 'Status',
    align: 'center',
    dataIndex: 'status',
    width: 100,
    customRender: ({ text, record }) => renderStatusBadge(text, record, {
      '1': 'green',
      '0': 'red'
    })
  }
];
