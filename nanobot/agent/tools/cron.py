"""Cron tool for scheduling reminders and tasks with execution modes.

Execution Modes:
- echo: Reminder/notification (output the composed message verbatim)
- command: Task execution (agent performs task at scheduled time)
"""

from datetime import datetime
from typing import Any, Literal

from nanobot.agent.tools.base import Tool
from nanobot.cron.service import CronService
from nanobot.cron.types import CronSchedule


class CronTool(Tool):
    """Tool to schedule and manage automated tasks."""

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
        return """Schedule automated tasks. Actions: add, list, remove, execute_job.

Workflow:
- add: Create job → Verify with list → Confirm to user → STOP
- list: Show jobs → Send to user → STOP
- remove: Delete job → Confirm → STOP
- execute_job: Get instructions → Execute → STOP

Execution modes:
- echo: Compose reminder text (output verbatim at scheduled time)
- command: Compose task instruction (execute at scheduled time)

Compose messages based on user intent. Do not copy user's exact words."""

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
                    "description": "Composed message for scheduled time. Write what should be output/done at that moment, not user's exact words.",
                },
                "execution_mode": {
                    "type": "string",
                    "enum": ["echo", "command"],
                    "description": (
                        "Execution mode. 'echo' = output message verbatim (compose reminder text). "
                        "'command' = execute task (compose instruction for yourself)."
                    ),
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
        execution_mode: Literal["echo", "command"] | None = None,
        every_seconds: int | None = None,
        cron_expr: str | None = None,
        tz: str | None = None,
        at: str | None = None,
        job_id: str | None = None,
        **kwargs: Any,
    ) -> str:
        if action == "add":
            return self._add_job(message, execution_mode, every_seconds, cron_expr, tz, at)
        elif action == "list":
            return self._list_jobs()
        elif action == "remove":
            return self._remove_job(job_id)
        elif action == "execute_job":
            return self._execute_job(job_id)
        return f"Unknown action: {action}"

    def _add_job(
        self,
        message: str,
        execution_mode: Literal["echo", "command"] | None = None,
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

        # Require explicit mode from agent
        if execution_mode is None:
            return "Error: execution_mode is required. Specify 'echo' for reminders (output message) or 'command' for tasks (perform action)."

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
            execution_mode=execution_mode,
            deliver=True,
            channel=self._channel,
            to=self._chat_id,
            delete_after_run=delete_after,
        )
        return f"Created job '{job.name}' (id: {job.id})"

    def _execute_job(self, job_id: str | None) -> str:
        """Execute a dispatched cron job by ID.

        Loads the full job from jobs.json and returns structured instructions
        based on the execution mode (echo or command).
        """
        if not job_id:
            return "Error: job_id is required for execute_job"

        job = self._cron.get_job(job_id)
        if not job:
            return f"Error: Job {job_id} not found"

        # Format timestamps with timezone
        tz_str = job.schedule.tz or "UTC"
        try:
            from zoneinfo import ZoneInfo
            tz = ZoneInfo(tz_str)
            created = datetime.fromtimestamp(job.created_at_ms / 1000, tz=tz).strftime("%Y-%m-%d %H:%M %Z")
        except Exception:
            created = datetime.fromtimestamp(job.created_at_ms / 1000).strftime("%Y-%m-%d %H:%M") + f" ({tz_str})"

        # Delivery info
        delivery_status = "No"
        delivery_target = ""
        if job.payload.deliver and job.payload.to:
            delivery_status = "Yes"
            delivery_target = f" → {job.payload.channel}/{job.payload.to}"

        execution_mode = job.payload.execution_mode
        message = job.payload.message

        # Build mode-specific sections
        if execution_mode == "echo":
            task_section = f"""### TASK

Output the following reminder message:

> {message}

---

### EXECUTION

1. Output the message above exactly as written
2. Do NOT use any tools
3. Do NOT add commentary or modifications
4. This is a pre-composed reminder - just deliver it"""

        else:  # command
            task_section = f"""### TASK

{message}

---

### EXECUTION

1. Analyze the task and determine the best approach
2. Use tools if needed, or respond directly if appropriate
3. Send the result to the recipient (delivery enabled)"""

        return f"""## CRON JOB: {job.name}

**Job ID:** {job.id}
**Execution Mode:** {execution_mode.upper()}
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

        lines = []
        for j in jobs:
            # Format next run with timezone
            next_run = ""
            if j.state.next_run_at_ms:
                ts = j.state.next_run_at_ms / 1000
                tz_str = j.schedule.tz or "UTC"
                try:
                    from zoneinfo import ZoneInfo
                    tz = ZoneInfo(tz_str)
                    next_run_str = datetime.fromtimestamp(ts, tz).strftime("%Y-%m-%d %H:%M %Z")
                except Exception:
                    next_run_str = datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M") + f" ({tz_str})"
                next_run = f", next: {next_run_str}"

            lines.append(f"- {j.name} (id: {j.id}, {j.schedule.kind}{next_run})")

        return "Scheduled jobs:\n" + "\n".join(lines)

    def _remove_job(self, job_id: str | None) -> str:
        if not job_id:
            return "Error: job_id is required for remove"
        if self._cron.remove_job(job_id):
            return f"Removed job {job_id}"
        return f"Job {job_id} not found"
