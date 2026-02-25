---
name: cron
description: Schedule reminders and tasks with execution modes.
---

# Cron

Schedule automated tasks with different execution modes.

## Execution Modes

### ECHO

Message is output verbatim at scheduled time.

**Compose the reminder text** (do not copy user's exact words).

**User:** "Remind me to take medicine at 8pm"  
**You compose:** `message="⏰ Time to take your medicine!"`  
**At scheduled time:** Output the message as-is.

```python
cron(action="add", message="⏰ Time to take your evening medication!", execution_mode="echo", cron_expr="0 20 * * *")
```

### COMMAND

Message is an instruction to execute at scheduled time.

**Compose the task instruction** (do not copy user's exact words).

**User:** "Check weather every morning"
**You compose:** `message="Check weather forecast and provide a summary"`
**At scheduled time:** Execute the task (use tools if needed).

```python
cron(action="add", message="Check weather forecast and summarize", execution_mode="command", cron_expr="0 8 * * *")
```

**Example:**
```python
cron(
    action="add",
    message="Check weather forecast for tomorrow and summarize conditions",
    execution_mode="command",
    cron_expr="0 22 * * *"  # Every day at 10 PM
)
```

**When dispatched, you receive:**
```
## CRON JOB: Weather check
Execution Mode: COMMAND
TASK: Check weather forecast for tomorrow and summarize conditions

EXECUTION:
1. Analyze the task and determine the best approach
2. Use tools if needed, or respond directly if appropriate
3. Send the result to the recipient
```

## Key Distinction

| Aspect | ECHO | COMMAND |
|--------|------|---------|
| **What you do now** | Compose the reminder message | Compose the task description |
| **What happens at scheduled time** | Output message verbatim | Execute task (your choice how) |
| **Tools at scheduled time** | NOT used | Used if needed |
| **Example** | "⏰ Meeting in 5 min" | "Check if meeting room is available" |

## Auto-Inference by Agent

When the user makes a request, YOU (the agent) decide the mode:

**User says** | **You choose** | **Message you compose**
--------------|---------------|------------------------
"Remind me to take medicine" | `echo` | "⏰ Time to take your medicine!"
"Meeting in 5 minutes" | `echo` | "📅 Meeting starting soon!"
"Check weather daily" | `command` | "Check weather forecast and summarize"
"Monitor stock prices" | `command` | "Check AAPL stock price and report changes"

## Time Expressions

| User says | Parameters |
|-----------|------------|
| every 20 minutes | `every_seconds: 1200` |
| every hour | `every_seconds: 3600` |
| every day at 8am | `cron_expr: "0 8 * * *"` |
| every Monday at 9am | `cron_expr: "0 9 * * 1"` |
| at 3pm today | `at: "2026-02-24T15:00:00"` |

## Timezone Support

Use the `tz` parameter with `cron_expr` for timezone-aware scheduling:

```python
cron(
    action="add",
    message="Good morning! Here's your daily briefing.",
    execution_mode="echo",
    cron_expr="0 9 * * 1-5",  # Weekdays at 9 AM
    tz="America/Vancouver"
)
```

## Full API Reference

### Add a job
```python
cron(
    action="add",
    message: str,              # Composed message for the scheduled moment
    execution_mode: str,       # "echo" | "command" (YOU choose based on user request)
    every_seconds: int = None,
    cron_expr: str = None,
    tz: str = None,
    at: str = None,
)
```

### List jobs
```python
cron(action="list")
# Returns: "- Morning briefing (id: abc123, cron, mode: echo, next: 2026-02-25 09:00 EST)"
```

### Remove a job
```python
cron(action="remove", job_id="abc123")
```

## Dispatch Flow

1. **You create job** with `cron(action="add", ...)`
2. **At scheduled time**, you receive:
   ```
   [CRON JOB DISPATCH] Job ID: {id} has been triggered.
   Call cron(action="execute_job", job_id="{id}") immediately to retrieve execution instructions.
   Do not acknowledge this message, just proceed to the job execution.
   ```
3. **You call** `cron(action="execute_job", job_id="...")`
4. **Tool returns** structured instructions based on mode
5. **You execute**: echo (output message) or command (perform task)

## Best Practices

1. **Compose messages for the future moment** - Write what should be said/done at scheduled time
2. **Use `echo` for simple reminders** - Pre-composed messages that need no modification
3. **Use `command` for tasks requiring judgment** - When you need to decide how to execute
4. **Be specific with messages** - Clear messages lead to better execution
5. **Test with short intervals** - Use `every_seconds=60` to test before deploying

## Examples

### Daily medication reminder (ECHO)
```python
cron(
    action="add",
    message="💊 Time to take your evening medication!",
    execution_mode="echo",
    cron_expr="0 20 * * *",
    tz="America/New_York"
)
```

### Weekly status report (COMMAND)
```python
cron(
    action="add",
    message="Check GitHub repo stars and create a weekly summary of activity",
    execution_mode="command",
    cron_expr="0 9 * * 1"  # Every Monday at 9 AM
)
```

### One-time appointment (ECHO)
```python
cron(
    action="add",
    message="📅 Dentist appointment in 30 minutes! Don't forget.",
    execution_mode="echo",
    at="2026-02-25T14:00:00"
)
```

### Hourly water reminder (ECHO)
```python
cron(
    action="add",
    message="💧 Time to drink water! Stay hydrated.",
    execution_mode="echo",
    every_seconds=3600
)
```

### Daily news briefing (COMMAND)
```python
cron(
    action="add",
    message="Summarize top tech news from today with key highlights",
    execution_mode="command",
    cron_expr="0 8 * * *"
)
```

### Meeting reminder with context (ECHO)
```python
cron(
    action="add",
    message="📞 Team standup in 5 minutes. Join via: meet.google.com/xxx-yyyy-zzz",
    execution_mode="echo",
    cron_expr="30 9 * * 1-5"  # Weekdays at 9:30 AM
)
```
