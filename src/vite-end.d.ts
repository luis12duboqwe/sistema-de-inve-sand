/// <reference types="vite/client" />
declare const GITHUB_RUNTIME_PERMANENT_NAME: string
declare const BASE_KV_SERVICE_URL: string

interface SparkKV {
  get: <T>(key: string) => Promise<T | undefined>
  set: <T>(key: string, value: T) => Promise<void>
  delete: (key: string) => Promise<void>
  keys: () => Promise<string[]>
}

interface Spark {
  kv: SparkKV
  llmPrompt: (strings: TemplateStringsArray | string[], ...values: any[]) => string
  llm: (prompt: string, modelName?: string, jsonMode?: boolean) => Promise<string>
  user: () => Promise<{
    avatarUrl: string
    email: string
    id: string
    isOwner: boolean
    login: string
  }>
}

declare global {
  interface Window {
    spark: Spark
  }
  const spark: Spark
}

export {}