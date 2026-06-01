import { initializeApp, cert, getApps, type ServiceAccount } from 'firebase-admin/app';
import { getAuth, type DecodedIdToken } from 'firebase-admin/auth';

let firebaseInitialized = false;

export function initializeFirebaseAdmin() {
  if (firebaseInitialized) return;

  try {
    const serviceAccountKey = process.env.FIREBASE_SERVICE_ACCOUNT_KEY;
    const projectId = process.env.VITE_FIREBASE_PROJECT_ID;

    if (!projectId) {
      console.log('Firebase Admin SDK not initialized: Missing VITE_FIREBASE_PROJECT_ID');
      return;
    }

    if (getApps().length > 0) {
      firebaseInitialized = true;
      return;
    }

    if (serviceAccountKey) {
      try {
        let keyToParse = serviceAccountKey.trim();
        if (!keyToParse.startsWith('{')) {
          keyToParse = Buffer.from(keyToParse, 'base64').toString('utf-8');
        }
        const serviceAccount = JSON.parse(keyToParse);
        if (serviceAccount.project_id) {
          serviceAccount.project_id = serviceAccount.project_id.trim();
        }
        if (serviceAccount.client_email) {
          serviceAccount.client_email = serviceAccount.client_email.trim();
        }
        initializeApp({
          credential: cert(serviceAccount as ServiceAccount),
          projectId: projectId.trim(),
        });
        firebaseInitialized = true;
        console.log('Firebase Admin SDK initialized with service account');
        return;
      } catch (parseError) {
        console.error('Failed to parse FIREBASE_SERVICE_ACCOUNT_KEY:', parseError);
      }
    } else {
      console.log('FIREBASE_SERVICE_ACCOUNT_KEY environment variable is not set');
    }

    const clientEmail = process.env.FIREBASE_CLIENT_EMAIL;
    const privateKey = process.env.FIREBASE_PRIVATE_KEY;

    if (clientEmail && privateKey) {
      initializeApp({
        credential: cert({
          projectId: projectId.trim(),
          clientEmail: clientEmail.trim(),
          privateKey: privateKey.replace(/\\n/g, '\n'),
        }),
        projectId: projectId.trim(),
      });
      firebaseInitialized = true;
      console.log('Firebase Admin SDK initialized with individual credentials');
      return;
    }

    console.log('Firebase Admin SDK not initialized: Missing service account credentials');
  } catch (error) {
    console.error('Error initializing Firebase Admin SDK:', error);
  }
}

export function isFirebaseAdminInitialized() {
  return firebaseInitialized;
}

export async function verifyFirebaseToken(idToken: string): Promise<DecodedIdToken> {
  if (!firebaseInitialized) {
    throw new Error('Firebase Admin SDK not initialized');
  }
  return getAuth().verifyIdToken(idToken);
}

export function getFirebaseAuth() {
  return getAuth();
}
