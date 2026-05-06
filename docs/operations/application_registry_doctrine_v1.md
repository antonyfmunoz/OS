# Application Registry Doctrine v1

**Phase:** 96.8F
**Status:** Active
**Layer:** UMH Substrate — Adapter Boundary Layer

## Doctrine

Every external application used by UMH must have a registered
ApplicationBinding that declares its identity, executable path,
allowed launch method, and disallowed launch methods.

Applications without a registered binding cannot be used in
governed work packets.

## Current Registry

| Application ID | Name | Launch Method | Platform |
|---------------|------|---------------|----------|
| `google_chrome_windows` | Google Chrome | `direct_executable` | Windows |

## ApplicationBinding Contract

Each registered application declares:

| Field | Purpose |
|-------|---------|
| `application_id` | Unique identifier |
| `application_name` | Human-readable name |
| `executable_path` | Windows-native path to executable |
| `wsl_executable_path` | WSL-accessible path to same executable |
| `launch_method` | How the application is invoked |
| `disallowed_launch_methods` | Methods that must NOT be used |

## Why This Matters

Without an application registry, the system can:

1. Substitute a different application silently
2. Use a generic OS handler instead of the specific application
3. Route through an ungoverned shell command
4. Produce false evidence (Chrome process detected but Edge opened)

The registry makes application identity explicit and auditable.

## Adding New Applications

To register a new application:

1. Create an `ApplicationBinding` with all required fields
2. Define the disallowed launch methods for that application
3. Add it to the execution binding preset or build function
4. Write tests that verify the binding rejects disallowed methods

## Relationship to Execution Binding Contract

The Application Binding is layer 3 of 6 in the Execution Binding
Contract. It cannot stand alone — it must be part of a complete
ExecutionBinding that also declares environment, execution surface,
target service, capability, and proof.
