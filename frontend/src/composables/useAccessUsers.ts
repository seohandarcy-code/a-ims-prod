import { ref } from 'vue'
import {
  createAccessUser,
  deleteAccessUser,
  fetchAccessUsers,
  updateAccessUser,
} from '../api/client'
import type { AllowedUser } from '../types/api'
import { useAdminAuth } from './useAdminAuth'

export function useAccessUsers() {
  const { token } = useAdminAuth()

  const users = ref<AllowedUser[]>([])
  const loading = ref(false)
  const error = ref<string | null>(null)

  async function load(): Promise<void> {
    if (!token.value) return
    loading.value = true
    error.value = null

    try {
      users.value = await fetchAccessUsers(token.value)
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
    } finally {
      loading.value = false
    }
  }

  async function createUser(ssoId: string, name: string, team: string, isAdmin: boolean): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await createAccessUser({ sso_id: ssoId, name, team, is_admin: isAdmin }, token.value)
      await load()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function updateUser(ssoId: string, name: string, team: string, isAdmin: boolean): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await updateAccessUser(ssoId, { name, team, is_admin: isAdmin }, token.value)
      await load()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  async function deleteUser(ssoId: string): Promise<boolean> {
    if (!token.value) return false
    error.value = null

    try {
      await deleteAccessUser(ssoId, token.value)
      await load()
      return true
    } catch (err) {
      error.value = err instanceof Error ? err.message : String(err)
      return false
    }
  }

  return { users, loading, error, load, createUser, updateUser, deleteUser }
}
