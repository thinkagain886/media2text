<template>
  <div class="upload-wrap">
    <a-upload-dragger
      v-model:file-list="internalList"
      name="file"
      :multiple="true"
      :before-upload="beforeUpload"
      :show-upload-list="false"
      accept=".mp4,.mkv,.avi,.mov,.flv,.wmv,.webm,.mp3,.wav,.m4a,.aac,.flac,.ogg,.amr"
      class="dragger"
    >
      <p class="ant-upload-drag-icon"><inbox-outlined /></p>
      <p class="ant-upload-text">点击或拖拽文件到此处</p>
      <p class="ant-upload-hint">支持常见音视频格式，可多选</p>
    </a-upload-dragger>
  </div>
</template>

<script setup>
import { ref, watch } from 'vue'
import { InboxOutlined } from '@ant-design/icons-vue'
import { useFilesStore } from '@/stores/files.js'

const files = useFilesStore()
const internalList = ref([])

const beforeUpload = (file) => {
  files.addFiles([file])
  return false
}

watch(
  () => files.fileList,
  (list) => {
    internalList.value = (list || []).map((x, i) => ({
      uid: x.id || String(i),
      name: x.filename,
      status: 'done',
    }))
  },
  { deep: true }
)
</script>

<style scoped>
.upload-wrap {
  flex-shrink: 0;
}
.dragger {
  border-radius: 12px !important;
  overflow: hidden;
  border: 1px dashed rgba(99, 102, 241, 0.35) !important;
  background: linear-gradient(145deg, rgba(238, 242, 255, 0.9) 0%, rgba(255, 255, 255, 0.95) 50%, rgba(250, 245, 255, 0.85) 100%) !important;
  transition: border-color 0.2s ease, box-shadow 0.2s ease;
}
.dragger:hover {
  border-color: rgba(99, 102, 241, 0.65) !important;
  box-shadow: 0 8px 24px rgba(99, 102, 241, 0.12);
}
.dragger :deep(.ant-upload) {
  padding: 20px 16px 18px;
}
.dragger :deep(.ant-upload-drag-icon) {
  margin-bottom: 8px;
}
.dragger :deep(.ant-upload-drag-icon .anticon) {
  color: #6366f1;
  font-size: 40px;
}
.dragger :deep(.ant-upload-text) {
  font-size: 15px;
  font-weight: 600;
  color: rgba(0, 0, 0, 0.78);
  margin-bottom: 4px;
}
.dragger :deep(.ant-upload-hint) {
  font-size: 12px;
  color: rgba(0, 0, 0, 0.45);
}
</style>
