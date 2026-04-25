<template>
  <a-modal v-model:open="visible" title="添加提示词" @ok="onOk" @cancel="close">
    <a-form layout="vertical">
      <a-form-item label="标题" required>
        <a-input v-model:value="title" />
      </a-form-item>
      <a-form-item label="内容" required>
        <a-textarea v-model:value="content" :rows="6" />
      </a-form-item>
    </a-form>
  </a-modal>
</template>

<script setup>
import { ref, watch } from 'vue'
import { message } from 'ant-design-vue'
import { useConfigStore } from '@/stores/config.js'

const props = defineProps({ open: { type: Boolean, default: false } })
const emit = defineEmits(['update:open', 'done'])

const config = useConfigStore()
const visible = ref(false)
const title = ref('')
const content = ref('')

watch(
  () => props.open,
  (v) => {
    visible.value = v
    if (v) {
      title.value = ''
      content.value = ''
    }
  }
)
watch(visible, (v) => emit('update:open', v))

function close() {
  visible.value = false
}

async function onOk() {
  const t = title.value.trim()
  const c = content.value.trim()
  if (!t || !c) {
    message.warning('请填写标题和内容')
    return
  }
  try {
    await config.addPrompt(t, c)
    message.success('已添加')
    emit('done')
    visible.value = false
  } catch (e) {
    message.error(String(e))
  }
}
</script>
