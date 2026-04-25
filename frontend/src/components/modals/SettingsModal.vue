<template>
  <a-modal
    v-model:open="visible"
    title="系统设置"
    width="800px"
    :footer="null"
    destroy-on-close
    wrap-class-name="settings-modal-root"
    :body-style="{ padding: 0 }"
    @cancel="$emit('update:open', false)"
  >
    <div class="settings-modal-body">
      <a-tabs v-model:activeKey="tab" tab-position="left" class="settings-tabs">
      <a-tab-pane key="oss" tab="OSS 配置">
        <div class="hint" style="margin-bottom: 12px">是否在转写前上传音频到 OSS 请在主页「处理选项」中开关；此处仅填写凭证。</div>
        <a-input v-model:value="local.oss_access_key_id" placeholder="Access Key ID" />
        <a-input-password v-model:value="local.oss_access_key_secret" placeholder="Access Key Secret" style="margin-top: 8px" />
        <a-input v-model:value="local.oss_bucket_name" placeholder="Bucket Name" style="margin-top: 8px" />
        <a-input v-model:value="local.oss_endpoint" placeholder="oss-cn-hangzhou.aliyuncs.com" style="margin-top: 8px" />
        <a-button style="margin-top: 12px" @click="testOss">测试连接</a-button>
        <div v-if="ossMsg" class="hint">{{ ossMsg }}</div>
      </a-tab-pane>
      <a-tab-pane key="path" tab="本地路径与存储">
        <a-form layout="vertical">
          <a-form-item label="音频输出根目录">
            <a-input v-model:value="local.audio_local_base_path" placeholder="./output" />
          </a-form-item>
          <a-form-item label="字幕输出根目录">
            <a-input v-model:value="local.transcript_local_base_path" placeholder="./output" />
          </a-form-item>
          <a-form-item label="临时文件目录">
            <a-input v-model:value="local.temp_dir" placeholder="./temp" />
          </a-form-item>
          <a-form-item label="文件名清洗正则">
            <a-textarea
              v-model:value="local.filename_clean_regex"
              placeholder="留空则不清洗；Python 正则，作用于去掉扩展名后的主名"
              :auto-size="{ minRows: 2, maxRows: 6 }"
            />
            <div class="hint">
              例：去掉首段「作者-」可用 <code>^[^-]*-\s*</code>；取中间段可用带捕获组如
              <code>^[^-]*-(.*)-[^-]*$</code>。title、列表与 OSS/本地命名均用清洗后名称；原始名在
              <code>original_filename</code> 保留。
            </div>
          </a-form-item>
        </a-form>
      </a-tab-pane>
      <a-tab-pane key="ai" tab="AI 模型">
        <a-input-password v-model:value="local.qwen_api_key" placeholder="通义千问 API Key（用于总结）" />
        <a-button style="margin-top: 8px" @click="testQwen">测试</a-button>
      </a-tab-pane>
      <a-tab-pane key="push" tab="推送">
        <div class="hint" style="margin-bottom: 12px">
          多维表格 / Notion Database 中的<strong>列名须与输出 JSON 的键名完全一致</strong>（无需在此填写列名）。
          Notion 请创建 Integration 并邀请到目标库；Database ID 支持粘贴完整页面链接（自动提取 32 位 ID）。
          飞书请创建自建应用并开通多维表格权限。
        </div>
        <a-space style="margin-bottom: 12px">
          <a-button :loading="fieldGuideLoading" @click="openFieldGuide">查看需建字段与类型</a-button>
        </a-space>
        <a-divider orientation="left">Notion</a-divider>
        <a-input-password
          v-model:value="local.notion_integration_token"
          placeholder="Internal Integration Secret"
          style="margin-bottom: 8px"
        />
        <a-input
          v-model:value="local.notion_database_id"
          placeholder="Database ID 或 Notion 数据库页面链接"
        />
        <a-divider orientation="left">飞书多维表格</a-divider>
        <a-input v-model:value="local.feishu_app_id" placeholder="App ID" style="margin-bottom: 8px" />
        <a-input-password v-model:value="local.feishu_app_secret" placeholder="App Secret" style="margin-bottom: 8px" />
        <a-input v-model:value="local.feishu_bitable_app_token" placeholder="多维表格 App Token（URL 中 apps/ 后一段）" style="margin-bottom: 8px" />
        <a-input v-model:value="local.feishu_table_id" placeholder="数据表 Table ID" style="margin-bottom: 8px" />
      </a-tab-pane>
      <a-tab-pane key="db" tab="数据库">
        <div class="hint" style="margin-bottom: 12px">
          SQLite 路径也可在后端 <code>.env</code> 的 SQLITE_PATH 配置；此处留空则沿用环境变量。
          切换引擎并保存后，建议「测试连接」确认。
        </div>
        <a-form layout="vertical" style="margin-bottom: 16px">
          <a-form-item label="保存处理结果到历史记录（数据库）">
            <a-switch v-model:checked="local.save_to_db" />
            <div class="hint">关闭后仅本次会话展示结果，不写入数据库。</div>
          </a-form-item>
        </a-form>
        <a-radio-group v-model:value="local.db_engine">
          <a-radio value="sqlite">SQLite</a-radio>
          <a-radio value="supabase">Supabase</a-radio>
        </a-radio-group>
        <template v-if="local.db_engine === 'sqlite'">
          <a-input
            v-model:value="local.sqlite_path"
            placeholder="留空则使用环境变量 SQLITE_PATH，或填写 ./media2text.db"
            style="margin-top: 12px"
          />
        </template>
        <template v-else>
          <a-input v-model:value="local.supabase_url" placeholder="https://xxx.supabase.co" style="margin-top: 12px" />
          <a-input-password v-model:value="local.supabase_key" placeholder="Supabase Key" style="margin-top: 8px" />
          <a-input v-model:value="local.supabase_table" placeholder="表名 records" style="margin-top: 8px" />
        </template>
        <a-button style="margin-top: 12px" :loading="testingDb" @click="testDb">测试连接</a-button>
      </a-tab-pane>
      <a-tab-pane key="snapshot" tab="配置快照">
        <div class="export-json-title">配置快照（JSON）</div>
        <div class="hint json-hint">
          导出为<strong>完整</strong> JSON（含密钥），请妥善保管；Markdown 导出仍为<strong>脱敏</strong>便于分享。
        </div>
        <a-space wrap class="json-actions">
          <a-button :loading="copyingMd" size="small" @click="copyMarkdown">复制 Markdown（脱敏）</a-button>
          <a-button :loading="copyingJson" size="small" type="primary" ghost @click="copyJsonFull">
            复制 JSON（完整）
          </a-button>
          <a-button :loading="copyingJson" size="small" @click="downloadJsonFile">下载 JSON 文件</a-button>
          <a-button size="small" :loading="importingJson" @click="triggerImportFile">从 JSON 导入…</a-button>
        </a-space>
        <input ref="jsonFileInputRef" type="file" accept=".json,application/json" class="sr-only" @change="onImportJsonFile" />
      </a-tab-pane>
    </a-tabs>
    </div>

    <div class="footer-btns">
      <a-button danger :loading="resetting" @click="onReset">恢复默认设置</a-button>
      <div class="footer-right">
        <a-button @click="close">取消</a-button>
        <a-button type="primary" :loading="saving" @click="save">保存设置</a-button>
      </div>
    </div>

    <a-modal v-model:open="fieldGuideOpen" title="Notion / 飞书 — 字段名与类型" width="720px" :footer="null">
      <div v-if="fieldGuide">
        <p class="hint">{{ fieldGuide.notion_note }}</p>
        <p class="hint">{{ fieldGuide.feishu_note }}</p>
        <a-table
          :columns="fieldGuideColumns"
          :data-source="fieldGuide.fields"
          :pagination="false"
          size="small"
          row-key="key"
          bordered
        />
      </div>
    </a-modal>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useConfigStore } from '@/stores/config.js'
import * as api from '@/api/index.js'

const props = defineProps({
  open: { type: Boolean, default: false },
})
const emit = defineEmits(['update:open'])

const config = useConfigStore()
const visible = ref(false)
const tab = ref('oss')
const local = ref({})
const ossMsg = ref('')
const saving = ref(false)
const resetting = ref(false)
const fieldGuideOpen = ref(false)
const fieldGuide = ref(null)
const fieldGuideLoading = ref(false)
const testingDb = ref(false)
const copyingMd = ref(false)
const copyingJson = ref(false)
const importingJson = ref(false)
const jsonFileInputRef = ref(null)

const fieldGuideColumns = [
  { title: '键名（列名）', dataIndex: 'key', key: 'key', width: 120 },
  { title: 'Notion', dataIndex: 'notion_type', ellipsis: true },
  { title: '飞书', dataIndex: 'feishu_type', ellipsis: true },
]

watch(
  () => props.open,
  async (v) => {
    visible.value = v
    if (v) {
      await config.loadConfig()
      local.value = { ...config.buildProcessPayload() }
      ossMsg.value = ''
    }
  }
)

watch(visible, (v) => emit('update:open', v))

function close() {
  visible.value = false
}

function onReset() {
  Modal.confirm({
    title: '恢复默认设置',
    content:
      '将清空 Redis 中的全部配置（含密钥、路径、自定义分类与提示词），并恢复为初始默认值。此操作不可撤销。',
    okText: '确定恢复',
    okType: 'danger',
    cancelText: '取消',
    async onOk() {
      resetting.value = true
      try {
        await api.resetConfig()
        await Promise.all([config.loadConfig(), config.loadCategories(), config.loadPrompts()])
        local.value = { ...config.buildProcessPayload() }
        ossMsg.value = ''
        message.success('已恢复默认设置')
      } catch (e) {
        message.error(String(e?.response?.data?.detail || e))
        throw e
      } finally {
        resetting.value = false
      }
    },
  })
}

async function save() {
  saving.value = true
  try {
    await config.saveConfig({ ...local.value })
    await config.loadConfig()
    message.success('已保存')
    visible.value = false
  } catch (e) {
    message.error(String(e))
  } finally {
    saving.value = false
  }
}

async function testOss() {
  ossMsg.value = ''
  try {
    await api.testOss({
      oss_access_key_id: local.value.oss_access_key_id,
      oss_access_key_secret: local.value.oss_access_key_secret,
      oss_bucket_name: local.value.oss_bucket_name,
      oss_endpoint: local.value.oss_endpoint,
    })
    ossMsg.value = 'OSS 连接成功'
    message.success('OSS OK')
  } catch (e) {
    ossMsg.value = String(e?.response?.data?.detail || e)
    message.error('OSS 失败')
  }
}

async function testQwen() {
  try {
    await api.testDashScope(local.value.qwen_api_key)
    message.success('Key 可用（与百炼同域校验）')
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e))
  }
}

async function openFieldGuide() {
  fieldGuideLoading.value = true
  try {
    fieldGuide.value = await api.getIntegrationSchema()
    fieldGuideOpen.value = true
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e.message || e))
  } finally {
    fieldGuideLoading.value = false
  }
}

async function testDb() {
  testingDb.value = true
  try {
    await api.testDbConnection()
    message.success('数据库连接正常')
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e.message || e))
  } finally {
    testingDb.value = false
  }
}

async function copyMarkdown() {
  copyingMd.value = true
  try {
    const md = await api.exportConfigMarkdown()
    await navigator.clipboard.writeText(md)
    message.success('已复制 Markdown（脱敏）')
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e.message || e))
  } finally {
    copyingMd.value = false
  }
}

async function copyJsonFull() {
  copyingJson.value = true
  try {
    const blob = await api.exportConfigJson()
    const text = JSON.stringify(blob, null, 2)
    await navigator.clipboard.writeText(text)
    message.success('已复制完整 JSON')
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e.message || e))
  } finally {
    copyingJson.value = false
  }
}

async function downloadJsonFile() {
  copyingJson.value = true
  try {
    const blob = await api.exportConfigJson()
    const text = JSON.stringify(blob, null, 2)
    const url = URL.createObjectURL(new Blob([text], { type: 'application/json;charset=utf-8' }))
    const a = document.createElement('a')
    a.href = url
    a.download = `media2text-config-${Date.now()}.json`
    a.click()
    URL.revokeObjectURL(url)
    message.success('已开始下载')
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e.message || e))
  } finally {
    copyingJson.value = false
  }
}

function triggerImportFile() {
  jsonFileInputRef.value?.click?.()
}

async function onImportJsonFile(ev) {
  const input = ev.target
  const file = input.files && input.files[0]
  if (!file) return
  importingJson.value = true
  try {
    const text = await file.text()
    let payload
    try {
      payload = JSON.parse(text)
    } catch (_) {
      message.error('JSON 格式无效')
      return
    }
    await api.importConfigJson(payload)
    await Promise.all([config.loadConfig(), config.loadCategories(), config.loadPrompts()])
    local.value = { ...config.buildProcessPayload() }
    message.success('已从 JSON 导入并重载')
  } catch (e) {
    message.error(String(e?.response?.data?.detail || e.message || e))
  } finally {
    importingJson.value = false
    input.value = ''
  }
}
</script>

<style scoped>
.settings-modal-body {
  height: min(72vh, 680px);
  min-height: 420px;
  max-height: 680px;
  overflow: hidden;
  display: flex;
  flex-direction: column;
}
:deep(.settings-tabs) {
  flex: 1;
  min-height: 0;
  display: flex;
  flex-direction: row;
}
:deep(.settings-tabs .ant-tabs-content-holder) {
  flex: 1;
  min-height: 0;
  overflow-y: auto;
  padding: 12px 16px 8px 4px;
}
:deep(.settings-tabs .ant-tabs-nav) {
  flex-shrink: 0;
  padding-top: 8px;
}
.hint {
  margin-top: 8px;
  color: #888;
  font-size: 12px;
}
.footer-btns {
  margin-top: 16px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  flex-wrap: wrap;
  gap: 8px;
}
.footer-right {
  display: flex;
  gap: 8px;
  margin-left: auto;
}
.export-json-title {
  font-weight: 600;
  margin-bottom: 6px;
  font-size: 13px;
}
.json-hint {
  margin-bottom: 10px !important;
}
.json-actions {
  width: 100%;
}
.sr-only {
  position: absolute;
  width: 1px;
  height: 1px;
  padding: 0;
  margin: -1px;
  overflow: hidden;
  clip: rect(0, 0, 0, 0);
  white-space: nowrap;
  border: 0;
}
</style>
