<template>
  <a-card size="small" class="card">
    <template #title>
      <span class="card-title">识别结果</span>
    </template>
    <template #extra>
      <a-space size="small" wrap>
        <a-checkbox
          :checked="allSelected"
          :indeterminate="indeterminate"
          @change="onToggleAll"
        >
          全选
        </a-checkbox>
        <a-button size="small" class="ghost-btn" :disabled="!selectedCount" @click="copySelectedJson">
          复制所选 JSON
        </a-button>
        <a-button size="small" class="ghost-btn" :disabled="!selectedCount" @click="downloadSelectedJson">
          下载所选 JSON
        </a-button>
        <a-button size="small" class="ghost-btn" @click="copyJson">复制全部 JSON</a-button>
        <a-button size="small" class="ghost-btn" @click="downloadJson">下载全部</a-button>
        <a-button size="small" danger ghost @click="clear">清除</a-button>
      </a-space>
    </template>
    <div v-if="selectedCount" class="sel-hint">已选 {{ selectedCount }} 条（复制 / 下载所选 使用勾选条目）</div>
    <a-empty v-if="!list.length" description="暂无结果" />
    <a-collapse v-else accordion class="collapse">
      <a-collapse-panel v-for="(it, idx) in list" :key="idx">
        <template #header>
          <span class="hdr-row" @click.stop>
            <a-checkbox
              :checked="isSelected(idx)"
              @change="(e) => toggleIdx(idx, e.target.checked)"
              @click.stop
            />
            <a-tag :color="it.status === 'success' ? 'success' : 'error'">
              {{ it.status === 'success' ? '成功' : '失败' }}
            </a-tag>
            <span class="t-title">{{ it.title }}</span>
            <span class="wc">{{ (it.captions || '').length }} 字</span>
          </span>
        </template>
        <a-tabs>
          <a-tab-pane key="c" tab="原文">
            <a-textarea :value="it.captions || ''" readonly :auto-size="{ minRows: 6, maxRows: 24 }" class="ta" />
          </a-tab-pane>
          <a-tab-pane key="s" tab="总结" :disabled="!it.summary">
            <a-textarea :value="it.summary || ''" readonly :auto-size="{ minRows: 4, maxRows: 20 }" class="ta" />
          </a-tab-pane>
        </a-tabs>
        <div v-if="links(it).length" class="links">
          <div v-for="(u, i) in links(it)" :key="i">
            <a :href="u.url" target="_blank" rel="noopener">{{ u.label }}</a>
          </div>
        </div>
      </a-collapse-panel>
    </a-collapse>
  </a-card>
</template>

<script setup>
import { computed, ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useTaskStore } from '@/stores/task.js'

const task = useTaskStore()
const list = computed(() => task.resultList || [])
const selectedIdx = ref([])

const selectedCount = computed(() => selectedIdx.value.length)

const allSelected = computed(
  () => list.value.length > 0 && selectedIdx.value.length === list.value.length
)
const indeterminate = computed(
  () => selectedIdx.value.length > 0 && selectedIdx.value.length < list.value.length
)

watch(
  () => task.resultList,
  () => {
    selectedIdx.value = []
  },
  { deep: true }
)

function toggleIdx(idx, checked) {
  const arr = [...selectedIdx.value]
  const j = arr.indexOf(idx)
  if (checked && j < 0) arr.push(idx)
  if (!checked && j >= 0) arr.splice(j, 1)
  selectedIdx.value = arr
}

function onToggleAll(e) {
  const on = e.target.checked
  if (!list.value.length) return
  if (on) {
    selectedIdx.value = list.value.map((_, i) => i)
  } else {
    selectedIdx.value = []
  }
}

function plainItems(indices) {
  const arr = indices.map((i) => list.value[i]).filter(Boolean)
  return JSON.parse(JSON.stringify(arr))
}

function selectedPayload() {
  const idxs = [...selectedIdx.value].sort((a, b) => a - b)
  if (!idxs.length) return []
  return plainItems(idxs)
}

function isSelected(idx) {
  return selectedIdx.value.includes(idx)
}

function links(it) {
  const out = []
  const sfs = it.source_files || []
  for (const sf of sfs) {
    if (sf.audio_oss_url) out.push({ label: `音频: ${sf.audio_oss_url}`, url: sf.audio_oss_url })
    if (sf.caption_oss_url) out.push({ label: `字幕: ${sf.caption_oss_url}`, url: sf.caption_oss_url })
  }
  return out
}

function copyJson() {
  const t = JSON.stringify(list.value, null, 2)
  navigator.clipboard.writeText(t).then(
    () => message.success('已复制'),
    () => message.error('复制失败')
  )
}

function copySelectedJson() {
  const items = selectedPayload()
  if (!items.length) {
    message.warning('请先勾选结果')
    return
  }
  const t = JSON.stringify(items, null, 2)
  navigator.clipboard.writeText(t).then(
    () => message.success('已复制所选 JSON 数组'),
    () => message.error('复制失败')
  )
}

function downloadJson() {
  const blob = new Blob([JSON.stringify(list.value, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `result_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function downloadSelectedJson() {
  const items = selectedPayload()
  if (!items.length) {
    message.warning('请先勾选结果')
    return
  }
  const blob = new Blob([JSON.stringify(items, null, 2)], {
    type: 'application/json;charset=utf-8',
  })
  const url = URL.createObjectURL(blob)
  const a = document.createElement('a')
  a.href = url
  a.download = `result_selected_${Date.now()}.json`
  a.click()
  URL.revokeObjectURL(url)
}

function clear() {
  task.resultList = []
}
</script>

<style scoped>
.card {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  border: none;
  box-shadow: none;
  background: transparent;
}
.card :deep(.ant-card-head) {
  flex-wrap: wrap;
  gap: 8px;
}
.card :deep(.ant-card-extra) {
  max-width: 100%;
}
.card :deep(.ant-card-body) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-top: 8px;
}
.card-title {
  font-weight: 700;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.78);
}
.sel-hint {
  font-size: 12px;
  color: rgba(99, 102, 241, 0.9);
  margin-bottom: 8px;
}
.ghost-btn {
  border-color: rgba(99, 102, 241, 0.35) !important;
  color: #6366f1 !important;
}
.collapse {
  border: none;
  background: transparent;
}
.collapse :deep(.ant-collapse-item) {
  border-radius: 10px !important;
  margin-bottom: 10px;
  border: 1px solid rgba(99, 102, 241, 0.12) !important;
  overflow: hidden;
  background: rgba(255, 255, 255, 0.65);
}
.hdr-row {
  display: inline-flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}
.t-title {
  font-weight: 500;
}
.wc {
  margin-left: 4px;
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
}
.ta {
  font-size: 13px !important;
}
.links {
  margin-top: 8px;
  font-size: 12px;
  word-break: break-all;
}
.links a {
  color: #6366f1;
}
</style>
