<template>
  <a-card size="small" class="card surface-inner">
    <template #title>
      <span class="card-title">处理进度</span>
    </template>
    <div v-if="!rows.length" class="empty">暂无任务</div>
    <div v-else class="scroll-area">
      <div v-for="r in rows" :key="r.key" class="row">
        <span class="idx">{{ r.index }}</span>
        <span class="fn" :title="r.filename">{{ r.filename }}</span>
        <a-tag :color="r.isVideo ? 'processing' : 'success'">{{ r.isVideo ? '视频' : '音频' }}</a-tag>
        <span class="sd" :title="r.step_desc">{{ r.step_desc }}</span>
        <a-progress :percent="r.progress" :stroke-width="6" class="prog" />
        <a-tag :color="tagColor(r)">{{ stepLabel(r) }}</a-tag>
      </div>
    </div>
  </a-card>
</template>

<script setup>
import { computed } from 'vue'
import { useTaskStore } from '@/stores/task.js'

const task = useTaskStore()
const rows = computed(() => task.progressList)

function stepLabel(r) {
  const m = {
    waiting: '等待',
    converting: '转码',
    saving: '保存',
    uploading_oss: 'OSS',
    transcribing: '转写',
    summarizing: '总结',
    done: '完成',
    error: '失败',
  }
  return m[r.step] || r.step || ''
}

function tagColor(r) {
  const s = r.step || ''
  if (r.status === 'error') return 'error'
  if (s === 'waiting') return 'default'
  if (s === 'converting') return 'processing'
  if (s === 'transcribing') return 'warning'
  if (s === 'summarizing') return 'purple'
  if (s === 'done') return 'success'
  return 'processing'
}
</script>

<style scoped>
.card {
  flex-shrink: 0;
  margin-bottom: 0 !important;
  border: none;
  box-shadow: none;
  background: rgba(255, 255, 255, 0.55);
}
.surface-inner {
  border-radius: 12px;
  border: 1px solid rgba(99, 102, 241, 0.1);
}
.card-title {
  font-weight: 700;
  font-size: 14px;
  color: rgba(0, 0, 0, 0.78);
}
/* 约 3 行列表高度：每行 ~52px + 间距 */
.scroll-area {
  max-height: 168px;
  overflow-y: auto;
  padding-right: 4px;
}
.row {
  display: grid;
  grid-template-columns: 26px minmax(0, 1fr) 52px minmax(0, 1fr) 100px 52px;
  gap: 6px;
  align-items: center;
  font-size: 12px;
  margin-bottom: 10px;
  padding-bottom: 8px;
  border-bottom: 1px dashed rgba(0, 0, 0, 0.06);
}
.row:last-child {
  margin-bottom: 0;
  padding-bottom: 0;
  border-bottom: none;
}
.prog {
  min-width: 0;
}
.prog :deep(.ant-progress-outer) {
  margin-inline-end: 0;
  padding-inline-end: 0;
}
.fn {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(0, 0, 0, 0.78);
}
.sd {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  color: rgba(0, 0, 0, 0.5);
}
.idx {
  color: rgba(0, 0, 0, 0.4);
  font-variant-numeric: tabular-nums;
}
.empty {
  color: rgba(0, 0, 0, 0.38);
  font-size: 12px;
  padding: 12px 0;
  text-align: center;
}
</style>
