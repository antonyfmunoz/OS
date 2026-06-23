# C24 Session 9: PostHog Analytics

Generated via UMH governed development loop
Latency: 27544.5ms

## PostHog Integration Plan â€” LYFEOS

| event_name | file_path | function_name | properties | side |
|---|---|---|---|---|
| `user_signed_up` | `server/routes/auth.ts` | `registerUser` | `{ method: 'email'|'google'|'apple', userId }` | server |
| `user_logged_in` | `server/routes/auth.ts` | `loginUser` | `{ method: 'email'|'google'|'apple', userId }` | server |
| `user_logged_out` | `server/routes/auth.ts` | `logoutUser` | `{ userId }` | server |
| `mission_created` | `server/routes/missions.ts` | `createMission` | `{ missionId, missionType, userId }` | server |
| `mission_completed` | `server/routes/missions.ts` | `completeMission` | `{ missionId, missionType, userId, durationMs }` | server |
| `streak_achieved` | `server/routes/streaks.ts` | `updateStreak` | `{ userId, streakCount, streakType }` | server |
| `profile_updated` | `server/routes/profiles.ts` | `updateProfile` | `{ userId, fieldsChanged: string[] }` | server |
| `push_notification_enabled` | `client/src/components/NotificationSettings.tsx` | `handleEnablePush` | `{ userId }` | client |
| `push_notification_disabled` | `client/src/components/NotificationSettings.tsx` | `handleDisablePush` | `{ userId }` | client |
| `page_viewed` | `client/src/App.tsx` | `usePageTracking` (hook) | `{ path, referrer, title }` | client |
| `feature_used` | `client/src/hooks/useFeatureTracking.ts` | `trackFeature` | `{ featureName, context, userId }` | client |

### Implementation notes

**Server-side** â€” use `posthog-node`:
```ts
import { PostHog } from 'posthog-node'
const posthog = new PostHog(process.env.POSTHOG_API_KEY!, { host: process.env.POSTHOG_HOST })

// Call after the action succeeds, not before
posthog.capture({ distinctId: userId, event: 'mission_completed', properties: { missionId, missionType, durationMs } })
```

**Client-side** â€” use `posthog-js`:
```ts
import posthog from 'posthog-js'
posthog.init(import.meta.env.VITE_POSTHOG_KEY, { api_host: import.meta.env.VITE_POSTHOG_HOST })

// page_viewed: auto-capture via route change listener in App.tsx
// feature_used: call posthog.capture() from a shared hook
```

**Key decisions:**
- Auth and data-mutation events fire **server-side** (can't be spoofed, guaranteed to fire)
- UI preference events (`push_notification_enabled/disabled`) fire **client-side** (immediate, tied to UI state)
- `page_viewed` uses a route-change hook, not PostHog's autocapture (cleaner, no noise)
- `feature_used` is a generic catch-all for tracking specific UI interactions (e.g. "clicked_skill_tree", "opened_calendar") â€” keeps the event list extensible without adding new named events for every button
- `distinctId` should be the internal `userId`, with `posthog.alias()` called at signup to link anonymous â†’ identified