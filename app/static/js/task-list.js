// Enhanced task list with tabs and better display

let currentTaskFilter = 'all'; // 'all', 'active', 'completed'

const renderTaskListWithTabs = (tasks) => {
    if (!tasks) {
        tasks = [];
    }

    // Filter tasks based on current filter
    const filterTasks = (tasks, filter) => {
        switch (filter) {
            case 'active':
                return tasks.filter(t => t.status === 'pending' || t.status === 'running');
            case 'completed':
                return tasks.filter(t => t.status === 'completed' || t.status === 'failed');
            default:
                return tasks;
        }
    };

    const filteredTasks = filterTasks(tasks, currentTaskFilter);

    // Count for tabs
    const activeTasks = tasks.filter(t => t.status === 'pending' || t.status === 'running').length;
    const completedTasks = tasks.filter(t => t.status === 'completed' || t.status === 'failed').length;
    const allTasks = tasks.length;

    // Task limit warning
    const taskLimitWarning = activeTasks >= 3 ? `
        <div class="mb-4 p-4 bg-red-50 border-2 border-red-200 rounded-xl">
            <div class="flex items-center">
                <span class="text-2xl mr-3">⚠️</span>
                <div>
                    <p class="font-semibold text-red-900">Task Limit Reached (${activeTasks}/3)</p>
                    <p class="text-sm text-red-700">You have reached the maximum of 3 active tasks. Please wait for existing tasks to complete.</p>
                </div>
            </div>
        </div>
    ` : activeTasks === 2 ? `
        <div class="mb-4 p-3 bg-yellow-50 border border-yellow-200 rounded-lg">
            <div class="flex items-center">
                <span class="text-xl mr-2">💡</span>
                <p class="text-sm text-yellow-800">You have <strong>${activeTasks}/3</strong> active tasks. One more slot available.</p>
            </div>
        </div>
    ` : '';

    // Tabs HTML
    const tabsHTML = `
        ${taskLimitWarning}
        <div class="border-b border-gray-200 mb-6">
            <div class="flex">
                <button onclick="switchTaskFilter('active')"
                    class="task-tab px-6 py-3 font-medium transition-colors ${currentTaskFilter === 'active' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-600 hover:text-gray-900'}">
                    ⚡ Active ${activeTasks > 0 ? `(${activeTasks})` : ''}
                </button>
                <button onclick="switchTaskFilter('completed')"
                    class="task-tab px-6 py-3 font-medium transition-colors ${currentTaskFilter === 'completed' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-600 hover:text-gray-900'}">
                    ✓ Completed ${completedTasks > 0 ? `(${completedTasks})` : ''}
                </button>
                <button onclick="switchTaskFilter('all')"
                    class="task-tab px-6 py-3 font-medium transition-colors ${currentTaskFilter === 'all' ? 'border-b-2 border-blue-600 text-blue-600' : 'text-gray-600 hover:text-gray-900'}">
                    📋 All ${allTasks > 0 ? `(${allTasks})` : ''}
                </button>
            </div>
        </div>
    `;

    // Empty state
    if (filteredTasks.length === 0) {
        const emptyMessage = currentTaskFilter === 'all'
            ? 'No tasks yet'
            : currentTaskFilter === 'active'
            ? 'No active tasks'
            : 'No completed tasks';

        taskListContainer.innerHTML = `
            <div class="bg-white rounded-2xl shadow-xl p-8">
                <h2 class="text-2xl font-bold mb-6 text-gray-900">Your Tasks</h2>
                ${tabsHTML}
                <div class="text-center py-16">
                    <div class="text-6xl mb-4">${currentTaskFilter === 'all' ? '📭' : currentTaskFilter === 'active' ? '⏸️' : '✅'}</div>
                    <p class="text-xl font-medium text-gray-900 mb-2">${emptyMessage}</p>
                    <p class="text-gray-600">${currentTaskFilter === 'all' ? 'Create your first task above to get started!' : ''}</p>
                </div>
            </div>
        `;
        return;
    }

    // Task cards
    const taskCardsHTML = filteredTasks.map(task => {
        const getStatusColor = (status) => {
            switch (status) {
                case 'pending': return { bg: 'bg-yellow-100', text: 'text-yellow-800', border: 'border-yellow-300' };
                case 'running': return { bg: 'bg-blue-100', text: 'text-blue-800', border: 'border-blue-300' };
                case 'completed': return { bg: 'bg-green-100', text: 'text-green-800', border: 'border-green-300' };
                case 'failed': return { bg: 'bg-red-100', text: 'text-red-800', border: 'border-red-300' };
                default: return { bg: 'bg-gray-100', text: 'text-gray-800', border: 'border-gray-300' };
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

        const getAgentIcon = (agentType) => {
            return agentType === 'ai-travel-planner' ? '✈️' : '🔍';
        };

        const statusColors = getStatusColor(task.status);

        // Format input display
        let inputDisplay = '';
        if (task.agent_type === 'ai-travel-planner') {
            inputDisplay = `<span class="text-gray-600">Travel:</span> ${task.input_data.text?.substring(0, 60)}...`;
        } else if (task.input_data.mode === 'url') {
            inputDisplay = `<span class="text-gray-600">URL:</span> ${task.input_data.url?.substring(0, 50)}...`;
        } else {
            inputDisplay = `<span class="text-gray-600">Text:</span> ${task.input_data.text?.substring(0, 50)}...`;
        }

        return `
            <div class="bg-white border-2 ${statusColors.border} rounded-xl p-6 hover:shadow-lg transition-all">
                <div class="flex items-start justify-between mb-4">
                    <div class="flex items-center space-x-3">
                        <div class="text-3xl">${getAgentIcon(task.agent_type)}</div>
                        <div>
                            <div class="flex items-center gap-2 mb-1">
                                <span class="px-3 py-1 rounded-full text-xs font-semibold ${statusColors.bg} ${statusColors.text}">
                                    ${getStatusIcon(task.status)} ${task.status.toUpperCase()}
                                </span>
                                <span class="text-xs text-gray-500 font-medium">${task.agent_type}</span>
                            </div>
                            <p class="text-sm text-gray-700">${inputDisplay}</p>
                        </div>
                    </div>
                    <div class="text-right">
                        <p class="text-lg font-bold text-gray-900">$${(task.actual_cost || task.estimated_cost).toFixed(4)}</p>
                        <p class="text-xs text-gray-500">${task.actual_cost ? 'Actual' : 'Estimated'}</p>
                    </div>
                </div>

                ${task.status === 'running' ? `
                    <div class="mb-4">
                        <div class="w-full bg-gray-200 rounded-full h-2 overflow-hidden">
                            <div class="bg-blue-600 h-2 rounded-full animate-pulse" style="width: 60%"></div>
                        </div>
                        <p class="text-xs text-blue-600 mt-2 font-medium">
                            ${task.progress_message || 'Agent is processing your request...'}
                        </p>
                    </div>
                ` : ''}

                ${task.status === 'failed' && task.metadata?.error ? `
                    <div class="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
                        <p class="text-sm text-red-800 font-medium mb-1">❌ Task Failed</p>
                        <p class="text-xs text-red-700">${task.metadata.error}</p>
                    </div>
                ` : ''}

                <div id="task-result-${task.id}"></div>
            </div>
        `;
    }).join('');

    taskListContainer.innerHTML = `
        <div class="bg-white rounded-2xl shadow-xl p-8">
            <h2 class="text-2xl font-bold mb-6 text-gray-900">Your Tasks</h2>
            ${tabsHTML}
            <div class="space-y-4">
                ${taskCardsHTML}
            </div>
        </div>
    `;
};

window.switchTaskFilter = (filter) => {
    currentTaskFilter = filter;
    // Reload tasks with new filter
    if (window.lastLoadedTasks) {
        renderTaskListWithTabs(window.lastLoadedTasks);
    }
};

// Store original renderTaskList
const originalRenderTaskList = window.renderTaskList || function() {};

// Override renderTaskList to use tabs version
window.renderTaskList = (tasks) => {
    window.lastLoadedTasks = tasks;
    renderTaskListWithTabs(tasks);
};
