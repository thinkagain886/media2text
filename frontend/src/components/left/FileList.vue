<template>
  <div class="wrap">
    <div class="toolbar">
      <span class="toolbar-title">文件列表</span>
      <a-button size="small" danger ghost @click="files.clearAll">清空列表</a-button>
    </div>
    <div class="list">
      <template v-if="!rows.length">
        <div class="empty-hint">暂无文件，请在上方添加</div>
      </template>
      <div v-for="item in rows" :key="item.id" class="row">
        <span class="idx">{{ item.index }}</span>
        <a-tag :color="item.isVideo ? 'processing' : 'success'">{{ item.isVideo ? '视频' : '音频' }}</a-tag>
        <span class="name" :title="item.filename">{{ item.filename }}</span>
        <a-tag v-if="item.uploadStatus" :color="item.uploadColor" class="upload-tag">
          {{ item.uploadLabel }}
        </a-tag>
        <span class="sz">{{ item.sizeText }}</span>
        <a-button type="link" danger size="small" @click="files.removeFile(item.id)">删除</a-button>
      </div>
    </div>
  </div>
</template>

<script setup>
import { computed } from 'vue'
import { useFilesStore } from '@/stores/files.js'

const VIDEO = new Set(['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.ts'])

const files = useFilesStore()

function extOf(name) {
  const i = name.lastIndexOf('.')
  return i >= 0 ? name.slice(i).toLowerCase() : ''
}

function fmt(n) {
  if (n < 1024) return `${n} B`
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`
  return `${(n / 1024 / 1024).toFixed(1)} MB`
}

const UPLOAD_LABEL = { uploading: '上传中', done: '已上传', error: '失败' }
const UPLOAD_COLOR = { uploading: 'processing', done: 'success', error: 'error' }

const rows = computed(() =>
  files.fileList.map((f, i) => ({
    id: f.id,
    index: i + 1,
    filename: f.filename,
    sizeText: fmt(f.size),
    isVideo: VIDEO.has(extOf(f.filename)),
    uploadStatus: f.upload_status,
    uploadLabel: UPLOAD_LABEL[f.upload_status] || '',
    uploadColor: UPLOAD_COLOR[f.upload_status] || 'default',
  }))
)
</script>

<style scoped>
.wrap {
  display: flex;
  flex-direction: column;
  flex: 1;
  min-height: 0;
  gap: 10px;
}
.toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  flex-shrink: 0;
  padding: 0 2px;
}
.toolbar-title {
  font-size: 13px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.75);
}
.list {
  flex: 1;
  min-height: 120px;
  max-height: none;
  overflow-y: auto;
  border: 1px solid rgba(99, 102, 241, 0.15);
  border-radius: 10px;
  background: linear-gradient(180deg, rgba(255, 255, 255, 0.95) 0%, rgba(248, 250, 252, 0.98) 100%);
  box-shadow: inset 0 1px 2px rgba(255, 255, 255, 0.8);
}
.empty-hint {
  padding: 24px 16px;
  text-align: center;
  color: rgba(0, 0, 0, 0.35);
  font-size: 13px;
}
.row {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 10px 12px;
  border-bottom: 1px solid rgba(0, 0, 0, 0.04);
  font-size: 13px;
}
.row:last-child {
  border-bottom: none;
}
.idx {
  width: 22px;
  color: rgba(0, 0, 0, 0.45);
  flex-shrink: 0;
  font-variant-numeric: tabular-nums;
}
.name {
  flex: 1;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  min-width: 0;
  color: rgba(0, 0, 0, 0.82);
}
.upload-tag {
  flex-shrink: 0;
  margin: 0;
  font-size: 11px;
  line-height: 18px;
}
.sz {
  color: rgba(0, 0, 0, 0.45);
  font-size: 12px;
  flex-shrink: 0;
}
</style>
