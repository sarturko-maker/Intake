# Filling in the house files with Harvey

Attach `house/brief.md` and `house/areas.md` from the workspace. Point the conversation at the Vault with the emails. Then paste:

> I need to fill in two configuration files for our legal intake workspace: house/brief.md and house/areas.md (attached templates).
>
> 1. **Pre-fill from the Vault first.** Use the emails in the Vault to fill in what you can see:
>    - our legal entities, with full names and legal forms;
>    - the email domains our colleagues use;
>    - the legal team's addresses and the shared intake mailbox;
>    - the timezone;
>    - the practice areas, sub-areas and subject naming that the types of work suggest.
>
>    Mark each pre-filled value "to confirm", with the email it comes from.
> 2. **Then interview me.** Ask one question at a time; I will dictate the answers.
>    - Probe for exceptions, examples and gaps: entities that never appear in the emails, areas with little email traffic, teams we route work to (finance, procurement, HR, IT security), who signs what, and anything the agent must always or never do.
>    - Read back every legal name, domain and email address exactly.
> 3. **Keep the templates' structure exactly.**
>    - Same frontmatter keys.
>    - Comma-separated lists.
>    - In areas.md, one "## key" block per area, with "- field: value" lines.
>    - Area keys and sub-area names in lowercase with hyphens.
>    - "sub_areas: none" where there are none.
> 4. **Leave status as "template"** until I say "final". Then set "status: ready" in both files.
> 5. **Output** the two complete files as Markdown documents. Start each with a line "=== FILE: house/brief.md ===" or "=== FILE: house/areas.md ===".

When it is final:
1. Copy both files into the workspace's `house/` folder, replacing the templates. This is a manual step on purpose: only you change `house/`.
2. Say "cold start" in Claude Code. It checks the two files before anything else and tells you if a field is missing or will not parse.
