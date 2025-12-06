/**
 * Test manual para verificar el sistema KV Storage
 * Ejecutar en la consola del navegador:
 * 
 * import { getKV } from './lib/kvStorage'
 * const kv = getKV()
 * await kv.set('test-key', { message: 'Hello World' })
 * const result = await kv.get('test-key')
 * console.log('Result:', result)
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
  const undefined_result = await kv.get('non-existent-key')
  console.log('✅ Undefined key test passed:', undefined_result === undefined)
  
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

// Exponer la función globalmente para testing en consola
if (typeof window !== 'undefined') {
  (window as any).testKVStorage = testKVStorage
}
