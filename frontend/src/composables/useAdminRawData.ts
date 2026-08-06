import { ref } from 'vue'
import {
  addAdminColumn,
  addAdminRow,
  deleteAdminColumn,
  deleteAdminRow,
  editAdminRow,
  fetchAdminCsvBlob,
  fetchAdminRawData,
  restoreAdminBackup,
} from '../api/client'
import type { AddColumnRequest, RawDataResponse, RowEditRequest } from '../types/api'
import { useAdminAuth } from './useAdminAuth'

export function useAdminRawData() {
  const { token, bumpDataVersion } = useAdminAuth()

  const data = ref<RawDataResponse | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(): Promise<void> {
    if (!token.value) return
    loading.value = true
    error.value = null

    try {
      data.value = await fetchAdminRawData(token.value)
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  async function editRow(no: number | string, fields: Record<string, string>): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await editAdminRow(no, { fields } satisfies RowEditRequest, token.value)
      await load()
      bumpDataVersion()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function addRow(fields: Record<string, string>): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await addAdminRow({ fields } satisfies RowEditRequest, token.value)
      await load()
      bumpDataVersion()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function deleteRow(no: number | string): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await deleteAdminRow(no, token.value)
      await load()
      bumpDataVersion()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function restoreBackup(): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await restoreAdminBackup(token.value)
      await load()
      bumpDataVersion()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function addColumn(name: string, type: AddColumnRequest['type']): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await addAdminColumn({ name, type }, token.value)
      await load()
      bumpDataVersion()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function deleteColumn(key: string): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await deleteAdminColumn(key, token.value)
      await load()
      bumpDataVersion()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function downloadCsv(): Promise<void> {
    if (!token.value) return
    const blob = await fetchAdminCsvBlob(token.value)
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'investment_raw_data.csv'
    a.click()
    URL.revokeObjectURL(url)
  }

  return {
    data,
    loading,
    error,
    load,
    editRow,
    addRow,
    deleteRow,
    restoreBackup,
    addColumn,
    deleteColumn,
    downloadCsv,
  }
}
