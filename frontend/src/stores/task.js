import { defineStore } from 'pinia'
import * as api from '@/api/index.js'

export const useTaskStore = defineStore('task', {
  state: () => ({
    taskId: null,
    progressList: [],
    resultList: [],
    isProcessing: false,
    closeSse: null,
  }),
  actions: {
    async startProcess(configPayload, fileItems) {
      this.isProcessing = true
      this.progressList = []
      this.resultList = []
      this.taskId = null
      const files = fileItems
        .filter((x) => x.temp_path)
        .map((x) => ({ temp_path: x.temp_path, filename: x.filename }))
      const { task_id } = await api.startBatch({ config: configPayload, files })
      this.taskId = task_id
      const VIDEO = new Set(['.mp4', '.mkv', '.avi', '.mov', '.flv', '.wmv', '.webm', '.ts'])
      const ext = (n) => {
        const i = n.lastIndexOf('.')
        return i >= 0 ? n.slice(i).toLowerCase() : ''
      }
      this.progressList = files.map((f, i) => ({
        key: i,
        index: i + 1,
        filename: f.filename,
        isVideo: VIDEO.has(ext(f.filename)),
        step_desc: '等待开始',
        progress: 0,
        step: 'waiting',
        status: 'waiting',
      }))
      if (this.closeSse) this.closeSse()
      this.closeSse = api.subscribeProgress(task_id, (evt) => {
        if (evt.file_index === -1 && evt.error) {
          this.isProcessing = false
          return
        }
        if (evt.results && Array.isArray(evt.results)) {
          this.resultList = evt.results
          this.isProcessing = false
          // 合并+总结阶段会把第 0 行推到「总结中」88%，最终带 results 的事件 file_index 为 -1，
          // 若不刷新列表，界面会一直停在总结中
          this.progressList = this.progressList.map((r) => ({
            ...r,
            step_desc: '已完成',
            progress: 100,
            step: 'done',
            status: 'done',
          }))
          return
        }
        const idx = evt.file_index
        if (idx == null || idx < 0 || idx >= this.progressList.length) return
        const row = { ...this.progressList[idx] }
        row.step_desc = evt.step_desc || ''
        row.progress = evt.progress ?? 0
        row.step = evt.step || 'waiting'
        if (evt.step === 'error' || evt.error) {
          row.status = 'error'
        } else if (evt.step === 'done' && evt.progress >= 100) {
          row.status = 'done'
        } else {
          row.status = 'processing'
        }
        const next = [...this.progressList]
        next[idx] = row
        this.progressList = next
      })
    },
    clearTask() {
      if (this.closeSse) {
        this.closeSse()
        this.closeSse = null
      }
      this.taskId = null
      this.progressList = []
      this.resultList = []
      this.isProcessing = false
    },
  },
})
