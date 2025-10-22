"""
Task Service - Handles task creation, execution, and result management
"""
import uuid
import json
import aiosqlite
from datetime import datetime
from typing import Dict, List, Optional
from fastapi import BackgroundTasks

from app.config import get_settings
from app.agents.registry import get_agent, list_agents
from app.agents.base import AgentTask, AgentResult

settings = get_settings()


class TaskService:
    """Service for managing agent tasks"""

    def __init__(self):
        self.db_path = settings.DATABASE_PATH

    async def create_task(
        self,
        user_id: str,
        agent_type: str,
        input_data: Dict,
    ) -> Dict:
        """
        Create a new task

        Args:
            user_id: User ID from Auth0
            agent_type: Type of agent to use
            input_data: Input data for the agent

        Returns:
            Task dictionary with ID and estimated cost

        Raises:
            ValueError: If user has reached the task limit (3 active tasks)
        """
        try:
            # Check task limit (max 3 active tasks per user)
            async with aiosqlite.connect(self.db_path) as db:
                cursor = await db.execute(
                    """
                    SELECT COUNT(*) as count FROM tasks
                    WHERE user_id = ? AND status IN ('pending', 'running')
                    """,
                    (user_id,)
                )
                row = await cursor.fetchone()
                active_count = row[0] if row else 0

                if active_count >= 3:
                    raise ValueError(
                        f"Task limit reached. You have {active_count} active tasks. "
                        "Please wait for existing tasks to complete before creating new ones."
                    )

            # Validate agent type
            try:
                agent = get_agent(agent_type)
            except KeyError:
                raise ValueError(f"Unknown agent type: {agent_type}")

            # Estimate cost
            estimated_cost = await agent.estimate_cost(input_data)

            # Create task record
            task_id = str(uuid.uuid4())

            async with aiosqlite.connect(self.db_path) as db:
                await db.execute(
                    """
                    INSERT INTO tasks (
                        id, user_id, agent_type, status, input_data,
                        estimated_cost, created_at
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        task_id,
                        user_id,
                        agent_type,
                        "pending",
                        json.dumps(input_data),
                        estimated_cost,
                        datetime.utcnow().isoformat(),
                    )
                )
                await db.commit()

            return {
                "id": task_id,
                "user_id": user_id,
                "agent_type": agent_type,
                "status": "pending",
                "input_data": input_data,
                "estimated_cost": estimated_cost,
                "created_at": datetime.utcnow().isoformat(),
            }
        except Exception as e:
            print(f"!!!!!! CRITICAL ERROR IN create_task: {e} !!!!!!")
            import traceback
            traceback.print_exc()
            raise


    async def get_task(self, task_id: str, user_id: str) -> Optional[Dict]:
        """
        Get task details

        Args:
            task_id: Task ID
            user_id: User ID (for authorization check)

        Returns:
            Task dictionary or None if not found
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE id = ? AND user_id = ?
                """,
                (task_id, user_id)
            )
            row = await cursor.fetchone()

            if not row:
                return None

            task = dict(row)
            # Parse JSON fields
            task['input_data'] = json.loads(task['input_data'])
            if task['output_data']:
                task['output_data'] = json.loads(task['output_data'])
            if task['metadata']:
                task['metadata'] = json.loads(task['metadata'])

            return task

    async def list_user_tasks(
        self,
        user_id: str,
        limit: int = 50,
        offset: int = 0
    ) -> List[Dict]:
        """
        List user's tasks

        Args:
            user_id: User ID
            limit: Maximum number of tasks to return
            offset: Number of tasks to skip

        Returns:
            List of task dictionaries
        """
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM tasks
                WHERE user_id = ?
                ORDER BY created_at DESC
                LIMIT ? OFFSET ?
                """,
                (user_id, limit, offset)
            )
            rows = await cursor.fetchall()

            tasks = []
            for row in rows:
                task = dict(row)
                task['input_data'] = json.loads(task['input_data'])
                if task['output_data']:
                    task['output_data'] = json.loads(task['output_data'])
                if task['metadata']:
                    task['metadata'] = json.loads(task['metadata'])
                tasks.append(task)

            return tasks

    async def execute_task(self, task_id: str, user_id: str) -> Dict:
        """
        Execute a task with the appropriate agent

        Args:
            task_id: Task ID
            user_id: User ID (for authorization check)

        Returns:
            Updated task dictionary
        """
        # Get task
        task_data = await self.get_task(task_id, user_id)
        if not task_data:
            raise ValueError(f"Task {task_id} not found")

        if task_data['status'] != 'pending':
            raise ValueError(f"Task {task_id} is not pending (status: {task_data['status']})")

        # Update status to running
        await self._update_task_status(task_id, "running", started_at=datetime.utcnow().isoformat())

        try:
            # Get agent
            agent = get_agent(task_data['agent_type'])

            # Create agent task
            agent_task = AgentTask(
                id=task_id,
                user_id=user_id,
                agent_type=task_data['agent_type'],
                input_data=task_data['input_data'],
                estimated_cost=task_data['estimated_cost']
            )

            # Set initial progress message
            agent_name = agent.name
            await self.update_task_progress(task_id, f"🤖 Starting {agent_name}...")

            # Execute agent with timeout
            print(f"TaskService: Executing agent '{agent.name}' for task {task_id}...")

            # Update progress during execution
            await self.update_task_progress(task_id, f"⚙️ {agent_name} is analyzing your request...")

            # Execute with 5 minute timeout
            import asyncio
            try:
                result: AgentResult = await asyncio.wait_for(
                    agent.execute(agent_task),
                    timeout=300  # 5 minutes
                )
            except asyncio.TimeoutError:
                raise Exception("Task execution timed out after 5 minutes. Please try again with a simpler request.")

            # Update progress before saving
            await self.update_task_progress(task_id, f"✅ {agent_name} completed. Saving results...")

            # Save result
            completed_at = datetime.utcnow().isoformat()

            async with aiosqlite.connect(self.db_path) as db:
                # Update task
                await db.execute(
                    """
                    UPDATE tasks
                    SET status = ?,
                        output_data = ?,
                        actual_cost = ?,
                        completed_at = ?,
                        metadata = ?,
                        progress_message = NULL
                    WHERE id = ?
                    """,
                    (
                        "completed",
                        json.dumps({"output": result.output}),
                        result.actual_cost,
                        completed_at,
                        json.dumps(result.metadata),
                        task_id
                    )
                )

                # Save detailed result
                result_id = str(uuid.uuid4())
                await db.execute(
                    """
                    INSERT INTO task_results (
                        id, task_id, result_type, content, created_at
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    (
                        result_id,
                        task_id,
                        "text",
                        result.output,
                        completed_at
                    )
                )

                await db.commit()

            # Return updated task
            return await self.get_task(task_id, user_id)

        except Exception as e:
            # Create user-friendly error message
            error_msg = str(e)

            # Check for common API errors
            if "429" in error_msg or "RESOURCE_EXHAUSTED" in error_msg or "quota" in error_msg.lower():
                error_msg = "API quota exceeded. Please try again in a few minutes."
            elif "401" in error_msg or "authentication" in error_msg.lower():
                error_msg = "API authentication failed. Please check your API keys."
            elif "timeout" in error_msg.lower() or "timed out" in error_msg.lower():
                error_msg = "Request timed out. Please try again with a simpler request."
            elif "No such file or directory" in error_msg:
                error_msg = "Required dependency not found. Please contact support."

            print(f"❌ Task {task_id} failed: {error_msg}")
            print(f"   Original error: {e}")

            # Update status to failed
            await self._update_task_status(
                task_id,
                "failed",
                completed_at=datetime.utcnow().isoformat(),
                error=error_msg
            )

            # Return the failed task instead of raising
            return await self.get_task(task_id, user_id)

    async def get_task_result(self, task_id: str, user_id: str) -> Optional[Dict]:
        """
        Get task result

        Args:
            task_id: Task ID
            user_id: User ID (for authorization check)

        Returns:
            Result dictionary or None if not found/not completed
        """
        # Check task exists and belongs to user
        task = await self.get_task(task_id, user_id)
        if not task:
            return None

        if task['status'] not in ['completed', 'failed']:
            return {
                "status": task['status'],
                "message": f"Task is {task['status']}, result not available yet"
            }

        # Get result from task_results table
        async with aiosqlite.connect(self.db_path) as db:
            db.row_factory = aiosqlite.Row
            cursor = await db.execute(
                """
                SELECT * FROM task_results
                WHERE task_id = ?
                ORDER BY created_at DESC
                LIMIT 1
                """,
                (task_id,)
            )
            row = await cursor.fetchone()

            if not row:
                # Fallback to output_data in tasks table
                return {
                    "task_id": task_id,
                    "status": task['status'],
                    "output": task.get('output_data'),
                    "actual_cost": task.get('actual_cost'),
                    "metadata": task.get('metadata'),
                }

            result = dict(row)
            return {
                "task_id": task_id,
                "status": task['status'],
                "result_type": result['result_type'],
                "content": result['content'],
                "actual_cost": task.get('actual_cost'),
                "metadata": task.get('metadata'),
                "created_at": result['created_at']
            }

    async def update_task_payment_status(self, task_id: str, tx_hash: str, status: str):
        """Update the payment status of a task."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET payment_status = ?, payment_tx_hash = ?, paid_at = ?
                WHERE id = ?
                """,
                (status, tx_hash, datetime.utcnow().isoformat(), task_id)
            )
            await db.commit()
        print(f"✅ Updated payment status for task {task_id} to '{status}'")

    async def update_task_ciba_request(self, task_id: str, ciba_request_id: str):
        """Update the CIBA request ID for a task."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                """
                UPDATE tasks
                SET ciba_request_id = ?
                WHERE id = ?
                """,
                (ciba_request_id, task_id)
            )
            await db.commit()
        print(f"✅ Associated CIBA request {ciba_request_id} with task {task_id}")

    async def _update_task_status(
        self,
        task_id: str,
        status: str,
        started_at: Optional[str] = None,
        completed_at: Optional[str] = None,
        error: Optional[str] = None
    ):
        """Update task status"""
        async with aiosqlite.connect(self.db_path) as db:
            query = "UPDATE tasks SET status = ?"
            params = [status]

            if started_at:
                query += ", started_at = ?"
                params.append(started_at)

            if completed_at:
                query += ", completed_at = ?"
                params.append(completed_at)

            if error:
                query += ", metadata = json_object('error', ?)"
                params.append(error)

            # Clear progress message when task completes or fails
            if status in ['completed', 'failed']:
                query += ", progress_message = NULL"

            query += " WHERE id = ?"
            params.append(task_id)

            await db.execute(query, params)
            await db.commit()

    async def update_task_progress(
        self,
        task_id: str,
        progress_message: str
    ):
        """Update task progress message"""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(
                "UPDATE tasks SET progress_message = ? WHERE id = ?",
                (progress_message, task_id)
            )
            await db.commit()


# Singleton instance
_task_service = None

def get_task_service() -> TaskService:
    """Get or create TaskService singleton"""
    global _task_service
    if _task_service is None:
        _task_service = TaskService()
    return _task_service
