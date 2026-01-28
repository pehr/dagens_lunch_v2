
const pathParts = window.location.pathname.split('/').filter(Boolean);
const inSubfolder =
    pathParts.length > 1 ||
    (pathParts.length === 1 && !["index.html", "about.html", "restaurant.html"].includes(pathParts[0]));
const linkPrefix = inSubfolder ? ".." : ".";

// Define the components
const header = `
    <header class="site-header">
        <div class="site-header-content">
            <a href="${linkPrefix}/index.html" class="site-header-title">Veckans Lunch</a>
            <div class="nav-wrap">
                <button class="nav-toggle" type="button" aria-expanded="false" aria-label="Menu">
                    <span class="nav-toggle-text">Menu</span>
                    <svg xmlns="http://www.w3.org/2000/svg" class="nav-toggle-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor">
                        <path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 9l-7 7-7-7" />
                    </svg>
                </button>
                <nav class="site-header-nav">
                    <a href="${linkPrefix}/index.html" class="site-header-link">Göteborg</a>
                    <a href="${linkPrefix}/kungsbacka/index.html" class="site-header-link">Kungsbacka</a>
                    <a href="${linkPrefix}/stockholm/index.html" class="site-header-link">Stockholm</a>
                    <a href="${linkPrefix}/about.html" class="site-header-link">About</a>
                </nav>
            </div>
        </div>
    </header>
`;

const footer = `
    <footer class="site-footer">
        <div class="site-footer-content">
            <p>&copy; 2025 padev.se. All rights reserved.</p>
        </div>
    </footer>
`;

// Insert components when the DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    // Insert header at the beginning of the body
    document.body.insertAdjacentHTML('afterbegin', header);
    
    // Insert footer at the end of the body
    document.body.insertAdjacentHTML('beforeend', footer);

    const toggle = document.querySelector('.nav-toggle');
    const nav = document.querySelector('.site-header-nav');
    if (toggle && nav) {
        toggle.addEventListener('click', () => {
            const isOpen = nav.classList.toggle('is-open');
            toggle.setAttribute('aria-expanded', isOpen ? 'true' : 'false');
        });
    }
}); 
