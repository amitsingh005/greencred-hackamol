/**
 * auth.js — Auth state management + Firebase Google Auth
 * In demo mode (no Firebase), uses localStorage user directly.
 */

// ── Toast Notification System ─────────────────────────────────────────────

function showToast(message, type = 'success', duration = 3000) {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;
    toast.textContent = message;
    container.appendChild(toast);

    setTimeout(() => {
        toast.classList.add('out');
        setTimeout(() => toast.remove(), 300);
    }, duration);
}

// ── Auth Guard ────────────────────────────────────────────────────────────

function requireAuth() {
    const user = getCurrentUser();
    if (!user) {
        window.location.href = '/login/';
        return null;
    }
    return user;
}

function redirectIfLoggedIn() {
    const user = getCurrentUser();
    if (user) {
        window.location.href = '/';
    }
}

// ── Sidebar Initializer ────────────────────────────────────────────────────

function initSidebar() {
    const user = getCurrentUser();

    // Set active nav link
    const currentPath = window.location.pathname;
    document.querySelectorAll('.nav-link').forEach(link => {
        link.classList.remove('active');
        const href = link.getAttribute('href');
        if (href === currentPath || (href === '/' && currentPath === '/')) {
            link.classList.add('active');
        } else if (href !== '/' && currentPath.startsWith(href)) {
            link.classList.add('active');
        }
    });

    // Update sidebar user info
    if (user) {
        const nameEl = document.getElementById('sidebar-user-name');
        const rankEl = document.getElementById('sidebar-user-rank');
        const avatarEl = document.getElementById('sidebar-user-avatar');
        const gcEl = document.getElementById('sidebar-user-gc');

        if (nameEl) nameEl.textContent = user.display_name || 'User';
        if (rankEl) rankEl.textContent = `${getRankEmoji(user.rank)} ${user.rank || 'Seedling'} • ${user.green_credits || 0} GC`;
        if (avatarEl && user.photo_url) avatarEl.src = user.photo_url;
        if (gcEl) gcEl.textContent = `${user.green_credits || 0} GC`;
    }

    // Mobile sidebar toggle
    const menuBtn = document.getElementById('mobile-menu-btn');
    const sidebar = document.querySelector('.sidebar');
    const overlay = document.querySelector('.sidebar-overlay');

    if (menuBtn && sidebar && overlay) {
        menuBtn.addEventListener('click', () => {
            sidebar.classList.toggle('open');
            overlay.classList.toggle('open');
        });

        overlay.addEventListener('click', () => {
            sidebar.classList.remove('open');
            overlay.classList.remove('open');
        });
    }

    // Logout
    const logoutBtn = document.getElementById('logout-btn');
    if (logoutBtn) {
        logoutBtn.addEventListener('click', () => {
            clearCurrentUser();
            window.location.href = '/login/';
        });
    }
}

// ── Firebase Auth (Production) ──────────────────────────────────────────────

async function signInWithGoogle() {
    // Try Firebase if configured
    if (typeof firebase !== 'undefined' && firebase.apps && firebase.apps.length > 0) {
        try {
            const provider = new firebase.auth.GoogleAuthProvider();
            const result = await firebase.auth().signInWithPopup(provider);
            const token = await result.user.getIdToken();

            const data = await authFirebase(token);
            setCurrentUser(data.user, token);
            showToast(`Welcome, ${data.user.display_name}! 🌿`, 'success');
            window.location.href = '/';
            return;
        } catch (err) {
            console.error('Firebase sign-in failed:', err);
            showToast('Google sign-in failed. Please try demo mode.', 'error');
            return;
        }
    }

    showToast('Firebase not configured. Use demo login.', 'info');
}

// ── Demo Auth (Development) ────────────────────────────────────────────────

async function signInDemo(uid, displayName, email, photoUrl) {
    try {
        const data = await authDemo(uid, displayName, email, photoUrl);
        setCurrentUser(data.user, uid);
        showToast(`Welcome, ${data.user.display_name}! 🌿`, 'success');
        setTimeout(() => { window.location.href = '/'; }, 800);
    } catch (err) {
        console.error('Demo login failed:', err);
        showToast('Login failed. Make sure Django is running.', 'error');
    }
}

// ── Refresh User Data ──────────────────────────────────────────────────────

async function refreshCurrentUser() {
    const user = getCurrentUser();
    if (!user) return null;
    try {
        const data = await getUser(user.firebase_uid);
        setCurrentUser(data.user, getAuthToken());
        return data.user;
    } catch (err) {
        console.error('Failed to refresh user:', err);
        return user;
    }
}

// ── Firebase Token Auto-Refresh ────────────────────────────────────────────

function startFirebaseTokenRefresh() {
    // Refresh the Firebase ID token every 55 minutes (tokens expire at 60 min)
    // Only runs if Firebase is initialized and user is logged in
    const REFRESH_INTERVAL = 55 * 60 * 1000;

    setInterval(async () => {
        try {
            if (typeof firebase !== 'undefined' && firebase.apps && firebase.apps.length > 0) {
                const fbUser = firebase.auth().currentUser;
                if (fbUser) {
                    const newToken = await fbUser.getIdToken(true);
                    localStorage.setItem('gc_token', newToken);
                    console.log('Firebase token refreshed.');
                }
            }
        } catch (err) {
            console.warn('Token refresh failed:', err);
        }
    }, REFRESH_INTERVAL);
}

// ── Auto-init ─────────────────────────────────────────────────────────────

document.addEventListener('DOMContentLoaded', () => {
    initSidebar();
    startFirebaseTokenRefresh();
});
