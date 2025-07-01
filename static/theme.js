document.addEventListener('DOMContentLoaded', function() {
    const body = document.body;
    const switchBtn = document.getElementById('theme-switch');
    const THEME_KEY = 'collecteur_theme';
    function setTheme(theme) {
        if (theme === 'dark') {
            body.classList.add('dark');
            switchBtn.innerHTML = '🌙';
        } else {
            body.classList.remove('dark');
            switchBtn.innerHTML = '☀️';
        }
        localStorage.setItem(THEME_KEY, theme);
    }
    let theme = localStorage.getItem(THEME_KEY) || 'light';
    setTheme(theme);
    if (switchBtn) {
        switchBtn.onclick = function() {
            theme = (theme === 'dark') ? 'light' : 'dark';
            setTheme(theme);
        };
    }
}); 