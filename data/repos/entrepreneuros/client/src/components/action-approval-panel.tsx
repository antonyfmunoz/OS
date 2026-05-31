import { useQuery, useMutation } from "@tanstack/react-query";
import { queryClient, apiRequest } from "@/lib/queryClient";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { CheckCircle, XCircle, Mail, FileText, ListTodo, Clock, Loader2 } from "lucide-react";
import { useToast } from "@/hooks/use-toast";

type AgentAction = {
  id: string;
  agentId: string;
  actionType: string;
  actionName: string;
  description: string | null;
  parameters: Record<string, any>;
  status: string;
  priority: string;
  estimatedTimeSaved: number | null;
  createdAt: string;
};

const actionIcons: Record<string, any> = {
  send_email: Mail,
  create_task: ListTodo,
  create_document: FileText,
};

const priorityColors: Record<string, string> = {
  low: "bg-gray-100 text-gray-700",
  medium: "bg-blue-100 text-blue-700",
  high: "bg-orange-100 text-orange-700",
  urgent: "bg-red-100 text-red-700",
};

function ActionDetails({ action }: { action: AgentAction }) {
  const params = action.parameters;
  switch (action.actionType) {
    case "send_email":
      return (
        <div className="text-sm space-y-1 mt-2">
          <div><span className="font-medium">To:</span> {params.to}</div>
          <div><span className="font-medium">Subject:</span> {params.subject}</div>
          {params.body && (
            <div className="text-gray-500 truncate max-w-xs">
              <span className="font-medium">Body:</span> {params.body}
            </div>
          )}
        </div>
      );
    case "create_task":
      return (
        <div className="text-sm space-y-1 mt-2">
          <div><span className="font-medium">Title:</span> {params.title}</div>
          {params.description && (
            <div className="text-gray-500 truncate max-w-xs">{params.description}</div>
          )}
          {params.priority && <Badge variant="outline">{params.priority}</Badge>}
        </div>
      );
    case "create_document":
      return (
        <div className="text-sm space-y-1 mt-2">
          <div><span className="font-medium">Title:</span> {params.title}</div>
          {params.content && (
            <div className="text-gray-500 truncate max-w-xs">{params.content}</div>
          )}
        </div>
      );
    default:
      return (
        <div className="text-sm text-gray-500 mt-2">
          {JSON.stringify(params, null, 2)}
        </div>
      );
  }
}

export function ActionApprovalPanel() {
  const { toast } = useToast();

  const { data: pendingActions = [], isLoading } = useQuery<AgentAction[]>({
    queryKey: ["/api/actions/pending"],
    refetchInterval: 10000,
  });

  const approveMutation = useMutation({
    mutationFn: async (actionId: string) => {
      const res = await apiRequest("POST", `/api/actions/${actionId}/approve`);
      return res.json();
    },
    onSuccess: (data) => {
      queryClient.invalidateQueries({ queryKey: ["/api/actions/pending"] });
      queryClient.invalidateQueries({ queryKey: ["/api/actions"] });
      toast({
        title: data.success ? "Action executed" : "Action failed",
        description: data.success 
          ? "The action was approved and executed successfully." 
          : `Error: ${data.error}`,
        variant: data.success ? "default" : "destructive",
      });
    },
    onError: (error: any) => {
      toast({
        title: "Error",
        description: error.message || "Failed to approve action",
        variant: "destructive",
      });
    },
  });

  const rejectMutation = useMutation({
    mutationFn: async (actionId: string) => {
      const res = await apiRequest("POST", `/api/actions/${actionId}/reject`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/actions/pending"] });
      queryClient.invalidateQueries({ queryKey: ["/api/actions"] });
      toast({ title: "Action rejected", description: "The action was rejected." });
    },
  });

  if (isLoading) {
    return (
      <Card>
        <CardContent className="flex items-center justify-center py-6">
          <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
        </CardContent>
      </Card>
    );
  }

  if (pendingActions.length === 0) return null;

  return (
    <Card className="mb-6">
      <CardHeader className="pb-3">
        <CardTitle className="text-base flex items-center gap-2">
          <Clock size={18} className="text-amber-500" />
          Pending Actions ({pendingActions.length})
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3">
        {pendingActions.map((action) => {
          const Icon = actionIcons[action.actionType] || ListTodo;
          return (
            <div
              key={action.id}
              className="border rounded-lg p-3 flex items-start justify-between gap-3"
            >
              <div className="flex items-start gap-3 flex-1 min-w-0">
                <div className="w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center flex-shrink-0 mt-0.5">
                  <Icon size={16} className="text-primary" />
                </div>
                <div className="flex-1 min-w-0">
                  <div className="flex items-center gap-2">
                    <span className="font-medium text-sm">{action.actionName}</span>
                    <Badge className={`text-xs ${priorityColors[action.priority || "medium"]}`} variant="secondary">
                      {action.priority}
                    </Badge>
                  </div>
                  {action.description && (
                    <p className="text-xs text-gray-500 mt-0.5">{action.description}</p>
                  )}
                  <ActionDetails action={action} />
                  {action.estimatedTimeSaved && (
                    <div className="text-xs text-green-600 mt-1 flex items-center gap-1">
                      <Clock size={12} />
                      Saves ~{action.estimatedTimeSaved} min
                    </div>
                  )}
                </div>
              </div>
              <div className="flex gap-1.5 flex-shrink-0">
                <Button
                  size="sm"
                  variant="default"
                  className="gap-1"
                  disabled={approveMutation.isPending}
                  onClick={() => approveMutation.mutate(action.id)}
                >
                  {approveMutation.isPending ? (
                    <Loader2 size={14} className="animate-spin" />
                  ) : (
                    <CheckCircle size={14} />
                  )}
                  Approve
                </Button>
                <Button
                  size="sm"
                  variant="outline"
                  className="gap-1"
                  disabled={rejectMutation.isPending}
                  onClick={() => rejectMutation.mutate(action.id)}
                >
                  <XCircle size={14} />
                  Reject
                </Button>
              </div>
            </div>
          );
        })}
      </CardContent>
    </Card>
  );
}
