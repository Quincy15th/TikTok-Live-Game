import { config } from '../config'

export async function apiGet<T>(path: string): Promise<T> {
  const response = await fetch(`${config.apiUrl}${path}`)
  if (!response.ok) {
    throw new Error(`GET ${path} failed: ${response.status}`)
  }
  return response.json() as Promise<T>
}
