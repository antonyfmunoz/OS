---
type: codewiki-inventory
dir: cockpit
source_sha: 0312cc4e33802424a5a6a5c1807dcd0097e63208
---

# `cockpit/` — File Inventory

**Files:** 431 regular + 0 symlinks · **Bytes:** 4,598,832

[Narrative page](../dirs/cockpit.md)


## cockpit/ (root)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/.dockerignore` | 7 | Docker build ignore patterns |
| `cockpit/.env` | 2 | — |
| `cockpit/.gitignore` | 9 | Git ignore patterns |
| `cockpit/DESIGN.md` | 482 | UMH Cockpit — Design Specification |
| `cockpit/Dockerfile` | 26 | Container image build definition |
| `cockpit/browse-proxy.mjs` | 144 | — |
| `cockpit/capacitor.config.ts` | 34 | Capacitor mobile app configuration |
| `cockpit/deploy.sh` | 140 | — |
| `cockpit/electron.vite.config.ts` | 25 | — |
| `cockpit/fly.toml` | 18 | Fly.io deployment configuration |
| `cockpit/nginx.conf.template` | 175 | — |
| `cockpit/package-lock.json` | 12,004 | npm dependency lockfile |
| `cockpit/package.json` | 57 | npm package manifest |
| `cockpit/start.sh` | 83 | Copy nginx template — no secrets to inject (Clerk JWT auth handled by backend). |
| `cockpit/tsconfig.json` | 7 | TypeScript compiler configuration |
| `cockpit/tsconfig.node.json` | 19 | TypeScript compiler configuration (node context) |
| `cockpit/tsconfig.web.json` | 18 | TypeScript compiler configuration (web context) |
| `cockpit/vite.verify.config.ts` | 30 | WP-P4-COCKPIT-BROWSER-VERIFY-001 — local verification runtime config. |
| `cockpit/vite.web.config.ts` | 28 | — |
| `cockpit/vitest.config.ts` | 18 | Vitest test runner configuration |

## cockpit/android/ (51 files)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/android/.gitignore` | 101 | Git ignore patterns |
| `cockpit/android/app/.gitignore` | 2 | Git ignore patterns |
| `cockpit/android/app/build.gradle` | 54 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/proguard-rules.pro` | 21 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/androidTest/java/com/getcapacitor/myapp/ExampleInstrumentedTest.java` | 26 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/AndroidManifest.xml` | 44 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/java/tech/universalmetaharness/cockpit/MainActivity.java` | 5 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-land-hdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-land-mdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-land-xhdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-land-xxhdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-land-xxxhdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-port-hdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-port-mdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-port-xhdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-port-xxhdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-port-xxxhdpi/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable-v24/ic_launcher_foreground.xml` | 34 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable/ic_launcher_background.xml` | 170 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/drawable/splash.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/layout/activity_main.xml` | 12 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml` | 5 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml` | 5 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-hdpi/ic_launcher.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-hdpi/ic_launcher_foreground.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-hdpi/ic_launcher_round.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-mdpi/ic_launcher.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-mdpi/ic_launcher_foreground.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-mdpi/ic_launcher_round.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xhdpi/ic_launcher.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xhdpi/ic_launcher_foreground.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xhdpi/ic_launcher_round.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xxhdpi/ic_launcher.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xxhdpi/ic_launcher_foreground.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xxhdpi/ic_launcher_round.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_foreground.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/mipmap-xxxhdpi/ic_launcher_round.png` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/values/ic_launcher_background.xml` | 4 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/values/strings.xml` | 7 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/values/styles.xml` | 22 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/main/res/xml/file_paths.xml` | 5 | Android (Capacitor) build scaffolding |
| `cockpit/android/app/src/test/java/com/getcapacitor/myapp/ExampleUnitTest.java` | 18 | Android (Capacitor) build scaffolding |
| `cockpit/android/build.gradle` | 29 | Android (Capacitor) build scaffolding |
| `cockpit/android/gradle.properties` | 22 | Android (Capacitor) build scaffolding |
| `cockpit/android/gradle/wrapper/gradle-wrapper.jar` | — | Android (Capacitor) build scaffolding |
| `cockpit/android/gradle/wrapper/gradle-wrapper.properties` | 7 | Android (Capacitor) build scaffolding |
| `cockpit/android/gradlew` | 252 | Copyright © 2015-2021 the original authors. |
| `cockpit/android/gradlew.bat` | 94 | Windows batch script — gradlew |
| `cockpit/android/settings.gradle` | 5 | Android (Capacitor) build scaffolding |
| `cockpit/android/variables.gradle` | 16 | Android (Capacitor) build scaffolding |

## cockpit/assets/ (5 files)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/assets/icon-background.png` | — | png asset (6,491 B) |
| `cockpit/assets/icon-foreground.png` | — | png asset (67,488 B) |
| `cockpit/assets/icon-only.png` | — | png asset (48,039 B) |
| `cockpit/assets/splash-dark.png` | — | png asset (58,447 B) |
| `cockpit/assets/splash.png` | — | png asset (58,447 B) |

## cockpit/ios/ (15 files)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/ios/.gitignore` | 13 | Git ignore patterns |
| `cockpit/ios/App/App.xcodeproj/project.pbxproj` | 408 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App.xcworkspace/xcshareddata/IDEWorkspaceChecks.plist` | 8 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/AppDelegate.swift` | 49 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/AppIcon.appiconset/AppIcon-512@2x.png` | — | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/AppIcon.appiconset/Contents.json` | 14 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/Contents.json` | 6 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/Splash.imageset/Contents.json` | 23 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/Splash.imageset/splash-2732x2732-1.png` | — | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/Splash.imageset/splash-2732x2732-2.png` | — | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Assets.xcassets/Splash.imageset/splash-2732x2732.png` | — | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Base.lproj/LaunchScreen.storyboard` | 32 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Base.lproj/Main.storyboard` | 19 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/App/Info.plist` | 51 | iOS (Capacitor) Xcode project scaffolding |
| `cockpit/ios/App/Podfile` | 23 | iOS (Capacitor) Xcode project scaffolding |

## cockpit/src/ (338 files)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/src/main/desktop-voice-adapter.ts` | 130 | desktop-voice-adapter — P4S-31D-3 SCAFFOLD (flag-disabled, no activation). |
| `cockpit/src/main/index.ts` | 299 | — |
| `cockpit/src/preload/index.ts` | 33 | — |
| `cockpit/src/renderer/App.tsx` | 151 | — |
| `cockpit/src/renderer/__tests__/apiClient.test.ts` | 80 | test suite — api client.test |
| `cockpit/src/renderer/__tests__/cockpitStore.test.ts` | 111 | test suite — cockpit store.test |
| `cockpit/src/renderer/__tests__/eosActionQueue.test.tsx` | 492 | WP-P4-EOS-ACTION-QUEUE-COCKPIT-001 — cockpit approval queue over the |
| `cockpit/src/renderer/__tests__/ids.test.ts` | 35 | WP-P4-COCKPIT-BROWSER-VERIFY-001 — randomId must work in insecure contexts. |
| `cockpit/src/renderer/__tests__/projectionMirrors.test.tsx` | 167 | P4S-30 — LyfeOS + CreatorOS projection mirror panels. |
| `cockpit/src/renderer/__tests__/setup.ts` | 1 | test suite — setup |
| `cockpit/src/renderer/api/broadcast-ws.ts` | 100 | API/WS client module — broadcast ws |
| `cockpit/src/renderer/api/browser-ws.ts` | 205 | API/WS client module — browser ws |
| `cockpit/src/renderer/api/client.ts` | 202 | API/WS client module — client |
| `cockpit/src/renderer/api/device-presence.ts` | 59 | API/WS client module — device presence |
| `cockpit/src/renderer/api/platform-voice-adapter.ts` | 414 | PlatformVoiceAdapter — desktop browser push-to-talk (P4S-31D-1). |
| `cockpit/src/renderer/api/tts-playback-controller.ts` | 292 | TTS Playback Controller — manages audio playback with iOS unlock support. |
| `cockpit/src/renderer/api/vision-ws.ts` | 811 | API/WS client module — vision ws |
| `cockpit/src/renderer/api/voice-controller.ts` | 1,398 | voice-controller — P4S-31D1-B voice-MESSAGE flow (lanes C+D+E). |
| `cockpit/src/renderer/api/voice-diag.ts` | 83 | Voice client-side diagnostic collector (P4S-VOICE-CLIENT-DIAG). |
| `cockpit/src/renderer/api/voice-turn-assembler.ts` | 288 | Voice Turn Assembler — collects STT transcript segments into a single |
| `cockpit/src/renderer/api/voice-ws.ts` | 552 | API/WS client module — voice ws |
| `cockpit/src/renderer/api/voiceErrorCodes.ts` | 28 | AUTO-GENERATED by scripts/gen_voice_error_codes_ts.py — DO NOT EDIT BY HAND. |
| `cockpit/src/renderer/api/websocket.ts` | 202 | API/WS client module — websocket |
| `cockpit/src/renderer/capacitor-init.ts` | 43 | — |
| `cockpit/src/renderer/components/ActionRequired.tsx` | 117 | React component — action required |
| `cockpit/src/renderer/components/AgentCard.tsx` | 110 | React component — agent card |
| `cockpit/src/renderer/components/CallOverlay.tsx` | 69 | React component — call overlay |
| `cockpit/src/renderer/components/CameraController.tsx` | 1,399 | React component — camera controller |
| `cockpit/src/renderer/components/CameraPreview.tsx` | 201 | React component — camera preview |
| `cockpit/src/renderer/components/CanvasMenuBar.tsx` | 252 | React component — canvas menu bar |
| `cockpit/src/renderer/components/ChannelList.tsx` | 90 | React component — channel list |
| `cockpit/src/renderer/components/ChannelView.tsx` | 113 | React component — channel view |
| `cockpit/src/renderer/components/CommandPalette.tsx` | 181 | React component — command palette |
| `cockpit/src/renderer/components/ConnectionBanner.tsx` | 50 | React component — connection banner |
| `cockpit/src/renderer/components/ControlPanel.tsx` | 436 | React component — control panel |
| `cockpit/src/renderer/components/CronTable.tsx` | 102 | React component — cron table |
| `cockpit/src/renderer/components/DetailDrawer.tsx` | 140 | React component — detail drawer |
| `cockpit/src/renderer/components/DeviceDiagnosisInline.tsx` | 170 | React component — device diagnosis inline |
| `cockpit/src/renderer/components/DeviceOnboardingCard.tsx` | 128 | React component — device onboarding card |
| `cockpit/src/renderer/components/EOSActionQueue.tsx` | 160 | EOS projection action queue — WP-P4-EOS-ACTION-QUEUE-COCKPIT-001. |
| `cockpit/src/renderer/components/ErrorBoundary.tsx` | 51 | React component — error boundary |
| `cockpit/src/renderer/components/EventConsole.tsx` | 174 | React component — event console |
| `cockpit/src/renderer/components/ExecutionTimeline.tsx` | 207 | React component — execution timeline |
| `cockpit/src/renderer/components/ExecutorBadge.tsx` | 27 | React component — executor badge |
| `cockpit/src/renderer/components/FabLarge.tsx` | 139 | React component — fab large |
| `cockpit/src/renderer/components/FabMedium.tsx` | 62 | React component — fab medium |
| `cockpit/src/renderer/components/FabSmall.tsx` | 31 | React component — fab small |
| `cockpit/src/renderer/components/GraphView.tsx` | 183 | React component — graph view |
| `cockpit/src/renderer/components/HudBar.tsx` | 237 | React component — hud bar |
| `cockpit/src/renderer/components/IDEMenuBar.tsx` | 238 | React component — i d e menu bar |
| `cockpit/src/renderer/components/LeftDrawer.tsx` | 28 | React component — left drawer |
| `cockpit/src/renderer/components/LeftRail.tsx` | 86 | React component — left rail |
| `cockpit/src/renderer/components/LivePreview.tsx` | 287 | React component — live preview |
| `cockpit/src/renderer/components/NavRail.tsx` | 72 | React component — nav rail |
| `cockpit/src/renderer/components/OverlayToggle.tsx` | 35 | React component — overlay toggle |
| `cockpit/src/renderer/components/ProjectionMirrorCard.tsx` | 93 | Projection mirror card — P4S-30. |
| `cockpit/src/renderer/components/ResumeCard.tsx` | 163 | React component — resume card |
| `cockpit/src/renderer/components/RightDrawer.tsx` | 24 | React component — right drawer |
| `cockpit/src/renderer/components/RightRail.tsx` | 1,260 | React component — right rail |
| `cockpit/src/renderer/components/RingGauge.tsx` | 52 | React component — ring gauge |
| `cockpit/src/renderer/components/RuntimeBadge.tsx` | 65 | React component — runtime badge |
| `cockpit/src/renderer/components/Shell.tsx` | 75 | React component — shell |
| `cockpit/src/renderer/components/SplitPane.tsx` | 79 | React component — split pane |
| `cockpit/src/renderer/components/SplitPreview.tsx` | 130 | React component — split preview |
| `cockpit/src/renderer/components/StatusBadge.tsx` | 39 | React component — status badge |
| `cockpit/src/renderer/components/StorePolling.tsx` | 21 | React component — store polling |
| `cockpit/src/renderer/components/TaskBlock.tsx` | 58 | React component — task block |
| `cockpit/src/renderer/components/TimelineView.tsx` | 106 | React component — timeline view |
| `cockpit/src/renderer/components/TitleBar.tsx` | 74 | React component — title bar |
| `cockpit/src/renderer/components/TopologyMap.tsx` | 204 | React component — topology map |
| `cockpit/src/renderer/components/TrackingPanel.tsx` | 329 | React component — tracking panel |
| `cockpit/src/renderer/components/ViewportSelector.tsx` | 92 | React component — viewport selector |
| `cockpit/src/renderer/components/VisionPopout.tsx` | 284 | React component — vision popout |
| `cockpit/src/renderer/components/VoiceCommandBar.tsx` | 419 | React component — voice command bar |
| `cockpit/src/renderer/components/VoiceWaveform.tsx` | 31 | React component — voice waveform |
| `cockpit/src/renderer/components/canvas/AgentCanvasNode.tsx` | 113 | React component — agent canvas node |
| `cockpit/src/renderer/components/canvas/AgentCanvasWorkspace.tsx` | 171 | React component — agent canvas workspace |
| `cockpit/src/renderer/components/canvas/BaseCanvas.tsx` | 291 | React component — base canvas |
| `cockpit/src/renderer/components/canvas/CanvasContextMenu.tsx` | 156 | React component — canvas context menu |
| `cockpit/src/renderer/components/canvas/CanvasPalette.tsx` | 468 | React component — canvas palette |
| `cockpit/src/renderer/components/canvas/CanvasToolbar.tsx` | 341 | React component — canvas toolbar |
| `cockpit/src/renderer/components/canvas/CanvasWindow.tsx` | 472 | React component — canvas window |
| `cockpit/src/renderer/components/canvas/CanvasWorkspace.tsx` | 139 | React component — canvas workspace |
| `cockpit/src/renderer/components/canvas/HarnessCanvasWorkspace.tsx` | 250 | React component — harness canvas workspace |
| `cockpit/src/renderer/components/canvas/LoopCanvasWorkspace.tsx` | 309 | React component — loop canvas workspace |
| `cockpit/src/renderer/components/canvas/OrganismCanvasWorkspace.tsx` | 198 | React component — organism canvas workspace |
| `cockpit/src/renderer/components/canvas/UnifiedCanvasWorkspace.tsx` | 187 | React component — unified canvas workspace |
| `cockpit/src/renderer/components/canvas/WindowContent.tsx` | 121 | React component — window content |
| `cockpit/src/renderer/components/canvas/WorkflowCanvasWorkspace.tsx` | 256 | React component — workflow canvas workspace |
| `cockpit/src/renderer/components/canvas/WorkflowConnection.tsx` | 75 | React component — workflow connection |
| `cockpit/src/renderer/components/canvas/WorkflowNode.tsx` | 261 | React component — workflow node |
| `cockpit/src/renderer/components/canvas/windows/AgentConfigView.tsx` | 474 | React component — agent config view |
| `cockpit/src/renderer/components/canvas/windows/AgentWindowContent.tsx` | 94 | React component — agent window content |
| `cockpit/src/renderer/components/canvas/windows/BrowserWindowContent.tsx` | 17 | React component — browser window content |
| `cockpit/src/renderer/components/canvas/windows/DesktopWindowContent.tsx` | 335 | React component — desktop window content |
| `cockpit/src/renderer/components/canvas/windows/PanelWindowContent.tsx` | 119 | React component — panel window content |
| `cockpit/src/renderer/components/canvas/windows/PreviewWindowContent.tsx` | 45 | React component — preview window content |
| `cockpit/src/renderer/components/canvas/windows/TerminalWindowContent.tsx` | 281 | React component — terminal window content |
| `cockpit/src/renderer/components/canvas/windows/VisionWindowContent.tsx` | 107 | React component — vision window content |
| `cockpit/src/renderer/components/cards/ApprovalCard.tsx` | 80 | React component — approval card |
| `cockpit/src/renderer/components/cards/CommandResultCard.tsx` | 74 | React component — command result card |
| `cockpit/src/renderer/components/cards/ConversationBubble.tsx` | 71 | React component — conversation bubble |
| `cockpit/src/renderer/components/cards/ErrorCard.tsx` | 47 | React component — error card |
| `cockpit/src/renderer/components/cards/RRIPRenderer.tsx` | 35 | React component — r r i p renderer |
| `cockpit/src/renderer/components/cards/ReportCard.tsx` | 113 | React component — report card |
| `cockpit/src/renderer/components/rooms/ChannelCreateModal.tsx` | 170 | React component — channel create modal |
| `cockpit/src/renderer/components/rooms/ChannelSidebar.tsx` | 242 | React component — channel sidebar |
| `cockpit/src/renderer/components/rooms/ForumChannelView.tsx` | 219 | React component — forum channel view |
| `cockpit/src/renderer/components/rooms/GuestJoinPage.tsx` | 1,365 | React component — guest join page |
| `cockpit/src/renderer/components/rooms/InvitePanel.tsx` | 362 | React component — invite panel |
| `cockpit/src/renderer/components/rooms/MeetingRoomPanel.tsx` | 1,592 | React component — meeting room panel |
| `cockpit/src/renderer/components/rooms/MemberListPanel.tsx` | 116 | React component — member list panel |
| `cockpit/src/renderer/components/rooms/RoomAuditLog.tsx` | 50 | React component — room audit log |
| `cockpit/src/renderer/components/rooms/RoomChatPanel.tsx` | 180 | React component — room chat panel |
| `cockpit/src/renderer/components/rooms/RoomDexPanel.tsx` | 178 | React component — room dex panel |
| `cockpit/src/renderer/components/rooms/RoomMainView.tsx` | 96 | React component — room main view |
| `cockpit/src/renderer/components/rooms/RoomRightRail.tsx` | 103 | React component — room right rail |
| `cockpit/src/renderer/components/rooms/ServerCreateModal.tsx` | 160 | React component — server create modal |
| `cockpit/src/renderer/components/rooms/ServerRail.tsx` | 62 | React component — server rail |
| `cockpit/src/renderer/components/rooms/TextChannelView.tsx` | 382 | React component — text channel view |
| `cockpit/src/renderer/components/rooms/ThreadPanel.tsx` | 110 | React component — thread panel |
| `cockpit/src/renderer/components/rooms/VoiceRoomPanel.tsx` | 1,252 | React component — voice room panel |
| `cockpit/src/renderer/components/vision/CameraModeSelector.tsx` | 157 | React component — camera mode selector |
| `cockpit/src/renderer/components/vision/DiagnosticsPanel.tsx` | 295 | React component — diagnostics panel |
| `cockpit/src/renderer/components/vision/FaceTrackingOverlay.tsx` | 50 | React component — face tracking overlay |
| `cockpit/src/renderer/components/vision/HandLandmarkOverlay.tsx` | 39 | React component — hand landmark overlay |
| `cockpit/src/renderer/components/vision/NotificationCenter.tsx` | 129 | React component — notification center |
| `cockpit/src/renderer/components/vision/PoseSkeletonOverlay.tsx` | 39 | React component — pose skeleton overlay |
| `cockpit/src/renderer/components/vision/SceneInventory.tsx` | 232 | React component — scene inventory |
| `cockpit/src/renderer/components/vision/StatusHud.tsx` | 298 | React component — status hud |
| `cockpit/src/renderer/components/vision/ToastContainer.tsx` | 46 | React component — toast container |
| `cockpit/src/renderer/components/vision/TrackedObjectBox.tsx` | 44 | React component — tracked object box |
| `cockpit/src/renderer/components/vision/VisionConnectionStatus.tsx` | 129 | React component — vision connection status |
| `cockpit/src/renderer/components/vision/VisionOverlay.tsx` | 113 | React component — vision overlay |
| `cockpit/src/renderer/components/vision/VisionSettings.tsx` | 473 | React component — vision settings |
| `cockpit/src/renderer/components/vision/index.ts` | 11 | React component — index |
| `cockpit/src/renderer/constants.ts` | 7 | — |
| `cockpit/src/renderer/constants/devices.ts` | 68 | Device Naming Protocol — single source of truth for all device labels. |
| `cockpit/src/renderer/dist/web/assets/index-BJmTyqJa.js` | 16 | — |
| `cockpit/src/renderer/dist/web/assets/index-DBUsbnfc.css` | 1 | stylesheet — index d b usbnfc |
| `cockpit/src/renderer/dist/web/index.html` | 16 | — |
| `cockpit/src/renderer/global.d.ts` | 36 | — |
| `cockpit/src/renderer/hooks/useAuthedMedia.ts` | 87 | React hook — use authed media |
| `cockpit/src/renderer/hooks/useBroadcastConnection.ts` | 61 | React hook — use broadcast connection |
| `cockpit/src/renderer/hooks/useBrowserStream.ts` | 110 | React hook — use browser stream |
| `cockpit/src/renderer/hooks/useCanvasDrag.ts` | 53 | React hook — use canvas drag |
| `cockpit/src/renderer/hooks/useCanvasResize.ts` | 97 | React hook — use canvas resize |
| `cockpit/src/renderer/hooks/useConferenceRoom.ts` | 304 | React hook — use conference room |
| `cockpit/src/renderer/hooks/useIsMobile.ts` | 17 | React hook — use is mobile |
| `cockpit/src/renderer/hooks/useKeyboard.ts` | 55 | React hook — use keyboard |
| `cockpit/src/renderer/hooks/useOrganismRealtime.ts` | 279 | React hook — use organism realtime |
| `cockpit/src/renderer/hooks/usePolling.ts` | 30 | React hook — use polling |
| `cockpit/src/renderer/hooks/useVisionConnection.ts` | 873 | React hook — use vision connection |
| `cockpit/src/renderer/hooks/useVoiceDetection.ts` | 116 | React hook — use voice detection |
| `cockpit/src/renderer/hooks/useVoiceRoom.ts` | 74 | React hook — use voice room |
| `cockpit/src/renderer/index.html` | 21 | — |
| `cockpit/src/renderer/lib/pushNotifications.ts` | 69 | library module — push notifications |
| `cockpit/src/renderer/lib/rrip-normalize.ts` | 53 | library module — rrip normalize |
| `cockpit/src/renderer/lib/time.ts` | 24 | library module — time |
| `cockpit/src/renderer/main.tsx` | 43 | — |
| `cockpit/src/renderer/operator/speechInputAdapter.ts` | 197 | — |
| `cockpit/src/renderer/operator/voiceTypes.ts` | 137 | — |
| `cockpit/src/renderer/panels/ActionsPanel.tsx` | 186 | Cockpit panel component — actions panel |
| `cockpit/src/renderer/panels/ActivityPanel.tsx` | 105 | Cockpit panel component — activity panel |
| `cockpit/src/renderer/panels/AnalyticsPanel.tsx` | 121 | Cockpit panel component — analytics panel |
| `cockpit/src/renderer/panels/ApprovalsPanel.tsx` | 273 | Cockpit panel component — approvals panel |
| `cockpit/src/renderer/panels/BroadcastPanel.tsx` | 281 | Cockpit panel component — broadcast panel |
| `cockpit/src/renderer/panels/BrowserPanel.tsx` | 539 | Cockpit panel component — browser panel |
| `cockpit/src/renderer/panels/BuildLoopPanel.tsx` | 184 | Cockpit panel component — build loop panel |
| `cockpit/src/renderer/panels/CapabilitiesPanel.tsx` | 370 | Cockpit panel component — capabilities panel |
| `cockpit/src/renderer/panels/CapabilityMapPanel.tsx` | 163 | Cockpit panel component — capability map panel |
| `cockpit/src/renderer/panels/CommandCenterPanel.tsx` | 459 | Cockpit panel component — command center panel |
| `cockpit/src/renderer/panels/CommandsPanel.tsx` | 395 | Cockpit panel component — commands panel |
| `cockpit/src/renderer/panels/CommsPanel.tsx` | 234 | Cockpit panel component — comms panel |
| `cockpit/src/renderer/panels/CompanyPanel.tsx` | 291 | Cockpit panel component — company panel |
| `cockpit/src/renderer/panels/ConferenceRoomsPanel.tsx` | 72 | Cockpit panel component — conference rooms panel |
| `cockpit/src/renderer/panels/ContinuityPanel.tsx` | 376 | Cockpit panel component — continuity panel |
| `cockpit/src/renderer/panels/DashboardPanel.tsx` | 489 | Cockpit panel component — dashboard panel |
| `cockpit/src/renderer/panels/DelegationPanel.tsx` | 242 | Cockpit panel component — delegation panel |
| `cockpit/src/renderer/panels/DistributedRuntimePanel.tsx` | 293 | Cockpit panel component — distributed runtime panel |
| `cockpit/src/renderer/panels/EngineeringPanel.tsx` | 555 | Cockpit panel component — engineering panel |
| `cockpit/src/renderer/panels/ExecCoordPanel.tsx` | 345 | Cockpit panel component — exec coord panel |
| `cockpit/src/renderer/panels/ExecutionPanel.tsx` | 188 | Cockpit panel component — execution panel |
| `cockpit/src/renderer/panels/ExecutivePanel.tsx` | 233 | Cockpit panel component — executive panel |
| `cockpit/src/renderer/panels/ExecutorPanel.tsx` | 1,016 | Cockpit panel component — executor panel |
| `cockpit/src/renderer/panels/GoalPanel.tsx` | 451 | Cockpit panel component — goal panel |
| `cockpit/src/renderer/panels/GovernancePanel.tsx` | 267 | Cockpit panel component — governance panel |
| `cockpit/src/renderer/panels/InfrastructurePanel.tsx` | 196 | Cockpit panel component — infrastructure panel |
| `cockpit/src/renderer/panels/IntelligencePanel.tsx` | 657 | Cockpit panel component — intelligence panel |
| `cockpit/src/renderer/panels/IntentLoopPanel.tsx` | 183 | Intent-loop panel — P4S-31 read surface + P4S-31B downstream controls. |
| `cockpit/src/renderer/panels/IntentPanel.tsx` | 126 | Cockpit panel component — intent panel |
| `cockpit/src/renderer/panels/KnowledgePanel.tsx` | 338 | Cockpit panel component — knowledge panel |
| `cockpit/src/renderer/panels/LearningPanel.tsx` | 289 | Cockpit panel component — learning panel |
| `cockpit/src/renderer/panels/MVPReadinessPanel.tsx` | 160 | Cockpit panel component — m v p readiness panel |
| `cockpit/src/renderer/panels/MemoryPanel.tsx` | 430 | Cockpit panel component — memory panel |
| `cockpit/src/renderer/panels/MetaIDEPanel.tsx` | 1,285 | Cockpit panel component — meta i d e panel |
| `cockpit/src/renderer/panels/OperatingLoopPanel.tsx` | 152 | Cockpit panel component — operating loop panel |
| `cockpit/src/renderer/panels/OperationsPanel.tsx` | 298 | Cockpit panel component — operations panel |
| `cockpit/src/renderer/panels/OperatorContinuityPanel.tsx` | 248 | Cockpit panel component — operator continuity panel |
| `cockpit/src/renderer/panels/OperatorHomePanel.tsx` | 249 | Cockpit panel component — operator home panel |
| `cockpit/src/renderer/panels/OperatorPanel.tsx` | 951 | Cockpit panel component — operator panel |
| `cockpit/src/renderer/panels/OperatorTimelinePanel.tsx` | 135 | Cockpit panel component — operator timeline panel |
| `cockpit/src/renderer/panels/OrchestratorPanel.tsx` | 134 | Cockpit panel component — orchestrator panel |
| `cockpit/src/renderer/panels/OrganismLoopPanel.tsx` | 341 | Cockpit panel component — organism loop panel |
| `cockpit/src/renderer/panels/OrganismMapPanel.tsx` | 104 | Cockpit panel component — organism map panel |
| `cockpit/src/renderer/panels/OrganismPanel.tsx` | 349 | Cockpit panel component — organism panel |
| `cockpit/src/renderer/panels/PortfolioPanel.tsx` | 231 | Cockpit panel component — portfolio panel |
| `cockpit/src/renderer/panels/PredictionPanel.tsx` | 277 | Cockpit panel component — prediction panel |
| `cockpit/src/renderer/panels/PresencePanel.tsx` | 371 | Cockpit panel component — presence panel |
| `cockpit/src/renderer/panels/ProfilePanel.tsx` | 464 | Cockpit panel component — profile panel |
| `cockpit/src/renderer/panels/ProjectionIntegrationPanel.tsx` | 239 | Cockpit panel component — projection integration panel |
| `cockpit/src/renderer/panels/ProjectionMirrorsPanel.tsx` | 61 | Projection mirror panels — P4S-30. |
| `cockpit/src/renderer/panels/ProjectionPanel.tsx` | 419 | Cockpit panel component — projection panel |
| `cockpit/src/renderer/panels/ProofInspectorPanel.tsx` | 318 | Cockpit panel component — proof inspector panel |
| `cockpit/src/renderer/panels/PropagationGraphPanel.tsx` | 233 | Cockpit panel component — propagation graph panel |
| `cockpit/src/renderer/panels/RealityGraphPanel.tsx` | 609 | Cockpit panel component — reality graph panel |
| `cockpit/src/renderer/panels/RealityIntelligencePanel.tsx` | 225 | Cockpit panel component — reality intelligence panel |
| `cockpit/src/renderer/panels/RealityTimelinePanel.tsx` | 159 | Cockpit panel component — reality timeline panel |
| `cockpit/src/renderer/panels/RecoveryDashboardPanel.tsx` | 294 | Cockpit panel component — recovery dashboard panel |
| `cockpit/src/renderer/panels/RuntimePanel.tsx` | 383 | Cockpit panel component — runtime panel |
| `cockpit/src/renderer/panels/ScreenAwarenessPanel.tsx` | 422 | Cockpit panel component — screen awareness panel |
| `cockpit/src/renderer/panels/SelfBuildPanel.tsx` | 303 | Cockpit panel component — self build panel |
| `cockpit/src/renderer/panels/ServiceGraphPanel.tsx` | 231 | Cockpit panel component — service graph panel |
| `cockpit/src/renderer/panels/SessionPanel.tsx` | 417 | Cockpit panel component — session panel |
| `cockpit/src/renderer/panels/SessionResumePanel.tsx` | 164 | Cockpit panel component — session resume panel |
| `cockpit/src/renderer/panels/SettingsPanel.tsx` | 636 | Cockpit panel component — settings panel |
| `cockpit/src/renderer/panels/SkillsPanel.tsx` | 47 | Cockpit panel component — skills panel |
| `cockpit/src/renderer/panels/StateAuthorityPanel.tsx` | 104 | Cockpit panel component — state authority panel |
| `cockpit/src/renderer/panels/StrategicPanel.tsx` | 417 | Cockpit panel component — strategic panel |
| `cockpit/src/renderer/panels/StrategyPanel.tsx` | 593 | Cockpit panel component — strategy panel |
| `cockpit/src/renderer/panels/TasksPanel.tsx` | 96 | Cockpit panel component — tasks panel |
| `cockpit/src/renderer/panels/TickLoopPanel.tsx` | 489 | Cockpit panel component — tick loop panel |
| `cockpit/src/renderer/panels/TmuxPanel.tsx` | 111 | Cockpit panel component — tmux panel |
| `cockpit/src/renderer/panels/UMHNodePanel.tsx` | 135 | Cockpit panel component — u m h node panel |
| `cockpit/src/renderer/panels/UnifiedExecutionPanel.tsx` | 199 | Cockpit panel component — unified execution panel |
| `cockpit/src/renderer/panels/UniversalWorkPanel.tsx` | 879 | Cockpit panel component — universal work panel |
| `cockpit/src/renderer/panels/VisionPanel.tsx` | 142 | Cockpit panel component — vision panel |
| `cockpit/src/renderer/panels/WorkIntelligencePanel.tsx` | 350 | Cockpit panel component — work intelligence panel |
| `cockpit/src/renderer/panels/WorkPanel.tsx` | 569 | Cockpit panel component — work panel |
| `cockpit/src/renderer/panels/WorkspaceTopologyPanel.tsx` | 161 | WorkspaceTopologyPanel — workspace→repos→runtimes→devices topology view. |
| `cockpit/src/renderer/panels/WorkstationPanel.tsx` | 458 | Cockpit panel component — workstation panel |
| `cockpit/src/renderer/panels/WorldModelPanel.tsx` | 649 | Cockpit panel component — world model panel |
| `cockpit/src/renderer/public/favicon.ico` | — | ico asset (568 B) |
| `cockpit/src/renderer/public/icon-192.png` | — | png asset (1,321 B) |
| `cockpit/src/renderer/public/icon-512.png` | — | png asset (3,797 B) |
| `cockpit/src/renderer/public/icon-maskable-192.png` | — | png asset (7,108 B) |
| `cockpit/src/renderer/public/icon-maskable-512.png` | — | png asset (22,991 B) |
| `cockpit/src/renderer/public/manifest.json` | 35 | — |
| `cockpit/src/renderer/public/offline.html` | 73 | — |
| `cockpit/src/renderer/stores/actionsStore.ts` | 123 | Zustand store — actions store |
| `cockpit/src/renderer/stores/activityStore.ts` | 52 | Zustand store — activity store |
| `cockpit/src/renderer/stores/agentCanvasStore.ts` | 217 | Zustand store — agent canvas store |
| `cockpit/src/renderer/stores/agentStore.ts` | 125 | Zustand store — agent store |
| `cockpit/src/renderer/stores/analyticsStore.ts` | 123 | Zustand store — analytics store |
| `cockpit/src/renderer/stores/bootstrapStore.ts` | 260 | Zustand store — bootstrap store |
| `cockpit/src/renderer/stores/broadcastStore.ts` | 120 | Zustand store — broadcast store |
| `cockpit/src/renderer/stores/buildLoopStore.ts` | 60 | Zustand store — build loop store |
| `cockpit/src/renderer/stores/canvasStore.ts` | 561 | Zustand store — canvas store |
| `cockpit/src/renderer/stores/capabilityIntelligenceStore.ts` | 83 | Zustand store — capability intelligence store |
| `cockpit/src/renderer/stores/capabilityMapStore.ts` | 47 | Zustand store — capability map store |
| `cockpit/src/renderer/stores/chatStore.ts` | 408 | Zustand store — chat store |
| `cockpit/src/renderer/stores/cockpitStore.ts` | 226 | Zustand store — cockpit store |
| `cockpit/src/renderer/stores/coherenceStore.ts` | 248 | Zustand store — coherence store |
| `cockpit/src/renderer/stores/collapseStore.ts` | 33 | Zustand store — collapse store |
| `cockpit/src/renderer/stores/configStore.ts` | 78 | Zustand store — config store |
| `cockpit/src/renderer/stores/delegationStore.ts` | 133 | Zustand store — delegation store |
| `cockpit/src/renderer/stores/deviceSessionStore.ts` | 163 | Zustand store — device session store |
| `cockpit/src/renderer/stores/deviceStore.ts` | 194 | Zustand store — device store |
| `cockpit/src/renderer/stores/editorStore.ts` | 218 | Zustand store — editor store |
| `cockpit/src/renderer/stores/engineeringStore.ts` | 367 | Zustand store — engineering store |
| `cockpit/src/renderer/stores/eosActionQueueStore.ts` | 229 | EOS action approval queue store — WP-P4-EOS-ACTION-QUEUE-COCKPIT-001. |
| `cockpit/src/renderer/stores/executionSummaryStore.ts` | 105 | Zustand store — execution summary store |
| `cockpit/src/renderer/stores/executiveStore.ts` | 160 | Zustand store — executive store |
| `cockpit/src/renderer/stores/goalStore.ts` | 95 | Zustand store — goal store |
| `cockpit/src/renderer/stores/governanceStore.ts` | 191 | Zustand store — governance store |
| `cockpit/src/renderer/stores/harnessCanvasStore.ts` | 80 | Zustand store — harness canvas store |
| `cockpit/src/renderer/stores/intelligenceStore.ts` | 126 | Zustand store — intelligence store |
| `cockpit/src/renderer/stores/intentLoopStore.ts` | 128 | Intent-loop store — P4S-31 read surface + P4S-31B downstream decision. |
| `cockpit/src/renderer/stores/intentStore.ts` | 88 | Zustand store — intent store |
| `cockpit/src/renderer/stores/knowledgeStore.ts` | 107 | Zustand store — knowledge store |
| `cockpit/src/renderer/stores/learningStore.ts` | 173 | Zustand store — learning store |
| `cockpit/src/renderer/stores/loopCanvasStore.ts` | 149 | Zustand store — loop canvas store |
| `cockpit/src/renderer/stores/memoryStore.ts` | 135 | Zustand store — memory store |
| `cockpit/src/renderer/stores/metaIDEStore.ts` | 316 | Zustand store — meta i d e store |
| `cockpit/src/renderer/stores/mvpReadinessStore.ts` | 77 | Zustand store — mvp readiness store |
| `cockpit/src/renderer/stores/operatingLoopStore.ts` | 95 | Zustand store — operating loop store |
| `cockpit/src/renderer/stores/operationsStore.ts` | 59 | Zustand store — operations store |
| `cockpit/src/renderer/stores/operatorExperienceStore.ts` | 376 | Zustand store — operator experience store |
| `cockpit/src/renderer/stores/operatorHomeStore.ts` | 87 | Zustand store — operator home store |
| `cockpit/src/renderer/stores/operatorLoopStore.ts` | 1,553 | Zustand store — operator loop store |
| `cockpit/src/renderer/stores/operatorTimelineStore.ts` | 43 | Zustand store — operator timeline store |
| `cockpit/src/renderer/stores/orchestratorAwarenessStore.ts` | 66 | Zustand store — orchestrator awareness store |
| `cockpit/src/renderer/stores/organismCanvasStore.ts` | 99 | Zustand store — organism canvas store |
| `cockpit/src/renderer/stores/organismLoopStore.ts` | 85 | Zustand store — organism loop store |
| `cockpit/src/renderer/stores/organismStore.ts` | 473 | Zustand store — organism store |
| `cockpit/src/renderer/stores/predictionStore.ts` | 133 | Zustand store — prediction store |
| `cockpit/src/renderer/stores/presenceStore.ts` | 112 | Zustand store — presence store |
| `cockpit/src/renderer/stores/projectionIntegrationStore.ts` | 78 | Zustand store — projection integration store |
| `cockpit/src/renderer/stores/projectionMirrorStore.ts` | 65 | Projection mirror stores — P4S-30. |
| `cockpit/src/renderer/stores/proofInspectorStore.ts` | 175 | Zustand store — proof inspector store |
| `cockpit/src/renderer/stores/providerRegistryStore.ts` | 85 | Zustand store — provider registry store |
| `cockpit/src/renderer/stores/realityGraphStore.ts` | 250 | Zustand store — reality graph store |
| `cockpit/src/renderer/stores/realityIntelligenceStore.ts` | 134 | Zustand store — reality intelligence store |
| `cockpit/src/renderer/stores/realityTimelineStore.ts` | 66 | Zustand store — reality timeline store |
| `cockpit/src/renderer/stores/realtimeStore.ts` | 154 | Zustand store — realtime store |
| `cockpit/src/renderer/stores/recoveryDashboardStore.ts` | 173 | Zustand store — recovery dashboard store |
| `cockpit/src/renderer/stores/roomsStore.ts` | 1,042 | Zustand store — rooms store |
| `cockpit/src/renderer/stores/screenAwarenessStore.ts` | 165 | Zustand store — screen awareness store |
| `cockpit/src/renderer/stores/serviceGraphStore.ts` | 76 | Zustand store — service graph store |
| `cockpit/src/renderer/stores/settingsStore.ts` | 157 | Zustand store — settings store |
| `cockpit/src/renderer/stores/stateAuthorityStore.ts` | 61 | Zustand store — state authority store |
| `cockpit/src/renderer/stores/strategicStore.ts` | 84 | Zustand store — strategic store |
| `cockpit/src/renderer/stores/systemStore.ts` | 224 | Zustand store — system store |
| `cockpit/src/renderer/stores/taskStore.ts` | 71 | Zustand store — task store |
| `cockpit/src/renderer/stores/umhNodeStore.ts` | 81 | Zustand store — umh node store |
| `cockpit/src/renderer/stores/unifiedApprovalStore.ts` | 158 | Zustand store — unified approval store |
| `cockpit/src/renderer/stores/unifiedCanvasStore.ts` | 95 | Zustand store — unified canvas store |
| `cockpit/src/renderer/stores/unifiedExecutionStore.ts` | 71 | Zustand store — unified execution store |
| `cockpit/src/renderer/stores/unifiedWorkstationStore.ts` | 102 | Zustand store — unified workstation store |
| `cockpit/src/renderer/stores/viewContextStore.ts` | 134 | Zustand store — view context store |
| `cockpit/src/renderer/stores/visionStore.ts` | 1,288 | Zustand store — vision store |
| `cockpit/src/renderer/stores/voiceMessageStore.ts` | 704 | voiceMessageStore — P4S-31D1-B voice-MESSAGE rail (lanes C+D+E). |
| `cockpit/src/renderer/stores/voiceSessionStore.ts` | 1,220 | Zustand store — voice session store |
| `cockpit/src/renderer/stores/voiceStore.ts` | 173 | Zustand store — voice store |
| `cockpit/src/renderer/stores/workIntelligenceStore.ts` | 123 | Zustand store — work intelligence store |
| `cockpit/src/renderer/stores/workflowCanvasStore.ts` | 330 | Zustand store — workflow canvas store |
| `cockpit/src/renderer/stores/workspaceContextStore.ts` | 103 | Zustand store — workspace context store |
| `cockpit/src/renderer/stores/workspaceTopologyStore.ts` | 85 | Workspace Topology Store — Phase 27 |
| `cockpit/src/renderer/stores/workstationSessionStore.ts` | 78 | Zustand store — workstation session store |
| `cockpit/src/renderer/stores/worldModelStore.ts` | 248 | Zustand store — world model store |
| `cockpit/src/renderer/styles/globals.css` | 365 | stylesheet — globals |
| `cockpit/src/renderer/styles/tokens.css` | 62 | stylesheet — tokens |
| `cockpit/src/renderer/sw.ts` | 121 | <reference lib="webworker" /> |
| `cockpit/src/renderer/types/rooms.ts` | 381 | type definitions — rooms |
| `cockpit/src/renderer/types/routes.ts` | 180 | type definitions — routes |
| `cockpit/src/renderer/types/rrip.ts` | 66 | type definitions — rrip |
| `cockpit/src/renderer/utils/canvasCoords.ts` | 46 | utility module — canvas coords |
| `cockpit/src/renderer/utils/ids.ts` | 17 | Random id generation that works in BOTH secure and insecure contexts. |

## cockpit/tests/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/tests/__init__.py` | 0 | package marker (empty) |

## cockpit/verify-env-empty/ (1 files)

| Path | Lines | Purpose |
|---|---|---|
| `cockpit/verify-env-empty/.gitkeep` | 0 | Placeholder to keep empty directory in git |
