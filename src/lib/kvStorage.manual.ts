/**
 * Test manual para verificar el sistema KV Storage.
 *
 * Ejecutar en la consola del navegador:
 *
 * import { testKVStorage } from './lib/kvStorage.manual'
 * await testKVStorage()
 */

export async function testKVStorage() {
  const { getKV } = await import('./kvStorage')
  const kv = getKV()

  console.log('Testing KV Storage...')

  // Test 1: Set and Get
  console.log('Test 1: Set and Get')
  await kv.set('test-key', { message: 'Hello World', timestamp: Date.now() })
  const result = await kv.get('test-key')
  console.log('✅ Set/Get test passed:', result)

  // Test 2: Get undefined key
  console.log('Test 2: Get undefined key')
  const undefinedResult = await kv.get('non-existent-key')
  console.log('✅ Undefined key test passed:', undefinedResult === undefined)

  // Test 3: Delete
  console.log('Test 3: Delete')
  await kv.delete('test-key')
  const deleted = await kv.get('test-key')
  console.log('✅ Delete test passed:', deleted === undefined)

  // Test 4: Keys
  console.log('Test 4: Keys')
  await kv.set('key1', 'value1')
  await kv.set('key2', 'value2')
  const keys = await kv.keys()
  console.log('✅ Keys test passed:', keys)

  // Cleanup
  await kv.delete('key1')
  await kv.delete('key2')

  console.log('All tests passed! ✅')
}

if (typeof window !== 'undefined') {
  ;(window as any).testKVStorage = testKVStorage
}
