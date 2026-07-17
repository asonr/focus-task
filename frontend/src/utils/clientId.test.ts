import { describe, expect, it, vi } from 'vitest'

import { createClientId } from './clientId'

describe('createClientId', () => {
  it('uses randomUUID when the browser provides it', () => {
    const randomUUID = vi.fn(() => '12345678-1234-4123-8123-123456789abc' as `${string}-${string}-${string}-${string}-${string}`)

    expect(createClientId({ randomUUID })).toBe('12345678-1234-4123-8123-123456789abc')
    expect(randomUUID).toHaveBeenCalledOnce()
  })

  it('creates a UUID v4 when randomUUID is unavailable over HTTP', () => {
    const getRandomValues = vi.fn(<T extends Exclude<BufferSource, ArrayBuffer>>(array: T) => {
      if (array instanceof Uint8Array) array.fill(0)
      return array
    })

    expect(createClientId({ getRandomValues })).toBe('00000000-0000-4000-8000-000000000000')
    expect(getRandomValues).toHaveBeenCalledOnce()
  })
})
