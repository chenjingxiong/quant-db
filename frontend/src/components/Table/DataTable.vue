<template>
  <div class="data-table">
    <el-table
      :data="tableData"
      :stripe="stripe"
      :border="border"
      :height="height"
      :max-height="maxHeight"
      :empty-text="emptyText"
      :default-sort="defaultSort"
      :row-key="rowKey"
      :expand-row-keys="expandRowKeys"
      @row-click="handleRowClick"
      @selection-change="handleSelectionChange"
      @sort-change="handleSortChange"
    >
      <!-- 多选列 -->
      <el-table-column
        v-if="showSelection"
        type="selection"
        width="55"
        :selectable="selectable"
      />

      <!-- 索引列 -->
      <el-table-column
        v-if="showIndex"
        type="index"
        :label="indexLabel"
        :width="indexWidth"
        :align="indexAlign"
      />

      <!-- 展开列 -->
      <el-table-column
        v-if="showExpand"
        type="expand"
      >
        <template #default="props">
          <slot name="expand" :row="props.row" />
        </template>
      </el-table-column>

      <!-- 数据列 -->
      <el-table-column
        v-for="column in columns"
        :key="column.prop"
        :prop="column.prop"
        :label="column.label"
        :width="column.width"
        :min-width="column.minWidth"
        :align="column.align || 'left'"
        :sortable="column.sortable"
        :fixed="column.fixed"
        :resizable="column.resizable !== false"
        :show-overflow-tooltip="column.showOverflowTooltip !== false"
      >
        <template #header>
          <slot :name="`header-${column.prop}`" :column="column">
            {{ column.label }}
          </slot>
        </template>

        <template #default="scope">
          <slot :name="column.prop" :row="scope.row" :$index="scope.$index" :column="column">
            <!-- 自定义格式化 -->
            <template v-if="column.formatter">
              {{ column.formatter(scope.row, scope.column, scope.row[column.prop], scope.$index) }}
            </template>
            <!-- 颜色标记 -->
            <span
              v-else-if="column.colorMap"
              :style="{ color: column.colorMap[scope.row[column.prop]] || '#333' }"
            >
              {{ scope.row[column.prop] }}
            </span>
            <!-- 默认显示 -->
            <span v-else>
              {{ scope.row[column.prop] }}
            </span>
          </slot>
        </template>
      </el-table-column>

      <!-- 操作列 -->
      <el-table-column
        v-if="showAction"
        :label="actionLabel"
        :width="actionWidth"
        :fixed="actionFixed"
        align="center"
      >
        <template #default="scope">
          <slot name="action" :row="scope.row" :$index="scope.$index">
            <el-button
              v-for="btn in actions"
              :key="btn.label"
              :type="btn.type || 'text'"
              :size="btn.size || 'small'"
              :disabled="btn.disabled ? btn.disabled(scope.row) : false"
              :icon="btn.icon"
              @click.stop="handleAction(btn.handler, scope.row, scope.$index)"
            >
              {{ btn.label }}
            </el-button>
          </slot>
        </template>
      </el-table-column>
    </el-table>

    <!-- 分页 -->
    <div v-if="showPagination" class="pagination-wrapper">
      <el-pagination
        v-model:current-page="currentPage"
        v-model:page-size="pageSize"
        :page-sizes="pageSizes"
        :total="total"
        :layout="paginationLayout"
        :background="paginationBackground"
        @current-change="handlePageChange"
        @size-change="handleSizeChange"
      />
    </div>
  </div>
</template>

<script setup>
import { ref, computed, watch } from 'vue'

const props = defineProps({
  // 表格数据
  data: {
    type: Array,
    default: () => []
  },
  // 列配置
  columns: {
    type: Array,
    default: () => []
  },
  // 是否显示斑马纹
  stripe: {
    type: Boolean,
    default: true
  },
  // 是否显示边框
  border: {
    type: Boolean,
    default: true
  },
  // 表格高度
  height: {
    type: [String, Number],
    default: null
  },
  // 最大高度
  maxHeight: {
    type: [String, Number],
    default: null
  },
  // 空数据文本
  emptyText: {
    type: String,
    default: '暂无数据'
  },
  // 默认排序
  defaultSort: {
    type: Object,
    default: null
  },
  // 行key
  rowKey: {
    type: String,
    default: ''
  },
  // 展开行
  expandRowKeys: {
    type: Array,
    default: () => []
  },
  // 是否显示多选
  showSelection: {
    type: Boolean,
    default: false
  },
  // 是否显示索引
  showIndex: {
    type: Boolean,
    default: false
  },
  // 索引标签
  indexLabel: {
    type: String,
    default: '#'
  },
  // 索引宽度
  indexWidth: {
    type: [String, Number],
    default: 60
  },
  // 索引对齐方式
  indexAlign: {
    type: String,
    default: 'center'
  },
  // 是否显示展开
  showExpand: {
    type: Boolean,
    default: false
  },
  // 是否显示操作列
  showAction: {
    type: Boolean,
    default: false
  },
  // 操作列标签
  actionLabel: {
    type: String,
    default: '操作'
  },
  // 操作列宽度
  actionWidth: {
    type: [String, Number],
    default: 150
  },
  // 操作列固定
  actionFixed: {
    type: [Boolean, String],
    default: 'right'
  },
  // 操作按钮配置
  actions: {
    type: Array,
    default: () => []
  },
  // 是否显示分页
  showPagination: {
    type: Boolean,
    default: true
  },
  // 总数据数
  total: {
    type: Number,
    default: 0
  },
  // 当前页
  currentPage: {
    type: Number,
    default: 1
  },
  // 每页条数
  pageSize: {
    type: Number,
    default: 20
  },
  // 每页条数选项
  pageSizes: {
    type: Array,
    default: () => [10, 20, 50, 100, 200]
  },
  // 分页布局
  paginationLayout: {
    type: String,
    default: 'total, sizes, prev, pager, next, jumper'
  },
  // 分页背景色
  paginationBackground: {
    type: Boolean,
    default: true
  }
})

const emit = defineEmits([
  'row-click',
  'selection-change',
  'sort-change',
  'page-change',
  'size-change',
  'action'
])

// 内部状态
const tableData = ref(props.data)
const currentPage = ref(props.currentPage)
const pageSize = ref(props.pageSize)

// 监听数据变化
watch(() => props.data, (newData) => {
  tableData.value = newData
}, { immediate: true, deep: true })

// 监听分页参数变化
watch([() => props.currentPage, () => props.pageSize], ([newPage, newSize]) => {
  currentPage.value = newPage
  pageSize.value = newSize
})

// 行点击事件
const handleRowClick = (row, column, event) => {
  emit('row-click', row, column, event)
}

// 选择变化事件
const handleSelectionChange = (selection) => {
  emit('selection-change', selection)
}

// 排序变化事件
const handleSortChange = ({ prop, order }) => {
  emit('sort-change', { prop, order })
}

// 页码变化事件
const handlePageChange = (page) => {
  emit('page-change', page)
}

// 每页条数变化事件
const handleSizeChange = (size) => {
  pageSize.value = size
  emit('size-change', size)
}

// 操作按钮点击
const handleAction = (handler, row, index) => {
  if (typeof handler === 'function') {
    handler(row, index)
  }
  emit('action', handler, row, index)
}

// 暴露方法
defineExpose({
  toggleRowSelection: (row, selected) => {
    // 可通过ref调用
  },
  clearSelection: () => {
    // 可通过ref调用
  },
  clearSort: () => {
    // 可通过ref调用
  }
})
</script>

<style scoped>
.data-table {
  width: 100%;
}

.pagination-wrapper {
  display: flex;
  justify-content: flex-end;
  margin-top: 16px;
}

.el-table :deep(.el-table__row) {
  cursor: pointer;
}

.el-table :deep(.el-table__row:hover) {
  background-color: #f5f7fa;
}
</style>
