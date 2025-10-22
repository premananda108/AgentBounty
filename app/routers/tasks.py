"""
Task Router - API endpoints for task management
"""
from fastapi import APIRouter, HTTPException, Depends, BackgroundTasks, Response, Request
from pydantic import BaseModel, Field
from typing import Dict, List, Optional

from app.services.task_service import get_task_service, TaskService
from app.services.payment_service import get_payment_service, PaymentService
from app.services.async_approval_service import get_async_approval_service, AsyncApprovalService
from app.services.auth0_service import auth0_service
from app.routers.auth import require_auth, require_mcp_auth
from app.config import settings

router = APIRouter(prefix="/api/tasks", tags=["tasks"])


# Request/Response Models
class CreateTaskRequest(BaseModel):
    """Request model for creating a task"""
    agent_type: str = Field(..., description="Type of agent to use (e.g., 'research')")
    input_data: Dict = Field(..., description="Input data for the agent")

    class Config:
        json_schema_extra = {
            "example": {
                "agent_type": "research",
                "input_data": {
                    "query": "What are the latest developments in AI agent frameworks?",
                    "max_results": 5
                }
            }
        }


class TaskResponse(BaseModel):
    """Response model for task operations"""
    id: str
    user_id: str
    agent_type: str
    status: str
    input_data: Dict
    estimated_cost: float
    actual_cost: Optional[float] = None
    created_at: str
    started_at: Optional[str] = None
    completed_at: Optional[str] = None
    output_data: Optional[Dict] = None
    metadata: Optional[Dict] = None
    payment_status: Optional[str] = None
    progress_message: Optional[str] = None


class TaskListResponse(BaseModel):
    """Response model for task list"""
    tasks: List[TaskResponse]
    total: int


class TaskResultResponse(BaseModel):
    """Response model for task result"""
    task_id: str
    status: str
    result_type: Optional[str] = None
    content: Optional[str] = None
    actual_cost: Optional[float] = None
    metadata: Optional[Dict] = None
    message: Optional[str] = None


# Endpoints
@router.post("/", response_model=TaskResponse, status_code=201)
async def create_task(
    request_obj: Request,
    data: CreateTaskRequest,
    user: dict = Depends(require_mcp_auth),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Create a new task

    **Requires authentication** (Auth0 session or MCP service token).

    For MCP clients: Include headers:
    - Authorization: Bearer <MCP_SERVICE_TOKEN>
    - X-User-ID: <user_id>
    - X-User-Email: <user_email> (optional)
    - X-User-Name: <user_name> (optional)

    Wallet connection is optional at creation time, but will be required for payment.

    - **agent_type**: Type of agent to use (e.g., 'research')
    - **input_data**: Input parameters for the agent

    Returns the created task with estimated cost
    """
    # Get Auth0 user ID
    user_id = user.get('sub')
    print(f"🔍 DEBUG create_task: user dict = {user}")
    print(f"🔍 DEBUG create_task: user_id (sub) = {user_id}")

    # Check if wallet is connected (optional at this stage)
    wallet_address = request_obj.session.get('wallet_address')
    print(f"🔍 DEBUG create_task: wallet_address from session = {wallet_address}")

    if not wallet_address:
        # Try to get from Auth0
        print(f"🔍 DEBUG create_task: Trying to get wallet from Auth0 for user_id = {user_id}")
        wallet_address = await auth0_service.get_user_wallet(user_id)
        print(f"🔍 DEBUG create_task: wallet_address from Auth0 = {wallet_address}")

        if wallet_address:
            # Cache in session if found
            request_obj.session['wallet_address'] = wallet_address
            print(f"✅ DEBUG create_task: Cached wallet_address in session")
        else:
            print(f"ℹ️  DEBUG create_task: No wallet connected yet for user {user_id} (optional at creation)")

    try:
        task = await task_service.create_task(
            user_id=user_id,
            agent_type=data.agent_type,
            input_data=data.input_data
        )
        return TaskResponse(**task)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to create task: {str(e)}")


@router.get("/", response_model=TaskListResponse)
async def list_tasks(
    limit: int = 50,
    offset: int = 0,
    user: dict = Depends(require_auth),
    task_service: TaskService = Depends(get_task_service)
):
    """
    List user's tasks

    **Requires Auth0 authentication.**

    - **limit**: Maximum number of tasks to return (default: 50)
    - **offset**: Number of tasks to skip (default: 0)

    Returns a list of tasks ordered by creation date (newest first)
    """
    user_id = user.get('sub')

    try:
        tasks = await task_service.list_user_tasks(
            user_id=user_id,
            limit=limit,
            offset=offset
        )
        return TaskListResponse(
            tasks=[TaskResponse(**task) for task in tasks],
            total=len(tasks)
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list tasks: {str(e)}")


@router.get("/{task_id}", response_model=TaskResponse)
async def get_task(
    task_id: str,
    user: dict = Depends(require_auth),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Get task details by ID

    **Requires Auth0 authentication.**

    Returns detailed information about a specific task
    """
    user_id = user.get('sub')

    task = await task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    return TaskResponse(**task)


@router.post("/{task_id}/start", response_model=TaskResponse)
async def start_task(
    task_id: str,
    background_tasks: BackgroundTasks,
    user: dict = Depends(require_auth),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Start task execution

    **Requires Auth0 authentication.**

    Initiates the agent execution in the background.
    The task status will change to 'running', then 'completed' or 'failed'.

    Use GET /api/tasks/{task_id} to check status.
    Use GET /api/tasks/{task_id}/result to get the result when completed.
    """
    user_id = user.get('sub')

    # Verify task exists and belongs to user
    task = await task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task['status'] != 'pending':
        raise HTTPException(
            status_code=400,
            detail=f"Task is not pending (current status: {task['status']})"
        )

    # Execute task in background
    background_tasks.add_task(task_service.execute_task, task_id, user_id)

    # Return task with updated status
    return TaskResponse(**task)


@router.get("/{task_id}/result")
async def get_task_result(
    task_id: str,
    response: Response,
    request_obj: Request,
    user: dict = Depends(require_auth),
    task_service: TaskService = Depends(get_task_service),
    payment_service: PaymentService = Depends(get_payment_service),
    async_approval_service: AsyncApprovalService = Depends(get_async_approval_service)
):
    """
    Get task result (X402 Protocol enabled)

    **Requires Auth0 authentication.**

    Returns the result if task is completed AND paid.
    Returns HTTP 402 Payment Required with payment details if not paid.
    Returns status message if task is still running or pending.

    **Payment Flow:**
    1. GET /api/tasks/{id}/result → Returns 402 with payment requirements
    2. User signs authorization off-chain
    3. POST /api/payments/authorize → Processes payment
    4. GET /api/tasks/{id}/result → Returns actual result
    """
    user_id = user.get('sub')
    print(f"🔍 DEBUG get_task_result: task_id={task_id}, user_id={user_id}")

    # Get wallet address from session or Auth0
    user_address = request_obj.session.get('wallet_address')
    print(f"🔍 DEBUG get_task_result: wallet from session={user_address}")

    if not user_address:
        user_address = await auth0_service.get_user_wallet(user_id)
        print(f"🔍 DEBUG get_task_result: wallet from Auth0={user_address}")

    # Get task
    task = await task_service.get_task(task_id, user_id)
    if not task:
        print(f"❌ DEBUG get_task_result: Task {task_id} not found for user {user_id}")
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    print(f"🔍 DEBUG get_task_result: task status={task['status']}, payment_status={task.get('payment_status')}")

    # Check if task is completed
    if task['status'] == 'failed':
        # Failed tasks - return error, NO PAYMENT REQUIRED
        error_message = 'Task execution failed'

        # Try to get error from metadata
        if task.get('metadata') and isinstance(task['metadata'], dict):
            error_message = task['metadata'].get('error', error_message)

        return {
            "status": "failed",
            "error": error_message,
            "message": "Task failed. No payment required."
        }

    if task['status'] != 'completed':
        return {
            "status": task['status'],
            "message": f"Task is {task['status']}, result not available yet"
        }

    # Check payment status (only for completed tasks)
    payment_status = task.get('payment_status')
    actual_cost = task.get('actual_cost', task.get('estimated_cost', 0))
    print(f"🔍 DEBUG get_task_result: payment_status={payment_status}, actual_cost={actual_cost}")

    # If task is free (cost = 0), return result immediately without payment
    if actual_cost == 0:
        print(f"✅ DEBUG get_task_result: Free task, returning result without payment")
        result = await task_service.get_task_result(task_id, user_id)
        if not result:
            raise HTTPException(status_code=500, detail="Result not found despite task being completed")
        return result

    if payment_status != 'paid':
        print(f"🔍 DEBUG get_task_result: Task not paid, checking wallet")
        # Check if user has wallet connected (required for payment)
        if not user_address:
            print(f"❌ DEBUG get_task_result: No wallet connected, returning 400")
            raise HTTPException(
                status_code=400,
                detail="Please connect your wallet to view paid results. Use POST /api/wallet/connect to connect your wallet."
            )
        # Get result preview (first 200 chars)
        preview = None
        result = await task_service.get_task_result(task_id, user_id)
        if result and result.get('content'):
            content = result['content']
            # Get first 200 characters, cut at word boundary
            if len(content) > 200:
                preview = content[:200].rsplit(' ', 1)[0] + '...'
            else:
                preview = content

        # Return 402 Payment Required with X402 headers

        # Check if async approval is required (for payments >= threshold)
        requires_approval = actual_cost >= settings.APPROVAL_THRESHOLD_USD

        if requires_approval:
            # Check if approval request already exists
            approval_request_id = task.get('ciba_request_id')  # DB column name kept for compatibility

            if not approval_request_id:
                # Initiate async approval
                print(f"💳 Initiating async approval for task {task_id}, amount ${actual_cost}")

                approval_result = await async_approval_service.initiate_payment_approval(
                    task_id=task_id,
                    user_id=user_id,
                    amount=actual_cost,
                    task_description=f"Task result payment"
                )

                # Check if approval initiation failed
                if approval_result.get('status') == 'failed':
                    print(f"❌ Approval initiation failed: {approval_result.get('error')}")
                    response.status_code = 500
                    return {
                        "error": "Approval Initiation Failed",
                        "status_code": 500,
                        "message": f"Failed to initiate payment approval: {approval_result.get('error')}",
                        "hint": "Please try again or contact support"
                    }

                # Store approval request ID in task
                await task_service.update_task_ciba_request(task_id, approval_result['ciba_request_id'])

                # Return 402 with approval requirement
                response.status_code = 402
                response.headers["Content-Type"] = "application/json"

                return {
                    "error": "Payment Approval Required",
                    "status_code": 402,
                    "requires_ciba": True,  # Keep for backward compatibility
                    "ciba_request_id": approval_result['ciba_request_id'],  # Keep for backward compatibility
                    "requires_approval": True,
                    "approval_request_id": approval_result['ciba_request_id'],
                    "amount": actual_cost,
                    "message": f"Payment of ${actual_cost:.4f} USDC requires approval. Check your email.",
                    "expires_at": approval_result.get('expires_at'),
                    "instructions": {
                        "1": "Check your email for approval request",
                        "2": "Click 'Approve Payment' in the email",
                        "3": "Return here - approval will be detected automatically",
                        "4": "After approval, proceed with payment signature"
                    }
                }
            else:
                # Check approval status
                approval_status = await async_approval_service.check_approval_status(approval_request_id)

                if approval_status and approval_status['status'] == 'approved':
                    # Approval confirmed, proceed with payment signature requirement
                    print(f"✅ Payment approved for task {task_id}, proceeding with payment signature")
                    pass  # Fall through to payment signature flow below
                elif approval_status and approval_status['status'] in ['denied', 'expired']:
                    # Approval denied or expired
                    response.status_code = 403
                    return {
                        "error": "Payment Approval Denied",
                        "status_code": 403,
                        "ciba_status": approval_status['status'],  # Keep for backward compatibility
                        "approval_status": approval_status['status'],
                        "message": f"Payment approval was {approval_status['status']}"
                    }
                else:
                    # Still pending
                    response.status_code = 402
                    return {
                        "error": "Awaiting Payment Approval",
                        "status_code": 402,
                        "requires_ciba": True,  # Keep for backward compatibility
                        "ciba_request_id": approval_request_id,  # Keep for backward compatibility
                        "ciba_status": "pending",  # Keep for backward compatibility
                        "requires_approval": True,
                        "approval_request_id": approval_request_id,
                        "approval_status": "pending",
                        "amount": actual_cost,
                        "message": "Waiting for payment approval via email"
                    }

        # Create payment requirements (either no approval needed, or approval already confirmed)
        payment_req = payment_service.create_payment_requirements(
            task_id=task_id,
            amount_usd=actual_cost,
            user_address=user_address
        )

        # Set X402 headers
        for header_name, header_value in payment_req['headers'].items():
            response.headers[header_name] = header_value

        # Set standard headers
        response.status_code = 402
        response.headers["Content-Type"] = "application/json"

        return {
            "error": "Payment Required",
            "status_code": 402,
            "payment": payment_req,
            "preview": preview,  # Preview of the result
            "ciba_approved": requires_approval,  # Keep for backward compatibility
            "approval_confirmed": requires_approval,  # Indicate approval was already confirmed if required
            "message": f"Payment of ${actual_cost:.4f} USDC required to access result",
            "instructions": {
                "1": "Sign authorization off-chain using provided domain and message",
                "2": "POST /api/payments/authorize with signature",
                "3": "GET /api/tasks/{id}/result to retrieve result"
            }
        }

    # Payment confirmed - return result
    result = await task_service.get_task_result(task_id, user_id)
    if not result:
        raise HTTPException(status_code=500, detail="Result not found despite task being completed")

    return result


@router.delete("/{task_id}", status_code=204)
async def delete_task(
    task_id: str,
    user: dict = Depends(require_auth),
    task_service: TaskService = Depends(get_task_service)
):
    """
    Delete a task

    **Requires Auth0 authentication.**

    Only pending tasks can be deleted.
    Running or completed tasks cannot be deleted.
    """
    user_id = user.get('sub')

    task = await task_service.get_task(task_id, user_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")

    if task['status'] not in ['pending', 'failed']:
        raise HTTPException(
            status_code=400,
            detail=f"Cannot delete task with status: {task['status']}"
        )

    # TODO: Implement task deletion in TaskService
    raise HTTPException(status_code=501, detail="Task deletion not yet implemented")
