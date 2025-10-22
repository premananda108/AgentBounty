/**
 * Demo Mode Frontend Module
 * Automatic activation of demo mode and UI improvements
 */

// Check for demo mode activation
const isDemoMode = () => {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('demo') === 'true' ||
           document.cookie.includes('demo_mode=true');
};

// Activate demo mode (automatically with ?demo=true)
const activateDemoMode = () => {
    console.log('🎭 Demo Mode activated');

    // Show the demo banner
    showDemoBanner();

    // Automatic "login"
    autoDemoLogin();
};

// Show the Demo Mode banner
const showDemoBanner = () => {
    // Check if the banner has already been added
    if (document.getElementById('demo-banner')) return;

    const banner = document.createElement('div');
    banner.id = 'demo-banner';
    banner.className = 'fixed top-0 left-0 right-0 bg-gradient-to-r from-yellow-400 via-yellow-500 to-yellow-400 text-gray-900 py-2 z-50 shadow-md';
    banner.innerHTML = `
        <div class="container mx-auto px-4 flex items-center justify-between">
            <div class="flex items-center gap-2">
                <span class="text-xl">🎭</span>
                <span class="font-bold text-sm uppercase tracking-wide">Demo Mode</span>
                <span class="hidden sm:inline text-sm opacity-80">— Exploring with sample data</span>
            </div>
            <button onclick="exitDemoMode()" class="px-3 py-1 bg-gray-900 text-yellow-400 rounded text-xs font-semibold hover:bg-gray-800 transition-colors">
                Exit Demo
            </button>
        </div>
    `;

    document.body.prepend(banner);

    // Shift the content down so the banner doesn't overlap
    document.body.style.paddingTop = '40px';
};

// Automatic login for demo
const autoDemoLogin = async () => {
    try {
        // Check if the user is already "logged in" via middleware
        const response = await fetch('/auth/user');

        if (response.ok) {
            const data = await response.json();

            if (data.authenticated && data.user) {
                console.log('✅ Demo user authenticated:', data.user.email);

                // Set the demo wallet
                window.userAddress = '0xdE3089c44de71234567890123456789012345678';

                // Initialize the app with the demo user
                if (typeof initializeApp === 'function') {
                    await initializeApp(data.user);
                }

                // Load tasks
                if (typeof loadTasks === 'function') {
                    await loadTasks();
                }

                return data.user;
            }
        }
    } catch (error) {
        console.error('Demo login failed:', error);
    }
};

// Exit demo mode
const exitDemoMode = async () => {
    try {
        // Call the API to exit demo mode (clears the session on the server)
        await fetch('/api/demo/exit', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Failed to exit demo mode:', error);
    }

    // Delete all demo cookies on the client
    document.cookie = 'demo_mode=; path=/; max-age=0';
    document.cookie = 'agentbounty_session=; path=/; max-age=0';

    // Clear localStorage
    localStorage.removeItem('demo_mode');

    // Reload to the main page
    window.location.href = '/';
};

// Add a watermark to the results (optional)
const addDemoWatermark = (element) => {
    if (!isDemoMode()) return;

    const watermark = document.createElement('div');
    watermark.className = 'text-xs text-gray-400 italic mt-2 border-t border-gray-200 pt-2';
    watermark.textContent = '🎭 Demo Mode - Sample data';

    element.appendChild(watermark);
};

// Initialize on page load
if (isDemoMode()) {
    // Wait for the DOM to load
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', activateDemoMode);
    } else {
        activateDemoMode();
    }
}

// Export functions to window for global access
window.isDemoMode = isDemoMode;
window.activateDemoMode = activateDemoMode;
window.exitDemoMode = exitDemoMode;
window.addDemoWatermark = addDemoWatermark;
