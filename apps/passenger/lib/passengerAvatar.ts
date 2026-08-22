import AsyncStorage from '@react-native-async-storage/async-storage'
import {supabase} from '@/lib/supabase'

const PENDING_AVATAR_KEY = 'clickgo_pending_passenger_avatar'

type PendingAvatar = {
  email: string
  uri: string
  mimeType: string
}

function extensionFromMime(mimeType: string) {
  if (mimeType.includes('png')) return 'png'
  if (mimeType.includes('webp')) return 'webp'
  return 'jpg'
}

export async function savePendingPassengerAvatar(email: string, uri: string, mimeType = 'image/jpeg') {
  const payload: PendingAvatar = {email: email.trim().toLowerCase(), uri, mimeType}
  await AsyncStorage.setItem(PENDING_AVATAR_KEY, JSON.stringify(payload))
}

export async function clearPendingPassengerAvatar() {
  await AsyncStorage.removeItem(PENDING_AVATAR_KEY)
}

export async function uploadPassengerAvatar(userId: string, uri: string, mimeType = 'image/jpeg') {
  const response = await fetch(uri)
  const arrayBuffer = await response.arrayBuffer()
  const extension = extensionFromMime(mimeType)
  const path = `${userId}/avatar.${extension}`

  const {error: uploadError} = await supabase.storage
    .from('passenger-avatars')
    .upload(path, arrayBuffer, {contentType: mimeType, upsert: true})

  if (uploadError) throw uploadError

  const {data} = supabase.storage.from('passenger-avatars').getPublicUrl(path)
  const {error: profileError} = await supabase
    .from('profiles')
    .update({avatar_url: data.publicUrl})
    .eq('id', userId)

  if (profileError) throw profileError
  return data.publicUrl
}

export async function uploadPendingPassengerAvatar(userId: string, email: string) {
  const raw = await AsyncStorage.getItem(PENDING_AVATAR_KEY)
  if (!raw) return false

  const pending = JSON.parse(raw) as PendingAvatar
  if (pending.email !== email.trim().toLowerCase()) return false

  await uploadPassengerAvatar(userId, pending.uri, pending.mimeType)
  await clearPendingPassengerAvatar()
  return true
}
