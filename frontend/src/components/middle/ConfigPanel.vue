<template>
  <div class="panel">
    <div class="panel-head">
      <span class="panel-title">处理选项</span>
      <span class="panel-sub">OSS / 路径 / 数据库 / 历史记录在「设置」</span>
    </div>

    <div class="form-inner compact-form">
      <section class="cfg-section">
        <h3 class="cfg-section-title">音频与上传</h3>
        <a-divider class="section-line" />
        <a-form
          layout="horizontal"
          label-align="left"
          :label-col="{ span: 10 }"
          :wrapper-col="{ span: 14 }"
        >
          <a-form-item label="保存音频到本地" class="row-item">
            <a-switch v-model:checked="config.save_audio_local" />
          </a-form-item>
          <a-form-item label="上传音频到 OSS" class="row-item">
            <a-switch v-model:checked="config.save_audio_oss" />
          </a-form-item>
        </a-form>
      </section>

      <section class="cfg-section">
        <h3 class="cfg-section-title">转写引擎</h3>
        <a-divider class="section-line" />
        <a-form
          layout="horizontal"
          label-align="left"
          :label-col="{ span: 10 }"
          :wrapper-col="{ span: 14 }"
        >
          <a-form-item label="引擎" class="row-item">
            <a-radio-group v-model:value="config.asr_engine" size="small">
              <a-radio value="funasr">本地 FunASR</a-radio>
              <a-radio value="dashscope">百炼 API</a-radio>
            </a-radio-group>
          </a-form-item>
        </a-form>
      </section>

      <section class="cfg-section">
        <h3 class="cfg-section-title">转写与文本</h3>
        <a-divider class="section-line" />
        <a-form
          layout="horizontal"
          label-align="left"
          :label-col="{ span: 10 }"
          :wrapper-col="{ span: 14 }"
        >
          <a-form-item label="开启转写" class="row-item">
            <a-switch v-model:checked="config.transcribe_enabled" />
          </a-form-item>
          <a-form-item label="保存文本到本地" class="row-item">
            <a-switch v-model:checked="config.transcript_save_local" :disabled="!config.transcribe_enabled" />
          </a-form-item>
          <a-form-item label="上传文本到 OSS" class="row-item">
            <a-switch v-model:checked="config.transcript_save_oss" :disabled="!config.transcribe_enabled" />
          </a-form-item>
        </a-form>
      </section>

      <section class="cfg-section">
        <h3 class="cfg-section-title">批量模式</h3>
        <a-divider class="section-line" />
        <a-form
          layout="horizontal"
          label-align="left"
          :label-col="{ span: 10 }"
          :wrapper-col="{ span: 14 }"
        >
          <a-form-item label="批量模式" class="row-item merge-row">
            <div class="merge-inline">
              <a-radio-group v-model:value="config.batch_mode" :disabled="!config.transcribe_enabled" size="small">
                <a-radio value="separate">分开</a-radio>
                <a-radio value="merge">合并</a-radio>
              </a-radio-group>
              <transition name="fade">
                <a-input
                  v-if="config.batch_mode === 'merge'"
                  v-model:value="config.merge_title"
                  placeholder="合并标题"
                  size="small"
                  class="merge-inp"
                  :disabled="!config.transcribe_enabled"
                />
              </transition>
            </div>
          </a-form-item>
        </a-form>
      </section>

      <section class="cfg-section">
        <h3 class="cfg-section-title">AI 总结</h3>
        <a-divider class="section-line" />
        <a-form
          layout="horizontal"
          label-align="left"
          :label-col="{ span: 10 }"
          :wrapper-col="{ span: 14 }"
        >
          <a-form-item label="开启 AI 总结" class="row-item">
            <a-switch v-model:checked="config.summary_enabled" :disabled="!config.transcribe_enabled" />
          </a-form-item>
          <a-form-item v-if="config.summary_enabled && config.transcribe_enabled" label="模型 / 提示词" class="row-item">
            <div class="sum-inline">
              <a-select
                v-model:value="config.summary_model"
                size="small"
                style="width: 110px"
                :options="[{ label: '通义千问', value: 'qwen' }]"
              />
              <a-select
                v-model:value="config.summary_prompt_title"
                size="small"
                style="width: calc(100% - 124px); min-width: 0"
                :options="promptOptions"
              />
              <a-tooltip title="管理提示词">
                <a-button size="small" type="text" class="icon-only" @click="$emit('manage-prompts')">
                  <BulbOutlined />
                </a-button>
              </a-tooltip>
              <a-button size="small" type="link" @click="$emit('add-prompt')">+</a-button>
            </div>
          </a-form-item>
        </a-form>
      </section>

      <section class="cfg-section">
        <h3 class="cfg-section-title">推送</h3>
        <a-divider class="section-line" />
        <a-form
          layout="horizontal"
          label-align="left"
          :label-col="{ span: 10 }"
          :wrapper-col="{ span: 14 }"
        >
          <a-form-item label="自动推送 Notion" class="row-item">
            <a-switch v-model:checked="config.push_notion_enabled" />
          </a-form-item>
          <a-form-item label="自动推送飞书" class="row-item">
            <a-switch v-model:checked="config.push_feishu_enabled" />
          </a-form-item>
        </a-form>
      </section>
    </div>
  </div>
</template>

<script setup>
import { computed, onMounted, watch, nextTick } from 'vue'
import { message } from 'ant-design-vue'
import { BulbOutlined } from '@ant-design/icons-vue'
import { useConfigStore } from '@/stores/config.js'
import * as api from '@/api/index.js'

defineEmits(['add-prompt', 'manage-prompts'])

const config = useConfigStore()

watch(
  () => config.asr_engine,
  (nv) => {
    if (nv === 'dashscope' && !config.save_audio_oss) {
      message.warning('请先开启「上传音频到 OSS」后再选择百炼 API')
      nextTick(() => {
        config.asr_engine = 'funasr'
      })
    }
  }
)

onMounted(async () => {
  await config.loadPrompts()
})

const promptOptions = computed(() =>
  (config.prompts || []).map((p) => ({ label: p.title, value: p.title }))
)
</script>

<style scoped>
.panel {
  height: 100%;
  min-height: 0;
  display: flex;
  flex-direction: column;
  align-items: flex-start;
  width: 100%;
  max-width: 100%;
  padding: 8px 10px 8px;
  box-sizing: border-box;
}
.panel-head {
  width: 100%;
  margin-bottom: 8px;
  padding-bottom: 8px;
  border-bottom: 1px solid rgba(99, 102, 241, 0.12);
  text-align: left;
}
.panel-title {
  display: block;
  font-size: 15px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.82);
}
.panel-sub {
  display: block;
  margin-top: 2px;
  font-size: 11px;
  color: rgba(0, 0, 0, 0.42);
}
.form-inner {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding-right: 2px;
  width: 100%;
}
.cfg-section {
  width: 100%;
  text-align: left;
  margin-bottom: 4px;
}
.cfg-section-title {
  margin: 0 0 2px;
  font-size: 13px;
  font-weight: 700;
  color: rgba(0, 0, 0, 0.78);
}
.section-line {
  margin: 6px 0 10px !important;
  border-color: rgba(99, 102, 241, 0.12) !important;
}
.compact-form :deep(.ant-form-item) {
  margin-bottom: 8px;
}
.compact-form :deep(.ant-form-item-label > label) {
  height: auto;
  font-size: 12px;
  justify-content: flex-start;
  padding-right: 8px;
}
.compact-form :deep(.ant-form-item-label) {
  text-align: left;
}
.compact-form :deep(.ant-form-item-control) {
  text-align: left;
}
.compact-form :deep(.ant-form-item-control-input-content) {
  justify-content: flex-start;
}
.row-item :deep(.ant-form-item-control-input) {
  min-height: 28px;
}
.merge-inline {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
  width: 100%;
}
.merge-inp {
  flex: 1;
  min-width: 120px;
}
.sum-inline {
  display: flex;
  align-items: center;
  gap: 6px;
  width: 100%;
  flex-wrap: nowrap;
}
.icon-only {
  padding: 0 6px !important;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.2s ease;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
.inline-hint {
  margin-top: 6px;
  font-size: 11px;
  color: rgba(0, 0, 0, 0.45);
  line-height: 1.4;
}
</style>
