/**
 * firebase-config.js
 * ─────────────────────────────────────────────────────────
 * STEP 1: Create a Firebase project at https://console.firebase.google.com
 * STEP 2: Enable Authentication → Sign-in method → Google
 * STEP 3: Go to Project Settings → General → Your apps → Add Web App
 * STEP 4: Copy the firebaseConfig object and paste it below
 * STEP 5: Add your domain to Firebase → Authentication → Settings → Authorized domains
 * ─────────────────────────────────────────────────────────
 */

const FIREBASE_CONFIG = {
    apiKey: "YOUR_API_KEY",
    authDomain: "YOUR_PROJECT_ID.firebaseapp.com",
    projectId: "YOUR_PROJECT_ID",
    storageBucket: "YOUR_PROJECT_ID.appspot.com",
    messagingSenderId: "YOUR_SENDER_ID",
    appId: "YOUR_APP_ID"
};

// Set to true once you've pasted your real Firebase config above
const FIREBASE_CONFIGURED = false;
