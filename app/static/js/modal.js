// Modal management for Create Task
console.log('modal.js loaded');

const showCreateTaskModal = (agentType, agentInfo) => {
    console.log('showCreateTaskModal called with:', agentType, agentInfo);
    const modal = document.getElementById('create-task-modal');
    const modalContent = modal.querySelector('.relative');

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
    modal.style.display = 'flex';
    modal.classList.remove('hidden');
    setTimeout(() => modal.classList.add('show'), 10);

    // Close on backdrop click
    modal.onclick = (e) => {
        if (e.target === modal) hideCreateTaskModal();
    };
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
        await handleTaskCreation(submitBtn, { agent_type: agentType, input_data });
        hideCreateTaskModal();
    } catch (error) {
        alert('Failed to create task: ' + error.message);
        submitBtn.disabled = false;
        submitBtn.textContent = 'Create & Start Task →';
    }
};

// Make functions globally available
window.showCreateTaskModal = showCreateTaskModal;
window.hideCreateTaskModal = hideCreateTaskModal;
window.toggleModalInputMode = toggleModalInputMode;
window.submitModalTask = submitModalTask;
