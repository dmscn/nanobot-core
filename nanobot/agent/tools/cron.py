"""Cron tool for scheduling reminders and tasks."""

import json
import re
from datetime import datetime
from typing import Any, Literal

from nanobot.agent.tools.base import Tool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


class CronTool(Tool):
    """Tool to schedule reminders and recurring tasks with explicit job types.

    Job Types:
    - echo: Simple reminder (output message directly)
    - command: Natural language task (use tools to complete)
    - tool_call: Execute specific tool with arguments
    """

    def __init__(self, cron_service: CronService):
        self._cron = cron_service
        self._channel = ""
        self._chat_id = ""

    def set_context(self, channel: str, chat_id: str) -> None:
        """Set the current session context for delivery."""
        self._channel = channel
        self._chat_id = chat_id

    @property
    def name(self) -> str:
        return "cron"

    @property
    def description(self) -> str:
        return """Schedule and manage automated tasks. Actions:
- add: Create a new scheduled job (echo/command/tool_call)
- list: List all scheduled jobs
- remove: Remove a job by ID
- execute_job: Execute a dispatched job by ID (internal use)

Job types:
- echo: Simple reminder (output message directly)
- command: Natural language task (use tools to complete)
- tool_call: Execute specific tool with arguments"""

    @property
    def parameters(self) -> dict[str, Any]:
        return {
            "type": "object",
            "properties": {
                "action": {
                    "type": "string",
                    "enum": ["add", "list", "remove", "execute_job"],
                    "description": "Action to perform",
                },
                "message": {
                    "type": "string",
                    "description": "Task description or reminder message",
                },
                "kind": {
                    "type": "string",
                    "enum": ["echo", "command", "tool_call"],
                    "description": (
                        "Job type: echo (simple reminder), command (natural"
                        " language task), tool_call (specific tool)"
                    ),
                },
                "tool": {
                    "type": "string",
                    "description": "Tool name (for tool_call type)",
                },
                "arguments": {
                    "type": "object",
                    "description": "Tool arguments (for tool_call type)",
                },
                "every_seconds": {
                    "type": "integer",
                    "description": "Interval in seconds (for recurring tasks)",
                },
                "cron_expr": {
                    "type": "string",
                    "description": "Cron expression like '0 9 * * *' (for scheduled tasks)",
                },
                "tz": {
                    "type": "string",
                    "description": "IANA timezone for cron expressions (e.g. 'America/Vancouver')",
                },
                "at": {
                    "type": "string",
                    "description": (
                        "ISO datetime for one-time execution"
                        " (e.g. '2026-02-12T10:30:00')"
                    ),
                },
                "job_id": {
                    "type": "string",
                    "description": "Job ID (for remove or execute_job)",
                },
            },
            "required": ["action"],
        }

    async def execute(
        self,
        action: str,
        message: str = "",
        kind: Literal["echo", "command", "tool_call"] | None = None,
        tool: str | None = None,
        arguments: dict | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        tz: str | None = None,
        at: str | None = None,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        if action == "add":
            return self._add_job(message, kind, tool, arguments, every_seconds, cron_expr, tz, at)
        elif action == "list":
            return self._list_jobs()
        elif action == "remove":
            return self._remove_job(job_id)
        elif action == "execute_job":
            return self._execute_job(job_id)
        return f"Unknown action: {action}"

    def _infer_job_type(self, message: str) -> Literal["echo", "command", "tool_call"]:
        """Infer job type from natural language message.

        Examples:
            "Remind me to take medicine" → echo
            "Send message to WhatsApp" → tool_call
            "Check the weather daily" → command
        """
        msg_lower = message.lower()

        # Tool call patterns: explicit tool mentions
        tool_patterns = [
            r"send (?:a )?message",
            r"send (?:an )?email",
            r"send to (?:whatsapp|telegram|slack)",
            r"call (?:the )?tool",
            r"use (?:the )?tool",
        ]
        for pattern in tool_patterns:
            if re.search(pattern, msg_lower):
                return "tool_call"

        # Echo patterns: simple reminders (short, imperative)
        echo_patterns = [
            r"remind me (?:to )?(?:that )?.+",
            r"remember to .+",
            r"don't forget .+",
            r"tell me .+",
        ]
        for pattern in echo_patterns:
            if re.search(pattern, msg_lower):
                # If it's short (< 10 words), likely a simple reminder
                if len(message.split()) < 10:
                    return "echo"

        # Default: command (natural language task)
        return "command"

    def _add_job(
        self,
        message: str,
        kind: Literal["echo", "command", "tool_call"] | None = None,
        tool: str | None = None,
        arguments: dict | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        tz: str | None = None,
        at: str | None = None,
    ) -> str:
        if not message:
            return "Error: message is required for add"
        if not self._channel or not self._chat_id:
            return "Error: no session context (channel/chat_id)"
        if tz and not cron_expr:
            return "Error: tz can only be used with cron_expr"
        if tz:
            from zoneinfo import ZoneInfo

            try:
                ZoneInfo(tz)
            except (KeyError, Exception):
                return f"Error: unknown timezone '{tz}'"
        if kind == "tool_call" and not tool:
            return "Error: tool is required when kind is tool_call"

        # Infer job type if not specified
        effective_kind = kind or self._infer_job_type(message)

        # Build schedule
        delete_after = False
        if every_seconds:
            schedule = CronSchedule(kind="every", every_ms=every_seconds * 1000)
        elif cron_expr:
            schedule = CronSchedule(kind="cron", expr=cron_expr, tz=tz)
        elif at:
            dt = datetime.fromisoformat(at)
            at_ms = int(dt.timestamp() * 1000)
            schedule = CronSchedule(kind="at", at_ms=at_ms)
            delete_after = True
        else:
            return "Error: either every_seconds, cron_expr, or at is required"

        job = self._cron.add_job(
            name=message[:30],
            schedule=schedule,
            message=message,
            job_type=effective_kind,
            tool=tool,
            arguments=arguments,
            deliver=True,
            channel=self._channel,
            to=self._chat_id,
            delete_after_run=delete_after,
        )
        return f"Created job '{job.name}' (id: {job.id}, type: {effective_kind})"

    def _execute_job(self, job_id: str | None) -> str:
        """Execute a dispatched cron job by ID.

        Loads the full job from jobs.json and returns structured instructions
        based on the job type (echo, command, or tool_call).
        """
        if not job_id:
            return "Error: job_id is required for execute_job"

        job = self._cron.get_job(job_id)
        if not job:
            return f"Error: Job {job_id} not found"

        # Format timestamps
        created = datetime.fromtimestamp(job.created_at_ms / 1000).strftime("%Y-%m-%d %H:%M")

        # Delivery info
        delivery_status = "No"
        delivery_target = ""
        if job.payload.deliver and job.payload.to:
            delivery_status = "Yes"
            delivery_target = f" → {job.payload.channel}/{job.payload.to}"

        job_type = job.payload.job_type
        message = job.payload.message

        # Build type-specific sections
        if job_type == "echo":
            task_section = f"""### TASK

Output the following message verbatim:

> {message}

---

### EXECUTION

1. Output the message above **exactly as written**
2. Do NOT use any tools
3. Do NOT add commentary or modifications
4. The message will be delivered to the recipient"""

        elif job_type == "tool_call":
            args_json = (
                json.dumps(job.payload.arguments, indent=2)
                if job.payload.arguments
                else "{}"
            )
            task_section = f"""### TASK

Execute the specified tool with the provided arguments.

**Tool:** `{job.payload.tool}`
**Arguments:**
```json
{args_json}
```

---

### EXECUTION

1. Call the `{job.payload.tool}` tool with the exact arguments above
2. Do NOT modify the arguments
3. The result will be delivered to the recipient"""

        else:  # command
            task_section = f"""### TASK

{message}

---

### EXECUTION

1. Use appropriate tools or skills to complete this task
2. Compose a clear response
3. Send the result to the recipient (delivery enabled)

You MUST use appropriate tools to complete this task."""

        return f"""## CRON JOB: {job.name}

**Job ID:** {job.id}
**Type:** {job_type.upper()}
**Delivery:** {delivery_status}{delivery_target}

---

{task_section}

---

**Metadata:**
- Schedule: {job.schedule.kind}
- Created: {created}"""

    def _list_jobs(self) -> str:
        jobs = self._cron.list_jobs()
        if not jobs:
            return "No scheduled jobs."
        lines = [
            f"- {j.name} (id: {j.id}, {j.schedule.kind}, type: {j.payload.job_type})"
            for j in jobs
        ]
        return "Scheduled jobs:\n" + "\n".join(lines)

    def _remove_job(self, job_id: str | None) -> str:
        if not job_id:
            return "Error: job_id is required for remove"
        if self._cron.remove_job(job_id):
            return f"Removed job {job_id}"
        return f"Job {job_id} not found"
