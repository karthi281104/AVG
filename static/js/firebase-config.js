// Firebase configuration for AGV Loan Management System
const firebaseConfig = {
  apiKey: "AIzaSyDdn3wwgunnrdYDAdAt82_zGyx2A_jh2ac",
  authDomain: "avg-finance-37e38.firebaseapp.com",
  projectId: "avg-finance-37e38",
  storageBucket: "avg-finance-37e38.appspot.com",
  messagingSenderId: "96272499240",
  appId: "1:96272499240:web:2e65debfad26d65472eb1d",
};

// Global variables for Firebase state
window.firebaseApp = null;
window.firebaseAuth = null;
window.firebaseNotConfigured = false;

// Initialize Firebase with proper error handling
function initializeFirebase() {
  try {
    // Check if Firebase is available
    if (typeof firebase === 'undefined') {
      console.error("Firebase SDK not loaded");
      window.firebaseNotConfigured = true;
      return false;
    }

    // Check if Firebase is already initialized
    if (firebase.apps && firebase.apps.length > 0) {
      console.log("Firebase already initialized");
      window.firebaseApp = firebase.app();
      window.firebaseAuth = firebase.auth();
      return true;
    }

    // Initialize Firebase
    window.firebaseApp = firebase.initializeApp(firebaseConfig);
    window.firebaseAuth = firebase.auth();

    console.log("Firebase initialized successfully");

    // Set up auth state persistence
    firebase.auth().setPersistence(firebase.auth.Auth.Persistence.LOCAL)
      .then(() => {
        console.log("Firebase persistence set to LOCAL");
      })
      .catch((error) => {
        console.warn("Could not set Firebase persistence:", error);
      });

    return true;
  } catch (error) {
    console.error("Error initializing Firebase:", error);
    window.firebaseNotConfigured = true;
    return false;
  }
}

// Check if Firebase is ready
function isFirebaseReady() {
  return window.firebaseApp !== null && window.firebaseAuth !== null && !window.firebaseNotConfigured;
}

// Firebase authentication helper functions
const FirebaseAuth = {
  // Sign in with email and password
  signIn: async (email, password, rememberMe = false) => {
    if (!isFirebaseReady()) {
      throw new Error("Firebase is not initialized");
    }

    try {
      // Set persistence based on remember me option
      const persistence = rememberMe ?
        firebase.auth.Auth.Persistence.LOCAL :
        firebase.auth.Auth.Persistence.SESSION;

      await firebase.auth().setPersistence(persistence);

      // Sign in user
      const userCredential = await firebase.auth().signInWithEmailAndPassword(email, password);
      console.log("Firebase sign in successful:", userCredential.user.email);
      return userCredential;
    } catch (error) {
      console.error("Firebase sign in error:", error);
      throw error;
    }
  },

  // Sign out user
  signOut: async () => {
    if (!isFirebaseReady()) {
      return;
    }

    try {
      await firebase.auth().signOut();
      console.log("User signed out successfully");

      // Clear backend session
      await fetch('/api/auth/logout', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json'
        }
      });
    } catch (error) {
      console.error("Error signing out:", error);
    }
  },

  // Get current user
  getCurrentUser: () => {
    if (!isFirebaseReady()) {
      return null;
    }
    return firebase.auth().currentUser;
  },

  // Get ID token
  getIdToken: async () => {
    if (!isFirebaseReady()) {
      throw new Error("Firebase is not initialized");
    }

    const user = firebase.auth().currentUser;
    if (!user) {
      throw new Error("No user is signed in");
    }

    return await user.getIdToken();
  },

  // Listen to auth state changes
  onAuthStateChanged: (callback) => {
    if (!isFirebaseReady()) {
      return () => {}; // Return empty unsubscribe function
    }
    return firebase.auth().onAuthStateChanged(callback);
  }
};

// Initialize Firebase when the script loads
document.addEventListener('DOMContentLoaded', function() {
  console.log("Initializing Firebase...");
  setTimeout(() => {
    initializeFirebase();
  }, 500);
});

// Export functions to global scope for use in other scripts
window.isFirebaseReady = isFirebaseReady;
window.FirebaseAuth = FirebaseAuth;
window.initializeFirebase = initializeFirebase;