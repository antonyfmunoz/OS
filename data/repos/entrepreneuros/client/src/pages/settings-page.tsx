import { useState } from "react";
import { Layout } from "@/components/layout";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Button } from "@/components/ui/button";
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from "@/components/ui/card";
import { useAuth } from "@/hooks/use-auth";
import { Switch } from "@/components/ui/switch";
import { Label } from "@/components/ui/label";
import { Input } from "@/components/ui/input";
import { Link } from "wouter";
import { ExternalLink, Shield, ShieldCheck, Phone, Loader2, Mail, CheckCircle2 } from "lucide-react";
import { Alert, AlertDescription } from "@/components/ui/alert";
import { useToast } from "@/hooks/use-toast";
import { sendEmailVerification, Auth } from "firebase/auth";
import { auth as firebaseAuth, isFirebaseConfigured } from "@/lib/firebase";

export default function SettingsPage() {
  const { user, firebaseUser, isFirebaseReady, enrollMFA, verifyMFAEnrollment, resetPassword } = useAuth();
  const { toast } = useToast();
  const [mfaStep, setMfaStep] = useState<'idle' | 'phone' | 'verify'>('idle');
  const [phoneNumber, setPhoneNumber] = useState('');
  const [verificationCode, setVerificationCode] = useState('');
  const [verificationId, setVerificationId] = useState<string | null>(null);
  const [mfaLoading, setMfaLoading] = useState(false);
  const [emailVerifyLoading, setEmailVerifyLoading] = useState(false);

  const isMFAEnrolled = firebaseUser?.providerData?.some(p => p.providerId === 'phone') || 
    (firebaseUser as any)?.multiFactor?.enrolledFactors?.length > 0;

  const isEmailVerified = firebaseUser?.emailVerified ?? false;

  const handleStartMFA = () => {
    setMfaStep('phone');
  };

  const handleSendMFACode = async () => {
    if (!phoneNumber) {
      toast({ title: "Enter phone number", description: "Please enter your phone number", variant: "destructive" });
      return;
    }
    setMfaLoading(true);
    try {
      const vId = await enrollMFA(phoneNumber, 'recaptcha-container-settings');
      setVerificationId(vId);
      setMfaStep('verify');
      toast({ title: "Code sent", description: "A verification code has been sent to your phone." });
    } catch (error: any) {
      toast({ title: "Error", description: error.message || "Failed to send code", variant: "destructive" });
    } finally {
      setMfaLoading(false);
    }
  };

  const handleVerifyMFA = async () => {
    if (!verificationId || !verificationCode) return;
    setMfaLoading(true);
    try {
      await verifyMFAEnrollment(verificationId, verificationCode);
      setMfaStep('idle');
      setPhoneNumber('');
      setVerificationCode('');
    } catch (error: any) {
      toast({ title: "Verification failed", description: error.message || "Invalid code", variant: "destructive" });
    } finally {
      setMfaLoading(false);
    }
  };

  const handleResendVerification = async () => {
    if (!firebaseUser) return;
    setEmailVerifyLoading(true);
    try {
      await sendEmailVerification(firebaseUser);
      toast({ title: "Email sent", description: "A new verification email has been sent to your inbox." });
    } catch (error: any) {
      toast({ title: "Error", description: error.message || "Failed to send email", variant: "destructive" });
    } finally {
      setEmailVerifyLoading(false);
    }
  };

  const handlePasswordReset = async () => {
    if (!user?.email) return;
    await resetPassword(user.email);
  };
  
  return (
    <Layout title="Settings">
      <div className="space-y-6">
        <Tabs defaultValue="general" className="w-full">
          <TabsList className="mb-4">
            <TabsTrigger value="general">General</TabsTrigger>
            <TabsTrigger value="account">Account</TabsTrigger>
            <TabsTrigger value="security">Security</TabsTrigger>
            <TabsTrigger value="notifications">Notifications</TabsTrigger>
          </TabsList>

          <TabsContent value="general" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Interface Settings</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">Dark Mode</h3>
                    <p className="text-sm text-muted-foreground">Toggle dark mode for the interface</p>
                  </div>
                  <Switch id="dark-mode" />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">Compact View</h3>
                    <p className="text-sm text-muted-foreground">Display more content with less padding</p>
                  </div>
                  <Switch id="compact-view" />
                </div>
              </CardContent>
            </Card>
            
            <Card>
              <CardHeader>
                <CardTitle>Integrations</CardTitle>
              </CardHeader>
              <CardContent>
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">External Services</h3>
                    <p className="text-sm text-muted-foreground">Connect your agents to external tools and services</p>
                  </div>
                  <Button variant="outline" asChild>
                    <Link href="/integrations">
                      Manage Integrations
                      <ExternalLink className="h-4 w-4 ml-2" />
                    </Link>
                  </Button>
                </div>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="account" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Account Information</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                <div className="grid gap-2">
                  <Label htmlFor="name">Name</Label>
                  <input 
                    type="text" 
                    id="name" 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    defaultValue={user?.fullName || user?.username || ""}
                  />
                </div>
                
                <div className="grid gap-2">
                  <Label htmlFor="email">Email</Label>
                  <input 
                    type="email" 
                    id="email" 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    defaultValue={user?.email || ""}
                  />
                </div>
                
                <div className="grid gap-2">
                  <Label htmlFor="company">Company/Organization</Label>
                  <input 
                    type="text" 
                    id="company" 
                    className="w-full px-3 py-2 border border-gray-300 rounded-md"
                    defaultValue={user?.company || ""}
                  />
                </div>

                <Button className="mt-2">Save Changes</Button>
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="security" className="space-y-4">
            {!isFirebaseReady && (
              <Alert>
                <AlertDescription>
                  Security features like 2FA, email verification, and password reset require Firebase to be configured. These features will become available once Firebase credentials are set up.
                </AlertDescription>
              </Alert>
            )}

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Mail className="h-5 w-5" />
                  Email Verification
                </CardTitle>
                <CardDescription>
                  Verify your email address to secure your account
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isFirebaseReady && firebaseUser ? (
                  isEmailVerified ? (
                    <div className="flex items-center gap-2 text-green-600">
                      <CheckCircle2 className="h-5 w-5" />
                      <span className="font-medium">Email verified</span>
                    </div>
                  ) : (
                    <div className="space-y-3">
                      <p className="text-sm text-muted-foreground">
                        Your email address has not been verified yet. Click below to send a verification email.
                      </p>
                      <Button 
                        variant="outline" 
                        onClick={handleResendVerification}
                        disabled={emailVerifyLoading}
                      >
                        {emailVerifyLoading ? (
                          <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending...</>
                        ) : (
                          <><Mail className="mr-2 h-4 w-4" /> Send Verification Email</>
                        )}
                      </Button>
                    </div>
                  )
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Email verification is available when Firebase is configured.
                  </p>
                )}
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle className="flex items-center gap-2">
                  <Shield className="h-5 w-5" />
                  Two-Factor Authentication (2FA)
                </CardTitle>
                <CardDescription>
                  Add an extra layer of security with phone-based verification
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isFirebaseReady && firebaseUser ? (
                  <>
                    {isMFAEnrolled ? (
                      <div className="flex items-center gap-2 text-green-600">
                        <ShieldCheck className="h-5 w-5" />
                        <span className="font-medium">2FA is enabled</span>
                      </div>
                    ) : mfaStep === 'idle' ? (
                      <div className="space-y-3">
                        <p className="text-sm text-muted-foreground">
                          Protect your account by requiring a verification code from your phone when signing in.
                        </p>
                        <Button onClick={handleStartMFA}>
                          <Phone className="mr-2 h-4 w-4" />
                          Enable 2FA
                        </Button>
                      </div>
                    ) : mfaStep === 'phone' ? (
                      <div className="space-y-3">
                        <Label htmlFor="phone">Phone Number</Label>
                        <Input
                          id="phone"
                          placeholder="+1 (555) 000-0000"
                          value={phoneNumber}
                          onChange={(e) => setPhoneNumber(e.target.value)}
                        />
                        <p className="text-xs text-muted-foreground">
                          Enter your phone number with country code (e.g., +1 for US)
                        </p>
                        <div className="flex gap-2">
                          <Button onClick={handleSendMFACode} disabled={mfaLoading}>
                            {mfaLoading ? (
                              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Sending...</>
                            ) : "Send Code"}
                          </Button>
                          <Button variant="outline" onClick={() => setMfaStep('idle')}>
                            Cancel
                          </Button>
                        </div>
                      </div>
                    ) : (
                      <div className="space-y-3">
                        <Label htmlFor="mfa-code">Verification Code</Label>
                        <Input
                          id="mfa-code"
                          placeholder="123456"
                          maxLength={6}
                          value={verificationCode}
                          onChange={(e) => setVerificationCode(e.target.value)}
                          className="text-center text-lg tracking-widest max-w-[200px]"
                        />
                        <p className="text-xs text-muted-foreground">
                          Enter the 6-digit code sent to your phone
                        </p>
                        <div className="flex gap-2">
                          <Button onClick={handleVerifyMFA} disabled={mfaLoading}>
                            {mfaLoading ? (
                              <><Loader2 className="mr-2 h-4 w-4 animate-spin" /> Verifying...</>
                            ) : "Verify & Enable"}
                          </Button>
                          <Button variant="outline" onClick={() => { setMfaStep('phone'); setVerificationCode(''); }}>
                            Back
                          </Button>
                        </div>
                      </div>
                    )}
                  </>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Two-factor authentication is available when Firebase is configured.
                  </p>
                )}
                <div id="recaptcha-container-settings" />
              </CardContent>
            </Card>

            <Card>
              <CardHeader>
                <CardTitle>Password</CardTitle>
                <CardDescription>
                  Change your password or request a password reset
                </CardDescription>
              </CardHeader>
              <CardContent>
                {isFirebaseReady ? (
                  <Button variant="outline" onClick={handlePasswordReset}>
                    Send Password Reset Email
                  </Button>
                ) : (
                  <p className="text-sm text-muted-foreground">
                    Password reset via email is available when Firebase is configured.
                  </p>
                )}
              </CardContent>
            </Card>
          </TabsContent>

          <TabsContent value="notifications" className="space-y-4">
            <Card>
              <CardHeader>
                <CardTitle>Notification Preferences</CardTitle>
              </CardHeader>
              <CardContent className="space-y-6">
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">Task Notifications</h3>
                    <p className="text-sm text-muted-foreground">Receive notifications when tasks are assigned or completed</p>
                  </div>
                  <Switch id="task-notifications" defaultChecked />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">Agent Activity</h3>
                    <p className="text-sm text-muted-foreground">Notifications for new agent activities and updates</p>
                  </div>
                  <Switch id="agent-activity" defaultChecked />
                </div>
                
                <div className="flex items-center justify-between">
                  <div>
                    <h3 className="text-sm font-medium">System Updates</h3>
                    <p className="text-sm text-muted-foreground">Get notified about system updates and new features</p>
                  </div>
                  <Switch id="system-updates" defaultChecked />
                </div>
              </CardContent>
            </Card>
          </TabsContent>
        </Tabs>
      </div>
    </Layout>
  );
}
