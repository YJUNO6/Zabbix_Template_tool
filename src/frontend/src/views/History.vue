<template>
  <div class="history-page">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon><Clock /></el-icon>
          <span>历史任务</span>
          <el-button size="small" style="margin-left: auto" @click="loadTasks">
            <el-icon><Refresh /></el-icon>
            刷新
          </el-button>
        </div>
      </template>

      <el-table :data="tasks" stripe border v-loading="loading">
        <el-table-column prop="task_id" label="任务ID" width="200" show-overflow-tooltip />
        <el-table-column prop="filename" label="MIB文件" width="200" show-overflow-tooltip />
        <el-table-column prop="created_at" label="创建时间" width="180">
          <template #default="{ row }">
            {{ formatTime(row.created_at) }}
          </template>
        </el-table-column>
        <el-table-column prop="status" label="状态" width="100" align="center">
          <template #default="{ row }">
            <el-tag :type="getStatusType(row.status)" size="small">
              {{ getStatusLabel(row.status) }}
            </el-tag>
          </template>
        </el-table-column>
        <el-table-column prop="message" label="消息" min-width="200" show-overflow-tooltip />
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button type="primary" size="small" text @click="handleReuse(row)">复用</el-button>
            <el-button type="danger" size="small" text @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="tasks.length === 0" style="text-align: center; padding: 40px; color: #999">
        暂无历史任务记录
      </div>
    </el-card>
  </div>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTaskList, deleteTask } from '../api/index.js'

const router = useRouter()
const tasks = ref([])
const loading = ref(false)

onMounted(() => {
  loadTasks()
})

async function loadTasks() {
  loading.value = true
  try {
    const { data } = await getTaskList()
    tasks.value = data
  } catch (e) {
    ElMessage.error('加载任务列表失败')
  } finally {
    loading.value = false
  }
}

function formatTime(isoStr) {
  if (!isoStr) return '-'
  return new Date(isoStr).toLocaleString('zh-CN')
}

function getStatusType(status) {
  const map = { pending: 'info', parsed: 'warning', exported: 'success', failed: 'danger' }
  return map[status] || 'info'
}

function getStatusLabel(status) {
  const map = { pending: '待处理', parsed: '已解析', exported: '已导出', failed: '失败' }
  return map[status] || status
}

function handleReuse(row) {
  router.push({ path: '/', query: { task_id: row.task_id } })
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm('确定删除该任务记录?', '确认删除')
    await deleteTask(row.task_id)
    ElMessage.success('已删除')
    await loadTasks()
  } catch (e) {
    if (e !== 'cancel') ElMessage.error('删除失败')
  }
}
</script>

<style scoped>
.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}
</style>
