# Admin UX + Requests Design (2026-02-08)

## Summary
Add a role-aware command list and an inline menu UI, plus a persistent requests workflow for users and chats. Root-admin can review pending requests, approve or deny with one tap, and manage chats/users from a single private UI. All admin actions remain in DM; group chats get only short confirmations.

## Goals
- Show only allowed commands to each user (DM, group, admin scopes).
- Provide a single `/menu` entry with role-aware inline buttons.
- Persist user/chat access requests with approve/deny flow.
- Root-admin can manage requests, chats, and users from DM UI.
- Approving a chat enables the bot and keeps `whitelist` mode.

## Non-goals
- Public admin actions in groups (except short confirmation).
- Advanced multi-admin workflows or audit exports.

## UX Surfaces
- `/help`: dynamic list of commands available to the current user and chat.
- `/menu`: role-aware inline menu.
  - User DM: Status, Request access, Help.
  - Group member: help + guidance that access is required.
  - Chat admin: Request chat access, Chat settings.
  - Root-admin DM: Admin mode toggle + Requests/Chats/Users/Stats/System.
- Admin actions always respond in DM; group message shows “Sent to your private chat.”

## Command Scopes (Telegram UI)
Set `BotCommand` per scope at startup:
- `all_private_chats`: `/menu`, `/help`, `/status`, `/start`.
- `all_group_chats`: `/menu`, `/help`, `/status`.
- `all_chat_administrators`: `/menu`, `/help`, `/status`, `/bot_settings`, `/bot_on`, `/bot_off`.
- Root-admin DM scope: `/menu`, `/help`, `/status`, `/admin`, `/allow`, `/deny`, `/stats`, `/system`.

## Requests Workflow
### User request
- Trigger: user sends media without access OR taps “Request access”.
- If no pending request exists, create `pending` request.
- Bot responds with status and a DM notification is sent to root-admins.

### Chat request
- Trigger: chat admin taps “Request chat access”.
- Create `pending` request for that chat.
- DM root-admins with approve/deny buttons.

### Approve/Deny
- Approve user: `is_allowed=true`, `is_blocked=false`.
- Deny user: `is_blocked=true`.
- Approve chat: `enabled=true`, `allowed_senders='whitelist'`.
- Deny chat: `enabled=false`.

## Data Model
Add `requests` table:
- `id` (PK), `kind` ('user'|'chat'), `status` ('pending'|'approved'|'denied')
- `user_id`, `chat_id`, `requested_by_id`
- `reason` (nullable), `created_at`, `updated_at`
Indexes:
- `(kind, status)`, `(user_id)`, `(chat_id)`

## Storage API
Add methods:
- `get_pending_request(kind, user_id/chat_id)`
- `create_request(...)`
- `list_requests(kind, status, limit, offset)`
- `set_request_status(id, status, reason)`

## Routers / Handlers
- `common`: add `/menu` and dynamic `/help`.
- `media`: auto-create user request on denied media.
- `chat_admin`: add “Request chat access” callback.
- `admin`: add DM menus for requests/users/chats.
- `services/keyboard`: new builders for menu and request lists.

## Error Handling
- Callback permission checks with alert on failure.
- If request is already resolved, show “Request already handled”.

## Tests
- `/help` and `/menu` role filtering.
- Auto-request on denied media (dedup).
- Chat request creation by chat admins only.
- Approve/deny effects on users/chats.
- Callback permission checks.
- Telegram command scopes set on startup.

## Open Questions (resolved)
- Chat approvals auto-enable bot and keep `whitelist` mode.
- Requests are created on denied media and via explicit button.
- Admin outputs are DM-only.
