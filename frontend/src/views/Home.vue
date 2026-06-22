<template>
  <a-layout class="root">
    <TopBar @history="showHistory = true" @settings="showSettings = true" />
    <div class="cols">
      <div class="col left">
        <div class="surface left-block">
          <CategorySelect />
          <FilenameCleanSection />
        </div>
        <div class="surface left-block upload-block">
          <UploadArea />
        </div>
        <div class="surface left-block list-block">
          <FileList />
        </div>
      </div>
      <div class="col mid surface mid-col">
        <div class="mid-scroll">
          <ConfigPanel @add-prompt="showAddPrompt = true" @manage-prompts="showPromptMgr = true" />
        </div>
        <div class="mid-footer">
          <a-tooltip :title="startTooltip">
            <a-button
              type="primary"
              block
              size="large"
              class="start-btn"
              :loading="task.isProcessing || files.isUploading"
              :disabled="startDisabled || files.isUploading"
              @click="onStart"
            >
              {{ startButtonText }}
            </a-button>
          </a-tooltip>
        </div>
      </div>
      <div class="col right">
        <TaskProgress />
        <div class="result-shell surface">
          <ResultPanel />
        </div>
      </div>
    </div>
    <SettingsModal v-model:open="showSettings" />
    <HistoryModal v-model:open="showHistory" />
    <AddPromptModal v-model:open="showAddPrompt" @done="onPromptDone" />
    <PromptManagerModal v-model:open="showPromptMgr" @changed="onPromptMgrDone" />
  </a-layout>
</template>

<script setup>
import { ref, onMounted, computed, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import TopBar from '@/components/layout/TopBar.vue'
import CategorySelect from '@/components/middle/CategorySelect.vue'
import FilenameCleanSection from '@/components/left/FilenameCleanSection.vue'
import UploadArea from '@/components/left/UploadArea.vue'
import FileList from '@/components/left/FileList.vue'
import ConfigPanel from '@/components/middle/ConfigPanel.vue'
import TaskProgress from '@/components/right/TaskProgress.vue'
import ResultPanel from '@/components/right/ResultPanel.vue'
import SettingsModal from '@/components/modals/SettingsModal.vue'
import HistoryModal from '@/components/modals/HistoryModal.vue'
import AddPromptModal from '@/components/modals/AddPromptModal.vue'
import PromptManagerModal from '@/components/modals/PromptManagerModal.vue'
import { useConfigStore } from '@/stores/config.js'
import { useFilesStore } from '@/stores/files.js'
import { useTaskStore } from '@/stores/task.js'

const config = useConfigStore()
const files = useFilesStore()
const task = useTaskStore()

const showSettings = ref(false)
const showHistory = ref(false)
const showAddPrompt = ref(false)
const showPromptMgr = ref(false)

const ossOk = computed(
  () =>
    config.oss_access_key_id?.trim() &&
    config.oss_access_key_secret?.trim() &&
    config.oss_bucket_name?.trim() &&
    config.oss_endpoint?.trim()
)

const startButtonText = computed(() => {
  if (files.isUploading) {
    const { done, total, current } = files.uploadProgress
    return current ? `上传中 (${done}/${total})…` : '上传中…'
  }
  if (task.isProcessing) return '处理中…'
  return '开始处理'
})

const startDisabled = computed(() => {
  if (!files.fileList.length) return true
  if (task.isProcessing || files.isUploading) return true
  if (config.transcribe_enabled && config.asr_engine === 'dashscope' && !ossOk.value) return true
  if (config.transcribe_enabled && config.batch_mode === 'merge' && !config.merge_title?.trim()) return true
  return false
})

const startTooltip = computed(() => {
  if (!files.fileList.length) return '请先添加文件'
  if (config.transcribe_enabled && config.asr_engine === 'dashscope' && !ossOk.value)
    return '百炼转写需完整 OSS 配置（在设置中填写）'
  if (config.transcribe_enabled && config.batch_mode === 'merge' && !config.merge_title?.trim())
    return '合并模式需填写合并标题'
  return ''
})

const mainPageHydrated = ref(false)
let mainPageSaveTimer = null

function scheduleMainPageRedisSave() {
  if (!mainPageHydrated.value) return
  clearTimeout(mainPageSaveTimer)
  mainPageSaveTimer = setTimeout(() => {
    config.persistMainPageToRedis().catch(() => {})
  }, 400)
}

watch(
  [
    () => config.category,
    () => config.save_audio_local,
    () => config.save_audio_oss,
    () => config.transcribe_enabled,
    () => config.subtitle_priority,
    () => config.asr_engine,
    () => config.dashscope_api_key,
    () => config.transcript_save_local,
    () => config.transcript_save_oss,
    () => config.batch_mode,
    () => config.merge_title,
    () => config.summary_enabled,
    () => config.summary_model,
    () => config.summary_prompt_title,
    () => config.push_notion_enabled,
    () => config.push_feishu_enabled,
    () => config.filename_temp_rules,
    () => config.filename_regex_library,
    () => config.filename_selected_regex_ids,
  ],
  () => scheduleMainPageRedisSave(),
  { deep: true }
)

onMounted(async () => {
  await Promise.all([config.loadConfig(), config.loadCategories(), config.loadPrompts()])
  await nextTick()
  mainPageHydrated.value = true
})

async function onStart() {
  if (!files.fileList.length) return
  try {
    await files.uploadAll()
    const ok = files.fileList.every((x) => x.temp_path)
    if (!ok) {
      message.error('部分文件未上传成功')
      return
    }
    await task.startProcess(config.buildProcessPayload(), files.fileList)
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  }
}

async function onPromptDone() {
  await config.loadPrompts()
}

async function onPromptMgrDone() {
  await Promise.all([config.loadConfig(), config.loadPrompts()])
}
</script>

<style scoped>
.root {
  min-height: 100vh;
  background: linear-gradient(165deg, #eef2ff 0%, #f8fafc 38%, #fdf4ff 100%);
}
.cols {
  display: flex;
  height: calc(100vh - 48px);
  padding: 14px;
  gap: 14px;
  box-sizing: border-box;
}
.col {
  box-sizing: border-box;
  min-width: 0;
  min-height: 0;
}
.surface {
  background: rgba(255, 255, 255, 0.78);
  backdrop-filter: blur(10px);
  border: 1px solid rgba(255, 255, 255, 0.85);
  border-radius: 14px;
  box-shadow: 0 4px 24px rgba(79, 70, 229, 0.07), 0 1px 3px rgba(0, 0, 0, 0.04);
}
.left {
  width: 33.33%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}
.left-block {
  padding: 12px 14px;
}
.upload-block {
  flex-shrink: 0;
}
.list-block {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: column;
  padding-bottom: 14px;
}
.mid {
  width: 33.33%;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
.mid-col {
  padding: 0 !important;
}
.mid-scroll {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
}
.mid-scroll > * {
  width: 100%;
  max-width: 100%;
}
.mid-footer {
  flex-shrink: 0;
  padding: 10px 14px 16px;
  position: sticky;
  bottom: 0;
  background: rgba(255, 255, 255, 0.95);
  backdrop-filter: blur(8px);
  border-top: 1px solid rgba(99, 102, 241, 0.12);
  border-radius: 0 0 14px 14px;
}
.right {
  width: 33.34%;
  display: flex;
  flex-direction: column;
  gap: 12px;
  overflow: hidden;
}
.start-btn {
  height: 46px !important;
  font-weight: 600;
  border: none !important;
  background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 55%, #a855f7 100%) !important;
  box-shadow: 0 6px 20px rgba(99, 102, 241, 0.35);
}
.start-btn:hover:not(:disabled) {
  filter: brightness(1.05);
}
.result-shell {
  flex: 1;
  min-height: 0;
  overflow: hidden;
  display: flex;
  flex-direction: column;
  padding: 0;
}
.result-shell :deep(.ant-card) {
  height: 100%;
}
</style>
