<template>
  <a-modal v-model:open="visible" title="历史记录" width="1380px" :footer="null" destroy-on-close>
    <div class="toolbar">
      <a-space wrap align="center">
        <a-checkbox v-model:checked="exportAsCsv">导出为 CSV（Notion 导入）</a-checkbox>
        <a-button :loading="exportingAll" @click="doExportAll">
          导出全部{{ exportAsCsv ? ' CSV' : ' Excel' }}
        </a-button>
        <a-button :disabled="!selectedRowKeys.length" :loading="exportingSel" @click="doExportSelected">
          导出所选{{ exportAsCsv ? ' CSV' : ' Excel' }}
        </a-button>
        <a-button danger :disabled="!selectedRowKeys.length" @click="batchDelete">删除选中</a-button>
        <a-button danger type="primary" ghost @click="clearAll">清空全部</a-button>
      </a-space>
    </div>
    <a-table
      :columns="columns"
      :data-source="data.items"
      :pagination="pagination"
      :loading="loading"
      :row-selection="rowSelection"
      :scroll="{ x: 1980 }"
      row-key="id"
      size="small"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'uuid'">
          <a-tooltip :title="record.record_uuid || ''">
            <span>{{ uuidShort(record.record_uuid) }}</span>
          </a-tooltip>
        </template>
        <template v-else-if="column.key === 'title'">
          <a-tooltip :title="tipText(record.title)">
            <span class="ellip">{{ clip(record.title, 24) }}</span>
          </a-tooltip>
        </template>
        <template v-else-if="column.key === 'cap_prev'">
          <a-tooltip :title="tipText(record.captions)">
            <span class="ellip">{{ clip(record.captions, 20) }}</span>
          </a-tooltip>
        </template>
        <template v-else-if="column.key === 'sum_prev'">
          <a-tooltip :title="tipText(record.summary)">
            <span class="ellip">{{ clip(record.summary, 20) }}</span>
          </a-tooltip>
        </template>
        <template v-else-if="column.key === 'created_at' || column.key === 'updated_at'">
          {{ formatUtcDbToLocal(record[column.key]) }}
        </template>
        <template v-else-if="column.key === 'mode'">
          {{ modeText(record) }}
        </template>
        <template v-else-if="column.key === 'oss_txt'">
          <div class="cell-pair">
            <span :class="ossOk(record) ? 'ok' : 'no'">{{ ossOk(record) ? '已上传✓' : '未上传' }}</span>
            <span class="sep">|</span>
            <a-button type="link" size="small" :loading="busy[`${record.id}_oss`]" @click="onUploadOss(record)">
              上传
            </a-button>
          </div>
        </template>
        <template v-else-if="column.key === 'ai_sum'">
          <div class="cell-pair">
            <span :class="summOk(record) ? 'ok' : 'no'">{{ summOk(record) ? '已总结✓' : '未总结' }}</span>
            <span class="sep">|</span>
            <a-button type="link" size="small" :loading="busy[`${record.id}_sum`]" @click="onSummarize(record)">
              {{ summOk(record) ? '重新总结' : '总结' }}
            </a-button>
          </div>
        </template>
        <template v-else-if="column.key === 'notion'">
          <div class="cell-pair">
            <span :class="pushN(record) ? 'ok' : 'no'">{{ pushN(record) ? '已推送✓' : '未推送' }}</span>
            <span class="sep">|</span>
            <a-button type="link" size="small" :loading="busy[`${record.id}_notion`]" @click="onPushNotion(record)">
              推送
            </a-button>
          </div>
        </template>
        <template v-else-if="column.key === 'feishu'">
          <div class="cell-pair">
            <span :class="pushF(record) ? 'ok' : 'no'">{{ pushF(record) ? '已推送✓' : '未推送' }}</span>
            <span class="sep">|</span>
            <a-button type="link" size="small" :loading="busy[`${record.id}_feishu`]" @click="onPushFeishu(record)">
              推送
            </a-button>
          </div>
        </template>
        <template v-else-if="column.key === 'action'">
          <a-button type="link" size="small" @click="openDetail(record)">查看</a-button>
          <a-button type="link" size="small" @click="copyJson(record)">复制</a-button>
          <a-button type="link" danger size="small" @click="onDel(record.id)">删除</a-button>
        </template>
      </template>
    </a-table>

    <a-modal v-model:open="detailOpen" title="记录详情" width="820px" :footer="null">
      <div v-if="detail" class="detail-wrap">
        <div class="meta-stack">
          <div class="meta-row">
            <span class="meta-k">UUID</span>
            <span class="mono meta-v">{{ detail.record_uuid || '—' }}</span>
          </div>
          <div class="meta-row">
            <span class="meta-k">标题</span>
            <span class="meta-v title-v">{{ detail.title || '—' }}</span>
          </div>
        </div>

        <div class="lbl">来源文件</div>
        <a-empty v-if="!(detail.source_files || []).length" description="无" />
        <div v-else class="sf-list">
          <div v-for="(sf, i) in detail.source_files || []" :key="i" class="sf-block">
            <div class="sf-head">{{ sf.filename || '(未命名)' }}</div>
            <div class="sf-body">
              <div v-if="sf.audio_oss_url || sf.caption_oss_url" class="sf-actions">
                <a-button v-if="sf.audio_oss_url" size="small" type="primary" ghost @click="openAudio(sf.audio_oss_url)">
                  ▶ 播放
                </a-button>
                <template v-if="sf.caption_oss_url">
                  <a :href="sf.caption_oss_url" target="_blank" rel="noopener">打开字幕链接</a>
                  <a-button size="small" type="link" @click="copyStr(sf.caption_oss_url)">复制链接</a-button>
                </template>
              </div>
              <div v-if="sf.audio_local_path" class="path-line">
                <span class="pk">音频</span>{{ sf.audio_local_path }}
              </div>
              <div v-if="sf.caption_local_path" class="path-line">
                <span class="pk">字幕</span>{{ sf.caption_local_path }}
              </div>
            </div>
          </div>
        </div>

        <div class="block-head">
          <span class="lbl-inline">原文</span>
          <a-space size="small">
            <a-button size="small" type="primary" ghost @click="openEditCaptions">编辑</a-button>
            <a-button size="small" type="link" @click="copyStr(detail.captions || '')">复制</a-button>
          </a-space>
        </div>
        <a-textarea :value="detail.captions || ''" readonly class="readonly-box" :auto-size="{ minRows: 6, maxRows: 24 }" />

        <div class="block-head">
          <span class="lbl-inline">总结</span>
          <a-space size="small">
            <a-button size="small" type="primary" ghost @click="openEditSummary">编辑</a-button>
            <a-button
              v-if="(detail.summary || '').trim()"
              size="small"
              type="link"
              @click="copyStr(detail.summary)"
            >
              复制
            </a-button>
          </a-space>
        </div>
        <a-textarea
          :value="detail.summary || ''"
          readonly
          class="readonly-box"
          :auto-size="{ minRows: 4, maxRows: 20 }"
          placeholder="暂无总结"
        />
      </div>
    </a-modal>

    <a-modal
      v-model:open="editOpen"
      :title="editKind === 'captions' ? '编辑原文' : '编辑总结'"
      width="720px"
      :footer="null"
      destroy-on-close
      @cancel="onEditCancel"
    >
      <div class="edit-toolbar">
        <a-button type="primary" :loading="editSaving" @click="saveEdit">保存</a-button>
        <a-button @click="onEditCancel">取消</a-button>
      </div>
      <a-textarea
        v-model:value="editDraft"
        class="edit-single"
        :auto-size="{ minRows: editKind === 'captions' ? 14 : 12, maxRows: 32 }"
        :placeholder="editKind === 'captions' ? '转写全文' : '总结内容（可空）'"
      />
    </a-modal>

    <a-modal v-model:open="audioOpen" title="音频播放" width="420px" :footer="null" destroy-on-close>
      <audio v-if="audioUrl" :src="audioUrl" controls style="width: 100%" />
    </a-modal>
  </a-modal>
</template>

<script setup>
import { ref, watch, reactive, computed } from 'vue'
import { Modal, message } from 'ant-design-vue'
import * as api from '@/api/index.js'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open'])

const visible = ref(false)
const loading = ref(false)
const data = ref({ total: 0, items: [] })
const page = ref(1)
const pageSize = ref(20)
const detailOpen = ref(false)
const detail = ref(null)
const selectedRowKeys = ref([])
const exportingAll = ref(false)
const exportingSel = ref(false)
const exportAsCsv = ref(false)
const busy = reactive({})
const audioOpen = ref(false)
const audioUrl = ref('')
const editOpen = ref(false)
const editKind = ref('captions')
const editDraft = ref('')
const editSaving = ref(false)

const pagination = computed(() => ({
  current: page.value,
  pageSize: pageSize.value,
  total: data.value.total,
  showSizeChanger: true,
  showTotal: (t) => `共 ${t} 条`,
  pageSizeOptions: ['10', '20', '50', '100'],
  onChange: (p, ps) => {
    pageSize.value = ps
    page.value = p
    selectedRowKeys.value = []
    load()
  },
}))

const rowSelection = computed(() => ({
  selectedRowKeys: selectedRowKeys.value,
  onChange: (keys) => {
    selectedRowKeys.value = keys
  },
}))

const columns = [
  { title: 'ID', dataIndex: 'id', key: 'id', width: 52 },
  { title: 'UUID', key: 'uuid', width: 96 },
  { title: '时间', dataIndex: 'created_at', key: 'created_at', width: 142 },
  { title: '更新时间', dataIndex: 'updated_at', key: 'updated_at', width: 158 },
  { title: '分类', dataIndex: 'category', key: 'category', width: 88 },
  { title: '标题', key: 'title', ellipsis: true, width: 160 },
  { title: '原文预览', key: 'cap_prev', width: 120 },
  { title: '总结预览', key: 'sum_prev', width: 120 },
  { title: '模式', key: 'mode', width: 84 },
  { title: '状态', dataIndex: 'status', key: 'status', width: 72 },
  { title: '文本OSS', key: 'oss_txt', width: 168, fixed: 'right' },
  { title: 'AI总结', key: 'ai_sum', width: 176, fixed: 'right' },
  { title: 'Notion', key: 'notion', width: 168, fixed: 'right' },
  { title: '飞书', key: 'feishu', width: 168, fixed: 'right' },
  { title: '操作', key: 'action', width: 200, fixed: 'right' },
]

function uuidShort(u) {
  if (!u) return '—'
  return u.length > 8 ? `${u.slice(0, 8)}…` : u
}

function clip(s, n) {
  const t = (s || '').trim()
  if (!t) return ''
  return t.length > n ? `${t.slice(0, n)}…` : t
}

function tipText(s) {
  const t = (s || '').trim()
  if (!t) return ''
  if (t.length <= 200) return t
  return `${t.slice(0, 200)}…（点「查看」看全文）`
}

function modeText(r) {
  return r.batch_mode_display || r.batch_mode || ''
}

function ossOk(r) {
  return !!(r.transcript_uploaded_oss ?? r.transcript_on_oss)
}

function summOk(r) {
  return !!(r.summarized ?? r.has_summary)
}

function pushN(r) {
  return !!(r.pushed_notion ?? r.notion_pushed)
}

function pushF(r) {
  return !!(r.pushed_feishu ?? r.feishu_pushed)
}

function sameRecordId(a, b) {
  return Number(a) === Number(b)
}

/** 后端存 UTC（与 SQLite CURRENT_TIMESTAMP 一致）；界面按本地时区展示 */
function formatUtcDbToLocal(s) {
  if (s == null || s === '') return '—'
  const t = String(s).trim()
  const m = /^(\d{4}-\d{2}-\d{2})[ T](\d{2}:\d{2})(?::(\d{2}))?/.exec(t)
  if (!m) return t
  const iso = `${m[1]}T${m[2]}:${m[3] || '00'}Z`
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return t
  return d.toLocaleString('zh-CN', { hour12: false })
}

function patchRecord(row) {
  const items = data.value.items.map((it) => (sameRecordId(it.id, row.id) ? { ...row } : it))
  data.value = { ...data.value, items }
}

watch(
  () => props.open,
  async (v) => {
    visible.value = v
    if (v) {
      page.value = 1
      selectedRowKeys.value = []
      await load()
    }
  }
)
watch(visible, (v) => emit('update:open', v))

async function load() {
  loading.value = true
  try {
    data.value = await api.getHistory(page.value, pageSize.value)
  } finally {
    loading.value = false
  }
}

async function openDetail(row) {
  detail.value = await api.getHistoryOne(row.id)
  detailOpen.value = true
}

function openEditCaptions() {
  if (!detail.value) return
  editKind.value = 'captions'
  editDraft.value = detail.value.captions ?? ''
  editOpen.value = true
}

function openEditSummary() {
  if (!detail.value) return
  editKind.value = 'summary'
  editDraft.value = detail.value.summary ?? ''
  editOpen.value = true
}

function onEditCancel() {
  editOpen.value = false
}

async function saveEdit() {
  if (!detail.value) return
  editSaving.value = true
  try {
    const payload =
      editKind.value === 'captions'
        ? { captions: editDraft.value }
        : { summary: editDraft.value }
    const { record } = await api.updateHistoryRecord(detail.value.id, payload)
    detail.value = record
    patchRecord(record)
    message.success('已保存')
    editOpen.value = false
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  } finally {
    editSaving.value = false
  }
}

function copyJson(row) {
  navigator.clipboard.writeText(JSON.stringify(row, null, 2)).then(
    () => message.success('已复制'),
    () => message.error('复制失败')
  )
}

function copyStr(t) {
  navigator.clipboard.writeText(t || '').then(
    () => message.success('已复制'),
    () => message.error('复制失败')
  )
}

function openAudio(url) {
  audioUrl.value = url
  audioOpen.value = true
}

async function onSummarize(record) {
  busy[`${record.id}_sum`] = true
  try {
    const { record: row } = await api.historySummarize(record.id)
    patchRecord(row)
    message.success('已完成')
    if (detail.value && sameRecordId(detail.value.id, row.id)) detail.value = row
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  } finally {
    busy[`${record.id}_sum`] = false
  }
}

async function onUploadOss(record) {
  busy[`${record.id}_oss`] = true
  try {
    const { record: row } = await api.historyUploadCaptionOss(record.id)
    patchRecord(row)
    message.success('已上传')
    if (detail.value && sameRecordId(detail.value.id, row.id)) detail.value = row
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  } finally {
    busy[`${record.id}_oss`] = false
  }
}

async function onPushNotion(record) {
  busy[`${record.id}_notion`] = true
  try {
    const { record: row } = await api.historyPushNotion(record.id)
    patchRecord(row)
    message.success('已推送 Notion')
    if (detail.value && sameRecordId(detail.value.id, row.id)) detail.value = row
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  } finally {
    busy[`${record.id}_notion`] = false
  }
}

async function onPushFeishu(record) {
  busy[`${record.id}_feishu`] = true
  try {
    const { record: row } = await api.historyPushFeishu(record.id)
    patchRecord(row)
    message.success('已推送飞书')
    if (detail.value && sameRecordId(detail.value.id, row.id)) detail.value = row
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  } finally {
    busy[`${record.id}_feishu`] = false
  }
}

const exportFmt = () => (exportAsCsv.value ? 'csv' : 'xlsx')

async function doExportAll() {
  if (!data.value.total) {
    message.warning('没有可导出的记录')
    return
  }
  exportingAll.value = true
  try {
    await api.exportHistoryExcel(null, exportFmt())
    message.success('已开始下载')
  } catch (e) {
    message.error(String(e?.message || e?.response?.data?.detail || e))
  } finally {
    exportingAll.value = false
  }
}

async function doExportSelected() {
  if (!selectedRowKeys.value.length) return
  exportingSel.value = true
  try {
    await api.exportHistoryExcel(selectedRowKeys.value.map((x) => Number(x)), exportFmt())
    message.success('已开始下载')
  } catch (e) {
    message.error(String(e?.message || e?.response?.data?.detail || e))
  } finally {
    exportingSel.value = false
  }
}

function onDel(id) {
  Modal.confirm({
    title: '确认删除该记录？',
    onOk: async () => {
      await api.deleteHistory(id)
      message.success('已删除')
      selectedRowKeys.value = selectedRowKeys.value.filter((k) => k !== id)
      await load()
    },
  })
}

function batchDelete() {
  if (!selectedRowKeys.value.length) return
  Modal.confirm({
    title: '删除选中记录',
    content: `将删除 ${selectedRowKeys.value.length} 条记录，不可恢复。`,
    okType: 'danger',
    async onOk() {
      await api.deleteHistoryBatch(selectedRowKeys.value)
      message.success('已删除')
      selectedRowKeys.value = []
      await load()
    },
  })
}

function clearAll() {
  Modal.confirm({
    title: '清空全部历史',
    content: '将删除数据库中所有历史记录，不可恢复。',
    okText: '清空',
    okType: 'danger',
    async onOk() {
      await api.clearHistory()
      message.success('已清空')
      selectedRowKeys.value = []
      await load()
    },
  })
}
</script>

<style scoped>
.toolbar {
  margin-bottom: 12px;
}
.lbl {
  font-weight: 600;
  margin: 14px 0 8px;
}
.detail-wrap {
  text-align: left;
}
.meta-stack {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 8px 10px;
  margin-bottom: 8px;
  background: rgba(99, 102, 241, 0.06);
  border-radius: 8px;
  border: 1px solid rgba(99, 102, 241, 0.1);
}
.meta-row {
  display: grid;
  grid-template-columns: 44px 1fr;
  align-items: start;
  gap: 8px;
  font-size: 12px;
}
.meta-k {
  color: rgba(0, 0, 0, 0.45);
  flex-shrink: 0;
}
.meta-v {
  word-break: break-all;
  color: rgba(0, 0, 0, 0.85);
}
.title-v {
  font-weight: 600;
}
.mono {
  font-family: ui-monospace, monospace;
  font-size: 11px;
}
.sf-list {
  display: flex;
  flex-direction: column;
  gap: 12px;
}
.sf-block {
  padding: 10px 12px;
  border: 1px solid rgba(0, 0, 0, 0.06);
  border-radius: 8px;
  background: rgba(0, 0, 0, 0.02);
}
.sf-head {
  font-weight: 700;
  margin-bottom: 8px;
  font-size: 13px;
}
.sf-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
}
.sf-actions {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 10px;
}
.path-line {
  font-size: 11px;
  color: rgba(0, 0, 0, 0.55);
  word-break: break-all;
  line-height: 1.5;
}
.pk {
  display: inline-block;
  min-width: 36px;
  margin-right: 6px;
  color: rgba(0, 0, 0, 0.38);
}
.block-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-top: 12px;
  margin-bottom: 6px;
}
.lbl-inline {
  font-weight: 700;
  font-size: 13px;
}
.readonly-box {
  margin-bottom: 4px;
}
.edit-toolbar {
  display: flex;
  justify-content: flex-start;
  gap: 8px;
  margin-bottom: 10px;
}
.edit-single {
  font-family: inherit;
}
.flex-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.muted {
  color: rgba(0, 0, 0, 0.45);
}
.ellip {
  display: inline-block;
  max-width: 100%;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  vertical-align: bottom;
}
.cell-pair {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  font-size: 12px;
}
.cell-pair .ok {
  color: #52c41a;
}
.cell-pair .no {
  color: rgba(0, 0, 0, 0.45);
}
.sep {
  color: rgba(0, 0, 0, 0.25);
}
</style>
