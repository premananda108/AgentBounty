// New simplified UI for agent cards with modal

const renderTaskCreator = async (isAuthenticated) => {
    const message = isAuthenticated ? '' : `
        <div class="text-center p-6 mb-6 bg-yellow-50 border-2 border-yellow-200 rounded-xl">
            <div class="text-4xl mb-3">🔐</div>
            <p class="font-semibold text-gray-900 mb-1">Authentication Required</p>
            <p class="text-sm text-gray-600">Please log in and connect your wallet to create tasks</p>
        </div>
    `;

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
            <div class="space-y-8">
                <div class="text-center">
                    <h3 class="text-3xl font-bold text-gray-900 mb-3">Choose Your AI Agent</h3>
                    <p class="text-lg text-gray-600">Select an agent to start your task</p>
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
                        return `
                        <div class="agent-card bg-white border-2 border-gray-200 rounded-2xl overflow-hidden transition-all ${!isAuthenticated ? 'opacity-50' : 'cursor-pointer hover:shadow-2xl'}"
                             data-agent-type="${agentType}"
                             data-agent-info='${JSON.stringify(agentInfo)}'
                             ${!isAuthenticated ? 'data-disabled="true"' : ''}
                             onclick="${isAuthenticated ? `handleAgentCardClick('${agentType}', this)` : ''}">

                            <!-- Card Header with Gradient -->
                            <div class="bg-gradient-to-r ${config.gradient} p-6 text-white">
                                <div class="flex items-start justify-between">
                                    <div class="text-5xl">${config.icon}</div>
                                    <span class="px-3 py-1 bg-white bg-opacity-30 rounded-full text-sm font-semibold">
                                        $${agentInfo.base_cost.toFixed(4)}
                                    </span>
                                </div>
                            </div>

                            <!-- Card Body -->
                            <div class="p-6 space-y-4">
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
                                <button class="w-full py-3 px-4 bg-gradient-to-r ${config.gradient} hover:opacity-90 text-white font-semibold rounded-xl transition-all transform hover:scale-105">
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
            ${agentsHTML}
        </div>
    `;

    // Store agents data globally for modal
    window.agentsData = agentsData;
};

// Handle agent card click
window.handleAgentCardClick = (agentType, cardElement) => {
    const agentInfo = JSON.parse(cardElement.dataset.agentInfo);
    showCreateTaskModal(agentType, agentInfo);
};
