<template>
  <div class="translate-page">
    <el-card shadow="hover">
      <template #header>
        <div class="card-header">
          <el-icon><Edit /></el-icon>
          <span>中英翻译词库管理</span>
          <el-button type="primary" size="small" style="margin-left: auto" @click="showAddDialog = true">
            <el-icon><Plus /></el-icon>
            新增词条
          </el-button>
        </div>
      </template>

      <el-alert type="info" :closable="false" style="margin-bottom: 16px">
        内置词库覆盖常见运维词汇。可在此新增/修改自定义翻译，解析MIB时会自动应用。
      </el-alert>

      <!-- 搜索 -->
      <el-input
        v-model="searchText"
        placeholder="搜索英文或中文..."
        clearable
        prefix-icon="Search"
        style="margin-bottom: 16px"
      />

      <!-- 内置词库 -->
      <el-divider content-position="left">内置标准词库</el-divider>
      <el-table :data="filteredBuiltin" stripe border size="small" max-height="300">
        <el-table-column prop="english" label="英文关键词" width="200" />
        <el-table-column prop="chinese" label="中文翻译" width="200" />
        <el-table-column label="来源" width="80" align="center">
          <template #default>
            <el-tag type="info" size="small">内置</el-tag>
          </template>
        </el-table-column>
      </el-table>

      <!-- 自定义词库 -->
      <el-divider content-position="left">自定义词库</el-divider>
      <el-table :data="filteredCustom" stripe border size="small">
        <el-table-column prop="english" label="英文关键词" width="200" />
        <el-table-column prop="chinese" label="中文翻译" width="200" />
        <el-table-column prop="category" label="分类" width="100" />
        <el-table-column label="操作" width="100" align="center">
          <template #default="{ row }">
            <el-button type="danger" size="small" text @click="handleDelete(row)">删除</el-button>
          </template>
        </el-table-column>
      </el-table>

      <div v-if="customList.length === 0" style="text-align: center; padding: 20px; color: #999">
        暂无自定义词条，点击右上角"新增词条"添加
      </div>
    </el-card>

    <!-- 新增词条弹窗 -->
    <el-dialog v-model="showAddDialog" title="新增翻译词条" width="400px">
      <el-form :model="newEntry" label-width="80px">
        <el-form-item label="英文关键词">
          <el-input v-model="newEntry.english" placeholder="如: temperature" />
        </el-form-item>
        <el-form-item label="中文翻译">
          <el-input v-model="newEntry.chinese" placeholder="如: 温度" />
        </el-form-item>
        <el-form-item label="分类">
          <el-select v-model="newEntry.category" clearable placeholder="可选">
            <el-option label="状态类" value="status" />
            <el-option label="性能类" value="performance" />
            <el-option label="信息类" value="info" />
          </el-select>
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="showAddDialog = false">取消</el-button>
        <el-button type="primary" @click="handleAdd">添加</el-button>
      </template>
    </el-dialog>
  </div>
</template>

<script setup>
import { ref, computed, onMounted } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { getTranslations, addTranslation, deleteTranslation } from '../api/index.js'

const searchText = ref('')
const builtinList = ref([])
const customList = ref([])
const showAddDialog = ref(false)
const newEntry = ref({ english: '', chinese: '', category: '' })

onMounted(() => {
  loadTranslations()
})

async function loadTranslations() {
  try {
    const { data } = await getTranslations()
    // 内置词库转为数组
    builtinList.value = Object.entries(data.all).map(([en, cn]) => ({
      english: en,
      chinese: cn,
    }))
    customList.value = data.custom || []
  } catch (e) {
    ElMessage.error('加载翻译词库失败')
  }
}

const filteredBuiltin = computed(() => {
  if (!searchText.value) return builtinList.value.slice(0, 50)
  const q = searchText.value.toLowerCase()
  return builtinList.value.filter(
    item => item.english.includes(q) || item.chinese.includes(q)
  ).slice(0, 50)
})

const filteredCustom = computed(() => {
  if (!searchText.value) return customList.value
  const q = searchText.value.toLowerCase()
  return customList.value.filter(
    item => item.english.includes(q) || item.chinese.includes(q)
  )
})

async function handleAdd() {
  if (!newEntry.value.english || !newEntry.value.chinese) {
    ElMessage.warning('请填写英文和中文')
    return
  }
  try {
    await addTranslation(newEntry.value)
    ElMessage.success('添加成功')
    showAddDialog.value = false
    newEntry.value = { english: '', chinese: '', category: '' }
    await loadTranslations()
  } catch (e) {
    ElMessage.error('添加失败')
  }
}

async function handleDelete(row) {
  try {
    await ElMessageBox.confirm(`确定删除词条 "${row.english}" ?`, '确认')
    await deleteTranslation(row.english)
    ElMessage.success('已删除')
    await loadTranslations()
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
