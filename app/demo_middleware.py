"""
Demo Mode Middleware - Simple approach with request interception
Automatically substitutes data in demo mode without changing the services
"""
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse
from app.demo_data import (
    DEMO_USER, DEMO_WALLET, DEMO_TASKS, DEMO_RESULTS, DEMO_PREVIEWS
)
import re


class DemoModeMiddleware(BaseHTTPMiddleware):
    """
    Intercepts requests in demo mode and returns mock data
    Activated via /?demo=true or cookie demo_mode=true
    """

    async def dispatch(self, request, call_next):
        # Check for demo mode activation
        # Check query params, cookies AND session
        is_demo = (
            request.query_params.get('demo') == 'true' or
            request.cookies.get('demo_mode') == 'true'
        )

        # If no params, check session (available after SessionMiddleware)
        if not is_demo and hasattr(request, 'session'):
            try:
                is_demo = request.session.get('demo_mode') == True
            except:
                is_demo = False

        if is_demo:
            # Activate demo mode in session
            if hasattr(request, 'session'):
                request.session['demo_mode'] = True
                request.session['user'] = DEMO_USER
                request.session['wallet_address'] = DEMO_WALLET['wallet_address']

            # Intercept API requests
            path = request.url.path
            method = request.method

            # --- AUTH ENDPOINTS ---
            if path == '/auth/user' and method == 'GET':
                return JSONResponse({
                    "authenticated": True,
                    "user": DEMO_USER
                })

            if path == '/api/me' and method == 'GET':
                return JSONResponse({
                    "user": DEMO_USER,
                    "authenticated": True
                })

            # --- WALLET ENDPOINTS ---
            if path == '/api/wallet/info' and method == 'GET':
                return JSONResponse({
                    "wallet_address": DEMO_WALLET['wallet_address'],
                    "connected": True,
                    "usdc_balance": DEMO_WALLET['usdc_balance'],
                    "chain": "base-sepolia",
                    "chain_id": 84532
                })

            # --- TASK ENDPOINTS ---
            if path == '/api/tasks/' and method == 'GET':
                return JSONResponse({
                    "tasks": DEMO_TASKS,
                    "total": len(DEMO_TASKS)
                })

            if path == '/api/tasks/' and method == 'POST':
                # Create a new task (return a pending task)
                return JSONResponse(
                    DEMO_TASKS[2],  # pending task
                    status_code=201
                )

            # GET /api/tasks/{task_id}
            task_match = re.match(r'/api/tasks/(demo_task_\d+)$', path)
            if task_match and method == 'GET':
                task_id = task_match.group(1)
                task = next((t for t in DEMO_TASKS if t['id'] == task_id), None)
                if task:
                    return JSONResponse(task)

            # POST /api/tasks/{task_id}/start
            start_match = re.match(r'/api/tasks/(demo_task_\d+)/start$', path)
            if start_match and method == 'POST':
                task_id = start_match.group(1)
                task = next((t for t in DEMO_TASKS if t['id'] == task_id), None)
                if task:
                    # Change status to running (simulation)
                    running_task = task.copy()
                    running_task['status'] = 'running'
                    return JSONResponse(running_task)

            # GET /api/tasks/{task_id}/result
            result_match = re.match(r'/api/tasks/(demo_task_\d+)/result$', path)
            if result_match and method == 'GET':
                task_id = result_match.group(1)
                task = next((t for t in DEMO_TASKS if t['id'] == task_id), None)

                if not task:
                    return JSONResponse(
                        {"error": "Task not found"},
                        status_code=404
                    )

                # If the task is not completed
                if task['status'] != 'completed':
                    return JSONResponse({
                        "status": task['status'],
                        "message": f"Task is {task['status']}, result not available yet"
                    })

                # Check payment: either payment_status=paid, or marked as paid in session
                demo_paid_tasks = []
                if hasattr(request, 'session'):
                    demo_paid_tasks = request.session.get('demo_paid_tasks', [])
                is_paid = task['payment_status'] == 'paid' or task_id in demo_paid_tasks

                # If not paid - return 402 with preview
                if not is_paid:
                    preview = DEMO_PREVIEWS.get(task_id)

                    return JSONResponse(
                        {
                            "error": "Payment Required",
                            "status_code": 402,
                            "preview": preview,
                            "payment": {
                                "amount_usdc": str(int(task['actual_cost'] * 1000000)),  # Convert to USDC units
                                "domain": {
                                    "name": "USDC",
                                    "version": "2",
                                    "chainId": 84532,
                                    "verifyingContract": "0x036CbD53842c5426634e7929541eC2318f3dCF7e"
                                },
                                "message": {
                                    "from": DEMO_WALLET['wallet_address'],
                                    "to": "0x742d35Cc6634C0532925a3b844Bc9e7595f0bEb1",
                                    "value": str(int(task['actual_cost'] * 1000000)),
                                    "validAfter": 0,
                                    "validBefore": 2000000000,
                                    "nonce": "0xdemo1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab"
                                }
                            },
                            "message": f"Payment of ${task['actual_cost']:.4f} USDC required to access result"
                        },
                        status_code=402
                    )

                # Paid - return result
                result = DEMO_RESULTS.get(task_id)
                if result:
                    return JSONResponse(result)

            # --- PAYMENT ENDPOINTS ---
            if path == '/api/payments/authorize' and method == 'POST':
                # Get task_id from body
                try:
                    body = await request.json()
                    task_id = body.get('task_id', 'demo_task_002')
                except:
                    task_id = 'demo_task_002'

                # Mark task as paid in session
                if hasattr(request, 'session'):
                    if 'demo_paid_tasks' not in request.session:
                        request.session['demo_paid_tasks'] = []
                    if task_id not in request.session['demo_paid_tasks']:
                        request.session['demo_paid_tasks'].append(task_id)

                # In demo mode, payment is always successful
                return JSONResponse({
                    "success": True,
                    "message": "Demo payment processed",
                    "tx_hash": "0xdemo1234567890abcdef1234567890abcdef1234567890abcdef1234567890ab",
                    "task_id": task_id
                })

            # --- EXIT DEMO ENDPOINT ---
            if path == '/api/demo/exit' and method == 'POST':
                # Clear demo mode from session
                if hasattr(request, 'session'):
                    request.session['demo_mode'] = False
                    request.session.pop('user', None)
                    request.session.pop('wallet_address', None)

                response = JSONResponse({"success": True, "message": "Exited demo mode"})
                # Delete cookie
                response.delete_cookie('demo_mode')
                return response

            # --- AGENTS ENDPOINT ---
            if path == '/api/agents' and method == 'GET':
                return JSONResponse({
                    "agents": {
                        "factcheck": {
                            "name": "FactCheck Agent",
                            "description": "Multi-stage fact verification with source citation",
                            "base_cost": 0.002
                        },
                        "ai-travel-planner": {
                            "name": "AI Travel Planner",
                            "description": "Flight search, hotel recommendations, itinerary generation",
                            "base_cost": 0.0015
                        }
                    }
                })

        # If not demo or endpoint not intercepted - normal processing
        response = await call_next(request)

        # Add cookie for demo mode if activated
        if is_demo:
            response.set_cookie(
                key='demo_mode',
                value='true',
                max_age=3600,  # 1 hour
                httponly=False,
                samesite='lax'
            )

        return response
