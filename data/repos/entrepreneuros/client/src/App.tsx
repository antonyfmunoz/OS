import { Switch, Route } from "wouter";
import { queryClient } from "./lib/queryClient";
import { QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "@/components/ui/toaster";
import NotFound from "@/pages/not-found";
import Dashboard from "@/pages/dashboard";
import TaskBoardPage from "@/pages/task-board-page";
import AgentChat from "@/pages/agent-chat";
import AgentProgramming from "@/pages/agent-programming";
import IntegrationsPage from "@/pages/integrations-page";
import AnalyticsPage from "@/pages/analytics-page";
import NotificationsPage from "@/pages/notifications-page";
import SettingsPage from "@/pages/settings-page";
import TutorialsPage from "@/pages/tutorials-page";
import SupportPage from "@/pages/support-page";
import CRMPage from "@/pages/crm-page";
import DocumentsPage from "@/pages/documents-page";


import AuthPage from "@/pages/auth-page";
import { AuthProvider } from "@/hooks/use-auth";
import { ProtectedRoute } from "@/lib/protected-route";

function Router() {
  return (
    <Switch>
      <ProtectedRoute path="/" component={Dashboard} />
      <ProtectedRoute path="/tasks" component={TaskBoardPage} />
      <ProtectedRoute path="/chat/:agentId">
        {(params) => <AgentChat params={params as {agentId: string}} />}
      </ProtectedRoute>
      <ProtectedRoute path="/agent-chat/:agentId">
        {(params) => <AgentChat params={params as {agentId: string}} />}
      </ProtectedRoute>
      {/* Legacy route kept for compatibility */}
      <Route path="/agent/:agentId/program">
        {(params) => <AgentProgramming agentId={params.agentId} />}
      </Route>
      {/* New agent programming route with agentId parameter */}
      <ProtectedRoute path="/agent-programming/:agentId">
        {(params) => <AgentProgramming agentId={params.agentId} />}
      </ProtectedRoute>
      {/* Generic agent programming route */}
      <ProtectedRoute path="/agent-programming">
        {() => <AgentProgramming />}
      </ProtectedRoute>
      <ProtectedRoute path="/integrations" component={IntegrationsPage} />
      <ProtectedRoute path="/analytics" component={AnalyticsPage} />
      <ProtectedRoute path="/crm" component={CRMPage} />
      <ProtectedRoute path="/documents" component={DocumentsPage} />
      <ProtectedRoute path="/settings" component={SettingsPage} />
      <ProtectedRoute path="/notifications" component={NotificationsPage} />
      <ProtectedRoute path="/support" component={SupportPage} />
      <ProtectedRoute path="/tutorials" component={TutorialsPage} />
      <Route path="/auth" component={AuthPage} />
      <Route component={NotFound} />
    </Switch>
  );
}

function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <AuthProvider>
        <Router />
        <Toaster />
      </AuthProvider>
    </QueryClientProvider>
  );
}

export default App;
