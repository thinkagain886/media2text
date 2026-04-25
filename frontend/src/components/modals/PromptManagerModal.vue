<template>
  <a-modal v-model:open="visible" title="提示词管理" width="700px" :footer="null" destroy-on-close>
    <div class="toolbar">
      <a-button type="primary" @click="startAdd">+ 新增提示词</a-button>
    </div>
    <a-table
      :columns="columns"
      :data-source="rows"
      :pagination="false"
      row-key="title"
      size="small"
      :loading="loading"
    >
      <template #bodyCell="{ column, record }">
        <template v-if="column.key === 'content'">
          <a-tooltip v-if="(record.content || '').length > 60" :title="record.content">
            <span>{{ (record.content || '').slice(0, 60) }}…</span>
          </a-tooltip>
          <span v-else>{{ record.content || '' }}</span>
        </template>
        <template v-else-if="column.key === 'action'">
          <template v-if="editingTitle === record.title">
            <a-button type="link" size="small" @click="saveEdit">保存</a-button>
            <a-button type="link" size="small" @click="cancelEdit">取消</a-button>
          </template>
          <template v-else>
            <a-button type="link" size="small" @click="startEdit(record)">编辑</a-button>
            <a-button
              type="link"
              danger
              size="small"
              :disabled="record.title === '默认总结'"
              @click="onDelete(record.title)"
            >
              删除
            </a-button>
          </template>
        </template>
      </template>
    </a-table>

    <div v-if="editingTitle && rows.find((r) => r.title === editingTitle)" class="edit-panel">
      <a-form layout="vertical">
        <a-form-item :label="editingTitle === '默认总结' ? '标题（内置不可改）' : '标题'">
          <a-input v-model:value="editForm.title" :disabled="editingTitle === '默认总结'" />
        </a-form-item>
        <a-form-item label="内容">
          <a-textarea v-model:value="editForm.content" :rows="8" />
        </a-form-item>
      </a-form>
    </div>

    <div v-if="adding" class="edit-panel">
      <a-form layout="vertical">
        <a-form-item label="标题">
          <a-input v-model:value="addForm.title" placeholder="唯一标题" />
        </a-form-item>
        <a-form-item label="内容">
          <a-textarea v-model:value="addForm.content" :rows="6" />
        </a-form-item>
        <a-space>
          <a-button type="primary" @click="saveAdd">保存</a-button>
          <a-button @click="adding = false">取消</a-button>
        </a-space>
      </a-form>
    </div>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { Modal, message } from 'ant-design-vue'
import * as api from '@/api/index.js'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open', 'changed'])

const visible = ref(false)
const loading = ref(false)
const rows = ref([])
const editingTitle = ref(null)
const editForm = ref({ title: '', content: '' })
const adding = ref(false)
const addForm = ref({ title: '', content: '' })

const columns = [
  { title: '标题', dataIndex: 'title', key: 'title', width: 140 },
  { title: '内容', key: 'content', ellipsis: true },
  { title: '操作', key: 'action', width: 160 },
]

watch(
  () => props.open,
  async (v) => {
    visible.value = v
    if (v) {
      await load()
      editingTitle.value = null
      adding.value = false
    }
  }
)
watch(visible, (v) => emit('update:open', v))

async function load() {
  loading.value = true
  try {
    rows.value = await api.getPrompts()
  } finally {
    loading.value = false
  }
}

function startEdit(record) {
  editingTitle.value = record.title
  editForm.value = { title: record.title, content: record.content || '' }
}

function cancelEdit() {
  editingTitle.value = null
}

async function saveEdit() {
  const oldTitle = editingTitle.value
  if (!oldTitle) return
  const newTitle = (editForm.value.title || '').trim()
  const content = editForm.value.content || ''
  if (oldTitle !== '默认总结' && !newTitle) {
    message.warning('请填写标题')
    return
  }
  if (oldTitle !== '默认总结' && newTitle === '默认总结') {
    message.warning('不能使用保留标题「默认总结」')
    return
  }
  try {
    const body = { content }
    if (oldTitle !== '默认总结' && newTitle !== oldTitle) {
      body.new_title = newTitle
    }
    await api.putPrompt(oldTitle, body)
    message.success('已保存')
    editingTitle.value = null
    await load()
    emit('changed')
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  }
}

function startAdd() {
  adding.value = true
  addForm.value = { title: '', content: '' }
}

async function saveAdd() {
  const t = (addForm.value.title || '').trim()
  if (!t) {
    message.warning('请填写标题')
    return
  }
  try {
    await api.addPrompt(t, addForm.value.content || '')
    message.success('已新增')
    adding.value = false
    await load()
    emit('changed')
  } catch (e) {
    message.error(e?.response?.data?.detail || e.message || String(e))
  }
}

function onDelete(title) {
  if (title === '默认总结') return
  Modal.confirm({
    title: '删除该提示词？',
    onOk: async () => {
      await api.deletePrompt(title)
      message.success('已删除')
      await load()
      emit('changed')
    },
  })
}
</script>

<style scoped>
.toolbar {
  display: flex;
  justify-content: flex-end;
  margin-bottom: 12px;
}
.edit-panel {
  margin-top: 16px;
  padding: 12px;
  background: rgba(99, 102, 241, 0.06);
  border-radius: 8px;
}
</style>
