import { defineStore } from 'pinia'
import * as api from '@/api/index.js'

let _id = 0
function nid() {
  _id += 1
  return String(_id)
}

export const useFilesStore = defineStore('files', {
  state: () => ({
    fileList: [],
    isUploading: false,
    uploadProgress: { done: 0, total: 0, current: null },
  }),
  actions: {
    addFiles(rawFiles) {
      const incoming = Array.from(rawFiles || [])
      for (const f of incoming) {
        const dup = this.fileList.some((x) => x.filename === f.name && x.size === f.size)
        if (dup) continue
        this.fileList.push({
          id: nid(),
          file: f,
          filename: f.name,
          size: f.size,
          file_type: null,
          temp_path: null,
          upload_status: null,
        })
      }
    },
    removeFile(id) {
      this.fileList = this.fileList.filter((x) => x.id !== id)
    },
    clearAll() {
      this.fileList = []
      this.uploadProgress = { done: 0, total: 0, current: null }
    },
    /** 逐文件上传，避免单次请求体积过大导致超时或 413 */
    async uploadAll() {
      const pendingIdx = this.fileList
        .map((row, i) => (row.file && !row.temp_path ? i : -1))
        .filter((i) => i >= 0)
      if (!pendingIdx.length) return

      this.isUploading = true
      this.uploadProgress = { done: 0, total: pendingIdx.length, current: null }
      const failed = []

      for (const idx of pendingIdx) {
        const row = this.fileList[idx]
        this.uploadProgress.current = row.filename
        this.fileList[idx] = { ...row, upload_status: 'uploading' }

        try {
          const [hit] = await api.uploadFiles([row.file])
          if (!hit?.temp_path) throw new Error('服务器未返回有效路径')
          this.fileList[idx] = {
            ...this.fileList[idx],
            file_type: hit.file_type,
            temp_path: hit.temp_path,
            upload_status: 'done',
          }
        } catch (e) {
          const msg = e?.response?.data?.detail || e.message || String(e)
          this.fileList[idx] = { ...this.fileList[idx], upload_status: 'error' }
          failed.push({ filename: row.filename, message: msg })
        }

        this.uploadProgress.done += 1
      }

      this.isUploading = false
      this.uploadProgress = { ...this.uploadProgress, current: null }

      if (failed.length) {
        const names = failed.map((x) => x.filename).join('、')
        throw new Error(`以下文件上传失败：${names}`)
      }
    },
  },
})
