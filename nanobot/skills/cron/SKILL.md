---
name: cron
description: Schedule reminders and recurring tasks with explicit job types.
---

# Cron Tool

Use the `cron` tool to schedule and manage automated tasks.

## Job Types

When creating a job, specify the `kind` parameter to define how the agent should execute it:

### 1. ECHO - Simple Reminder

Use for straightforward messages that should be output verbatim.

**Example:**
```python
cron(
    action="add",
    message="Take medicine",
    kind="echo",
    every_seconds=14400  # Every 4 hours
)
```

**Agent behavior:** Outputs the message directly, no tools used.

**When dispatched, agent receives:**
```
## CRON JOB: Take medicine
**Job ID:** abc123
**Type:** ECHO
**Delivery:** Yes → telegram/123456

### TASK
Output the following message verbatim:
> Take medicine

### EXECUTION
1. Output the message above **exactly as written**
2. Do NOT use any tools
3. Do NOT add commentary or modifications
```

---

### 2. COMMAND - Natural Language Task

Use for tasks requiring the agent to take action using tools or skills.

**Example:**
```python
cron(
    action="add",
    message="Check the weather and send a summary report",
    kind="command",  # default
    cron_expr="0 8 * * *"  # Daily at 8am
)
```

**Agent behavior:** Uses web_search/web_fetch tools, composes response.

**When dispatched, agent receives:**
```
## CRON JOB: Daily weather report
**Job ID:** def456
**Type:** COMMAND
**Delivery:** Yes → telegram/123456

### TASK
Check the weather and send a summary report.

### EXECUTION
1. Use appropriate tools or skills to complete this task
2. Compose a clear response
3. Send the result to the recipient (delivery enabled)

You MUST use appropriate tools to complete this task.
```

---

### 3. TOOL_CALL - Specific Tool Execution

Use for executing a specific tool with predefined arguments.

**Example:**
```python
cron(
    action="add",
    message="Send daily standup",
    kind="tool_call",
    tool="message",
    arguments={"content": "Daily standup: All systems operational"},
    every_seconds=86400  # Daily
)
```

**Agent behavior:** Calls the specified tool with exact arguments.

**When dispatched, agent receives:**
```
## CRON JOB: Daily standup
**Job ID:** ghi789
**Type:** TOOL_CALL
**Delivery:** Yes → telegram/123456

### TASK
Execute the specified tool with the provided arguments.

**Tool:** `message`
**Arguments:**
```json
{
  "content": "Daily standup: All systems operational"
}
```

### EXECUTION
1. Call the `message` tool with the exact arguments above
2. Do NOT modify the arguments
```

---

## Actions

### `add` - Create a new job

**Parameters:**
- `action`: "add"
- `message`: The task or reminder message
- `kind`: "echo" | "command" | "tool_call" (default: inferred from message)
- `tool`: Tool name (required for tool_call)
- `arguments`: Tool arguments as dict (required for tool_call)
- `every_seconds`: Interval in seconds
- `cron_expr`: Cron expression (e.g., "0 9 * * *")
- `tz`: Timezone for cron expressions (e.g., "America/Sao_Paulo")
- `at`: ISO datetime for one-time execution

**Examples:**

```python
# Simple reminder every 4 hours
cron(action="add", message="Take medicine", kind="echo", every_seconds=14400)

# Daily weather check at 8am
cron(action="add", message="Check weather and report", cron_expr="0 8 * * *")

# Send message at specific time
cron(action="add", message="Meeting reminder", at="2026-02-24T15:00:00")

# Timezone-aware cron
cron(action="add", message="Morning standup", cron_expr="0 9 * * 1-5", tz="America/Sao_Paulo")

# Tool call with specific arguments
cron(
    action="add",
    message="Send report",
    kind="tool_call",
    tool="message",
    arguments={"content": "Weekly report here"},
    cron_expr="0 17 * * 5"
)
```

---

### `execute_job` - Execute a dispatched job (Internal)

**Parameters:**
- `action`: "execute_job"
- `job_id`: The job ID to execute

**Note:** This action is called automatically when a scheduled job is dispatched. Users don't call this directly.

**Flow:**
1. Scheduled time arrives
2. Agent receives: `[CRON JOB DISPATCH] Job ID: {id} has been triggered. Call cron(action="execute_job", job_id="{id}") immediately to retrieve execution instructions.`
3. Agent calls `cron(action="execute_job", job_id="{id}")`
4. Cron tool returns structured instructions based on job type
5. Agent executes the task

---

### `list` - List all jobs

```python
cron(action="list")
```

Returns all scheduled jobs with their IDs, names, schedules, and types.

---

### `remove` - Remove a job

```python
cron(action="remove", job_id="abc123")
```

---

## How Cron Jobs Work

### 1. User Creates Job

User schedules a task using natural language or explicit parameters.

**User:** "Remind me to take the trash out in 2 minutes"

**Agent:** Creates job with type ECHO, stores message "Reminding you to take the trash out now!"

---

### 2. Job is Stored

The job is saved to `jobs.json` with all metadata:

```json
{
  "id": "abc123",
  "name": "Take trash out",
  "schedule": {"kind": "at", "at_ms": 1740369720000},
  "payload": {
    "message": "Reminding you to take the trash out now!",
    "job_type": "echo",
    "deliver": true,
    "channel": "telegram",
    "to": "123456"
  }
}
```

---

### 3. Scheduled Time Arrives

When the scheduled time is reached, the cron service dispatches the job.

---

### 4. Agent Receives Dispatch Notification

Agent receives a hard-coded system message:

```
[CRON JOB DISPATCH] Job ID: abc123 has been triggered. Call cron(action="execute_job", job_id="abc123") immediately to retrieve execution instructions.
```

---

### 5. Agent Calls `execute_job`

The agent calls the cron tool to fetch job details.

---

### 6. Cron Tool Returns Structured Instructions

Based on job type, the tool returns detailed instructions:

- **ECHO:** Output message verbatim
- **COMMAND:** Execute natural language task using tools
- **TOOL_CALL:** Call specified tool with exact arguments

---

### 7. Agent Executes Task

Based on the instructions:
- **ECHO:** Outputs message directly
- **COMMAND:** Uses tools to complete the task
- **TOOL_CALL:** Executes the specified tool

---

### 8. Result Delivered (if enabled)

If delivery is enabled, the result is sent to the specified channel/recipient.

---

## Best Practices

### Use ECHO for:
- Medication reminders
- Simple notifications
- Break reminders
- Status check prompts
- Any message that should be output verbatim

### Use COMMAND for:
- Weather reports
- News summaries
- Data gathering tasks
- Multi-step workflows
- Tasks requiring fresh data each time

### Use TOOL_CALL for:
- Scheduled messages with fixed content
- Repetitive API calls
- Fixed report generation
- Automated notifications with exact format

---

## Message Guidelines

### For ECHO Jobs

**Transform messages to present tense** as they will be delivered verbatim at the scheduled time.

**❌ Bad:**
```python
cron(action="add", message="Remind me to take the trash out", kind="echo", at="...")
```
When delivered: "Remind me to take the trash out" (sounds wrong!)

**✅ Good:**
```python
cron(action="add", message="Reminding you to take the trash out now!", kind="echo", at="...")
```
When delivered: "Reminding you to take the trash out now!" (makes sense!)

### For COMMAND Jobs

Use natural language describing what the agent should do. The message is an **instruction**, not a delivery string.

**Example:**
```python
cron(
    action="add",
    message="Check the weather forecast for tomorrow and send a summary",
    kind="command",
    cron_expr="0 22 * * *"
)
```

When dispatched, the agent will execute the instruction and compose a fresh response each time.

---

## Time Expressions

| User says | Parameters |
|-----------|------------|
| every 20 minutes | `every_seconds: 1200` |
| every hour | `every_seconds: 3600` |
| every day at 8am | `cron_expr: "0 8 * * *"` |
| weekdays at 5pm | `cron_expr: "0 17 * * 1-5"` |
| 9am Sao Paulo time daily | `cron_expr: "0 9 * * *", tz: "America/Sao_Paulo"` |
| at a specific time | `at: "2026-02-24T15:00:00"` |

---

## Timezone Support

Use `tz` with `cron_expr` to schedule in a specific IANA timezone:

```python
cron(
    action="add",
    message="Morning standup",
    cron_expr="0 9 * * 1-5",
    tz="America/Sao_Paulo"
)
```

Without `tz`, the user's configured timezone is used.

---

## Examples

### Medication Reminder
```python
cron(
    action="add",
    message="Take your medication",
    kind="echo",
    every_seconds=14400  # Every 4 hours
)
```

### Daily News Briefing
```python
cron(
    action="add",
    message="Get top tech news and summarize",
    kind="command",
    cron_expr="0 7 * * *"
)
```

### Automated Status Report
```python
cron(
    action="add",
    message="Send status report",
    kind="tool_call",
    tool="message",
    arguments={"content": "Status: All systems operational"},
    cron_expr="0 17 * * 5"  # Every Friday at 5pm
)
```

### One-Time Meeting Reminder
```python
cron(
    action="add",
    message="Team meeting in 15 minutes",
    kind="echo",
    at="2026-02-24T15:00:00"
)
```

### Weather Check with Timezone
```python
cron(
    action="add",
    message="Check weather forecast for tomorrow",
    kind="command",
    cron_expr="0 22 * * *",
    tz="America/Sao_Paulo"
)
```
