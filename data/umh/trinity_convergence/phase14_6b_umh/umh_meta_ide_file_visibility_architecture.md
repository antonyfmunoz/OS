# UMH Meta-IDE and File Visibility Architecture

Phase: 14.6B-UMH
Status: DRAFT

## Current State

### EditorPanel

- `EditorPanel` component exists in cockpit frontend
- Displays file content in read-only view
- No syntax highlighting beyond basic formatting
- Used for viewing reports, logs, and configuration files

### File Download

- `/api/umh/chat/attachment` endpoint serves file downloads
- Path-restricted: only serves files from allowed directories
- Prevents directory traversal and access to sensitive files (.env, credentials)

### What Does NOT Exist

- No integrated file browser in cockpit
- No diff viewer for comparing file versions
- No inline editing capability from cockpit UI
- No git integration in cockpit (no commit, branch, or merge UI)
- No live file watching or auto-refresh

## How Development Actually Happens

- **Primary**: Claude Code CLI running in tmux session on VPS
- Session: `dex_main` tmux session at `/opt/OS`
- Developer connects via SSH (Termius on iPhone, code-server on iPad)
- All code changes happen through CLI, not cockpit
- Cockpit is for monitoring and control, not development

## Future Vision: VS Code Fork

- Per UMH IDE vision: end-state is a forked VS Code IDE embedded in cockpit
- Would provide full editing, diffing, git integration within cockpit chrome
- VS Code fork would run as a web component within cockpit shell
- Not actively being built -- future phase after revenue milestone
- Reference: `project_umh_ide.md` in memory
