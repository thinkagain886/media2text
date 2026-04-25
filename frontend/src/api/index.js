import axios from 'axios'

const http = axios.create({
  baseURL: '/api',
  timeout: 600000,
})

export async function getConfig() {
  const { data } = await http.get('/config')
  return data
}

export async function putConfig(partial) {
  const { data } = await http.put('/config', partial)
  return data
}

export async function resetConfig() {
  const { data } = await http.post('/config/reset')
  return data
}

export async function getCategories() {
  const { data } = await http.get('/config/categories')
  return data
}

export async function addCategory(name) {
  const { data } = await http.post('/config/categories', { name })
  return data
}

export async function deleteCategory(name) {
  const { data } = await http.delete('/config/categories', { params: { name } })
  return data
}

export async function getPrompts() {
  const { data } = await http.get('/config/prompts')
  return data
}

export async function addPrompt(title, content) {
  const { data } = await http.post('/config/prompts', { title, content })
  return data
}

export async function deletePrompt(title) {
  const { data } = await http.delete('/config/prompts', { params: { title } })
  return data
}

export async function testOss(payload) {
  const { data } = await http.post('/config/test-oss', payload)
  return data
}

export async function testDashScope(apiKey) {
  const { data } = await http.post('/config/test-dashscope', {
    dashscope_api_key: apiKey,
  })
  return data
}

export async function uploadFiles(fileList) {
  const fd = new FormData()
  for (const f of fileList) {
    fd.append('files', f)
  }
  const { data } = await http.post('/upload', fd, {
    headers: { 'Content-Type': 'multipart/form-data' },
  })
  return data
}

export async function startBatch(payload) {
  const { data } = await http.post('/process/batch', payload)
  return data
}

export function subscribeProgress(taskId, onMessage) {
  const url = `/api/process/progress/${taskId}`
  const es = new EventSource(url)
  es.onmessage = (ev) => {
    try {
      const j = JSON.parse(ev.data)
      onMessage(j)
    } catch (e) {
      console.error(e)
    }
  }
  es.onerror = () => {
    es.close()
  }
  return () => es.close()
}

export async function getHistory(page, pageSize) {
  const { data } = await http.get('/history', { params: { page, page_size: pageSize } })
  return data
}

export async function getHistoryOne(id) {
  const { data } = await http.get(`/history/${id}`)
  return data
}

export async function deleteHistory(id) {
  const { data } = await http.delete(`/history/${id}`)
  return data
}

export async function deleteHistoryBatch(ids) {
  const { data } = await http.post('/history/delete-batch', { ids })
  return data
}

export async function clearHistory() {
  const { data } = await http.delete('/history')
  return data
}

async function parseBlobError(blob) {
  const t = await blob.text()
  try {
    const j = JSON.parse(t)
    return j.detail || j.message || t
  } catch (_) {
    return t || '请求失败'
  }
}

/** ids 为空数组或省略：导出全部；fmt 默认 xlsx，csv 便于 Notion 导入 */
export async function exportHistoryExcel(ids, fmt = 'xlsx') {
  const body = { fmt }
  if (ids && ids.length) body.ids = ids
  try {
    const res = await http.post('/history/export-excel', body, { responseType: 'blob' })
    const blob = res.data
    if (blob.type && blob.type.includes('application/json')) {
      throw new Error(await parseBlobError(blob))
    }
    const cd = res.headers['content-disposition'] || res.headers['Content-Disposition']
    let name = fmt === 'csv' ? `history_${Date.now()}.csv` : `history_${Date.now()}.xlsx`
    if (cd) {
      const m = /filename="?([^";\n]+)"?/i.exec(cd)
      if (m) name = m[1]
    }
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    a.click()
    URL.revokeObjectURL(url)
  } catch (e) {
    const d = e.response?.data
    if (d instanceof Blob) {
      throw new Error(await parseBlobError(d))
    }
    if (e.response?.data?.detail) {
      throw new Error(e.response.data.detail)
    }
    throw e
  }
}

export async function updateHistoryRecord(recordId, payload) {
  const { data } = await http.put(`/history/${recordId}`, payload)
  return data
}

export async function historySummarize(recordId) {
  const { data } = await http.post(`/history/${recordId}/summarize`)
  return data
}

export async function historyUploadCaptionOss(recordId) {
  const { data } = await http.post(`/history/${recordId}/upload-caption-oss`)
  return data
}

export async function historyPushNotion(recordId) {
  const { data } = await http.post(`/history/${recordId}/push/notion`)
  return data
}

export async function historyPushFeishu(recordId) {
  const { data } = await http.post(`/history/${recordId}/push/feishu`)
  return data
}

export async function getPushFieldGuide() {
  const { data } = await http.get('/push/field-guide')
  return data
}

export async function pushNotion(items) {
  const { data } = await http.post('/push/notion', { items })
  return data
}

export async function pushFeishu(items) {
  const { data } = await http.post('/push/feishu', { items })
  return data
}

export async function getIntegrationSchema() {
  const { data } = await http.get('/integrations/schema')
  return data
}

export async function exportConfigMarkdown() {
  const { data } = await http.get('/config/export-markdown', { responseType: 'text' })
  return data
}

/** 完整快照（含密钥）；勿公开分享 */
export async function exportConfigJson() {
  const { data } = await http.get('/config/export-json')
  return data
}

/** 导入快照：可仅含 config / categories / prompts 任一段 */
export async function importConfigJson(payload) {
  const { data } = await http.post('/config/import-json', payload)
  return data
}

/** @param body {{ content?: string, new_title?: string }} */
export async function putPrompt(title, body) {
  const payload =
    typeof body === 'string' ? { content: body || '' } : { ...(body || {}), content: body?.content ?? '' }
  const { data } = await http.put(`/config/prompts/${encodeURIComponent(title)}`, payload)
  return data
}

export async function testDbConnection() {
  const { data } = await http.post('/config/test-db')
  return data
}

export async function getAsrStatus() {
  const { data } = await http.get('/asr/status')
  return data
}

export async function loadFunasr() {
  const { data } = await http.post('/asr/load-funasr')
  return data
}
