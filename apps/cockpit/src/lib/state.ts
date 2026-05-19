export type UMHViewState<T> =
  | { status: 'loading' }
  | { status: 'error'; error: string }
  | { status: 'ready'; data: T }

export function loading(): UMHViewState<never> {
  return { status: 'loading' }
}

export function error(message: string): UMHViewState<never> {
  return { status: 'error', error: message }
}

export function ready<T>(data: T): UMHViewState<T> {
  return { status: 'ready', data }
}
