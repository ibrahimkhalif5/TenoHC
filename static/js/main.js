// THHIMS Custom JavaScript

document.addEventListener('DOMContentLoaded', function() {
    // Auto-dismiss alerts after 5 seconds (single handler)
    document.querySelectorAll('.messages-container .alert').forEach(function(el) {
        setTimeout(function() {
            bootstrap.Alert.getOrCreateInstance(el).close();
        }, 5000);
    });
});

// Sidebar toggle for mobile
function toggleSidebar() {
    const sidebar = document.getElementById('sidebar');
    const overlay = document.getElementById('sidebarOverlay');
    sidebar.classList.toggle('show');
    overlay.classList.toggle('show');
}
