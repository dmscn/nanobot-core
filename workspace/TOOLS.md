# Available Tools

This document describes the tools available to nanobot.

## File Operations

### read_file
Read the contents of a file.
```
read_file(path: str) -> str
```

### write_file
Write content to a file (creates parent directories if needed).
```
write_file(path: str, content: str) -> str
```

### edit_file
Edit a file by replacing specific text.
```
edit_file(path: str, old_text: str, new_text: str) -> str
```

### list_dir
List contents of a directory.
```
list_dir(path: str) -> str
```

## Shell Execution

### exec
Execute a shell command and return output.
```
exec(command: str, working_dir: str = None) -> str
```

**Safety Notes:**
- Commands have a configurable timeout (default 60s)
- Dangerous commands are blocked (rm -rf, format, dd, shutdown, etc.)
- Output is truncated at 10,000 characters
- Optional `restrictToWorkspace` config to limit paths

## Web Access

### web_search
Search the web using Brave Search API.
```
web_search(query: str, count: int = 5) -> str
```

Returns search results with titles, URLs, and snippets. Requires `tools.web.search.apiKey` in config.

### web_fetch
Fetch and extract main content from a URL.
```
web_fetch(url: str, extractMode: str = "markdown", maxChars: int = 50000) -> str
```

**Notes:**
- Content is extracted using readability
- Supports markdown or plain text extraction
- Output is truncated at 50,000 characters by default

## Communication

### message
Send a message to the user on a chat channel.
```
message(
    content: str,
    channel: str = None,
    chat_id: str = None,
    media: list[str] = None,
    callback_id: str = None,
    inline_buttons: list[dict] = None
) -> str
```

**Parameters:**
- `content` (required): The message text to send
- `channel` (optional): Target channel (telegram, discord, etc.)
- `chat_id` (optional): Target chat/user ID
- `media` (optional): List of file paths to attach
- `callback_id` (optional): Logical ID to group callback buttons (auto-generated if not provided)
- `inline_buttons` (optional): Interactive buttons (Telegram only)

### Inline Buttons (Telegram)

Send interactive buttons with your message to create rich user interactions:

```python
# Simple confirmation buttons
inline_buttons = [
    {"id": "confirm", "label": "✅ Confirm"},
    {"id": "cancel", "label": "❌ Cancel"}
]

# Buttons with instructions and metadata
inline_buttons = [
    {
        "id": "complete",
        "label": "✅ Done",
        "data": "Mark this task as completed",
        "metadata": {"task_id": "123"}
    }
]

# URL buttons (open link, no callback)
inline_buttons = [
    {"label": "Help", "url": "https://help.example.com"}
]

# Row layouts (multiple buttons per row)
inline_buttons = [
    [{"id": "yes", "label": "Yes"}, {"id": "no", "label": "No"}],
    [{"label": "Help", "url": "https://help.example.com"}]
]

# Using callback_id to group multiple messages
callback_id = "reminder_001"
```

**Button fields:**
- `id`: Button identifier (used for callbacks)
- `label`: Text shown on the button
- `data`: Instructions for the agent when button is clicked
- `metadata`: Additional structured data
- `url`: URL for link buttons (no callback)

### Handling Button Callbacks

When a user clicks a button, you receive a special message:

```python
# You receive this as an InboundMessage:
{
    "content": "",  # Empty - this is NOT a user message
    "metadata": {
        "event_type": "callback_query",
        "callback_id": "a1b2c3",
        "button": {
            "id": "complete",
            "label": "✅ Done",
            "data": "Mark this task as completed",
            "metadata": {"task_id": "123"}
        },
        "user_id": 6176528759,
        "username": "john_doe",
        "message_id": 456
    }
}
```

**How to handle:**
1. Check if `metadata.event_type == "callback_query"` (this is a button click, NOT a user message)
2. Read `metadata.button.id` to know which button was clicked
3. Read `metadata.button.data` for instructions on what to do
4. Use `metadata.button.metadata` for structured data
5. Execute the action and respond to the user

## Background Tasks

### spawn
Spawn a subagent to handle a task in the background.
```
spawn(task: str, label: str = None) -> str
```

Use for complex or time-consuming tasks that can run independently. The subagent will complete the task and report back when done.

## Scheduled Reminders (Cron)

Use the `exec` tool to create scheduled reminders with `nanobot cron add`:

### Set a recurring reminder
```bash
# Every day at 9am
nanobot cron add --name "morning" --message "Good morning! ☀️" --cron "0 9 * * *"

# Every 2 hours
nanobot cron add --name "water" --message "Drink water! 💧" --every 7200
```

### Set a one-time reminder
```bash
# At a specific time (ISO format)
nanobot cron add --name "meeting" --message "Meeting starts now!" --at "2025-01-31T15:00:00"
```

### Manage reminders
```bash
nanobot cron list              # List all jobs
nanobot cron remove <job_id>   # Remove a job
```

## Heartbeat Task Management

The `HEARTBEAT.md` file in the workspace is checked every 30 minutes.
Use file operations to manage periodic tasks:

### Add a heartbeat task
```python
# Append a new task
edit_file(
    path="HEARTBEAT.md",
    old_text="## Example Tasks",
    new_text="- [ ] New periodic task here\n\n## Example Tasks"
)
```

### Remove a heartbeat task
```python
# Remove a specific task
edit_file(
    path="HEARTBEAT.md",
    old_text="- [ ] Task to remove\n",
    new_text=""
)
```

### Rewrite all tasks
```python
# Replace the entire file
write_file(
    path="HEARTBEAT.md",
    content="# Heartbeat Tasks\n\n- [ ] Task 1\n- [ ] Task 2\n"
)
```

---

## Adding Custom Tools

To add custom tools:
1. Create a class that extends `Tool` in `nanobot/agent/tools/`
2. Implement `name`, `description`, `parameters`, and `execute`
3. Register it in `AgentLoop._register_default_tools()`
