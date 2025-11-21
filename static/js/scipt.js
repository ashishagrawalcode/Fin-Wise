// Dark Mode Toggle Logic
const themeToggle = document.getElementById('theme-toggle');
const body = document.body;
const icon = themeToggle.querySelector('i');

// Check if user previously chose dark mode
if (localStorage.getItem('theme') === 'dark') {
    body.classList.add('dark-mode');
    icon.classList.remove('fa-moon');
    icon.classList.add('fa-sun');
}

themeToggle.addEventListener('click', () => {
    body.classList.toggle('dark-mode');
    
    // Swap Icon
    if (body.classList.contains('dark-mode')) {
        icon.classList.remove('fa-moon');
        icon.classList.add('fa-sun');
        localStorage.setItem('theme', 'dark');
    } else {
        icon.classList.remove('fa-sun');
        icon.classList.add('fa-moon');
        localStorage.setItem('theme', 'light');
    }
});

// AI Coach Placeholder (For future functionality)
function openCoach() {
    alert("AI Coach: Hello! I am ready to answer your financial questions. (Chat interface coming soon!)");
}

// Toggle Password Visibility
function togglePassword(icon) {
    const input = icon.previousElementSibling; // The input field before the icon
    
    if (input.type === "password") {
        input.type = "text";
        icon.classList.remove("fa-eye");
        icon.classList.add("fa-eye-slash");
    } else {
        input.type = "password";
        icon.classList.remove("fa-eye-slash");
        icon.classList.add("fa-eye");
    }
}

// --- Dashboard Privacy Toggle ---
let isPrivacyMode = false;

function togglePrivacy() {
    const moneyElements = document.querySelectorAll('.privacy-blur'); // We will add this class to money numbers
    const icon = document.getElementById('privacy-eye');

    isPrivacyMode = !isPrivacyMode;

    if (isPrivacyMode) {
        // Hide Money
        moneyElements.forEach(el => {
            el.dataset.value = el.innerText; // Store real value
            el.innerText = '••••';
        });
        icon.classList.remove('fa-eye-slash');
        icon.classList.add('fa-eye');
    } else {
        // Show Money
        moneyElements.forEach(el => {
            el.innerText = el.dataset.value; // Restore real value
        });
        icon.classList.remove('fa-eye');
        icon.classList.add('fa-eye-slash');
    }
}

// Toggle Mobile Drawer
function toggleDrawer() {
    const drawer = document.querySelector('.side-drawer');
    const overlay = document.querySelector('.drawer-overlay');
    
    if (drawer.classList.contains('open')) {
        drawer.classList.remove('open');
        overlay.classList.remove('open');
    } else {
        drawer.classList.add('open');
        overlay.classList.add('open');
    }
}

// Close drawer when clicking outside
document.addEventListener('DOMContentLoaded', () => {
    const overlay = document.querySelector('.drawer-overlay');
    if(overlay) {
        overlay.addEventListener('click', toggleDrawer);
    }
});