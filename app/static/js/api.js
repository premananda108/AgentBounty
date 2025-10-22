const API_URL = '';

const fetchFromAPI = async (endpoint, options = {}) => {
    // Token and Authorization header are no longer needed for cookie-based auth.
    const headers = {
        'Content-Type': 'application/json',
    };

    const response = await fetch(`${API_URL}${endpoint}`, {
        ...options,
        headers: {
            ...headers,
            ...options.headers,
        },
    });

    if (!response.ok) {
        if (response.status === 402 || response.status === 403) {
            // For 402 and 403, we expect a JSON body with payment/CIBA info, so we return it
            return response.json();
        }
        // For other errors, try to get a detailed message from the body
        try {
            const errorData = await response.json();
            console.error('API error response:', errorData);
            const message = errorData.detail || errorData.message || JSON.stringify(errorData);
            throw new Error(`API request failed: ${message}`);
        } catch (e) {
            console.error('Error parsing API response:', e);
            // If the body isn't JSON or another error occurs, fall back to statusText
            throw new Error(`API request failed: ${response.statusText}`);
        }
    }

    return response.json();
};

const listAgents = () => fetchFromAPI('/api/agents');
const listTasks = () => fetchFromAPI('/api/tasks/');
const createTask = (task) => fetchFromAPI('/api/tasks/', { method: 'POST', body: JSON.stringify(task) });
const startTask = (taskId) => fetchFromAPI(`/api/tasks/${taskId}/start`, { method: 'POST' });
const getTaskResult = (taskId, address, signature) => {
    // Note: user_address is now retrieved from session on the server side
    // We keep the parameters for backwards compatibility but don't use them in URL
    let url = `/api/tasks/${taskId}/result`;
    if (signature) {
        url += `?authorization=${signature}`;
    }
    return fetchFromAPI(url);
};
const checkCIBAStatus = (cibaRequestId) => fetchFromAPI(`/api/payments/ciba/status/${cibaRequestId}`);
const simulateCIBAApproval = (cibaRequestId, approved = true) => fetchFromAPI(`/api/payments/ciba/simulate/${cibaRequestId}?approved=${approved}`, { method: 'POST' });

// Wallet connection
const connectWalletToAuth0 = (walletAddress, signature, message) =>
    fetchFromAPI('/api/wallet/connect', {
        method: 'POST',
        body: JSON.stringify({
            wallet_address: walletAddress,
            signature: signature,
            message: message
        })
    });

const getWalletInfo = () => fetchFromAPI('/api/wallet/info');