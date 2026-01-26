

// Define the components
const header = `
    <header class="site-header">
        <div class="site-header-content">
            <a href="index.html" class="site-header-title">Veckans Lunch</a>
            <nav class="site-header-nav">
                
                <a href="about.html" class="site-header-link">About</a>
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