# AutoSpec Implementation Guidance

- Never make architectural changes without asking first.
- Prefer the smallest correct patch.
- Preserve the existing code style.
- If a change affects the Vehicle_Data FastAPI API, identify the impact on the Vehicle_App Flutter frontend before implementation.
- Before changing code, explain the plan in five bullets or fewer.
- After coding, run relevant tests, summarize the changed files, and explain why each file changed.
- If behavior or scope is unclear, stop and ask instead of guessing.
- Never rewrite large files unless explicitly requested.
- Keep one logical change per commit.
- Keep commits clean and descriptive.
- ChatGPT/the user owns architecture, debugging direction, and final code review; Codex owns the approved implementation work.
