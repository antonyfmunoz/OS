import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Mail, Check, Loader2, Unplug } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

export function GmailConnectButton() {
  const { toast } = useToast();

  const { data: status, isLoading } = useQuery<{ connected: boolean; configured: boolean }>({
    queryKey: ["/api/integrations/gmail/status"],
  });

  const connectMutation = useMutation({
    mutationFn: async () => {
      const res = await apiRequest("GET", "/api/integrations/gmail/auth");
      const data = await res.json();
      return data.authUrl as string;
    },
    onSuccess: (authUrl) => {
      window.open(authUrl, "gmail-auth", "width=600,height=700,scrollbars=yes");
    },
    onError: (error: any) => {
      toast({
        title: "Connection Error",
        description: error.message || "Failed to start Gmail connection",
        variant: "destructive",
      });
    },
  });

  const disconnectMutation = useMutation({
    mutationFn: async () => {
      await apiRequest("POST", "/api/integrations/gmail/disconnect");
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/integrations/gmail/status"] });
      toast({ title: "Gmail disconnected", description: "Your Gmail account has been disconnected." });
    },
  });

  if (isLoading) {
    return (
      <div className="flex items-center gap-2 p-4 border rounded-lg">
        <Loader2 className="h-4 w-4 animate-spin" />
        <span className="text-sm text-muted-foreground">Checking Gmail status...</span>
      </div>
    );
  }

  if (!status?.configured) {
    return (
      <div className="flex items-center justify-between p-4 border rounded-lg bg-gray-50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
            <Mail className="w-5 h-5 text-red-600" />
          </div>
          <div>
            <h3 className="font-medium text-sm">Gmail</h3>
            <p className="text-xs text-gray-500">Not configured - requires Google OAuth credentials</p>
          </div>
        </div>
        <Badge variant="outline" className="text-xs">Setup Required</Badge>
      </div>
    );
  }

  if (status?.connected) {
    return (
      <div className="flex items-center justify-between p-4 border rounded-lg bg-green-50/50">
        <div className="flex items-center gap-3">
          <div className="w-10 h-10 bg-green-100 rounded-lg flex items-center justify-center">
            <Check className="w-5 h-5 text-green-600" />
          </div>
          <div>
            <h3 className="font-medium text-sm">Gmail</h3>
            <p className="text-xs text-green-600">Connected - agents can send emails</p>
          </div>
        </div>
        <Button
          variant="outline"
          size="sm"
          className="gap-1.5"
          onClick={() => disconnectMutation.mutate()}
          disabled={disconnectMutation.isPending}
        >
          <Unplug size={14} />
          Disconnect
        </Button>
      </div>
    );
  }

  return (
    <div className="flex items-center justify-between p-4 border rounded-lg">
      <div className="flex items-center gap-3">
        <div className="w-10 h-10 bg-red-100 rounded-lg flex items-center justify-center">
          <Mail className="w-5 h-5 text-red-600" />
        </div>
        <div>
          <h3 className="font-medium text-sm">Gmail</h3>
          <p className="text-xs text-gray-500">Connect to send emails through agents</p>
        </div>
      </div>
      <Button
        size="sm"
        className="gap-1.5"
        onClick={() => connectMutation.mutate()}
        disabled={connectMutation.isPending}
      >
        {connectMutation.isPending ? (
          <Loader2 size={14} className="animate-spin" />
        ) : (
          <Mail size={14} />
        )}
        Connect Gmail
      </Button>
    </div>
  );
}
