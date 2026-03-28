/**
 * api.js — All fetch() calls to Django REST API
 */

// Auto-detect environment: local dev → localhost:8000, deployed → Railway
const API_BASE = (
    window.location.hostname === 'localhost' ||
    window.location.hostname === '127.0.0.1'
) ? 'http://localhost:8000/api'
  : 'https://greencred-production.up.railway.app/api';

// ── Auth Token Management ─────────────────────────────────────────────────

function getAuthToken() {
    return localStorage.getItem('gc_token') || '';
}

function getCurrentUser() {
    try {
        const u = localStorage.getItem('gc_user');
        return u ? JSON.parse(u) : null;
    } catch {
        return null;
    }
}

function setCurrentUser(user, token) {
    localStorage.setItem('gc_user', JSON.stringify(user));
    if (token) localStorage.setItem('gc_token', token);
}

function clearCurrentUser() {
    localStorage.removeItem('gc_user');
    localStorage.removeItem('gc_token');
}

// ── Base Fetch Wrapper ────────────────────────────────────────────────────

async function apiFetch(path, options = {}) {
    const token = getAuthToken();
    const headers = {
        ...options.headers,
    };

    if (token) {
        headers['Authorization'] = `Bearer ${token}`;
    }

    // Don't set Content-Type for FormData (browser does it)
    if (!(options.body instanceof FormData)) {
        headers['Content-Type'] = headers['Content-Type'] || 'application/json';
    }

    const response = await fetch(`${API_BASE}${path}`, {
        ...options,
        headers,
    });

    if (!response.ok) {
        let errorData;
        try {
            errorData = await response.json();
        } catch {
            errorData = { error: `HTTP ${response.status}` };
        }
        throw new Error(errorData.error || `HTTP ${response.status}`);
    }

    return response.json();
}

// ── Auth API ──────────────────────────────────────────────────────────────

async function authFirebase(token, extraData = {}) {
    return apiFetch('/auth/firebase/', {
        method: 'POST',
        body: JSON.stringify({ token, ...extraData }),
    });
}

async function authDemo(uid, displayName, email, photoUrl = '') {
    return apiFetch('/auth/firebase/', {
        method: 'POST',
        body: JSON.stringify({
            token: uid,
            uid,
            display_name: displayName,
            email,
            photo_url: photoUrl,
        }),
    });
}

// ── User API ──────────────────────────────────────────────────────────────

async function getUser(uid) {
    return apiFetch(`/users/${uid}/`);
}

async function updateUser(uid, data) {
    return apiFetch(`/users/${uid}/`, {
        method: 'PUT',
        body: JSON.stringify(data),
    });
}

// ── Actions API ───────────────────────────────────────────────────────────

async function getActions(filters = {}) {
    const params = new URLSearchParams();
    if (filters.type) params.set('type', filters.type);
    if (filters.user) params.set('user', filters.user);
    if (filters.challenge) params.set('challenge', filters.challenge);
    const query = params.toString() ? `?${params}` : '';
    return apiFetch(`/actions/${query}`);
}

async function createAction(formData) {
    const token = getAuthToken();
    const headers = {};
    if (token) headers['Authorization'] = `Bearer ${token}`;

    const response = await fetch(`${API_BASE}/actions/`, {
        method: 'POST',
        headers,
        body: formData,
    });

    if (!response.ok) {
        const err = await response.json().catch(() => ({ error: 'Upload failed' }));
        throw new Error(err.error || 'Upload failed');
    }

    return response.json();
}

async function likeAction(actionId) {
    return apiFetch(`/actions/${actionId}/like/`, { method: 'POST' });
}

// ── Challenges API ─────────────────────────────────────────────────────────

async function getChallenges(status = 'active') {
    return apiFetch(`/challenges/?status=${status}`);
}

async function createChallenge(data) {
    return apiFetch('/challenges/', {
        method: 'POST',
        body: JSON.stringify(data),
    });
}

async function getChallenge(id) {
    return apiFetch(`/challenges/${id}/`);
}

async function joinChallenge(id) {
    return apiFetch(`/challenges/${id}/join/`, { method: 'POST' });
}

// ── Badges API ─────────────────────────────────────────────────────────────

async function getBadges() {
    return apiFetch('/badges/');
}

async function getBadge(badgeId) {
    return apiFetch(`/badges/${badgeId}/`);
}

// ── Leaderboard API ────────────────────────────────────────────────────────

async function getLeaderboard(period = 'all') {
    return apiFetch(`/leaderboard/?period=${period}`);
}

// ── Seed API ───────────────────────────────────────────────────────────────

async function seedData() {
    return apiFetch('/seed/', { method: 'POST' });
}

async function clearData() {
    return apiFetch('/seed/', { method: 'DELETE' });
}

// ── Helper: Get action emoji ───────────────────────────────────────────────

function getActionEmoji(type) {
    const emojis = {
        tree_planting: '🌳',
        cleanup: '🧹',
        upcycling: '♻️',
        transport: '🚲',
        energy: '⚡',
        advocacy: '📣',
    };
    return emojis[type] || '🌿';
}

function getActionLabel(type) {
    const labels = {
        tree_planting: 'Tree Planting',
        cleanup: 'Clean-up Drive',
        upcycling: 'Upcycling / Repair',
        transport: 'Sustainable Transport',
        energy: 'Energy / Water Saving',
        advocacy: 'Community Advocacy',
    };
    return labels[type] || type;
}

function getRankEmoji(rank) {
    const emojis = { Seedling: '🌱', Sprout: '🌿', 'Grove Keeper': '🌲', 'Ecosystem Builder': '🌍', 'Earth Guardian': '⭐' };
    return emojis[rank] || '🌱';
}

function getRankClass(rank) {
    return 'rank-' + (rank || 'Seedling').replace(/ /g, '-');
}
