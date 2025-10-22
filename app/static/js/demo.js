/**
 * Demo Mode Frontend Module
 * Автоматическая активация demo режима и UI улучшения
 */

// Проверка активации demo режима
const isDemoMode = () => {
    const urlParams = new URLSearchParams(window.location.search);
    return urlParams.get('demo') === 'true' ||
           document.cookie.includes('demo_mode=true');
};

// Активация demo режима (автоматически при ?demo=true)
const activateDemoMode = () => {
    console.log('🎭 Demo Mode activated');

    // Показываем demo баннер
    showDemoBanner();

    // Автоматический "логин"
    autoDemoLogin();
};

// Показать баннер Demo Mode
const showDemoBanner = () => {
    // Проверяем, не добавлен ли уже баннер
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

    // Сдвигаем контент вниз, чтобы баннер не перекрывал
    document.body.style.paddingTop = '40px';
};

// Автоматический логин для demo
const autoDemoLogin = async () => {
    try {
        // Проверяем, что пользователь уже "залогинен" через middleware
        const response = await fetch('/auth/user');

        if (response.ok) {
            const data = await response.json();

            if (data.authenticated && data.user) {
                console.log('✅ Demo user authenticated:', data.user.email);

                // Устанавливаем demo wallet
                window.userAddress = '0xdE3089c44de71234567890123456789012345678';

                // Инициализируем приложение с demo пользователем
                if (typeof initializeApp === 'function') {
                    await initializeApp(data.user);
                }

                // Загружаем задачи
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

// Выход из demo режима
const exitDemoMode = async () => {
    try {
        // Вызываем API для выхода из demo (очищает session на сервере)
        await fetch('/api/demo/exit', {
            method: 'POST',
            credentials: 'include'
        });
    } catch (error) {
        console.error('Failed to exit demo mode:', error);
    }

    // Удаляем все demo cookies на клиенте
    document.cookie = 'demo_mode=; path=/; max-age=0';
    document.cookie = 'agentbounty_session=; path=/; max-age=0';

    // Очищаем localStorage
    localStorage.removeItem('demo_mode');

    // Перезагружаем на главную страницу
    window.location.href = '/';
};

// Добавить водяной знак на результаты (опционально)
const addDemoWatermark = (element) => {
    if (!isDemoMode()) return;

    const watermark = document.createElement('div');
    watermark.className = 'text-xs text-gray-400 italic mt-2 border-t border-gray-200 pt-2';
    watermark.textContent = '🎭 Demo Mode - Sample data';

    element.appendChild(watermark);
};

// Инициализация при загрузке страницы
if (isDemoMode()) {
    // Ждем загрузки DOM
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', activateDemoMode);
    } else {
        activateDemoMode();
    }
}

// Экспорт функций в window для глобального доступа
window.isDemoMode = isDemoMode;
window.activateDemoMode = activateDemoMode;
window.exitDemoMode = exitDemoMode;
window.addDemoWatermark = addDemoWatermark;
