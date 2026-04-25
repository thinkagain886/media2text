<template>
  <div class="row">
    <span class="lbl">当前分类</span>
    <a-select
      v-model:value="config.category"
      class="cat-select"
      style="flex: 1; min-width: 0"
      show-search
      option-label-prop="label"
    >
      <a-select-option v-for="c in config.categories" :key="c" :value="c" :label="c">
        <div class="cat-opt">
          <span class="cat-name">{{ c }}</span>
          <a-button
            v-if="c !== '默认分类'"
            type="link"
            size="small"
            danger
            class="cat-del"
            @mousedown.prevent.stop
            @click.stop.prevent="onDeleteCat(c)"
          >
            删除
          </a-button>
        </div>
      </a-select-option>
    </a-select>
    <a-button type="primary" @click="open = true">+ 添加</a-button>
  </div>
  <a-modal v-model:open="open" title="新建分类" @ok="onOk">
    <a-input v-model:value="newName" placeholder="分类名称" />
  </a-modal>
</template>

<script setup>
import { ref, onMounted } from 'vue'
import { message, Modal } from 'ant-design-vue'
import { useConfigStore } from '@/stores/config.js'

const config = useConfigStore()
const open = ref(false)
const newName = ref('')

onMounted(async () => {
  await config.loadCategories()
})

async function onOk() {
  const n = (newName.value || '').trim()
  if (!n) {
    message.warning('请输入分类名')
    return
  }
  try {
    await config.addCategory(n)
    config.category = n
    newName.value = ''
    open.value = false
    message.success('已添加')
  } catch (e) {
    message.error(e?.response?.data?.detail || String(e))
  }
}

function onDeleteCat(name) {
  Modal.confirm({
    title: '删除分类',
    content: `确定从列表中删除「${name}」吗？`,
    okText: '删除',
    okType: 'danger',
    async onOk() {
      try {
        await config.deleteCategory(name)
        message.success('已删除')
      } catch (e) {
        message.error(e?.response?.data?.detail || String(e))
        throw e
      }
    },
  })
}
</script>

<style scoped>
.row {
  display: flex;
  align-items: center;
  gap: 8px;
}
.lbl {
  white-space: nowrap;
}
.cat-opt {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  width: 100%;
}
.cat-name {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
}
.cat-del {
  flex-shrink: 0;
  padding: 0 4px !important;
  height: auto !important;
}
.cat-select :deep(.ant-select-selection-item) .cat-del {
  display: none;
}
</style>
