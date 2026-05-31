import { createContext, ReactNode, useContext, useEffect, useState } from "react";
import {
  useQuery,
  useMutation,
  UseMutationResult,
} from "@tanstack/react-query";
import type { User } from "@shared/schema";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { useToast } from "@/hooks/use-toast";
import { auth, googleProvider, isFirebaseConfigured } from "@/lib/firebase";
import {
  signInWithPopup,
  signInWithEmailAndPassword,
  createUserWithEmailAndPassword,
  sendEmailVerification,
  sendPasswordResetEmail,
  onAuthStateChanged,
  signOut,
  Auth,
  User as FirebaseUser,
  multiFactor,
  PhoneAuthProvider,
  PhoneMultiFactorGenerator,
  RecaptchaVerifier,
  getMultiFactorResolver,
  MultiFactorResolver,
} from "firebase/auth";
import { GoogleAuthProvider } from "firebase/auth";

type UserWithoutPassword = Omit<User, "password">;

type AuthContextType = {
  user: UserWithoutPassword | null;
  isLoading: boolean;
  error: Error | null;
  loginMutation: UseMutationResult<UserWithoutPassword, Error, LoginData>;
  logoutMutation: UseMutationResult<void, Error, void>;
  registerMutation: UseMutationResult<UserWithoutPassword, Error, RegisterData>;
  firebaseLoginMutation: UseMutationResult<void, Error, FirebaseLoginData>;
  firebaseRegisterMutation: UseMutationResult<void, Error, FirebaseRegisterData>;
  signInWithGoogle: () => Promise<void>;
  resetPassword: (email: string) => Promise<void>;
  isGoogleSignInAvailable: boolean;
  isFirebaseReady: boolean;
  firebaseUser: FirebaseUser | null;
  enrollMFA: (phoneNumber: string, recaptchaContainerId: string) => Promise<string>;
  verifyMFAEnrollment: (verificationId: string, code: string) => Promise<void>;
  mfaResolver: MultiFactorResolver | null;
  setMfaResolver: (resolver: MultiFactorResolver | null) => void;
  verifyMFASignIn: (verificationId: string, code: string) => Promise<void>;
  sendMFAVerificationCode: (phoneNumber: string, recaptchaContainerId: string) => Promise<string>;
};

type LoginData = {
  username: string;
  password: string;
};

type RegisterData = {
  username: string;
  password: string;
  email: string;
  fullName?: string;
  company?: string;
};

type FirebaseLoginData = {
  email: string;
  password: string;
};

type FirebaseRegisterData = {
  email: string;
  password: string;
  fullName?: string;
  company?: string;
};

export const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: ReactNode }) {
  const { toast } = useToast();
  const [firebaseUser, setFirebaseUser] = useState<FirebaseUser | null>(null);
  const [mfaResolver, setMfaResolver] = useState<MultiFactorResolver | null>(null);
  const [firebaseLoading, setFirebaseLoading] = useState(isFirebaseConfigured());

  const {
    data: userData,
    error,
    isLoading: queryLoading,
    refetch,
  } = useQuery<UserWithoutPassword | null, Error>({
    queryKey: ["/api/user"],
    queryFn: async () => {
      try {
        const res = await apiRequest("GET", "/api/user");
        if (res.status === 401) return null;
        if (!res.ok) throw new Error(`API error: ${res.status}`);
        return await res.json();
      } catch (error) {
        throw new Error(error instanceof Error ? error.message : "Unknown error");
      }
    },
  });
  
  const user = userData ?? null;
  const isLoading = queryLoading || firebaseLoading;

  const syncFirebaseUser = async (fbUser: FirebaseUser) => {
    try {
      const idToken = await fbUser.getIdToken();
      const res = await apiRequest("POST", "/api/auth/firebase", { idToken });
      if (res.ok) {
        const userData = await res.json();
        queryClient.setQueryData(["/api/user"], userData);
      }
    } catch (err) {
      console.error("Error syncing Firebase user:", err);
    }
  };

  useEffect(() => {
    if (isFirebaseConfigured() && auth) {
      const unsubscribe = onAuthStateChanged(auth as Auth, async (fbUser) => {
        setFirebaseUser(fbUser);
        if (fbUser) {
          await syncFirebaseUser(fbUser);
        }
        setFirebaseLoading(false);
      });
      return () => unsubscribe();
    } else {
      setFirebaseLoading(false);
    }
  }, []);

  const loginMutation = useMutation({
    mutationFn: async (credentials: LoginData) => {
      const res = await apiRequest("POST", "/api/login", credentials);
      if (!res.ok) {
        if (res.status === 401) throw new Error("Invalid username or password");
        throw new Error(`Login failed with status: ${res.status}`);
      }
      return await res.json();
    },
    onSuccess: (userData: UserWithoutPassword) => {
      queryClient.setQueryData(["/api/user"], userData);
      toast({ title: "Login successful", description: `Welcome back, ${userData.username}!` });
    },
    onError: (error: Error) => {
      toast({ title: "Login failed", description: error.message, variant: "destructive" });
    },
  });

  const firebaseLoginMutation = useMutation({
    mutationFn: async (data: FirebaseLoginData) => {
      if (!isFirebaseConfigured() || !auth) {
        throw new Error("Firebase is not configured");
      }
      try {
        const cred = await signInWithEmailAndPassword(auth as Auth, data.email, data.password);
        await syncFirebaseUser(cred.user);
      } catch (error: any) {
        if (error.code === 'auth/multi-factor-auth-required') {
          const resolver = getMultiFactorResolver(auth as Auth, error);
          setMfaResolver(resolver);
          throw new Error("MFA_REQUIRED");
        }
        if (error.code === 'auth/wrong-password' || error.code === 'auth/user-not-found' || error.code === 'auth/invalid-credential') {
          throw new Error("Invalid email or password");
        }
        if (error.code === 'auth/too-many-requests') {
          throw new Error("Too many attempts. Please try again later.");
        }
        throw error;
      }
    },
    onSuccess: () => {
      toast({ title: "Login successful", description: "Welcome back!" });
    },
    onError: (error: Error) => {
      if (error.message !== "MFA_REQUIRED") {
        toast({ title: "Login failed", description: error.message, variant: "destructive" });
      }
    },
  });

  const firebaseRegisterMutation = useMutation({
    mutationFn: async (data: FirebaseRegisterData) => {
      if (!isFirebaseConfigured() || !auth) {
        throw new Error("Firebase is not configured");
      }
      try {
        const cred = await createUserWithEmailAndPassword(auth as Auth, data.email, data.password);
        await sendEmailVerification(cred.user);
        await syncFirebaseUser(cred.user);
        toast({
          title: "Verification email sent",
          description: "Please check your inbox and verify your email address.",
        });
      } catch (error: any) {
        if (error.code === 'auth/email-already-in-use') {
          throw new Error("An account with this email already exists");
        }
        if (error.code === 'auth/weak-password') {
          throw new Error("Password should be at least 6 characters");
        }
        throw error;
      }
    },
    onSuccess: () => {
      toast({ title: "Account created", description: "Welcome to AgentOS!" });
    },
    onError: (error: Error) => {
      toast({ title: "Registration failed", description: error.message, variant: "destructive" });
    },
  });

  const registerMutation = useMutation({
    mutationFn: async (data: RegisterData) => {
      const res = await apiRequest("POST", "/api/register", data);
      if (!res.ok) {
        const errorData = await res.json().catch(() => ({ error: "Unknown error" }));
        throw new Error(errorData.error || `Registration failed with status: ${res.status}`);
      }
      return await res.json();
    },
    onSuccess: (userData: UserWithoutPassword) => {
      queryClient.setQueryData(["/api/user"], userData);
      toast({ title: "Registration successful", description: `Welcome to AgentOS, ${userData.username}!` });
    },
    onError: (error: Error) => {
      toast({ title: "Registration failed", description: error.message, variant: "destructive" });
    },
  });

  const logoutMutation = useMutation({
    mutationFn: async () => {
      if (isFirebaseConfigured() && auth) {
        await signOut(auth).catch(console.error);
      }
      const res = await apiRequest("POST", "/api/logout");
      if (!res.ok) throw new Error(`Logout failed with status: ${res.status}`);
    },
    onSuccess: () => {
      queryClient.setQueryData(["/api/user"], null);
      setFirebaseUser(null);
      toast({ title: "Logged out successfully" });
    },
    onError: (error: Error) => {
      toast({ title: "Logout failed", description: error.message, variant: "destructive" });
    },
  });

  const signInWithGoogle = async (): Promise<void> => {
    if (!isFirebaseConfigured() || !auth || !googleProvider) {
      toast({
        title: "Google Sign In not available",
        description: "Firebase configuration is missing",
        variant: "destructive",
      });
      return;
    }
    try {
      await signInWithPopup(auth as Auth, googleProvider as GoogleAuthProvider);
    } catch (error: any) {
      if (error.code === 'auth/multi-factor-auth-required') {
        const resolver = getMultiFactorResolver(auth as Auth, error);
        setMfaResolver(resolver);
        toast({
          title: "2FA Required",
          description: "Please enter your verification code",
        });
        return;
      }
      toast({
        title: "Google Sign In failed",
        description: error instanceof Error ? error.message : "Unknown error",
        variant: "destructive",
      });
    }
  };

  const resetPassword = async (email: string): Promise<void> => {
    if (!isFirebaseConfigured() || !auth) {
      toast({
        title: "Not available",
        description: "Firebase is not configured",
        variant: "destructive",
      });
      return;
    }
    try {
      await sendPasswordResetEmail(auth as Auth, email);
      toast({
        title: "Password reset email sent",
        description: "Check your inbox for instructions to reset your password.",
      });
    } catch (error: any) {
      if (error.code === 'auth/user-not-found') {
        toast({
          title: "Email not found",
          description: "No account exists with this email address.",
          variant: "destructive",
        });
        return;
      }
      toast({
        title: "Error",
        description: error.message || "Failed to send password reset email",
        variant: "destructive",
      });
    }
  };

  const enrollMFA = async (phoneNumber: string, recaptchaContainerId: string): Promise<string> => {
    if (!isFirebaseConfigured() || !auth || !firebaseUser) {
      throw new Error("Not authenticated");
    }
    const recaptchaVerifier = new RecaptchaVerifier(auth as Auth, recaptchaContainerId, { size: 'invisible' });
    const session = await multiFactor(firebaseUser).getSession();
    const phoneInfoOptions = { phoneNumber, session };
    const phoneAuthProvider = new PhoneAuthProvider(auth as Auth);
    const verificationId = await phoneAuthProvider.verifyPhoneNumber(phoneInfoOptions, recaptchaVerifier);
    return verificationId;
  };

  const verifyMFAEnrollment = async (verificationId: string, code: string): Promise<void> => {
    if (!firebaseUser) throw new Error("Not authenticated");
    const cred = PhoneAuthProvider.credential(verificationId, code);
    const multiFactorAssertion = PhoneMultiFactorGenerator.assertion(cred);
    await multiFactor(firebaseUser).enroll(multiFactorAssertion, "Phone Number");
    toast({ title: "2FA Enabled", description: "Two-factor authentication has been set up." });
  };

  const sendMFAVerificationCode = async (_phoneNumber: string, recaptchaContainerId: string): Promise<string> => {
    if (!mfaResolver || !auth) throw new Error("No MFA resolver available");
    const recaptchaVerifier = new RecaptchaVerifier(auth as Auth, recaptchaContainerId, { size: 'invisible' });
    const phoneInfoOptions = {
      multiFactorHint: mfaResolver.hints[0],
      session: mfaResolver.session,
    };
    const phoneAuthProvider = new PhoneAuthProvider(auth as Auth);
    const verificationId = await phoneAuthProvider.verifyPhoneNumber(phoneInfoOptions, recaptchaVerifier);
    return verificationId;
  };

  const verifyMFASignIn = async (verificationId: string, code: string): Promise<void> => {
    if (!mfaResolver) throw new Error("No MFA resolver available");
    const cred = PhoneAuthProvider.credential(verificationId, code);
    const multiFactorAssertion = PhoneMultiFactorGenerator.assertion(cred);
    const result = await mfaResolver.resolveSignIn(multiFactorAssertion);
    setMfaResolver(null);
    if (result.user) {
      await syncFirebaseUser(result.user);
    }
    toast({ title: "Login successful", description: "Welcome back!" });
  };

  return (
    <AuthContext.Provider
      value={{
        user,
        isLoading,
        error,
        loginMutation,
        logoutMutation,
        registerMutation,
        firebaseLoginMutation,
        firebaseRegisterMutation,
        signInWithGoogle,
        resetPassword,
        isGoogleSignInAvailable: isFirebaseConfigured(),
        isFirebaseReady: isFirebaseConfigured(),
        firebaseUser,
        enrollMFA,
        verifyMFAEnrollment,
        mfaResolver,
        setMfaResolver,
        verifyMFASignIn,
        sendMFAVerificationCode,
      }}
    >
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error("useAuth must be used within an AuthProvider");
  }
  return context;
}
