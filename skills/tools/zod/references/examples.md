# Zod — EOS-Aligned Examples

Real, execution-ready patterns for the EOS SaaS stack
(React 18 + TS strict + RHF + shadcn + Express + Drizzle).

---

## (a) Login form — schema + RHF + shadcn Form

```ts
// src/schemas/auth.ts
import { z } from "zod";

export const LoginSchema = z.object({
  email: z.string().trim().toLowerCase().email("Enter a valid email"),
  password: z
    .string()
    .min(8, "At least 8 characters")
    .max(128, "At most 128 characters"),
  remember: z.boolean().default(false),
});

export type LoginInput = z.input<typeof LoginSchema>;   // before transforms
export type LoginValues = z.output<typeof LoginSchema>; // after transforms
```

```tsx
// src/components/LoginForm.tsx
"use client";
import { useForm } from "react-hook-form";
import { zodResolver } from "@hookform/resolvers/zod";
import { LoginSchema, type LoginInput } from "@/schemas/auth";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Checkbox } from "@/components/ui/checkbox";
import {
  Form, FormControl, FormField, FormItem, FormLabel, FormMessage,
} from "@/components/ui/form";

export function LoginForm({
  onSubmit,
}: {
  onSubmit: (values: LoginInput) => Promise<void>;
}) {
  // Use z.input because .default() makes `remember` optional on input.
  const form = useForm<LoginInput>({
    resolver: zodResolver(LoginSchema),
    defaultValues: { email: "", password: "", remember: false },
    mode: "onBlur",
  });

  return (
    <Form {...form}>
      <form onSubmit={form.handleSubmit(onSubmit)} className="space-y-6">
        <FormField
          control={form.control}
          name="email"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Email</FormLabel>
              <FormControl><Input type="email" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="password"
          render={({ field }) => (
            <FormItem>
              <FormLabel>Password</FormLabel>
              <FormControl><Input type="password" {...field} /></FormControl>
              <FormMessage />
            </FormItem>
          )}
        />
        <FormField
          control={form.control}
          name="remember"
          render={({ field }) => (
            <FormItem className="flex items-center gap-2">
              <FormControl>
                <Checkbox
                  checked={field.value}
                  onCheckedChange={field.onChange}
                />
              </FormControl>
              <FormLabel className="m-0">Remember me</FormLabel>
            </FormItem>
          )}
        />
        <Button type="submit" disabled={form.formState.isSubmitting}>
          Sign in
        </Button>
      </form>
    </Form>
  );
}
```

---

## (b) API request/response — shared schema, server + React Query

```ts
// src/schemas/user.ts  (imported by BOTH client and server)
import { z } from "zod";

export const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  name: z.string().min(1).max(255),
  createdAt: z.coerce.date(),
});
export type User = z.infer<typeof UserSchema>;

export const CreateUserRequest = UserSchema.omit({ id: true, createdAt: true });
export type CreateUserRequest = z.infer<typeof CreateUserRequest>;

export const CreateUserResponse = z.object({
  user: UserSchema,
});
export type CreateUserResponse = z.infer<typeof CreateUserResponse>;
```

```ts
// server/routes/users.ts
import express from "express";
import { CreateUserRequest } from "@/schemas/user";
import { db } from "@/db";
import { users } from "@/db/schema";

export const usersRouter = express.Router();

usersRouter.post("/users", async (req, res) => {
  const parsed = CreateUserRequest.safeParse(req.body);
  if (!parsed.success) {
    return res.status(400).json({
      errors: parsed.error.flatten().fieldErrors,
    });
  }
  const [inserted] = await db.insert(users).values(parsed.data).returning();
  return res.status(201).json({ user: inserted });
});
```

```ts
// src/hooks/useCreateUser.ts
import { useMutation, useQueryClient } from "@tanstack/react-query";
import {
  CreateUserRequest,
  CreateUserResponse,
  type CreateUserRequest as CreateUserRequestT,
} from "@/schemas/user";

async function createUser(input: CreateUserRequestT) {
  // Client-side pre-flight parse — catches bugs before the network call.
  const body = CreateUserRequest.parse(input);
  const res = await fetch("/api/users", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  if (!res.ok) throw new Error("Create failed");
  // Parse the response so the client never trusts an unexpected shape.
  return CreateUserResponse.parse(await res.json());
}

export function useCreateUser() {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: createUser,
    onSuccess: () => qc.invalidateQueries({ queryKey: ["users"] }),
  });
}
```

---

## (c) Env parser at app boot

```ts
// src/lib/env.ts
import { z } from "zod";

const EnvSchema = z.object({
  NODE_ENV: z.enum(["development", "test", "production"]),
  DATABASE_URL: z.string().url(),
  JWT_SECRET: z.string().min(32, "JWT_SECRET must be at least 32 chars"),
  PORT: z.coerce.number().int().positive().default(3000),
  STRIPE_SECRET_KEY: z.string().startsWith("sk_"),
  LOG_LEVEL: z.enum(["debug", "info", "warn", "error"]).default("info"),
});

const parsed = EnvSchema.safeParse(process.env);
if (!parsed.success) {
  console.error(
    "Invalid environment variables:",
    parsed.error.flatten().fieldErrors
  );
  process.exit(1);
}

export const env = parsed.data;
// Import `env` everywhere — never touch process.env directly.
```

---

## (d) Discriminated union — polymorphic DTO

```ts
// src/schemas/events.ts
import { z } from "zod";

export const EventSchema = z.discriminatedUnion("type", [
  z.object({
    type: z.literal("user.created"),
    userId: z.string().uuid(),
    email: z.string().email(),
    createdAt: z.coerce.date(),
  }),
  z.object({
    type: z.literal("payment.succeeded"),
    paymentId: z.string(),
    amountCents: z.number().int().nonnegative(),
    currency: z.string().length(3),
  }),
  z.object({
    type: z.literal("subscription.canceled"),
    subscriptionId: z.string(),
    reason: z.string().max(500).optional(),
  }),
]);
export type Event = z.infer<typeof EventSchema>;

export function handleEvent(e: Event) {
  switch (e.type) {
    case "user.created":          return notifyNewUser(e.userId, e.email);
    case "payment.succeeded":     return recordRevenue(e.amountCents);
    case "subscription.canceled": return scheduleOffboarding(e.subscriptionId);
    // No default — TS enforces exhaustiveness.
  }
}

declare function notifyNewUser(id: string, email: string): void;
declare function recordRevenue(cents: number): void;
declare function scheduleOffboarding(id: string): void;
```

---

## (e) Drizzle → Zod bridge

```ts
// src/db/schema.ts
import { pgTable, uuid, text, timestamp } from "drizzle-orm/pg-core";

export const users = pgTable("users", {
  id: uuid("id").primaryKey().defaultRandom(),
  email: text("email").notNull().unique(),
  name: text("name").notNull(),
  createdAt: timestamp("created_at").notNull().defaultNow(),
});
```

```ts
// src/schemas/users.ts
import { createInsertSchema, createSelectSchema } from "drizzle-zod";
import { users } from "@/db/schema";
import { z } from "zod";

// Base schemas derived from the Drizzle table.
export const UserSelect = createSelectSchema(users);

// Extend the insert schema with business invariants Drizzle can't express.
export const UserInsert = createInsertSchema(users, {
  email: (s) => s.email().toLowerCase(),
  name: (s) => s.min(1).max(255),
}).omit({ id: true, createdAt: true }); // server generates these

export type UserSelect = z.infer<typeof UserSelect>;
export type UserInsert = z.infer<typeof UserInsert>;
```

---

## (f) Async refine — unique-username check

```ts
// src/schemas/signup.ts
import { z } from "zod";

async function usernameAvailable(username: string): Promise<boolean> {
  const res = await fetch(`/api/username-available?u=${encodeURIComponent(username)}`);
  const { available } = (await res.json()) as { available: boolean };
  return available;
}

export const SignupSchema = z
  .object({
    username: z
      .string()
      .min(3)
      .max(32)
      .regex(/^[a-z0-9_]+$/, "lowercase letters, numbers, underscore only")
      .refine(usernameAvailable, { message: "Username is taken" }),
    password: z.string().min(8),
    confirm: z.string(),
  })
  .superRefine((val, ctx) => {
    if (val.password !== val.confirm) {
      ctx.addIssue({
        code: z.ZodIssueCode.custom,
        path: ["confirm"],
        message: "Passwords do not match",
      });
    }
  });

// RHF usage (must be mode: onBlur to avoid firing the network check on every keystroke):
// useForm({ resolver: zodResolver(SignupSchema), mode: "onBlur" })
// Async refines force safeParseAsync under the hood — zodResolver handles it.
```

---

## (g) Transform + brand — strongly typed IDs

```ts
// src/lib/ids.ts
import { z } from "zod";

export const UserId = z.string().uuid().brand<"UserId">();
export type UserId = z.infer<typeof UserId>;

export const OrgId = z.string().uuid().brand<"OrgId">();
export type OrgId = z.infer<typeof OrgId>;

export const SubscriptionId = z.string().uuid().brand<"SubscriptionId">();
export type SubscriptionId = z.infer<typeof SubscriptionId>;

// Usage — the type system enforces that you never pass a plain string.
export function loadUser(id: UserId) { /* ... */ }
export function loadOrg(id: OrgId) { /* ... */ }

// From a raw string (e.g., URL param):
function handler(req: { params: { id: string } }) {
  const id = UserId.parse(req.params.id);  // runtime + type check together
  return loadUser(id);                      // type-safe
  // loadUser(req.params.id)                // TS error — plain string
  // loadOrg(id)                             // TS error — UserId is not OrgId
}
```

---

## Bonus: Express validation middleware

```ts
// server/middleware/validate.ts
import type { Request, Response, NextFunction } from "express";
import type { ZodSchema } from "zod";

type Target = "body" | "query" | "params";

export function validate(schema: ZodSchema, target: Target = "body") {
  return (req: Request, res: Response, next: NextFunction) => {
    const result = schema.safeParse(req[target]);
    if (!result.success) {
      return res.status(400).json({
        errors: result.error.flatten().fieldErrors,
      });
    }
    // Attach the parsed (and now fully typed) value back.
    (req as any)[target] = result.data;
    next();
  };
}

// Usage:
// usersRouter.post("/users", validate(CreateUserRequest), (req, res) => {
//   // req.body is now typed as CreateUserRequest — no cast needed
// });
```
