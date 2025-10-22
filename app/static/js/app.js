const initializeApp = async (user) => {
    renderHeader(true, user);
    renderTaskCreator(true);

    // In demo mode, skip wallet connection check
    if (window.isDemoMode && window.isDemoMode()) {
        console.log('🎭 Demo mode: skipping wallet connection check');
        // Demo wallet is already set in demo.js
    } else {
        checkWalletConnection();
    }

    // Load tasks regardless of wallet connection status
    loadTasks();
};

let pollingInterval = null;

const loadTasks = async () => {
    try {
        // Load tasks regardless of wallet connection status
        // Wallet is only required for payment, not for viewing tasks
        const tasks = await listTasks();
        renderTaskList(tasks.tasks);

        // Check for running tasks
        const hasRunningTasks = tasks.tasks.some(t => t.status === 'running');

        // Update UI state for running tasks
        if (window.updateUIForRunningTask) {
            window.updateUIForRunningTask(hasRunningTasks);
        }

        tasks.tasks.forEach(task => {
            if (task.status === 'completed') {
                handleCompletedTask(task);
            }
        });

        // Start/stop polling based on running tasks
        if (hasRunningTasks && !pollingInterval) {
            startTaskPolling();
        } else if (!hasRunningTasks && pollingInterval) {
            stopTaskPolling();
        }
    } catch (error) {
        console.error('Failed to load tasks:', error);
    }
};

const startTaskPolling = () => {
    if (pollingInterval) return;

    console.log('Starting task polling...');
    pollingInterval = setInterval(async () => {
        await loadTasks();
    }, 3000); // Poll every 3 seconds
};

const stopTaskPolling = () => {
    if (pollingInterval) {
        console.log('Stopping task polling...');
        clearInterval(pollingInterval);
        pollingInterval = null;
    }
};

const handleCompletedTask = async (task) => {
    const resultContainer = document.getElementById(`task-result-${task.id}`);
    if (!resultContainer) {
        console.log(`Result container not found for task ${task.id}`);
        return;
    }

    try {
        console.log(`Fetching result for task ${task.id}, wallet: ${window.userAddress}`);
        const result = await getTaskResult(task.id, window.userAddress);
        console.log('Task result response:', result);

        if (result.status_code === 403) {
            // CIBA approval denied or expired
            console.log('CIBA approval denied/expired');
            const statusText = result.ciba_status === 'expired' ? 'Expired' : 'Denied';
            resultContainer.innerHTML = `
                <div class="bg-red-50 rounded p-3 border border-red-200">
                    <p class="text-sm font-medium mb-2 text-red-800">❌ Payment Approval ${statusText}</p>
                    <p class="text-xs text-red-700 mb-2">${result.message || 'Payment approval was denied or expired'}</p>
                    ${result.ciba_status === 'expired' ? `
                        <p class="text-xs text-gray-600">Please refresh the page and try again to view the result.</p>
                    ` : ''}
                </div>`;
            return;
        } else if (result.status_code === 402) {
            // Check if CIBA approval is required
            if (result.requires_ciba) {
                console.log('CIBA approval required');

                if (result.ciba_status === 'pending') {
                    // Show preview if available
                    let previewHTML = '';
                    if (result.preview) {
                        const formattedPreview = formatMarkdownContent(result.preview);
                        previewHTML = `
                            <div class="mb-2 p-2 bg-white rounded border border-yellow-300">
                                <p class="text-xs font-medium text-gray-700 mb-1">📄 Preview:</p>
                                <div class="text-xs text-gray-600 prose prose-sm max-w-none">${formattedPreview}</div>
                            </div>`;
                    }

                    // Show waiting for CIBA approval
                    resultContainer.innerHTML = `
                        <div class="bg-yellow-50 rounded p-3 border border-yellow-200">
                            <p class="text-sm font-medium mb-2 text-yellow-800">⏳ Waiting for Payment Approval</p>
                            <p class="text-xs text-yellow-700 mb-2">${result.message}</p>
                            ${previewHTML}
                            <p class="text-xs text-gray-600 mt-2">📧 Check your email and click the approval link</p>
                        </div>`;

                    // Start polling for CIBA approval
                    pollForCIBAApproval(result.ciba_request_id, task);
                } else {
                    // Show preview if available
                    let previewHTML = '';
                    if (result.preview) {
                        const formattedPreview = formatMarkdownContent(result.preview);
                        previewHTML = `
                            <div class="mt-2 p-2 bg-white rounded border border-blue-300">
                                <p class="text-xs font-medium text-gray-700 mb-1">📄 Preview:</p>
                                <div class="text-xs text-gray-600 prose prose-sm max-w-none">${formattedPreview}</div>
                            </div>`;
                    }

                    // Initial CIBA request - show message and start polling
                    resultContainer.innerHTML = `
                        <div class="bg-blue-50 rounded p-3 border border-blue-200">
                            <p class="text-sm font-medium mb-2 text-blue-800">🔐 Payment Approval Required</p>
                            <p class="text-xs text-blue-700 mb-2">${result.message}</p>
                            <div class="text-xs text-gray-600">
                                <p>💳 Amount: $${result.amount}</p>
                                <p>⏰ Expires: ${new Date(result.expires_at).toLocaleTimeString()}</p>
                            </div>
                            ${previewHTML}
                            <div class="mt-3 p-3 bg-white rounded border border-blue-300">
                                <p class="text-xs font-semibold text-blue-900 mb-1">📧 Check Your Email</p>
                                <ol class="text-xs text-blue-800 space-y-1 ml-4 list-decimal">
                                    <li>We sent a confirmation link to your email</li>
                                    <li>Check your inbox (and spam folder)</li>
                                    <li>Click "Approve Payment" in the email</li>
                                    <li>Return here - approval will be detected automatically</li>
                                </ol>
                                <p class="text-xs text-gray-600 mt-2">💡 Email may take 1-2 minutes to arrive</p>
                            </div>
                        </div>`;

                    // Start polling for CIBA approval
                    pollForCIBAApproval(result.ciba_request_id, task);
                }
            } else {
                // Normal payment required (no CIBA)
                console.log('Payment required, showing payment button');

                // Show preview if available
                let previewHTML = '';
                if (result.preview) {
                    const formattedPreview = formatMarkdownContent(result.preview);
                    previewHTML = `
                        <div class="mb-3 p-3 bg-gray-50 rounded border border-gray-200">
                            <p class="text-xs font-medium text-gray-700 mb-1">📄 Preview:</p>
                            <div class="text-xs text-gray-600 prose prose-sm max-w-none">${formattedPreview}</div>
                            <p class="text-xs text-blue-600 mt-2">💳 Pay to see full result</p>
                        </div>`;
                }

                resultContainer.innerHTML = `
                    ${previewHTML}
                    <button id="view-result-button-${task.id}" class="w-full px-4 py-2 bg-blue-600 hover:bg-blue-700 text-white text-sm font-medium rounded-lg transition-colors">
                        🔓 View Full Result (Payment Required)
                    </button>`;

                const paymentButton = document.getElementById(`view-result-button-${task.id}`);
                if (paymentButton) {
                    paymentButton.addEventListener('click', () => {
                        console.log('Payment button clicked');
                        promptForPayment(result, task);
                    });
                }
            }
        } else if (result.status === 'failed') {
            // Task failed - show error message, NO PAYMENT
            console.log('Task failed:', result.error);
            resultContainer.innerHTML = `
                <div class="bg-red-50 rounded p-3 border border-red-200">
                    <p class="text-sm font-medium mb-1 text-red-800">❌ Task Failed</p>
                    <p class="text-xs text-red-700">${result.error || result.message || 'Task execution failed'}</p>
                    <p class="text-xs text-gray-600 mt-2">💡 No payment required for failed tasks</p>
                </div>`;
        } else if (result.content) {
            console.log('Showing result content');
            const formattedContent = formatMarkdownContent(result.content);
            resultContainer.innerHTML = `<div class="bg-gray-50 rounded p-3"><p class="text-sm font-medium mb-2">Result:</p><div class="prose prose-sm max-w-none">${formattedContent}</div></div>`;
        } else {
            console.log('Result status:', result.status, result.message);
            resultContainer.innerHTML = `<p class="text-sm text-gray-600">${result.message || 'Result not ready'}</p>`;
        }
    } catch (error) {
        console.error('Failed to get task result:', error);

        // Check if it's a wallet connection error
        if (error.message && error.message.includes('wallet')) {
            resultContainer.innerHTML = `
                <div class="bg-yellow-50 rounded p-3 border border-yellow-300">
                    <p class="text-sm font-medium mb-2 text-yellow-800">💳 Wallet Required</p>
                    <p class="text-xs text-yellow-700 mb-3">${error.message}</p>
                    <button onclick="window.location.reload()" class="text-xs px-3 py-1.5 bg-yellow-500 hover:bg-yellow-600 text-white font-semibold rounded shadow-sm">
                        Refresh to Connect Wallet
                    </button>
                </div>`;
        } else {
            resultContainer.innerHTML = `<p class="text-red-500 text-sm">Failed to load result: ${error.message}</p>`;
        }
    }
};

// Escape HTML to prevent XSS
const escapeHtml = (text) => {
    const div = document.createElement('div');
    div.textContent = text;
    return div.innerHTML;
};

// Poll for CIBA approval
const pollForCIBAApproval = async (cibaRequestId, task, maxAttempts = 60) => {
    console.log(`Starting CIBA polling for ${cibaRequestId}`);

    for (let attempt = 0; attempt < maxAttempts; attempt++) {
        try {
            const status = await checkCIBAStatus(cibaRequestId);
            console.log(`CIBA poll attempt ${attempt + 1}/${maxAttempts}:`, status.status);

            if (status.status === 'approved') {
                console.log('✅ CIBA approved! Reloading task result...');
                await handleCompletedTask(task);
                return;
            }

            if (status.status === 'denied' || status.status === 'expired') {
                console.log(`❌ CIBA ${status.status}`);
                const resultContainer = document.getElementById(`task-result-${task.id}`);
                if (resultContainer) {
                    resultContainer.innerHTML = `<div class="bg-red-50 rounded p-3 border border-red-200">
                        <p class="text-sm text-red-800">Payment approval ${status.status}</p>
                    </div>`;
                }
                return;
            }

            // Wait 5 seconds before next poll
            await new Promise(resolve => setTimeout(resolve, 5000));
        } catch (error) {
            console.error('CIBA polling error:', error);
            break;
        }
    }

    console.log('CIBA polling timeout');
};

// Export to window for access from ui.js
window.handleCompletedTask = handleCompletedTask;

const promptForPayment = (paymentReq, task) => {
    console.log('promptForPayment called with:', paymentReq);

    // paymentReq contains { payment: { amount_usdc, domain, message, ... }, ... }
    const payment = paymentReq.payment || paymentReq;
    console.log('Extracted payment object:', payment);

    // Check if amount_usdc exists
    if (!payment.amount_usdc) {
        console.error('amount_usdc is missing from payment data:', payment);
        console.error('Full paymentReq:', paymentReq);
        alert('Payment data is invalid. Please try again.');
        return;
    }

    console.log('Formatting amount_usdc:', payment.amount_usdc);
    const formattedAmount = ethers.utils.formatUnits(payment.amount_usdc, 6);
    console.log('Formatted amount:', formattedAmount);

    showPaymentModal(formattedAmount);

    const approveButton = document.getElementById('approve-payment-button');
    const cancelButton = document.getElementById('cancel-payment-button');

    approveButton.onclick = async () => {
        approveButton.disabled = true;
        approveButton.textContent = 'Processing...';

        try {
            // Check if we're in demo mode
            const isDemo = window.isDemoMode && window.isDemoMode();

            if (isDemo) {
                // Demo mode - simulate payment without MetaMask
                console.log('🎭 Demo mode: Simulating payment...');
                approveButton.textContent = 'Processing Payment...';

                await new Promise(resolve => setTimeout(resolve, 1000)); // Simulate delay

                const paymentResponse = await fetch('/api/payments/authorize?demo=true', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json'
                    },
                    body: JSON.stringify({
                        task_id: task.id
                    })
                });

                const paymentResult = await paymentResponse.json();
                console.log('Demo payment result:', paymentResult);

                if (!paymentResult.success) {
                    throw new Error(paymentResult.error || 'Payment failed');
                }

                // Show success and load result
                approveButton.textContent = 'Loading Result...';
                const finalResult = await getTaskResult(task.id, window.userAddress);

                const resultContainer = document.getElementById(`task-result-${task.id}`);
                const formattedContent = formatMarkdownContent(finalResult.content);

                resultContainer.innerHTML = `
                    <div class="bg-gray-50 rounded p-3">
                        <p class="text-xs text-green-600 mb-2">✅ Demo payment completed</p>
                        <p class="text-sm font-medium mb-2">Result:</p>
                        <div class="prose prose-sm max-w-none">${formattedContent}</div>
                    </div>`;

                hidePaymentModal();
                return;
            }

            // Real mode - use MetaMask
            if (!window.ethereum) {
                throw new Error('MetaMask not detected. Please install MetaMask.');
            }

            const provider = new ethers.providers.Web3Provider(window.ethereum);
            const network = await provider.getNetwork();
            console.log('Current network:', network);

            if (network.chainId !== 84532) {
                console.log('Wrong network, switching to Base Sepolia...');
                approveButton.textContent = 'Switching Network...';

                try {
                    // Try to switch to Base Sepolia
                    await window.ethereum.request({
                        method: 'wallet_switchEthereumChain',
                        params: [{ chainId: '0x14a34' }], // 84532 in hex
                    });
                } catch (switchError) {
                    // This error code indicates that the chain has not been added to MetaMask
                    if (switchError.code === 4902) {
                        console.log('Base Sepolia not found, adding network...');
                        await window.ethereum.request({
                            method: 'wallet_addEthereumChain',
                            params: [{
                                chainId: '0x14a34', // 84532 in hex
                                chainName: 'Base Sepolia',
                                nativeCurrency: {
                                    name: 'Ethereum',
                                    symbol: 'ETH',
                                    decimals: 18
                                },
                                rpcUrls: ['https://sepolia.base.org'],
                                blockExplorerUrls: ['https://sepolia.basescan.org']
                            }]
                        });
                    } else {
                        throw switchError;
                    }
                }

                // Refresh signer after network switch
                window.signer = provider.getSigner();
                approveButton.textContent = 'Processing...';
            }

            const domain = payment.domain;
            const types = {
                TransferWithAuthorization: [
                    { name: 'from', type: 'address' },
                    { name: 'to', type: 'address' },
                    { name: 'value', type: 'uint256' },
                    { name: 'validAfter', type: 'uint256' },
                    { name: 'validBefore', type: 'uint256' },
                    { name: 'nonce', type: 'bytes32' }
                ]
            };
            const message = payment.message;

            console.log('Requesting signature...');
            const signature = await window.signer._signTypedData(domain, types, message);
            console.log('Signature received:', signature);

            const sig = ethers.utils.splitSignature(signature);
            console.log('Split signature:', sig);

            // Process payment via POST /api/payments/authorize
            approveButton.textContent = 'Processing Payment...';

            const paymentData = {
                task_id: task.id,
                from_address: window.userAddress,
                amount_usdc: payment.amount_usdc,
                valid_after: payment.message.validAfter,
                valid_before: payment.message.validBefore,
                nonce: payment.message.nonce,
                signature: {
                    v: sig.v,
                    r: sig.r,
                    s: sig.s
                }
            };

            console.log('Sending payment authorization:', paymentData);

            const paymentResponse = await fetch('/api/payments/authorize', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(paymentData)
            });

            if (!paymentResponse.ok) {
                const errorData = await paymentResponse.json();
                throw new Error(errorData.detail || 'Payment failed');
            }

            const paymentResult = await paymentResponse.json();
            console.log('Payment result:', paymentResult);

            if (!paymentResult.success) {
                throw new Error(paymentResult.error || 'Payment failed');
            }

            // Show success message with transaction hash
            if (paymentResult.tx_hash) {
                console.log(`✅ Payment successful! TX: ${paymentResult.tx_hash}`);
            }

            // Now fetch the result
            approveButton.textContent = 'Loading Result...';
            const finalResult = await getTaskResult(task.id, window.userAddress);

            const resultContainer = document.getElementById(`task-result-${task.id}`);

            // Show result with transaction info
            const formattedContent = formatMarkdownContent(finalResult.content);
            let resultHTML = '<div class="bg-gray-50 rounded p-3">';
            if (paymentResult.tx_hash) {
                resultHTML += `<p class="text-xs text-green-600 mb-2">✅ Payment confirmed: <a href="https://sepolia.basescan.org/tx/${paymentResult.tx_hash}" target="_blank" class="underline">View TX</a></p>`;
            }
            resultHTML += `<p class="text-sm font-medium mb-2">Result:</p><div class="prose prose-sm max-w-none">${formattedContent}</div></div>`;

            resultContainer.innerHTML = resultHTML;
            hidePaymentModal();
        } catch (error) {
            console.error('Payment failed:', error);
            alert('Payment failed. Please try again.');
        } finally {
            approveButton.disabled = false;
            approveButton.textContent = 'Approve Payment';
        }
    };

    cancelButton.onclick = () => {
        hidePaymentModal();
    };
};

// Start a timer to reload tasks periodically
let taskInterval;
const startTaskUpdates = () => {
    if (taskInterval) clearInterval(taskInterval);
    taskInterval = setInterval(loadTasks, 5000);
};

const stopTaskUpdates = () => {
    if (taskInterval) clearInterval(taskInterval);
};

// Simple markdown to HTML converter
const formatMarkdownContent = (markdown) => {
    if (!markdown) return '';

    let html = markdown
        // Escape HTML
        .replace(/&/g, '&amp;')
        .replace(/</g, '&lt;')
        .replace(/>/g, '&gt;')

        // Headers
        .replace(/^### (.*$)/gim, '<h3 class="text-lg font-semibold mt-4 mb-2">$1</h3>')
        .replace(/^## (.*$)/gim, '<h2 class="text-xl font-bold mt-6 mb-3">$1</h2>')
        .replace(/^# (.*$)/gim, '<h1 class="text-2xl font-bold mt-6 mb-4">$1</h1>')

        // Bold
        .replace(/\*\*\*(.+?)\*\*\*/g, '<strong><em>$1</em></strong>')
        .replace(/\*\*(.+?)\*\*/g, '<strong>$1</strong>')
        .replace(/__(.+?)__/g, '<strong>$1</strong>')

        // Italic
        .replace(/\*(.+?)\*/g, '<em>$1</em>')
        .replace(/_(.+?)_/g, '<em>$1</em>')

        // Links
        .replace(/\[([^\]]+)\]\(([^)]+)\)/g, '<a href="$2" class="text-blue-600 hover:underline" target="_blank">$1</a>')

        // Code blocks
        .replace(/```([a-z]*)\n([\s\S]*?)```/g, '<pre class="bg-gray-800 text-white p-3 rounded my-2 overflow-x-auto"><code>$2</code></pre>')

        // Inline code
        .replace(/`([^`]+)`/g, '<code class="bg-gray-200 px-1 rounded text-sm">$1</code>')

        // Lists - unordered
        .replace(/^\* (.+)$/gim, '<li class="ml-4">• $1</li>')
        .replace(/^- (.+)$/gim, '<li class="ml-4">• $1</li>')

        // Lists - ordered
        .replace(/^\d+\. (.+)$/gim, '<li class="ml-4 list-decimal">$1</li>')

        // Line breaks
        .replace(/\n\n/g, '</p><p class="mb-2">')
        .replace(/\n/g, '<br>');

    // Wrap in paragraph
    html = '<p class="mb-2">' + html + '</p>';

    // Wrap consecutive list items in ul
    html = html.replace(/(<li class="ml-4">• .+?<\/li>(?:<br>)?)+/g, match => {
        return '<ul class="list-none my-2">' + match.replace(/<br>/g, '') + '</ul>';
    });

    return html;
};