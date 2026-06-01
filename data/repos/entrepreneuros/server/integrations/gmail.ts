import { google } from "googleapis";
import { storage } from "../storage";

const SCOPES = [
  "https://www.googleapis.com/auth/gmail.send",
  "https://www.googleapis.com/auth/gmail.readonly",
  "https://www.googleapis.com/auth/gmail.compose",
];

function getOAuth2Client() {
  const clientId = process.env.GOOGLE_CLIENT_ID;
  const clientSecret = process.env.GOOGLE_CLIENT_SECRET;
  const redirectUri = process.env.GOOGLE_REDIRECT_URI || "http://localhost:5000/api/auth/google/callback";

  if (!clientId || !clientSecret) {
    throw new Error("Google OAuth credentials not configured. Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET.");
  }

  return new google.auth.OAuth2(clientId, clientSecret, redirectUri);
}

export function getAuthUrl(): string {
  const oauth2Client = getOAuth2Client();
  return oauth2Client.generateAuthUrl({
    access_type: "offline",
    scope: SCOPES,
    prompt: "consent",
  });
}

export async function exchangeCode(code: string): Promise<{
  accessToken: string;
  refreshToken?: string;
  expiresAt?: Date;
  scope?: string;
}> {
  const oauth2Client = getOAuth2Client();
  const { tokens } = await oauth2Client.getToken(code);

  return {
    accessToken: tokens.access_token || "",
    refreshToken: tokens.refresh_token || undefined,
    expiresAt: tokens.expiry_date ? new Date(tokens.expiry_date) : undefined,
    scope: tokens.scope || undefined,
  };
}

export async function getAccessToken(userId: string): Promise<string> {
  const token = await storage.getOauthToken(userId, "gmail");
  if (!token) {
    throw new Error("Gmail not connected. Please connect Gmail first.");
  }

  if (token.expiresAt && new Date(token.expiresAt) < new Date()) {
    if (!token.refreshToken) {
      throw new Error("Gmail token expired and no refresh token available. Please reconnect Gmail.");
    }
    const oauth2Client = getOAuth2Client();
    oauth2Client.setCredentials({ refresh_token: token.refreshToken });
    const { credentials } = await oauth2Client.refreshAccessToken();

    await storage.upsertOauthToken({
      userId,
      provider: "gmail",
      accessToken: credentials.access_token || token.accessToken,
      refreshToken: credentials.refresh_token || token.refreshToken,
      expiresAt: credentials.expiry_date ? new Date(credentials.expiry_date) : undefined,
      scope: token.scope || undefined,
    });

    return credentials.access_token || token.accessToken;
  }

  return token.accessToken;
}

export async function sendEmail(
  userId: string,
  params: { to: string; subject: string; body: string; cc?: string; bcc?: string }
): Promise<{ messageId: string }> {
  const accessToken = await getAccessToken(userId);
  const oauth2Client = getOAuth2Client();
  oauth2Client.setCredentials({ access_token: accessToken });

  const gmail = google.gmail({ version: "v1", auth: oauth2Client });

  const headers = [
    `To: ${params.to}`,
    `Subject: ${params.subject}`,
    `Content-Type: text/html; charset=utf-8`,
  ];
  if (params.cc) headers.push(`Cc: ${params.cc}`);
  if (params.bcc) headers.push(`Bcc: ${params.bcc}`);

  const email = headers.join("\r\n") + "\r\n\r\n" + params.body;
  const encodedMessage = Buffer.from(email)
    .toString("base64")
    .replace(/\+/g, "-")
    .replace(/\//g, "_")
    .replace(/=+$/, "");

  const result = await gmail.users.messages.send({
    userId: "me",
    requestBody: { raw: encodedMessage },
  });

  return { messageId: result.data.id || "" };
}

export async function isConnected(userId: string): Promise<boolean> {
  try {
    const token = await storage.getOauthToken(userId, "gmail");
    return !!token;
  } catch {
    return false;
  }
}

export function isConfigured(): boolean {
  return !!(process.env.GOOGLE_CLIENT_ID && process.env.GOOGLE_CLIENT_SECRET);
}
