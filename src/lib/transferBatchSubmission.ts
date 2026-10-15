/** Una caída tras commit puede producir resultado incierto, por eso se detiene todo el intento. */
export async function submitTransferRequestsSequentially<T, R>(
  requests: readonly T[],
  create: (request: T) => Promise<R>,
): Promise<{
  confirmed: Array<{ request: T, result: R }>
  failure?: { index: number, request: T, error: unknown }
}> {
  const confirmed: Array<{ request: T, result: R }> = []
  for (let index = 0; index < requests.length; index++) {
    const request = requests[index]
    try {
      const result = await create(request)
      confirmed.push({ request, result })
    } catch (error) {
      return { confirmed, failure: { index, request, error } }
    }
  }
  return { confirmed }
}
