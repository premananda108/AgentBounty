// frontend/static/js/auth.js

// Redirects the user to the backend login route
const login = () => {
    window.location.href = '/auth/login';
};

// Redirects the user to the backend logout route
const logout = () => {
    stopTaskUpdates();
    window.location.href = '/auth/logout';
};

// Checks if a user session exists on the backend by calling the /api/me endpoint.
const checkSession = async () => {
    try {
        const response = await fetch('/api/me');
        if (response.ok) {
            const data = await response.json();
            return data.user; // Return the user object
        }
        return null; // No active session
    } catch (error) {
        console.error('Session check failed:', error);
        return null;
    }
};

// This function is kept for compatibility with api.js, but it's not fetching a token anymore.
const getToken = async () => {
    // The browser handles the session cookie automatically.
    return 'cookie-session'; // Placeholder value
};

// Check if demo mode is active (check directly from URL/cookie)
const isInDemoMode = () => {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('demo') === 'true' || document.cookie.includes('demo_mode=true');
};

// Main function to update the UI based on authentication state
const updateUI = async () => {
    // Check if we're in demo mode - if so, skip standard auth
    if (isInDemoMode()) {
        console.log('🎭 Demo mode detected - skipping standard auth flow');
        document.getElementById('main-content').classList.remove('hidden');
        // Demo mode will handle authentication via demo.js
        return;
    }

    const user = await checkSession();
    const isAuthenticated = !!user;

    // The main content is now always visible, but interactive elements will be disabled if not logged in.
    document.getElementById('main-content').classList.remove('hidden');

    if (isAuthenticated) {
        initializeApp(user);
    } else {
        // Not authenticated - show login/demo options
        renderHeader(false, null);
        renderTaskCreator(false);
        renderTaskList([]);
        stopTaskUpdates();
    }
};

// Add event listener to run the UI update when the page loads
window.addEventListener('DOMContentLoaded', updateUI);