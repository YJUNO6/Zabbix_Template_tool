import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 上传MIB文件
export function uploadMibFiles(files) {
  const formData = new FormData()
  files.forEach(file => formData.append('files', file))
  return api.post('/upload', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
}

// 解析MIB文件
export function parseMib(filenames, vendorOid = '', config = null) {
  return api.post('/parse', { filenames, vendor_oid: vendorOid, config })
}

// 获取默认配置
export function getDefaultConfig() {
  return api.get('/config/defaults')
}

// 获取发现规则列表
export function getDiscoveryRules(taskId) {
  return api.get(`/discovery-rules/${taskId}`)
}

// 获取发现规则的监控项原型
export function getPrototypes(taskId, tableKey) {
  return api.get(`/discovery-rules/${taskId}/prototypes`, { params: { table_key: tableKey } })
}

// 导出XML
export function exportXml(taskId, config, selectedRules = null, rulePrototypes = null) {
  return api.post('/export', {
    task_id: taskId,
    config,
    selected_rules: selectedRules,
    rule_prototypes: rulePrototypes,
  }, { responseType: 'blob' })
}

// 预览XML
export function previewXml(taskId, config, selectedRules = null, rulePrototypes = null) {
  return api.post('/export/preview', {
    task_id: taskId,
    config,
    selected_rules: selectedRules,
    rule_prototypes: rulePrototypes,
  })
}

// 获取预览数据
export function getPreviewData(taskId, page = 1, pageSize = 20) {
  return api.get(`/preview/${taskId}`, { params: { page, page_size: pageSize } })
}

// 翻译管理
export function getTranslations() {
  return api.get('/translations')
}

export function addTranslation(entry) {
  return api.post('/translations', entry)
}

export function deleteTranslation(english) {
  return api.delete(`/translations/${english}`)
}

// 任务管理
export function getTaskList(limit = 50) {
  return api.get('/tasks', { params: { limit } })
}

export function getTaskDetail(taskId) {
  return api.get(`/tasks/${taskId}`)
}

export function deleteTask(taskId) {
  return api.delete(`/tasks/${taskId}`)
}

export default api
