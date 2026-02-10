
# Claude Personality & Language Rules

## Communication Preference
- **Language**: All responses must be written in **Traditional Chinese (zh-TW)**.
- **Tone**: Technical, precise, and concise.
- **Regional Terms**: Use software terminology standard in Taiwan (e.g., "專案", "程式", "檔案").

## File Operations & Implementation Plans
- **File Name**: `implementation_plan.md`
- **Storage Rule**: Always save or update implementation plans in the **current project root directory**.
- **Execution**: Use the provided file-writing tools to commit changes directly to the workspace. DO NOT output large plans only in the chat interface.
- **Language Consistency**: The content of `implementation_plan.md` and all other generated `.md` files must be in **Traditional Chinese**.

## Technical Standards
- **Comments**: Include detailed comments in Traditional Chinese for all code snippets (Python/Streamlit).
- **Exceptions**: Maintain English for technical keywords, error logs, and industry-standard terms without direct translations (e.g., "Middleware", "Prompt Engineering").