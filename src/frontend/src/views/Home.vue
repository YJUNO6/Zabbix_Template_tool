<template>
  <div class="home-page">
    <el-row :gutter="20">
      <!-- 左侧: 上传 + 配置 -->
      <el-col :span="10">
        <!-- 文件上传区 -->
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <el-icon><Upload /></el-icon>
              <span>MIB 文件上传</span>
            </div>
          </template>

          <el-upload
            ref="uploadRef"
            drag
            multiple
            :auto-upload="false"
            :on-change="handleFileChange"
            :file-list="fileList"
            accept=".mib,.txt"
          >
            <el-icon class="el-icon--upload"><UploadFilled /></el-icon>
            <div class="el-upload__text">拖拽MIB文件到此处，或 <em>点击选择</em></div>
            <template #tip>
              <div class="el-upload__tip">支持 .mib / .txt 格式，可批量上传</div>
            </template>
          </el-upload>

          <el-input
            v-model="vendorOid"
            placeholder="厂商前缀OID (如 1.3.6.1.4.1.53184)"
            clearable
            style="margin-top: 12px"
          >
            <template #prepend>厂商OID</template>
          </el-input>

          <el-button
            type="primary"
            :loading="parsing"
            :disabled="fileList.length === 0"
            style="margin-top: 12px; width: 100%"
            @click="handleParse"
          >
            解析 MIB 文件
          </el-button>
        </el-card>

        <!-- 模板配置区 -->
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <el-icon><Setting /></el-icon>
              <span>模板配置</span>
            </div>
          </template>

          <el-form :model="config" label-width="120px" size="default">
            <el-form-item label="模板前缀">
              <el-input v-model="config.template_prefix" placeholder="LW_Template" />
            </el-form-item>
            <el-form-item label="设备型号">
              <el-input v-model="config.device_model" placeholder="SR660_V2" />
            </el-form-item>
            <el-form-item label="模板显示名">
              <el-autocomplete
                v-model="config.template_name"
                :fetch-suggestions="getTemplateNameSuggestions"
                placeholder="输入或选择模板名"
                clearable
                style="width: 100%"
                @select="handleTemplateNameSelect"
              >
                <template #default="{ item }">
                  <div class="suggestion-item">
                    <el-icon v-if="item.type === 'auto'" style="color: #409eff; margin-right: 6px"><MagicStick /></el-icon>
                    <el-icon v-else style="color: #67c23a; margin-right: 6px"><Edit /></el-icon>
                    <span>{{ item.value }}</span>
                    <el-tag v-if="item.type === 'auto'" size="small" type="info" style="margin-left: auto">根据MIB生成</el-tag>
                  </div>
                </template>
              </el-autocomplete>
            </el-form-item>
            <el-form-item label="SNMP团体字">
              <el-input v-model="config.snmp_community" placeholder="public" />
            </el-form-item>

            <el-divider content-position="left">采集间隔</el-divider>

            <el-form-item label="状态类间隔">
              <el-select v-model="config.status_delay">
                <el-option label="1分钟" value="1m" />
                <el-option label="5分钟" value="5m" />
              </el-select>
            </el-form-item>
            <el-form-item label="性能类间隔">
              <el-select v-model="config.performance_delay">
                <el-option label="1分钟" value="1m" />
                <el-option label="5分钟" value="5m" />
                <el-option label="10分钟" value="10m" />
              </el-select>
            </el-form-item>
            <el-form-item label="信息类间隔">
              <el-select v-model="config.info_delay">
                <el-option label="1小时" value="1h" />
                <el-option label="1天" value="1d" />
              </el-select>
            </el-form-item>

            <el-divider content-position="left">数据保留</el-divider>

            <el-form-item label="历史保留">
              <el-select v-model="config.history_days">
                <el-option label="7天" value="7d" />
                <el-option label="30天" value="30d" />
                <el-option label="90天" value="90d" />
              </el-select>
            </el-form-item>
            <el-form-item label="趋势保留">
              <el-select v-model="config.trends_days">
                <el-option label="30天" value="30d" />
                <el-option label="365天" value="365d" />
              </el-select>
            </el-form-item>
          </el-form>
        </el-card>
      </el-col>

      <!-- 右侧: 预览 + 导出 -->
      <el-col :span="14">
        <!-- 预览面板 -->
        <el-card shadow="hover" class="section-card">
          <template #header>
            <div class="card-header">
              <el-icon><View /></el-icon>
              <span>解析结果预览</span>
              <el-tag v-if="previewData" type="success" style="margin-left: auto">
                共 {{ previewData.total_oids }} 个OID
              </el-tag>
            </div>
          </template>

          <div v-if="!previewData" class="empty-tip">
            <el-empty description="请先上传并解析MIB文件" />
          </div>

          <div v-else>
            <el-tabs v-model="activeTab">
              <!-- 静态指标列表 -->
              <el-tab-pane label="静态指标" name="static">
                <el-table :data="previewData.static_items.items" stripe border size="small" max-height="400">
                  <el-table-column prop="chinese_name" label="中文名" width="140">
                    <template #default="{ row }">
                      <span class="copy-cell" @click="copyText(row.chinese_name)">
                        {{ row.chinese_name }}
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="name" label="英文名" width="130">
                    <template #default="{ row }">
                      <span class="copy-cell" @click="copyText(row.name)">
                        {{ row.name }}
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="zabbix_key" label="Zabbix Key" width="170">
                    <template #default="{ row }">
                      <span class="copy-cell copy-key" @click="copyText(row.zabbix_key)">
                        {{ row.zabbix_key }}
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="oid" label="OID" width="190">
                    <template #default="{ row }">
                      <span class="copy-cell copy-oid" @click="copyText(row.oid)">
                        {{ row.oid }}
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="delay" label="间隔" width="60" align="center" />
                  <el-table-column prop="category" label="分类" width="70" align="center">
                    <template #default="{ row }">
                      <el-tag :type="getCategoryType(row.category)" size="small">
                        {{ getCategoryLabel(row.category) }}
                      </el-tag>
                    </template>
                  </el-table-column>
                  <el-table-column prop="value_type" label="类型" width="60" align="center">
                    <template #default="{ row }">
                      {{ row.value_type === 0 ? 'FLOAT' : 'TEXT' }}
                    </template>
                  </el-table-column>
                  <el-table-column prop="unit" label="单位" width="50" align="center" />
                  <el-table-column prop="trends" label="趋势" width="50" align="center" />
                </el-table>
                <el-pagination
                  v-if="previewData.static_items.total > 20"
                  v-model:current-page="staticPage"
                  :page-size="20"
                  :total="previewData.static_items.total"
                  layout="total, prev, pager, next"
                  style="margin-top: 12px"
                  @current-change="loadPreview"
                />
              </el-tab-pane>

              <!-- LLD自动发现 -->
              <el-tab-pane label="LLD 自动发现" name="discovery">
                <div v-for="(group, groupName) in previewData.discovery_groups" :key="groupName" class="discovery-group">
                  <el-divider content-position="left">
                    <el-tag>{{ groupName.toUpperCase() }}</el-tag>
                    <span style="margin-left: 8px">共 {{ group.count }} 个实例指标</span>
                  </el-divider>
                  <el-table :data="group.items" stripe border size="small">
                    <el-table-column prop="chinese_name" label="中文名" width="140">
                      <template #default="{ row }">
                        <span class="copy-cell" @click="copyText(row.chinese_name)">
                          {{ row.chinese_name }}
                          <el-icon class="copy-icon"><CopyDocument /></el-icon>
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="zabbix_key" label="Key (含索引)" width="210">
                      <template #default="{ row }">
                        <span class="copy-cell copy-key" @click="copyText(row.zabbix_key)">
                          {{ row.zabbix_key }}
                          <el-icon class="copy-icon"><CopyDocument /></el-icon>
                        </span>
                      </template>
                    </el-table-column>
                    <el-table-column prop="delay" label="间隔" width="60" align="center" />
                    <el-table-column prop="category" label="分类" width="70" align="center">
                      <template #default="{ row }">
                        <el-tag :type="getCategoryType(row.category)" size="small">
                          {{ getCategoryLabel(row.category) }}
                        </el-tag>
                      </template>
                    </el-table-column>
                    <el-table-column label="触发器" width="70" align="center">
                      <template #default="{ row }">
                        <el-tag v-if="row.is_health" type="danger" size="small">有告警</el-tag>
                        <span v-else>-</span>
                      </template>
                    </el-table-column>
                  </el-table>
                </div>
              </el-tab-pane>

              <!-- 触发器预览 -->
              <el-tab-pane label="触发器告警" name="triggers">
                <el-table :data="previewData.health_triggers" stripe border size="small">
                  <el-table-column prop="chinese_name" label="指标名" width="180">
                    <template #default="{ row }">
                      <span class="copy-cell" @click="copyText(row.chinese_name)">
                        {{ row.chinese_name }}
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column prop="zabbix_key" label="Key" width="220">
                    <template #default="{ row }">
                      <span class="copy-cell copy-key" @click="copyText(row.zabbix_key)">
                        {{ row.zabbix_key }}
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="触发条件" min-width="250">
                    <template #default="{ row }">
                      <span class="copy-cell" @click="copyText(getTriggerExpr(row))">
                        <code>{{ getTriggerExpr(row) }}</code>
                        <el-icon class="copy-icon"><CopyDocument /></el-icon>
                      </span>
                    </template>
                  </el-table-column>
                  <el-table-column label="优先级" width="70" align="center">
                    <template #default>
                      <el-tag type="danger" size="small">HIGH</el-tag>
                    </template>
                  </el-table-column>
                </el-table>
              </el-tab-pane>
            </el-tabs>
          </div>
        </el-card>

        <!-- 发现规则选择 -->
        <el-card shadow="hover" class="section-card" v-if="discoveryRules.length > 0">
          <template #header>
            <div class="card-header">
              <el-icon><List /></el-icon>
              <span>选择发现规则</span>
              <el-checkbox
                v-model="selectAllRules"
                :indeterminate="isIndeterminate"
                style="margin-left: auto"
                @change="handleSelectAll"
              >全选</el-checkbox>
              <el-tag style="margin-left: 8px" size="small">
                已选 {{ selectedRuleKeys.length }}/{{ discoveryRules.length }}
              </el-tag>
            </div>
          </template>

          <el-checkbox-group v-model="selectedRuleKeys" class="rule-grid">
            <div v-for="rule in discoveryRules" :key="rule.table_key" class="rule-card"
                 :class="{ 'rule-selected': selectedRuleKeys.includes(rule.table_key) }">
              <el-checkbox :value="rule.table_key" class="rule-checkbox">
                <div class="rule-info">
                  <div class="rule-name">
                    <strong>{{ rule.name }}</strong>
                    <el-tag v-if="rule.has_trigger" type="danger" size="small" style="margin-left: 4px">有告警</el-tag>
                    <el-button
                      v-if="selectedRuleKeys.includes(rule.table_key)"
                      type="primary" link size="small"
                      style="margin-left: auto"
                      @click.stop="openProtoDialog(rule)"
                    >
                      选择原型
                      <el-tag v-if="getProtoSelectedCount(rule.table_key) !== null" size="small" type="warning" style="margin-left: 4px">
                        {{ getProtoSelectedCount(rule.table_key) }}/{{ rule.item_count }}
                      </el-tag>
                    </el-button>
                  </div>
                  <div class="rule-meta">
                    <span>{{ rule.item_count }} 个指标</span>
                    <span v-if="rule.status_count" class="meta-status">状态 {{ rule.status_count }}</span>
                    <span v-if="rule.perf_count" class="meta-perf">性能 {{ rule.perf_count }}</span>
                    <span v-if="rule.info_count" class="meta-info">信息 {{ rule.info_count }}</span>
                  </div>
                  <div class="rule-samples">
                    <el-tag v-for="s in rule.sample_items.slice(0, 3)" :key="s.key" size="small" type="info" class="sample-tag">
                      {{ s.name }}
                    </el-tag>
                  </div>
                </div>
              </el-checkbox>
            </div>
          </el-checkbox-group>
        </el-card>

        <!-- 导出区 -->
        <el-card shadow="hover" class="section-card" v-if="previewData">
          <template #header>
            <div class="card-header">
              <el-icon><Download /></el-icon>
              <span>导出 Zabbix XML</span>
            </div>
          </template>

          <el-descriptions :column="2" border size="small">
            <el-descriptions-item label="模板ID">{{ config.template_prefix }}_{{ config.device_model }}</el-descriptions-item>
            <el-descriptions-item label="显示名称">{{ config.template_name }}</el-descriptions-item>
            <el-descriptions-item label="主机组">服务器模板 / 监控模板</el-descriptions-item>
            <el-descriptions-item label="SNMP团体字">{{ config.snmp_community }}</el-descriptions-item>
            <el-descriptions-item label="状态类间隔">{{ config.status_delay }}</el-descriptions-item>
            <el-descriptions-item label="性能类间隔">{{ config.performance_delay }}</el-descriptions-item>
            <el-descriptions-item label="信息类间隔">{{ config.info_delay }}</el-descriptions-item>
            <el-descriptions-item label="历史/趋势">{{ config.history_days }} / {{ config.trends_days }}</el-descriptions-item>
          </el-descriptions>

          <div style="margin-top: 16px">
            <el-input v-model="exportFilename" placeholder="导出文件名" clearable>
              <template #prepend>文件名</template>
              <template #append>.xml</template>
            </el-input>
          </div>

          <div style="margin-top: 12px; display: flex; gap: 12px">
            <el-button type="primary" :loading="exporting" @click="handleExport">
              <el-icon><Download /></el-icon>
              下载 XML 文件
            </el-button>
            <el-button @click="handlePreviewXml">
              <el-icon><View /></el-icon>
              预览 XML
            </el-button>
          </div>

          <!-- XML预览弹窗 -->
          <el-dialog v-model="showXmlPreview" title="XML 预览" width="80%" top="5vh">
            <pre class="xml-preview">{{ xmlPreviewContent }}</pre>
            <template #footer>
              <el-tag v-if="xmlValidation" :type="xmlValidation.valid ? 'success' : 'danger'">
                {{ xmlValidation.valid ? '校验通过' : '校验失败' }}
              </el-tag>
              <el-button @click="showXmlPreview = false">关闭</el-button>
            </template>
          </el-dialog>
        </el-card>

        <!-- 原型选择弹窗 -->
        <el-dialog v-model="showProtoDialog" :title="protoDialogTitle" width="70%" top="5vh" destroy-on-close>
          <div v-loading="protoDialogLoading">
            <div style="margin-bottom: 12px; display: flex; align-items: center; gap: 12px">
              <el-checkbox
                v-model="allProtoSelected"
                :indeterminate="protoIndeterminate"
                @change="handleProtoSelectAll"
              >全选</el-checkbox>
              <el-tag size="small">已选 {{ selectedProtoOids.length }}/{{ protoList.length }}</el-tag>
            </div>

            <el-table
              ref="protoTableRef"
              :data="protoList"
              stripe border size="small"
              max-height="500"
              @selection-change="handleProtoTableSelect"
            >
              <el-table-column type="selection" width="45" align="center" :selectable="() => true" />
              <el-table-column prop="name" label="中文名" width="160" />
              <el-table-column prop="english_name" label="英文名" width="180" />
              <el-table-column prop="zabbix_key" label="Key" width="220">
                <template #default="{ row }">
                  <code style="font-size: 12px; color: #e6a23c">{{ row.zabbix_key }}</code>
                </template>
              </el-table-column>
              <el-table-column prop="category" label="分类" width="80" align="center">
                <template #default="{ row }">
                  <el-tag :type="row.category === 'status' ? 'warning' : row.category === 'performance' ? 'success' : 'info'" size="small">
                    {{ row.category === 'status' ? '状态' : row.category === 'performance' ? '性能' : '信息' }}
                  </el-tag>
                </template>
              </el-table-column>
              <el-table-column prop="delay" label="间隔" width="60" align="center" />
              <el-table-column prop="value_type" label="类型" width="60" align="center" />
              <el-table-column prop="unit" label="单位" width="50" align="center" />
              <el-table-column label="触发器" width="60" align="center">
                <template #default="{ row }">
                  <el-tag v-if="row.is_health" type="danger" size="small">有</el-tag>
                </template>
              </el-table-column>
            </el-table>
          </div>

          <template #footer>
            <el-button @click="cancelProtoSelection">取消</el-button>
            <el-button type="primary" @click="confirmProtoSelection">确认选择</el-button>
          </template>
        </el-dialog>
      </el-col>
    </el-row>
  </div>
</template>

<script setup>
import { ref, reactive, computed, onMounted, nextTick } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { CopyDocument, MagicStick, Edit, List } from '@element-plus/icons-vue'
import {
  uploadMibFiles, parseMib, getDefaultConfig,
  exportXml, previewXml, getPreviewData, getTaskDetail,
  getDiscoveryRules, getPrototypes
} from '../api/index.js'

const route = useRoute()

// 文件上传
const fileList = ref([])
const vendorOid = ref('')
const parsing = ref(false)

// 模板配置
const config = reactive({
  template_prefix: 'LW_Template',
  device_model: '',
  template_name: '',
  snmp_community: 'public',
  vendor_oid: '',
  status_delay: '1m',
  performance_delay: '5m',
  info_delay: '1d',
  history_days: '7d',
  trends_days: '30d',
})

// 模板名建议
const mibFileName = ref('')

// 从MIB文件名生成模板名建议
function generateTemplateName(filename) {
  if (!filename) return ''

  // 去掉扩展名
  let name = filename.replace(/\.(mib|txt|my)$/i, '')

  // 去掉常见前缀/后缀
  name = name.replace(/^lnvgy_fw_bmc_/i, '')   // Lenovo BMC前缀
  name = name.replace(/^lnvgy_/i, '')            // Lenovo前缀
  name = name.replace(/_anyos.*$/i, '')          // anyos后缀
  name = name.replace(/_noarch.*$/i, '')         // noarch后缀
  name = name.replace(/[-_]v(\d)/i, ' V$1')     // v2 -> V2
  name = name.replace(/[-_]+/g, ' ')             // 下划线/横杠变空格
  name = name.replace(/\s+/g, ' ').trim()        // 合并空格

  // 首字母大写
  name = name.replace(/\b\w/g, c => c.toUpperCase())

  // 加上"服务器模板"后缀
  if (!name.includes('模板') && !name.includes('Template')) {
    name += ' 服务器模板'
  }

  return name
}

// 从MIB文件名生成设备型号
function generateDeviceModel(filename) {
  if (!filename) return ''
  let name = filename.replace(/\.(mib|txt|my)$/i, '')
  name = name.replace(/^lnvgy_fw_bmc_/i, '')
  name = name.replace(/^lnvgy_/i, '')
  name = name.replace(/_anyos.*$/i, '')
  name = name.replace(/_noarch.*$/i, '')
  name = name.replace(/[-_]+/g, '_')
  name = name.replace(/^_+|_+$/g, '')
  return name.toUpperCase()
}

// 自动补全建议
function getTemplateNameSuggestions(queryString, cb) {
  const suggestions = []

  // 根据MIB文件名生成的建议
  if (mibFileName.value) {
    const autoName = generateTemplateName(mibFileName.value)
    if (autoName) {
      suggestions.push({ value: autoName, type: 'auto' })
    }
  }

  // 常用模板名
  const commonNames = [
    'Lenovo 服务器模板', 'Dell 服务器模板', 'HPE 服务器模板',
    '华为 服务器模板', 'H3C 服务器模板', '浪潮 服务器模板',
    '联想 SR660 V2 服务器模板', '联想 SR590 服务器模板',
  ]
  for (const name of commonNames) {
    if (!queryString || name.toLowerCase().includes(queryString.toLowerCase())) {
      suggestions.push({ value: name, type: 'common' })
    }
  }

  cb(suggestions)
}

function handleTemplateNameSelect(item) {
  config.template_name = item.value
  // 如果选了自动生成的，同时更新设备型号和导出文件名
  if (item.type === 'auto' && mibFileName.value) {
    config.device_model = generateDeviceModel(mibFileName.value)
    exportFilename.value = `${config.template_prefix}_${config.device_model}_zabbix6.4`
  }
}

// 预览
const previewData = ref(null)
const activeTab = ref('static')
const staticPage = ref(1)
const currentTaskId = ref('')

// 发现规则选择
const discoveryRules = ref([])
const selectedRuleKeys = ref([])
const selectAllRules = ref(true)
const isIndeterminate = ref(false)

// 原型选择弹窗
const protoTableRef = ref(null)
const showProtoDialog = ref(false)
const protoDialogTitle = ref('')
const protoDialogLoading = ref(false)
const currentRuleKey = ref('')
const protoList = ref([])
const selectedProtoOids = ref([])
const allProtoSelected = ref(true)
const protoIndeterminate = ref(false)
// 每个规则选中的原型OID {table_key: [oid1, oid2, ...]}
const rulePrototypeSelections = ref({})

// 导出
const exporting = ref(false)
const exportFilename = ref('')
const showXmlPreview = ref(false)
const xmlPreviewContent = ref('')
const xmlValidation = ref(null)

onMounted(async () => {
  try {
    const { data } = await getDefaultConfig()
    Object.assign(config, data)
  } catch (e) {
    // 使用默认值
  }

  // 检查是否有复用任务的 task_id 参数
  const taskId = route.query.task_id
  if (taskId) {
    await loadTaskForReuse(taskId)
  }
})

// 加载历史任务进行复用
async function loadTaskForReuse(taskId) {
  try {
    const { data: task } = await getTaskDetail(taskId)

    // 恢复配置
    if (task.config_json) {
      try {
        const savedConfig = JSON.parse(task.config_json)
        Object.assign(config, savedConfig)
      } catch (e) {
        // 配置解析失败，使用默认
      }
    }

    // 恢复文件名
    if (task.filename) {
      mibFileName.value = task.filename.split(',')[0]
      exportFilename.value = `${config.template_prefix}_${config.device_model}_zabbix6.4`
    }

    // 恢复预览数据
    currentTaskId.value = taskId
    await loadPreview()

    ElMessage.success(`已加载历史任务: ${task.filename}`)
  } catch (e) {
    ElMessage.error('加载历史任务失败: ' + (e.response?.data?.detail || e.message))
  }
}

// 复制到剪贴板
async function copyText(text) {
  if (!text) return
  try {
    await navigator.clipboard.writeText(text)
    ElMessage({ message: `已复制: ${text}`, type: 'success', duration: 1500 })
  } catch {
    // fallback
    const textarea = document.createElement('textarea')
    textarea.value = text
    textarea.style.position = 'fixed'
    textarea.style.opacity = '0'
    document.body.appendChild(textarea)
    textarea.select()
    document.execCommand('copy')
    document.body.removeChild(textarea)
    ElMessage({ message: `已复制: ${text}`, type: 'success', duration: 1500 })
  }
}

function getTriggerExpr(row) {
  return `last(/${'{'}HOST{'}'}/${row.zabbix_key})<>"Normal"`
}

function handleFileChange(file, newFileList) {
  fileList.value = newFileList
  // 记录第一个MIB文件名，用于生成模板名建议
  if (newFileList.length > 0) {
    mibFileName.value = newFileList[0].name
    // 如果模板名和设备型号为空，自动生成
    if (!config.template_name) {
      config.template_name = generateTemplateName(mibFileName.value)
    }
    if (!config.device_model) {
      config.device_model = generateDeviceModel(mibFileName.value)
    }
    // 自动生成导出文件名
    if (!exportFilename.value) {
      exportFilename.value = `${config.template_prefix}_${config.device_model}_zabbix6.4`
    }
  }
}

async function handleParse() {
  if (fileList.value.length === 0) {
    ElMessage.warning('请先选择MIB文件')
    return
  }

  parsing.value = true
  try {
    const rawFiles = fileList.value.map(f => f.raw)
    const uploadRes = await uploadMibFiles(rawFiles)
    if (!uploadRes.data.success) {
      ElMessage.error('文件上传失败: ' + uploadRes.data.errors.join('; '))
      return
    }

    const filenames = uploadRes.data.uploaded
    config.vendor_oid = vendorOid.value
    const parseRes = await parseMib(filenames, vendorOid.value, { ...config })

    if (parseRes.data.success) {
      currentTaskId.value = parseRes.data.task_id
      ElMessage.success(parseRes.data.message)
      await loadPreview()
    } else {
      ElMessage.error('解析失败: ' + parseRes.data.message)
    }
  } catch (e) {
    ElMessage.error('操作失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    parsing.value = false
  }
}

async function loadPreview() {
  if (!currentTaskId.value) return
  try {
    const { data } = await getPreviewData(currentTaskId.value, staticPage.value)
    previewData.value = data

    // 加载发现规则列表
    await loadDiscoveryRules()
  } catch (e) {
    ElMessage.error('加载预览失败')
  }
}

async function loadDiscoveryRules() {
  if (!currentTaskId.value) return
  try {
    const { data } = await getDiscoveryRules(currentTaskId.value)
    discoveryRules.value = data.rules || []
    // 默认全选
    selectedRuleKeys.value = discoveryRules.value.map(r => r.table_key)
    selectAllRules.value = true
    isIndeterminate.value = false
  } catch (e) {
    // 没有发现规则也正常
    discoveryRules.value = []
  }
}

function handleSelectAll(val) {
  if (val) {
    selectedRuleKeys.value = discoveryRules.value.map(r => r.table_key)
  } else {
    selectedRuleKeys.value = []
  }
  isIndeterminate.value = false
}

// 监听选择变化，更新全选状态
import { watch } from 'vue'
watch(selectedRuleKeys, (val) => {
  const total = discoveryRules.value.length
  if (val.length === 0) {
    selectAllRules.value = false
    isIndeterminate.value = false
  } else if (val.length === total) {
    selectAllRules.value = true
    isIndeterminate.value = false
  } else {
    isIndeterminate.value = true
  }
})

// === 原型选择弹窗 ===

async function openProtoDialog(rule) {
  currentRuleKey.value = rule.table_key
  protoDialogTitle.value = `${rule.name} - 监控项原型选择`
  showProtoDialog.value = true
  protoDialogLoading.value = true

  try {
    const { data } = await getPrototypes(currentTaskId.value, rule.table_key)
    protoList.value = data.prototypes || []

    // 恢复之前的选择状态，或默认全选
    const saved = rulePrototypeSelections.value[rule.table_key]
    if (saved) {
      selectedProtoOids.value = saved
    } else {
      selectedProtoOids.value = protoList.value.map(p => p.oid)
    }

    // 等表格渲染后设置选中状态
    await nextTick()
    if (protoTableRef.value) {
      protoTableRef.value.clearSelection()
      protoList.value.forEach(row => {
        if (selectedProtoOids.value.includes(row.oid)) {
          protoTableRef.value.toggleRowSelection(row, true)
        }
      })
    }
    updateProtoSelectAllState()
  } catch (e) {
    ElMessage.error('加载监控项原型失败')
    protoList.value = []
  } finally {
    protoDialogLoading.value = false
  }
}

function handleProtoSelectAll(val) {
  if (val) {
    selectedProtoOids.value = protoList.value.map(p => p.oid)
  } else {
    selectedProtoOids.value = []
  }
  protoIndeterminate.value = false
}

function updateProtoSelectAllState() {
  const total = protoList.value.length
  const selected = selectedProtoOids.value.length
  if (selected === 0) {
    allProtoSelected.value = false
    protoIndeterminate.value = false
  } else if (selected === total) {
    allProtoSelected.value = true
    protoIndeterminate.value = false
  } else {
    protoIndeterminate.value = true
  }
}

function handleProtoSelectionChange() {
  updateProtoSelectAllState()
}

function handleProtoTableSelect(selection) {
  selectedProtoOids.value = selection.map(p => p.oid)
  updateProtoSelectAllState()
}

function confirmProtoSelection() {
  // 保存选择
  rulePrototypeSelections.value[currentRuleKey.value] = [...selectedProtoOids.value]
  showProtoDialog.value = false

  const total = protoList.value.length
  const selected = selectedProtoOids.value.length
  ElMessage.success(`已选择 ${selected}/${total} 个监控项原型`)
}

function cancelProtoSelection() {
  showProtoDialog.value = false
}

function getProtoSelectedCount(tableKey) {
  const saved = rulePrototypeSelections.value[tableKey]
  if (!saved) return null  // null表示全选
  return saved.length
}

async function handleExport() {
  exporting.value = true
  try {
    const response = await exportXml(currentTaskId.value, config, selectedRuleKeys.value, rulePrototypeSelections.value)
    const blob = new Blob([response.data], { type: 'application/xml' })
    const url = window.URL.createObjectURL(blob)
    const link = document.createElement('a')
    link.href = url
    // 使用自定义文件名，或从配置自动生成
    const filename = exportFilename.value
      ? `${exportFilename.value}.xml`
      : `${config.template_prefix}_${config.device_model}_zabbix6.4.xml`
    link.download = filename
    link.click()
    window.URL.revokeObjectURL(url)
    ElMessage.success('XML文件下载成功')
  } catch (e) {
    ElMessage.error('导出失败: ' + (e.response?.data?.detail || e.message))
  } finally {
    exporting.value = false
  }
}

async function handlePreviewXml() {
  try {
    const { data } = await previewXml(currentTaskId.value, config, selectedRuleKeys.value, rulePrototypeSelections.value)
    xmlPreviewContent.value = data.xml_preview
    xmlValidation.value = data.validation
    showXmlPreview.value = true
  } catch (e) {
    ElMessage.error('预览失败: ' + (e.response?.data?.detail || e.message))
  }
}

function getCategoryType(category) {
  const map = { status: 'warning', performance: 'success', info: 'info' }
  return map[category] || ''
}

function getCategoryLabel(category) {
  const map = { status: '状态', performance: '性能', info: '信息' }
  return map[category] || category
}
</script>

<style scoped>
.section-card {
  margin-bottom: 20px;
}

.card-header {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
}

.card-header .el-icon {
  font-size: 18px;
  color: #409eff;
}

.empty-tip {
  padding: 40px 0;
}

.discovery-group {
  margin-bottom: 16px;
}

/* 悬停复制样式 */
.copy-cell {
  cursor: pointer;
  position: relative;
  display: inline-flex;
  align-items: center;
  gap: 4px;
  padding: 2px 4px;
  border-radius: 3px;
  transition: background-color 0.2s;
}

.copy-cell:hover {
  background-color: #ecf5ff;
}

.copy-cell .copy-icon {
  display: none;
  font-size: 12px;
  color: #409eff;
  flex-shrink: 0;
}

.copy-cell:hover .copy-icon {
  display: inline-flex;
}

.copy-key {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #e6a23c;
}

.copy-oid {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 12px;
  color: #67c23a;
}

/* 模板名建议下拉 */
.suggestion-item {
  display: flex;
  align-items: center;
  padding: 4px 0;
}

/* 发现规则选择网格 */
.rule-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(280px, 1fr));
  gap: 10px;
  width: 100%;
}

.rule-card {
  border: 1px solid #e4e7ed;
  border-radius: 6px;
  padding: 10px 12px;
  transition: all 0.2s;
  cursor: pointer;
}

.rule-card:hover {
  border-color: #409eff;
  background: #f0f7ff;
}

.rule-card.rule-selected {
  border-color: #409eff;
  background: #ecf5ff;
}

.rule-checkbox {
  width: 100%;
}

.rule-info {
  margin-top: 2px;
}

.rule-name {
  font-size: 14px;
  margin-bottom: 4px;
}

.rule-meta {
  font-size: 12px;
  color: #909399;
  display: flex;
  gap: 8px;
  margin-bottom: 4px;
}

.meta-status { color: #e6a23c; }
.meta-perf { color: #67c23a; }
.meta-info { color: #909399; }

.rule-samples {
  display: flex;
  flex-wrap: wrap;
  gap: 4px;
}

.sample-tag {
  font-size: 11px;
}

.xml-preview {
  background: #1e1e1e;
  color: #d4d4d4;
  padding: 16px;
  border-radius: 4px;
  overflow: auto;
  max-height: 60vh;
  font-size: 12px;
  line-height: 1.5;
  white-space: pre-wrap;
  word-break: break-all;
}
</style>
