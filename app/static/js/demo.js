/**
 * Demo Mode Frontend Module
 * Automatic activation of demo mode and UI improvements
 */

// Check for demo mode activation
const isDemoMode = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const hasDemoParam = urlParams.get('demo') === 'true';
    const hasDemoCookie = document.cookie.includes('demo_mode=true');

    return hasDemoParam || hasDemoCookie;
};

// Set demo mode cookie
const setDemoCookie = () => {
    // Set cookie for 1 hour
    const expiresAt = new Date(Date.now() + 3600 * 1000).toUTCString();
    document.cookie = `demo_mode=true; path=/; expires=${expiresAt}; SameSite=Lax`;
    console.log('🍪 Demo mode cookie set');
};

// Check if we need to force reload to activate demo mode
const checkAndActivateDemoMode = () => {
    const urlParams = new URLSearchParams(window.location.search);
    const hasDemoParam = urlParams.get('demo') === 'true';
    const hasDemoCookie = document.cookie.includes('demo_mode=true');
    const hasReloadFlag = sessionStorage.getItem('demo_reload_attempted');

    // If we have ?demo=true but no cookie and haven't tried reloading yet
    if (hasDemoParam && !hasDemoCookie && !hasReloadFlag) {
        console.log('🔄 Setting demo cookie and reloading...');
        setDemoCookie();
        sessionStorage.setItem('demo_reload_attempted', 'true');
        // Force hard reload
        window.location.reload(true);
        return false; // Don't continue initialization
    }

    // Clear reload flag if we're in demo mode
    if (hasDemoCookie) {
        sessionStorage.removeItem('demo_reload_attempted');
    }

    return hasDemoParam || hasDemoCookie;
};

// Activate demo mode (automatically with ?demo=true)
const activateDemoMode = async () => {
    console.log('🎭 Demo Mode activated');

    // Ensure cookie is set
    if (!document.cookie.includes('demo_mode=true')) {
        setDemoCookie();
    }

    // Show the demo banner
    showDemoBanner();

    // Automatic "login"
    await autoDemoLogin();
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
        // Create demo user object directly (no need to fetch from server)
        const demoUser = {
            sub: 'demo|user_12345',
            email: 'demo@agentbounty.com',
            name: 'Demo User',
            nickname: 'demo',
            picture: 'https://i.pravatar.cc/150?img=68',
            email_verified: true
        };

        console.log('✅ Demo user initialized:', demoUser.email);

        // Set the demo wallet
        window.userAddress = '0xdE3089c44de71234567890123456789012345678';
        window.demoWallet = true;

        // Initialize the app with the demo user
        if (typeof initializeApp === 'function') {
            await initializeApp(demoUser);
        }

        // Load tasks
        if (typeof loadTasks === 'function') {
            await loadTasks();
        }

        return demoUser;
    } catch (error) {
        console.error('Demo initialization failed:', error);
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

    // Clear localStorage and sessionStorage
    localStorage.removeItem('demo_mode');
    sessionStorage.removeItem('demo_reload_attempted');

    // Reload to the main page (without ?demo=true)
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

// Initialize on page load with reload check
const initDemoMode = () => {
    // Check and potentially reload
    const shouldActivate = checkAndActivateDemoMode();

    if (shouldActivate && isDemoMode()) {
        // Wait for the DOM to load
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', activateDemoMode);
        } else {
            activateDemoMode();
        }
    }
};

// Start initialization
initDemoMode();

// Export functions to window for global access
window.isDemoMode = isDemoMode;
window.activateDemoMode = activateDemoMode;
window.exitDemoMode = exitDemoMode;
window.addDemoWatermark = addDemoWatermark;
window.setDemoCookie = setDemoCookie;
