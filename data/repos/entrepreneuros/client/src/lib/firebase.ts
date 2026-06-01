import { initializeApp, FirebaseApp } from "firebase/app";
import { getAuth, GoogleAuthProvider, Auth, RecaptchaVerifier } from "firebase/auth";

const hasAllConfig = 
  !!import.meta.env.VITE_FIREBASE_API_KEY &&
  !!import.meta.env.VITE_FIREBASE_PROJECT_ID &&
  !!import.meta.env.VITE_FIREBASE_APP_ID;

const firebaseConfig = {
  apiKey: import.meta.env.VITE_FIREBASE_API_KEY || '',
  authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN || `${import.meta.env.VITE_FIREBASE_PROJECT_ID || 'placeholder'}.firebaseapp.com`,
  projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID || '',
  storageBucket: `${import.meta.env.VITE_FIREBASE_PROJECT_ID || 'placeholder'}.firebasestorage.app`,
  appId: import.meta.env.VITE_FIREBASE_APP_ID || '',
};

let firebaseApp: FirebaseApp | null = null;
let auth: Auth | null = null;
let googleProvider: GoogleAuthProvider | null = null;

if (hasAllConfig) {
  try {
    firebaseApp = initializeApp(firebaseConfig);
    auth = getAuth(firebaseApp);
    googleProvider = new GoogleAuthProvider();
  } catch (error) {
    console.error("Firebase initialization error:", error);
    firebaseApp = null;
    auth = null;
    googleProvider = null;
  }
}

export { firebaseApp, auth, googleProvider };

export const isFirebaseConfigured = (): boolean => {
  return hasAllConfig && firebaseApp !== null && auth !== null;
};
