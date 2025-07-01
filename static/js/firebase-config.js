// Firebase configuration for AGV Loan Management System
const firebaseConfig = {
  apiKey: "AIzaSyDdn3wwgunnrdYDAdAt82_zGyx2A_jh2ac",
  authDomain: "avg-finance-37e38.firebaseapp.com",
  projectId: "avg-finance-37e38",
  storageBucket: "avg-finance-37e38.appspot.com",
  messagingSenderId: "96272499240",
  appId: "1:96272499240:web:2e65debfad26d65472eb1d",
  measurementId: "G-P3MYNH97VL"
};

// Initialize Firebase with proper checks and enhanced error handling
try {
  // Check if the config has been properly updated
  if (firebaseConfig.apiKey.includes("REPLACE_WITH_YOUR")) {
    console.warn("Firebase is not properly configured. Please update the firebaseConfig object with your Firebase project details.");
    // Create a global variable to indicate Firebase is not configured
    window.firebaseNotConfigured = true;
  } else {
    // Check if Firebase is already initialized to prevent re-initialization
    if (!firebase.apps.length) {
      console.log("Initializing Firebase with configuration:", {
        authDomain: firebaseConfig.authDomain,
        projectId: firebaseConfig.projectId,
        storageBucket: firebaseConfig.storageBucket
      });
      firebase.initializeApp(firebaseConfig);
      console.log("Firebase initialized successfully");
    } else {
      console.log("Firebase already initialized, skipping re-initialization");
    }
  }
} catch (error) {
  console.error("Error initializing Firebase:", error);
  console.error("Firebase configuration:", firebaseConfig);
  console.error("Error details:", error.message, error.stack);
  window.firebaseNotConfigured = true;
}