// Firebase configuration for AGV Loan Management System
// Version: 1.1.0 - Added cache-busting and enhanced debugging
const FIREBASE_CONFIG_VERSION = "1.1.0";
console.log(`Firebase Config Loading - Version: ${FIREBASE_CONFIG_VERSION}`);

const firebaseConfig = {
  apiKey: "AIzaSyDdn3wwgunnrdYDAdAt82_zGyx2A_jh2ac",
  authDomain: "avg-finance-37e38.firebaseapp.com",
  projectId: "avg-finance-37e38",
  storageBucket: "avg-finance-37e38.appspot.com",
  messagingSenderId: "96272499240",
  appId: "1:96272499240:web:2e65debfad26d65472eb1d",
  measurementId: "G-P3MYNH97VL"
};

console.log("Firebase Config:", {
  ...firebaseConfig,
  apiKey: firebaseConfig.apiKey.substring(0, 10) + "..." // Partially hide API key for security
});

// Initialize Firebase with enhanced error handling and logging
try {
  console.log("Starting Firebase initialization...");
  
  // Check if Firebase SDK is loaded
  if (typeof firebase === 'undefined') {
    throw new Error("Firebase SDK not loaded");
  }
  
  // Check if the config has been properly updated
  if (firebaseConfig.apiKey.includes("REPLACE_WITH_YOUR")) {
    console.warn("Firebase is not properly configured. Please update the firebaseConfig object with your Firebase project details.");
    window.firebaseNotConfigured = true;
  } else {
    // Check if Firebase is already initialized
    if (firebase.apps.length === 0) {
      console.log("Initializing Firebase app...");
      const app = firebase.initializeApp(firebaseConfig);
      console.log("Firebase app initialized successfully:", app.name);
      
      // Verify Firebase Auth is available
      if (firebase.auth) {
        console.log("Firebase Auth module loaded successfully");
        // Set up auth state change listener for debugging
        firebase.auth().onAuthStateChanged((user) => {
          if (user) {
            console.log("Firebase Auth State: User signed in -", user.email);
          } else {
            console.log("Firebase Auth State: No user signed in");
          }
        });
      } else {
        console.error("Firebase Auth module not available");
        window.firebaseNotConfigured = true;
      }
    } else {
      console.log("Firebase app already initialized");
    }
  }
} catch (error) {
  console.error("Error initializing Firebase:", error);
  console.error("Error details:", {
    message: error.message,
    code: error.code,
    stack: error.stack
  });
  window.firebaseNotConfigured = true;
}

// Set global flag to indicate Firebase config completion
window.firebaseConfigLoaded = true;
console.log("Firebase configuration process completed. Not configured:", !!window.firebaseNotConfigured);