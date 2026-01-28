
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
            <nav class="site-header-nav">
                <a href="${linkPrefix}/index.html" class="site-header-link">Göteborg</a>
                <a href="${linkPrefix}/kungsbacka/index.html" class="site-header-link">Kungsbacka</a>
                <a href="${linkPrefix}/stockholm/index.html" class="site-header-link">Stockholm</a>
                <a href="${linkPrefix}/about.html" class="site-header-link">About</a>
            </nav>
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
}); 
