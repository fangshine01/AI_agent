# User-Specific API Keys Implementation Plan

## Goal
Enable team members to input their own OpenAI and Gemini API keys via the frontend UI. The system should dynamically select the correct key based on the chosen model (OpenAI vs Gemini) during chat interactions.

## User Review Required
> [!NOTE]
> This change primarily affects the **Chat** interface. 
> The background file watcher will continue to use the System Keys defined in `.env`.

## Proposed Changes

### Frontend (`frontend/pages/1_💬_Chat.py`)
- [MODIFY] Split the single "API Key" input into two fields:
    - "OpenAI API Key" (maps to `user_api_key`)
    - "Gemini API Key" (maps to `user_gemini_key`)
- [MODIFY] Update the `client.chat()` call to pass both keys.

### Client (`frontend/client/api_client.py`)
- [MODIFY] Update `chat()` method signature to accept `gemini_key`.
- [MODIFY] Add `gemini_key` to the JSON payload sent to `POST /chat/query`.

### Backend Schema (`backend/app/schemas/chat.py`)
- [MODIFY] Add optional `gemini_key: str` field to `ChatRequest` model.

### Backend API (`backend/app/api/v1/chat.py`)
- [MODIFY] In `query` function, implement key selection logic:
    ```python
    # Determine which key to use based on model
    if "gemini" in request.chat_model.lower():
        selected_key = request.gemini_key or config.GEMINI_API_KEY
    else:
        selected_key = request.api_key or config.OPENAI_API_KEY
    ```
- [MODIFY] Pass the `selected_key` to `ai_core.call_chat_model`.

## Verification Plan

### Manual Verification
1.  **OpenAI Test**:
    - Enter a valid OpenAI Key in the UI.
    - Select `gpt-4o-mini`.
    - Ask a question.
    - Verify response is generated.
2.  **Gemini Test**:
    - Enter a valid Gemini Key in the UI.
    - Select `gemini-2.0-flash-exp`.
    - Ask a question.
    - Verify response is generated.
3.  **Cross_Check**:
    - Clear OpenAI Key, keep Gemini Key.
    - Try to use `gpt-4o-mini` -> Should fail (or fallback to system key if allowed/configured).
