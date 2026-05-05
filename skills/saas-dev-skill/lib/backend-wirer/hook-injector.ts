import type { BackendEndpointSpec } from "@shared/spec-schema.js";
import type { PageSpecFull } from "@shared/spec-schema.js";
import type { HookInjection } from "./types.js";

// ─── HELPERS ──────────────────────────────────────────────────────────────────

/**
 * Convert a route path to a kebab-case page file name.
 * "/widgets" -> "widgets-page.tsx"
 * "/user-profiles" -> "user-profiles-page.tsx"
 * "/" -> "home-page.tsx"
 */
function routeToPageFileName(route: string): string {
  const slug = route.replace(/^\//, "").replace(/\//g, "-") || "home";
  return `${slug}-page.tsx`;
}

/**
 * Map a uiPageRef or page route to its page file path.
 */
function resolvePageFilePath(uiPageRef: string | undefined, pages: PageSpecFull[]): string {
  if (!uiPageRef) {
    return "client/src/pages/unknown-page.tsx";
  }

  // Try to find a matching page by route
  const matchedPage = pages.find((p) => p.route === uiPageRef);
  if (matchedPage) {
    const fileName = routeToPageFileName(matchedPage.route);
    return `client/src/pages/${fileName}`;
  }

  // Fallback: derive from the uiPageRef directly
  const slug = uiPageRef.replace(/^\//, "").replace(/\//g, "-") || "unknown";
  return `client/src/pages/${slug}-page.tsx`;
}

/**
 * Derive a resource name from an endpoint path for naming hooks and variables.
 * "/api/widgets" -> "widgets"
 * "/api/user-profiles" -> "userProfiles"
 */
function pathToResourceName(path: string): string {
  const segments = path.split("/").filter((s) => s && !s.startsWith(":") && s !== "api");
  const last = segments[segments.length - 1] ?? "items";
  return last.replace(/-([a-z])/g, (_, c: string) => c.toUpperCase());
}

/**
 * Singularize a resource name for mutation naming.
 * "widgets" -> "widget", "userProfiles" -> "userProfile"
 */
function singularize(resource: string): string {
  if (resource.endsWith("ies")) return resource.slice(0, -3) + "y";
  if (resource.endsWith("ses") || resource.endsWith("xes") || resource.endsWith("zes")) return resource.slice(0, -2);
  if (resource.endsWith("s") && !resource.endsWith("ss")) return resource.slice(0, -1);
  return resource;
}

// ─── HOOK INJECTOR ────────────────────────────────────────────────────────────

/**
 * Generate TanStack Query hook injection descriptors for each endpoint.
 * GET endpoints produce useQuery hooks.
 * POST/PUT/PATCH/DELETE endpoints produce useMutation hooks.
 * Per D-02 — matches the existing useQuery/useMutation pattern in client/src/hooks/.
 */
export function generateHookInjections(
  endpoints: BackendEndpointSpec[],
  pageSpecs: PageSpecFull[]
): HookInjection[] {
  return endpoints.map((endpoint) => {
    const pageFilePath = resolvePageFilePath(endpoint.uiPageRef, pageSpecs);
    const resource = pathToResourceName(endpoint.path);
    const single = singularize(resource);

    if (endpoint.method === "GET") {
      return generateQueryHook(endpoint, pageFilePath, resource);
    } else {
      return generateMutationHook(endpoint, pageFilePath, resource, single);
    }
  });
}

function generateQueryHook(
  endpoint: BackendEndpointSpec,
  pageFilePath: string,
  resource: string
): HookInjection {
  const hookImport = [
    `import { useQuery } from "@tanstack/react-query";`,
    `import { apiRequest } from "@/lib/queryClient";`,
  ].join("\n");

  const hookCode = [
    `const { data: ${resource}, isLoading } = useQuery({`,
    `  queryKey: ["${endpoint.path}"],`,
    `  queryFn: () => apiRequest("${endpoint.path}"),`,
    `});`,
  ].join("\n");

  return {
    pageFilePath,
    hookImport,
    hookCode,
    replacePattern: "",
  };
}

function generateMutationHook(
  endpoint: BackendEndpointSpec,
  pageFilePath: string,
  resource: string,
  single: string
): HookInjection {
  const methodLower = endpoint.method.toLowerCase();
  const mutationName = `${methodLower === "post" ? "create" : methodLower === "delete" ? "delete" : "update"}${single.charAt(0).toUpperCase() + single.slice(1)}`;

  // Derive related GET path for invalidation
  const relatedGetPath = endpoint.path.replace(/\/:id$/, "").replace(/\/[^/]*$/, (match) => {
    // If path ends with /:id, strip to collection path
    return match.startsWith("/:") ? "" : match;
  }) || endpoint.path.replace(/\/:id$/, "");

  const hookImport = [
    `import { useMutation, useQueryClient } from "@tanstack/react-query";`,
    `import { apiRequest } from "@/lib/queryClient";`,
  ].join("\n");

  const hookCode = [
    `const queryClient = useQueryClient();`,
    `const ${mutationName}Mutation = useMutation({`,
    `  mutationFn: (data: Record<string, unknown>) => apiRequest("${endpoint.path}", { method: "${endpoint.method}", body: JSON.stringify(data) }),`,
    `  onSuccess: () => queryClient.invalidateQueries({ queryKey: ["${relatedGetPath}"] }),`,
    `});`,
  ].join("\n");

  return {
    pageFilePath,
    hookImport,
    hookCode,
    replacePattern: "",
  };
}
