/** A failed HTTP response does not prove an upload was rolled back. Stop immediately. */
export async function uploadPhotosSequentially(
  operations: ReadonlyArray<() => Promise<unknown>>,
): Promise<{ confirmed: number; failure?: unknown }> {
  let confirmed = 0
  for (const operation of operations) {
    try {
      await operation()
      confirmed += 1
    } catch (failure) {
      return { confirmed, failure }
    }
  }
  return { confirmed }
}
