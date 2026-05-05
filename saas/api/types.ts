/**
 * Shared Hono Env type used by every route file and middleware.
 * Enables c.get('orgId') / c.get('userId') with full TypeScript safety.
 */
export type Env = {
  Variables: {
    orgId:  string
    userId: string
  }
}
