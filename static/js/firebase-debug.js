// Firebase Debug and Diagnostic Functions
// Version: 1.0.0
console.log("Firebase Debug module loaded - Version 1.0.0");

// Global debug object
window.FirebaseDebug = {
    version: "1.0.0",
    logs: [],
    
    // Add log entry with timestamp
    log: function(message, type = 'info', data = null) {
        const timestamp = new Date().toISOString();
        const logEntry = {
            timestamp,
            type,
            message,
            data
        };
        
        this.logs.push(logEntry);
        
        // Console output based on type
        switch(type) {
            case 'error':
                console.error(`[Firebase Debug] ${message}`, data);
                break;
            case 'warn':
                console.warn(`[Firebase Debug] ${message}`, data);
                break;
            case 'success':
                console.log(`[Firebase Debug] ✓ ${message}`, data);
                break;
            default:
                console.log(`[Firebase Debug] ${message}`, data);
        }
        
        // Update UI debug panel if it exists
        this.updateDebugPanel();
    },
    
    // Test Firebase connection and SDK
    testFirebaseConnection: function() {
        this.log("Starting Firebase connection test...");
        
        // Test 1: Check if Firebase SDK is loaded
        if (typeof firebase === 'undefined') {
            this.log("Firebase SDK not loaded", 'error');
            return false;
        }
        this.log("Firebase SDK loaded successfully", 'success');
        
        // Test 2: Check if Firebase is initialized
        if (firebase.apps.length === 0) {
            this.log("No Firebase apps initialized", 'error');
            return false;
        }
        this.log(`Firebase app initialized: ${firebase.apps[0].name}`, 'success');
        
        // Test 3: Check Auth module
        if (!firebase.auth) {
            this.log("Firebase Auth module not available", 'error');
            return false;
        }
        this.log("Firebase Auth module available", 'success');
        
        // Test 4: Check current auth state
        const currentUser = firebase.auth().currentUser;
        if (currentUser) {
            this.log(`User already authenticated: ${currentUser.email}`, 'success', {
                uid: currentUser.uid,
                email: currentUser.email,
                emailVerified: currentUser.emailVerified
            });
        } else {
            this.log("No user currently authenticated", 'info');
        }
        
        // Test 5: Test auth state listener
        try {
            firebase.auth().onAuthStateChanged((user) => {
                if (user) {
                    this.log("Auth state changed: User signed in", 'success', {
                        uid: user.uid,
                        email: user.email
                    });
                } else {
                    this.log("Auth state changed: User signed out", 'info');
                }
            });
            this.log("Auth state listener attached successfully", 'success');
        } catch (error) {
            this.log("Failed to attach auth state listener", 'error', error);
            return false;
        }
        
        this.log("Firebase connection test completed successfully", 'success');
        return true;
    },
    
    // Test Firebase authentication with dummy credentials (won't actually sign in)
    testFirebaseAuth: function() {
        this.log("Testing Firebase Auth capabilities...");
        
        if (!firebase.auth) {
            this.log("Firebase Auth not available", 'error');
            return false;
        }
        
        // Test auth methods availability
        const authMethods = [
            'signInWithEmailAndPassword',
            'createUserWithEmailAndPassword',
            'signOut',
            'onAuthStateChanged',
            'setPersistence'
        ];
        
        authMethods.forEach(method => {
            if (typeof firebase.auth()[method] === 'function') {
                this.log(`Auth method '${method}' available`, 'success');
            } else {
                this.log(`Auth method '${method}' not available`, 'error');
            }
        });
        
        // Test persistence options
        const persistenceTypes = [
            'LOCAL',
            'SESSION',
            'NONE'
        ];
        
        persistenceTypes.forEach(type => {
            if (firebase.auth.Auth.Persistence[type] !== undefined) {
                this.log(`Persistence type '${type}' available`, 'success');
            } else {
                this.log(`Persistence type '${type}' not available`, 'error');
            }
        });
        
        this.log("Firebase Auth test completed", 'success');
        return true;
    },
    
    // Display debug information in the UI
    displayDebugInfo: function() {
        const debugContainer = document.getElementById('firebase-debug-info');
        if (!debugContainer) {
            // Create debug container if it doesn't exist
            const container = document.createElement('div');
            container.id = 'firebase-debug-info';
            container.style.cssText = `
                position: fixed;
                top: 10px;
                right: 10px;
                background: rgba(0,0,0,0.9);
                color: white;
                padding: 10px;
                border-radius: 5px;
                font-family: monospace;
                font-size: 12px;
                max-width: 400px;
                max-height: 300px;
                overflow-y: auto;
                z-index: 9999;
                display: none;
            `;
            document.body.appendChild(container);
        }
        
        this.updateDebugPanel();
        
        // Toggle visibility
        const panel = document.getElementById('firebase-debug-info');
        panel.style.display = panel.style.display === 'none' ? 'block' : 'none';
    },
    
    // Update debug panel content
    updateDebugPanel: function() {
        const debugContainer = document.getElementById('firebase-debug-info');
        if (!debugContainer) return;
        
        const recentLogs = this.logs.slice(-10); // Show last 10 logs
        const html = `
            <div style="font-weight: bold; margin-bottom: 10px;">Firebase Debug Panel</div>
            <div style="margin-bottom: 10px;">
                <strong>Status:</strong> ${window.firebaseNotConfigured ? '❌ Not Configured' : '✅ Configured'}<br>
                <strong>SDK Loaded:</strong> ${typeof firebase !== 'undefined' ? '✅ Yes' : '❌ No'}<br>
                <strong>Apps:</strong> ${typeof firebase !== 'undefined' ? firebase.apps.length : '0'}<br>
                <strong>Auth Available:</strong> ${typeof firebase !== 'undefined' && firebase.auth ? '✅ Yes' : '❌ No'}
            </div>
            <div style="border-top: 1px solid #ccc; padding-top: 10px;">
                <strong>Recent Logs:</strong><br>
                ${recentLogs.map(log => `
                    <div style="margin: 2px 0; color: ${this.getLogColor(log.type)};">
                        [${log.timestamp.split('T')[1].split('.')[0]}] ${log.message}
                    </div>
                `).join('')}
            </div>
            <div style="margin-top: 10px;">
                <button onclick="FirebaseDebug.testFirebaseConnection()" style="margin-right: 5px; padding: 2px 5px;">Test Connection</button>
                <button onclick="FirebaseDebug.testFirebaseAuth()" style="margin-right: 5px; padding: 2px 5px;">Test Auth</button>
                <button onclick="FirebaseDebug.clearLogs()" style="padding: 2px 5px;">Clear Logs</button>
            </div>
        `;
        
        debugContainer.innerHTML = html;
    },
    
    // Get color for log type
    getLogColor: function(type) {
        switch(type) {
            case 'error': return '#ff6b6b';
            case 'warn': return '#ffd93d';
            case 'success': return '#51cf66';
            default: return '#fff';
        }
    },
    
    // Clear debug logs
    clearLogs: function() {
        this.logs = [];
        this.updateDebugPanel();
        console.log("Firebase debug logs cleared");
    },
    
    // Export logs as JSON
    exportLogs: function() {
        const blob = new Blob([JSON.stringify(this.logs, null, 2)], {type: 'application/json'});
        const url = URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = `firebase-debug-logs-${new Date().toISOString().split('T')[0]}.json`;
        a.click();
        URL.revokeObjectURL(url);
    }
};

// Auto-run initial tests when the module loads
document.addEventListener('DOMContentLoaded', function() {
    // Wait a bit for Firebase to initialize
    setTimeout(() => {
        FirebaseDebug.log("Firebase Debug module initialized");
        FirebaseDebug.testFirebaseConnection();
    }, 1000);
});

// Add keyboard shortcut to toggle debug panel (Ctrl+Shift+F)
document.addEventListener('keydown', function(event) {
    if (event.ctrlKey && event.shiftKey && event.key === 'F') {
        event.preventDefault();
        FirebaseDebug.displayDebugInfo();
    }
});

// Make it globally accessible
console.log("Firebase Debug functions available globally as 'FirebaseDebug'");
console.log("Press Ctrl+Shift+F to toggle debug panel");