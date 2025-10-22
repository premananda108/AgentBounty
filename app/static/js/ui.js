const headerContainer = document.getElementById('header-container');
const taskCreatorContainer = document.getElementById('task-creator-container');
const taskListContainer = document.getElementById('task-list-container');
const paymentModal = document.getElementById('payment-modal');

// Global state for running tasks
window.hasRunningTask = false;

const updateUIForRunningTask = (hasRunning) => {
    console.log('updateUIForRunningTask called with hasRunning:', hasRunning);
    window.hasRunningTask = hasRunning;
    console.log('window.hasRunningTask set to:', window.hasRunningTask);
    // Re-render task creator to update card states
    if (window.lastIsAuthenticated !== undefined) {
        console.log('Re-rendering task creator with auth:', window.lastIsAuthenticated);
        renderTaskCreator(window.lastIsAuthenticated);
    } else {
        console.log('lastIsAuthenticated is undefined, skipping re-render');
    }
};

const renderHeader = (isAuthenticated, user) => {
    const isDemoActive = window.isDemoMode && window.isDemoMode();

    headerContainer.innerHTML = `
        <header class="border-b border-gray-200 bg-white/80 backdrop-blur-sm sticky top-0 z-50 mb-4">
            <div class="container mx-auto px-4 py-3">
                <div class="flex items-center justify-between">
                    <div>
                        <h1 class="text-xl font-bold text-primary-600">AgentBounty</h1>
                        <p class="text-xs text-gray-600">AI Agent Marketplace</p>
                    </div>
                    <div class="flex items-center gap-4" id="auth-container">
                        ${isAuthenticated ? `
                            <div id="user-profile" class="flex items-center gap-4">
                                <span class="text-sm text-gray-600">${user.email}</span>
                                <div id="wallet-container"></div>
                            </div>
                            <button id="logout-button" class="bg-red-500 text-white px-4 py-2 rounded">Log Out</button>
                        ` : `
                            ${!isDemoActive ? `
                                <a href="/?demo=true" class="bg-yellow-500 text-black px-4 py-2 rounded font-semibold hover:bg-yellow-600 transition-colors">
                                    🎭 Try Demo
                                </a>
                            ` : ''}
                            <button id="login-button" class="bg-blue-500 text-white px-4 py-2 rounded">Log In</button>
                        `}
                    </div>
                </div>
            </div>
        </header>
    `;

    if (isAuthenticated) {
        document.getElementById('logout-button').addEventListener('click', logout);
    } else {
        document.getElementById('login-button').addEventListener('click', login);
    }
};

async function setupWalletConnection(provider) {
    const walletContainer = document.getElementById('wallet-container');
    if (!walletContainer) return;

    try {
        // Check network and switch if needed
        const network = await provider.getNetwork();
        console.log('Connected to network:', network);

        if (network.chainId !== 84532) {
            console.log('Wrong network, switching to Base Sepolia...');
            try {
                await window.ethereum.request({
                    method: 'wallet_switchEthereumChain',
                    params: [{ chainId: '0x14a34' }], // 84532 in hex
                });
            } catch (switchError) {
                if (switchError.code === 4902) {
                    console.log('Base Sepolia not found, adding network...');
                    await window.ethereum.request({
                        method: 'wallet_addEthereumChain',
                        params: [{
                            chainId: '0x14a34',
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
        }

        const signer = provider.getSigner();
        const userAddress = await signer.getAddress();

        // Try to get signature to verify wallet ownership (optional)
        try {
            const timestamp = Math.floor(Date.now() / 1000);
            const message = `Connect wallet ${userAddress.substring(0, 6)}...${userAddress.substring(userAddress.length - 4)} to AgentBounty at ${timestamp}`;

            console.log('Requesting signature for wallet connection...');
            const signature = await signer.signMessage(message);
            console.log('Signature received, saving to Auth0...');

            // Save wallet to Auth0
            try {
                const result = await connectWalletToAuth0(userAddress, signature, message);
                console.log('✅ Wallet connected to Auth0:', result);
            } catch (error) {
                console.error('⚠️ Failed to save wallet to Auth0:', error);
                // Continue anyway - wallet is still available in session
            }
        } catch (signatureError) {
            console.log('ℹ️ User declined signature request. Wallet connected but not verified.');
            // User declined signature - wallet is still usable for viewing tasks
            // Just won't be able to make payments without signature
        }

        walletContainer.innerHTML = `<p class="text-sm text-gray-600">💳 ${userAddress.substring(0, 6)}...${userAddress.substring(userAddress.length - 4)}</p>`;
        window.signer = signer;
        window.userAddress = userAddress;

        // Reload tasks now that wallet is connected (may show additional info)
        if (window.loadTasks) {
            loadTasks();
        }
    } catch (error) {
        console.error("Failed to setup wallet connection:", error);
        walletContainer.innerHTML = `<button id="connect-wallet-button" class="bg-purple-500 text-white px-4 py-2 rounded">Connect Wallet</button>`;
        document.getElementById('connect-wallet-button').addEventListener('click', connectWallet);
    }
}

// Detect if user is on mobile
const isMobile = () => {
    return /Android|webOS|iPhone|iPad|iPod|BlackBerry|IEMobile|Opera Mini/i.test(navigator.userAgent);
};

// Get current page URL for deep linking
const getCurrentUrl = () => {
    return window.location.href;
};

async function connectWallet() {
    // Check if MetaMask is available
    if (window.ethereum) {
        try {
            const provider = new ethers.providers.Web3Provider(window.ethereum);
            await provider.send("eth_requestAccounts", []);
            await setupWalletConnection(provider);
        } catch (error) {
            console.error("Failed to connect wallet:", error);
            alert("Failed to connect wallet. Please try again.");
        }
    } else {
        // No MetaMask detected
        if (isMobile()) {
            // On mobile - provide options to open in MetaMask browser or install
            showMobileWalletOptions();
        } else {
            // On desktop - suggest installing MetaMask
            if (confirm('MetaMask is not installed. Would you like to install it?')) {
                window.open('https://metamask.io/download/', '_blank');
            }
        }
    }
}

// Show mobile wallet connection options
const showMobileWalletOptions = () => {
    const currentUrl = getCurrentUrl();
    const metamaskDeepLink = `https://metamask.app.link/dapp/${currentUrl.replace(/^https?:\/\//, '')}`;

    // Create modal for mobile options
    const modal = document.createElement('div');
    modal.className = 'fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50 p-4';
    modal.innerHTML = `
        <div class="bg-white rounded-lg p-6 max-w-sm w-full">
            <h3 class="text-lg font-bold mb-4">Connect Wallet</h3>
            <p class="text-sm text-gray-600 mb-4">To use AgentBounty, you need a Web3 wallet:</p>

            <div class="space-y-3">
                <a href="${metamaskDeepLink}"
                   class="block w-full bg-orange-500 text-white px-4 py-3 rounded-lg text-center font-semibold hover:bg-orange-600">
                    📱 Open in MetaMask App
                </a>

                <a href="https://metamask.io/download/"
                   target="_blank"
                   class="block w-full bg-blue-500 text-white px-4 py-3 rounded-lg text-center font-semibold hover:bg-blue-600">
                    📲 Install MetaMask
                </a>

                <button onclick="this.closest('.fixed').remove()"
                        class="block w-full bg-gray-300 text-gray-700 px-4 py-3 rounded-lg text-center font-semibold hover:bg-gray-400">
                    Cancel
                </button>
            </div>

            <p class="text-xs text-gray-500 mt-4 text-center">
                💡 If you have MetaMask installed, click "Open in MetaMask App"
            </p>
        </div>
    `;

    document.body.appendChild(modal);

    // Close on background click
    modal.addEventListener('click', (e) => {
        if (e.target === modal) {
            modal.remove();
        }
    });
};

async function checkWalletConnection() {
    // Skip wallet connection check in demo mode
    if (window.isDemoMode && window.isDemoMode()) {
        console.log('🎭 Demo mode: using demo wallet');
        renderDemoWallet();
        return;
    }

    if (window.ethereum) {
        try {
            const provider = new ethers.providers.Web3Provider(window.ethereum);
            const accounts = await provider.send("eth_accounts", []);
            if (accounts.length > 0) {
                console.log("Wallet already connected:", accounts[0]);
                await setupWalletConnection(provider);
            } else {
                console.log("Wallet not connected, showing connect button.");
                renderWalletConnect();
            }
        } catch (error) {
            console.error("Could not check for existing wallet connection:", error);
            renderWalletConnect();
        }
    } else {
        console.log("No Ethereum wallet detected.");
        renderWalletConnect();
    }
}

const renderWalletConnect = () => {
    const walletContainer = document.getElementById('wallet-container');
    if (!walletContainer) return;

    // Different button text for mobile
    const buttonText = isMobile() ? '📱 Connect Wallet' : 'Connect Wallet';

    walletContainer.innerHTML = `
        <button id="connect-wallet-button" class="bg-purple-500 text-white px-4 py-2 rounded hover:bg-purple-600 transition-colors">
            ${buttonText}
        </button>
    `;
    document.getElementById('connect-wallet-button').addEventListener('click', connectWallet);
};

const renderDemoWallet = () => {
    const walletContainer = document.getElementById('wallet-container');
    if (!walletContainer) return;

    // Demo wallet address from demo_data.py
    const demoAddress = '0xdE3089c44de71234567890123456789012345678';
    const demoBalance = '50.25'; // Demo USDC balance

    walletContainer.innerHTML = `
        <div class="flex items-center gap-2 bg-yellow-50 px-3 py-1 rounded border border-yellow-300">
            <span class="text-xs">🎭</span>
            <p class="text-sm text-gray-700">
                💳 ${demoAddress.substring(0, 6)}...${demoAddress.substring(demoAddress.length - 4)}
                <span class="text-xs text-gray-500 ml-2">(${demoBalance} USDC)</span>
            </p>
        </div>
    `;

    // Set demo wallet globally (already done in demo.js, but ensure it's set)
    window.userAddress = demoAddress;
    window.demoWallet = true;

    console.log('🎭 Demo wallet rendered:', demoAddress);
};

const renderTaskList = (tasks) => {
    if (!tasks || tasks.length === 0) {
        taskListContainer.innerHTML = `
            <div class="bg-white rounded-lg shadow-md p-6">
                <div class="text-center py-12">
                    <p class="text-gray-600 mb-2">No tasks yet</p>
                    <p class="text-sm text-gray-500">Log in and connect your wallet to see your tasks.</p>
                </div>
            </div>
        `;
        return;
    }

    const taskCards = tasks.map(task => {
        const getStatusColor = (status) => {
            switch (status) {
                case 'pending': return 'bg-gray-100 text-gray-800';
                case 'running': return 'bg-blue-100 text-blue-800';
                case 'completed': return 'bg-green-100 text-green-800';
                case 'failed': return 'bg-red-100 text-red-800';
                default: return 'bg-gray-100 text-gray-800';
            }
        };

        const getStatusIcon = (status) => {
            switch (status) {
                case 'pending': return '⏸️';
                case 'running': return '⚡';
                case 'completed': return '✅';
                case 'failed': return '❌';
                default: return '•';
            }
        };

        return `
            <div class="border border-gray-200 rounded-lg p-4 hover:shadow-md transition-shadow mb-4">
                <div class="flex items-start justify-between mb-3">
                    <div class="flex-1">
                        <div class="flex items-center gap-2 mb-1">
                            <span class="px-2 py-1 rounded text-xs font-medium ${getStatusColor(task.status)}">
                                ${getStatusIcon(task.status)} ${task.status.toUpperCase()}
                            </span>
                            <span class="text-xs text-gray-500">${task.agent_type}</span>
                        </div>
                        <p class="text-sm text-gray-600 mb-2">
                            ${task.agent_type === 'ai-travel-planner' ? `Travel: ${task.input_data.text?.substring(0, 50)}...` : task.input_data.mode === 'url' ? `URL: ${task.input_data.url?.substring(0, 50)}...` : `Text: ${task.input_data.text?.substring(0, 50)}...`}
                        </p>
                    </div>
                    <div class="text-right">
                        <p class="text-sm font-medium text-gray-900">
                            $${task.actual_cost?.toFixed(2) || task.estimated_cost.toFixed(2)}
                        </p>
                        <p class="text-xs text-gray-500">
                            ${task.actual_cost ? 'Actual' : 'Estimated'}
                        </p>
                    </div>
                </div>
                <div class="flex items-center justify-between text-xs text-gray-500 mb-3">
                    <span>Created: ${new Date(task.created_at).toLocaleString()}</span>
                    ${task.completed_at ? `<span>Completed: ${new Date(task.completed_at).toLocaleString()}</span>` : ''}
                </div>
                ${task.status === 'completed' ? `<div class="mt-3 pt-3 border-t border-gray-200" id="task-result-${task.id}"><button class="view-result-button w-full px-4 py-2 bg-primary-600 hover:bg-primary-700 text-white text-sm font-medium rounded-lg" data-task-id="${task.id}">View Result</button></div>` : ''}
                ${task.status === 'running' ? `<div class="mt-3 flex items-center gap-2 text-sm text-blue-600"><span class="animate-spin">⚡</span><span>Agent is working...</span></div>` : ''}
                ${task.status === 'failed' && task.metadata?.error ? `<div class="mt-3 p-3 bg-red-50 rounded text-sm text-red-800">Error: ${task.metadata.error}</div>` : ''}
            </div>
        `;
    }).join('');

    taskListContainer.innerHTML = `
        <div class="bg-white rounded-lg shadow-md p-6">
            <div class="flex items-center justify-between mb-4">
                <h2 class="text-xl font-bold">Your Tasks (${tasks.length})</h2>
            </div>
            ${taskCards}
        </div>
    `;

    // Add event listeners for "View Result" buttons
    document.querySelectorAll('.view-result-button').forEach(button => {
        button.addEventListener('click', async () => {
            const taskId = button.getAttribute('data-task-id');
            const task = tasks.find(t => t.id === taskId);
            if (task) {
                console.log('View Result button clicked for task:', taskId);
                // Import handleCompletedTask from app.js context
                if (window.handleCompletedTask) {
                    await window.handleCompletedTask(task);
                } else {
                    console.error('handleCompletedTask not found in window');
                }
            }
        });
    });
};

const showPaymentModal = (amount) => {
    console.log('showPaymentModal called with amount:', amount);
    const modal = document.getElementById('payment-modal');
    const amountElement = document.getElementById('payment-amount');

    if (amountElement) {
        amountElement.textContent = amount;
        console.log('Payment amount set to:', amount);
    } else {
        console.error('payment-amount element not found');
    }

    if (modal) {
        modal.classList.remove('hidden');
        modal.style.display = 'flex';
        console.log('Payment modal shown');

        // Close modal on background click
        modal.onclick = (e) => {
            if (e.target === modal) {
                hidePaymentModal();
            }
        };
    } else {
        console.error('payment-modal not found');
    }
};

const hidePaymentModal = () => {
    console.log('hidePaymentModal called');
    const modal = document.getElementById('payment-modal');
    if (modal) {
        modal.classList.add('hidden');
        modal.style.display = 'none';
        console.log('Payment modal hidden');
    }
};

// New simplified UI for agent cards with modal

const renderTaskCreator = async (isAuthenticated) => {
    // Save auth state for updates
    window.lastIsAuthenticated = isAuthenticated;

    console.log('renderTaskCreator called with isAuthenticated:', isAuthenticated, 'hasRunningTask:', window.hasRunningTask);

    const message = isAuthenticated ? '' : `
        <div class="text-center p-6 mb-6 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
            <div class="text-4xl mb-3">🔐</div>
            <p class="font-semibold text-gray-900 mb-1">Authentication Required</p>
            <p class="text-sm text-gray-600">Please log in and connect your wallet to create tasks</p>
        </div>
    `;

    // Show running task message if applicable
    const runningMessage = (isAuthenticated && window.hasRunningTask) ? `
        <div class="text-center p-4 mb-4 bg-blue-50 border-2 border-blue-200 rounded-xl">
            <div class="text-3xl mb-2">⚡</div>
            <p class="font-semibold text-gray-900 mb-1">Task in Progress</p>
            <p class="text-sm text-gray-600">Please wait for the current task to complete before starting a new one</p>
        </div>
    ` : '';

    // Fetch available agents
    let agentsHTML = '';
    let agentsData = {};

    try {
        const response = await listAgents();
        agentsData = response.agents;

        // Agent configurations
        const agentConfigs = {
            'factcheck': {
                icon: '🔍',
                color: 'purple',
                gradient: 'from-purple-500 to-pink-500',
                features: ['URL & Text modes', '4-stage verification', 'Multi-source checking'],
                examples: ['TikTok verification', 'News fact-check', 'Social media claims']
            },
            'ai-travel-planner': {
                icon: '✈️',
                color: 'teal',
                gradient: 'from-teal-500 to-cyan-500',
                features: ['Flight search', 'Hotel finder', 'Real-time pricing'],
                examples: ['Weekend getaway', 'Multi-city tour', 'Budget travel']
            }
        };

        agentsHTML = `
            <div class="space-y-4">
                <div class="text-center">
                    <h3 class="text-2xl font-bold text-gray-900 mb-2">Choose Your AI Agent</h3>
                    <p class="text-base text-gray-600">Select an agent to start your task</p>
                </div>

                <div class="grid grid-cols-1 lg:grid-cols-2 gap-8" id="agent-cards">
                    ${Object.entries(agentsData).map(([agentType, agentInfo]) => {
                        const config = agentConfigs[agentType] || {
                            icon: '🤖',
                            color: 'blue',
                            gradient: 'from-blue-500 to-indigo-500',
                            features: [],
                            examples: []
                        };
                        const isDisabled = !isAuthenticated || window.hasRunningTask;
                        console.log(`Agent ${agentType}: isAuthenticated=${isAuthenticated}, hasRunningTask=${window.hasRunningTask}, isDisabled=${isDisabled}`);
                        return `
                        <div class="agent-card bg-white border-2 border-gray-200 rounded-2xl overflow-hidden transition-all ${isDisabled ? 'opacity-50' : 'cursor-pointer hover:shadow-2xl'}"
                             data-agent-type="${agentType}"
                             data-agent-info='${JSON.stringify(agentInfo)}'
                             ${isDisabled ? 'data-disabled="true"' : ''}>

                            <!-- Card Header with Gradient -->
                            <div class="bg-gradient-to-r ${config.gradient} p-4 text-white">
                                <div class="flex items-start justify-between">
                                    <div class="text-4xl">${config.icon}</div>
                                    <span class="px-3 py-1 bg-white bg-opacity-30 rounded-full text-sm font-semibold text-gray-800">
                                        $${agentInfo.base_cost.toFixed(4)}
                                    </span>
                                </div>
                            </div>

                            <!-- Card Body -->
                            <div class="p-4 space-y-3">
                                <div>
                                    <h4 class="text-2xl font-bold text-gray-900 mb-2">${agentInfo.name}</h4>
                                    <p class="text-gray-600 leading-relaxed">${agentInfo.description}</p>
                                </div>

                                ${config.features.length > 0 ? `
                                <div class="space-y-2">
                                    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide">Features</p>
                                    ${config.features.map(feature => `
                                        <div class="flex items-center text-sm text-gray-700">
                                            <svg class="w-5 h-5 text-green-500 mr-2 flex-shrink-0" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                                <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M5 13l4 4L19 7"></path>
                                            </svg>
                                            <span>${feature}</span>
                                        </div>
                                    `).join('')}
                                </div>
                                ` : ''}

                                ${config.examples.length > 0 ? `
                                <div class="pt-4 border-t border-gray-100">
                                    <p class="text-xs font-semibold text-gray-500 uppercase tracking-wide mb-2">Use Cases</p>
                                    <div class="flex flex-wrap gap-2">
                                        ${config.examples.map(example => `
                                            <span class="px-3 py-1 bg-${config.color}-50 text-${config.color}-700 text-xs rounded-full">
                                                ${example}
                                            </span>
                                        `).join('')}
                                    </div>
                                </div>
                                ` : ''}

                                ${isAuthenticated ? `
                                <button class="w-full py-3 px-4 bg-gradient-to-r ${config.gradient} hover:opacity-90 text-gray-900 font-semibold rounded-xl transition-all transform hover:scale-105">
                                    Use This Agent →
                                </button>
                                ` : ''}
                            </div>
                        </div>
                    `}).join('')}
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Failed to load agents:', error);
        agentsHTML = `
            <div class="text-center p-12 bg-red-50 border-2 border-red-200 rounded-xl">
                <div class="text-4xl mb-3">⚠️</div>
                <p class="font-semibold text-red-900 mb-2">Failed to Load Agents</p>
                <p class="text-sm text-red-700">Please refresh the page to try again</p>
            </div>
        `;
    }

    taskCreatorContainer.innerHTML = `
        <div class="bg-gradient-to-br from-blue-50 to-indigo-50 rounded-2xl shadow-xl p-10 mb-8">
            ${message}
            ${runningMessage}
            ${agentsHTML}
        </div>
    `;

    // Store agents data globally for modal
    window.agentsData = agentsData;

    // Add click listeners to agent cards after rendering
    if (isAuthenticated) {
        const agentCards = document.querySelectorAll('.agent-card:not([data-disabled="true"])');
        agentCards.forEach(card => {
            card.addEventListener('click', function(e) {
                // Prevent button click from triggering twice
                if (e.target.tagName === 'BUTTON') {
                    e.preventDefault();
                }
                const agentType = this.dataset.agentType;
                const agentInfo = JSON.parse(this.dataset.agentInfo);
                console.log('Card clicked:', agentType);

                if (typeof showCreateTaskModal === 'function') {
                    showCreateTaskModal(agentType, agentInfo);
                } else {
                    console.error('showCreateTaskModal not found');
                    alert('Modal function not loaded. Please refresh the page.');
                }
            });
        });
    }
};

// Handle agent card click
window.handleAgentCardClick = (agentType, cardElement) => {
    console.log('Agent card clicked:', agentType);
    try {
        const agentInfo = JSON.parse(cardElement.dataset.agentInfo);
        console.log('Agent info:', agentInfo);

        if (typeof showCreateTaskModal !== 'function') {
            console.error('showCreateTaskModal is not defined');
            alert('Modal function not loaded. Please refresh the page.');
            return;
        }

        showCreateTaskModal(agentType, agentInfo);
    } catch (error) {
        console.error('Error in handleAgentCardClick:', error);
        alert('Failed to open modal: ' + error.message);
    }
};

const handleTaskCreation = async (submitButton, taskData) => {
    submitButton.disabled = true;
    submitButton.innerHTML = `<span class="animate-spin">⏳</span> Creating...`;

    try {
        const newTask = await createTask(taskData);
        await startTask(newTask.id);
        document.getElementById('text').value = '';
        document.getElementById('url').value = '';
        loadTasks();
    } catch (error) {
        console.error('Failed to create task:', error);
        alert(`Error: ${error.message}`);
    } finally {
        submitButton.disabled = false;
        submitButton.textContent = 'Create & Start Task';
    }
};// Modal management for Create Task
console.log('modal.js loaded');

const showCreateTaskModal = (agentType, agentInfo) => {
    console.log('showCreateTaskModal called with:', agentType, agentInfo);
    const modal = document.getElementById('create-task-modal');
    console.log('Modal element:', modal);

    if (!modal) {
        console.error('Modal element not found!');
        return;
    }

    const modalContent = modal.querySelector('.relative');
    console.log('Modal content element:', modalContent);

    // Agent configurations
    const agentConfigs = {
        'factcheck': {
            icon: '🔍',
            color: '#8b5cf6',
            modes: ['text', 'url'],
            placeholder: {
                text: 'Example: "The new iPhone has 10TB of storage and costs only $99"',
                url: 'https://tiktok.com/@user/video/...'
            },
            examples: [
                'Verify claims from TikTok videos',
                'Fact-check news articles',
                'Check social media posts'
            ]
        },
        'ai-travel-planner': {
            icon: '✈️',
            color: '#14b8a6',
            modes: ['text'],
            placeholder: {
                text: 'Example: "Find flights and hotels from New York to Miami, November 2-5, 2025, for 2 travelers"'
            },
            examples: [
                'Weekend getaway to Paris',
                'Multi-city European tour',
                'Budget beach vacation'
            ]
        }
    };

    const config = agentConfigs[agentType] || {};
    const hasTwoModes = config.modes && config.modes.length > 1;

    modalContent.innerHTML = `
        <!-- Modal Header -->
        <div class="flex items-center justify-between p-6 border-b border-gray-200">
            <div class="flex items-center space-x-3">
                <div class="text-3xl">${config.icon}</div>
                <div>
                    <h3 class="text-xl font-bold text-gray-900">${agentInfo.name}</h3>
                    <p class="text-sm text-gray-600">${agentInfo.description}</p>
                </div>
            </div>
            <button onclick="hideCreateTaskModal()" class="text-gray-400 hover:text-gray-600 transition-colors">
                <svg class="w-6 h-6" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M6 18L18 6M6 6l12 12"></path>
                </svg>
            </button>
        </div>

        <!-- Modal Body -->
        <form id="modal-task-form" class="p-6 space-y-6">
            ${config.examples && config.examples.length > 0 ? `
            <div class="bg-blue-50 border border-blue-200 rounded-lg p-4">
                <p class="text-sm font-semibold text-blue-900 mb-2">💡 Example Use Cases:</p>
                <ul class="text-sm text-blue-800 space-y-1">
                    ${config.examples.map(ex => `<li>• ${ex}</li>`).join('')}
                </ul>
            </div>
            ` : ''}

            ${hasTwoModes ? `
            <div>
                <label class="block text-sm font-semibold text-gray-700 mb-3">Input Mode</label>
                <div class="grid grid-cols-2 gap-3">
                    <label class="relative flex items-center p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition-all">
                        <input type="radio" name="modal-mode" value="text" checked class="mr-3" onchange="toggleModalInputMode()">
                        <div>
                            <div class="font-medium text-gray-900">📝 Text</div>
                            <div class="text-xs text-gray-600">Direct text input</div>
                        </div>
                    </label>
                    <label class="relative flex items-center p-4 border-2 border-gray-200 rounded-lg cursor-pointer hover:border-blue-400 transition-all">
                        <input type="radio" name="modal-mode" value="url" class="mr-3" onchange="toggleModalInputMode()">
                        <div>
                            <div class="font-medium text-gray-900">🔗 URL</div>
                            <div class="text-xs text-gray-600">Social media link</div>
                        </div>
                    </label>
                </div>
            </div>
            ` : ''}

            <div id="modal-text-input" ${!hasTwoModes || config.modes[0] === 'text' ? '' : 'class="hidden"'}>
                <label for="modal-text" class="block text-sm font-semibold text-gray-700 mb-2">Your Request</label>
                <textarea id="modal-text" rows="4"
                    placeholder="${config.placeholder?.text || 'Enter your request...'}"
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none"></textarea>
            </div>

            <div id="modal-url-input" class="hidden">
                <label for="modal-url" class="block text-sm font-semibold text-gray-700 mb-2">Social Media URL</label>
                <input id="modal-url" type="url"
                    placeholder="${config.placeholder?.url || 'https://...'}"
                    class="w-full px-4 py-3 border border-gray-300 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent">
            </div>

            <div class="flex items-center justify-between p-4 bg-gray-50 rounded-lg">
                <div class="text-sm text-gray-600">Estimated cost:</div>
                <div class="text-lg font-bold text-blue-600">$${agentInfo.base_cost.toFixed(4)} USDC</div>
            </div>
        </form>

        <!-- Modal Footer -->
        <div class="flex items-center justify-end space-x-3 p-6 border-t border-gray-200 bg-gray-50">
            <button onclick="hideCreateTaskModal()" type="button"
                class="px-6 py-2 border border-gray-300 rounded-lg text-gray-700 font-medium hover:bg-gray-100 transition-colors">
                Cancel
            </button>
            <button onclick="submitModalTask('${agentType}')" type="button"
                class="px-6 py-2 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-lg transition-colors shadow-md">
                Create & Start Task →
            </button>
        </div>
    `;

    // Show modal with animation
    console.log('Setting modal display to flex...');
    modal.style.display = 'flex';
    modal.classList.remove('hidden');
    console.log('Modal classes after show:', modal.className);
    console.log('Modal display style:', modal.style.display);

    setTimeout(() => modal.classList.add('show'), 10);

    // Close on backdrop click
    modal.onclick = (e) => {
        if (e.target === modal) hideCreateTaskModal();
    };

    console.log('Modal should now be visible');
};

const hideCreateTaskModal = () => {
    const modal = document.getElementById('create-task-modal');
    modal.classList.remove('show');
    setTimeout(() => {
        modal.style.display = 'none';
        modal.classList.add('hidden');
    }, 300);
};

const toggleModalInputMode = () => {
    const mode = document.querySelector('input[name="modal-mode"]:checked')?.value || 'text';
    const textInput = document.getElementById('modal-text-input');
    const urlInput = document.getElementById('modal-url-input');

    if (mode === 'text') {
        textInput.classList.remove('hidden');
        urlInput.classList.add('hidden');
    } else {
        textInput.classList.add('hidden');
        urlInput.classList.remove('hidden');
    }
};

const submitModalTask = async (agentType) => {
    const mode = document.querySelector('input[name="modal-mode"]:checked')?.value || 'text';
    const text = document.getElementById('modal-text').value;
    const url = document.getElementById('modal-url').value;

    let input_data;

    // Build input data based on agent type
    if (agentType === 'ai-travel-planner') {
        if (!text.trim()) {
            alert('Please enter your travel request');
            return;
        }
        input_data = { text: text.trim() };
    } else {
        // For factcheck agent
        if (mode === 'text') {
            if (!text.trim()) {
                alert('Please enter text to fact-check');
                return;
            }
            input_data = { mode: 'text', text: text.trim() };
        } else {
            if (!url.trim()) {
                alert('Please enter a URL to fact-check');
                return;
            }
            input_data = { mode: 'url', url: url.trim() };
        }
    }

    // Disable submit button
    const submitBtn = event.target;
    submitBtn.disabled = true;
    submitBtn.textContent = 'Creating...';

    try {
        const taskData = { agent_type: agentType, input_data };
        const newTask = await createTask(taskData);
        await startTask(newTask.id);
        hideCreateTaskModal();
        loadTasks();
    } catch (error) {
        console.error('Failed to create task:', error);

        // Check if it's a task limit error
        if (error.status === 400 && error.message.includes('Task limit reached')) {
            alert(
                '⚠️ Task Limit Reached\n\n' +
                error.message + '\n\n' +
                '💡 Tip: Tasks usually complete within 1-2 minutes. Please check your task list below.'
            );
        } else {
            alert('Failed to create task: ' + error.message);
        }

        submitBtn.disabled = false;
        submitBtn.textContent = 'Create & Start Task →';
    }
};

// Make functions globally available
window.showCreateTaskModal = showCreateTaskModal;
window.hideCreateTaskModal = hideCreateTaskModal;
window.toggleModalInputMode = toggleModalInputMode;
window.submitModalTask = submitModalTask;
window.updateUIForRunningTask = updateUIForRunningTask;
