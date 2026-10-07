// Set theme immediately to avoid flash
const initTheme = localStorage.getItem('naromyqa_theme');
if (initTheme === 'dark') {
    document.documentElement.setAttribute('data-theme', 'dark');
}

document.addEventListener('DOMContentLoaded', () => {
    // Inject the floating button
    const btn = document.createElement('button');
    btn.className = 'theme-toggle-floating';
    btn.setAttribute('aria-label', 'Activer le mode sombre');
    btn.innerHTML = `
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="moon-icon"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg>
        <svg width="22" height="22" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" class="sun-icon" style="display:none;"><circle cx="12" cy="12" r="5"></circle><line x1="12" y1="1" x2="12" y2="3"></line><line x1="12" y1="21" x2="12" y2="23"></line><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"></line><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"></line><line x1="1" y1="12" x2="3" y2="12"></line><line x1="21" y1="12" x2="23" y2="12"></line><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"></line><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"></line></svg>
    `;
    document.body.appendChild(btn);

    const applyThemeUI = (theme) => {
        if (theme === 'dark') {
            btn.querySelector('.moon-icon').style.display = 'none';
            btn.querySelector('.sun-icon').style.display = 'block';
        } else {
            btn.querySelector('.moon-icon').style.display = 'block';
            btn.querySelector('.sun-icon').style.display = 'none';
        }
    };

    if (initTheme) {
        applyThemeUI(initTheme);
    }

    btn.addEventListener('click', () => {
        const theme = document.documentElement.getAttribute('data-theme') === 'dark' ? 'light' : 'dark';
        localStorage.setItem('naromyqa_theme', theme);
        if (theme === 'dark') {
            document.documentElement.setAttribute('data-theme', 'dark');
        } else {
            document.documentElement.removeAttribute('data-theme');
        }
        applyThemeUI(theme);
    });
});
