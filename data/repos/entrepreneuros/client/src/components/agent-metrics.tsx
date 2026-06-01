import { useQuery } from "@tanstack/react-query";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { BarChart3, Clock, Zap, MessageSquare, Loader2 } from "lucide-react";

type MetricData = {
  id: string;
  agentId: string;
  date: string;
  messagesSent: number;
  messagesReceived: number;
  tasksCompleted: number;
  actionsExecuted: number;
  tokensUsed: number;
  apiCost: string;
  estimatedTimeSavedMinutes: number;
};

export function AgentMetrics({ agentId }: { agentId: string }) {
  const { data: metrics = [], isLoading } = useQuery<MetricData[]>({
    queryKey: [`/api/agents/${agentId}/metrics`],
  });

  if (isLoading) {
    return (
      <div className="flex items-center justify-center py-8">
        <Loader2 className="h-5 w-5 animate-spin text-muted-foreground" />
      </div>
    );
  }

  const totals = metrics.reduce(
    (acc, m) => ({
      messages: acc.messages + (m.messagesSent || 0) + (m.messagesReceived || 0),
      tasks: acc.tasks + (m.tasksCompleted || 0),
      actions: acc.actions + (m.actionsExecuted || 0),
      timeSaved: acc.timeSaved + (m.estimatedTimeSavedMinutes || 0),
      cost: acc.cost + parseFloat(m.apiCost || "0"),
    }),
    { messages: 0, tasks: 0, actions: 0, timeSaved: 0, cost: 0 }
  );

  const stats = [
    {
      label: "Messages",
      value: totals.messages,
      icon: MessageSquare,
      color: "text-blue-500",
      bgColor: "bg-blue-50",
    },
    {
      label: "Actions Executed",
      value: totals.actions,
      icon: Zap,
      color: "text-amber-500",
      bgColor: "bg-amber-50",
    },
    {
      label: "Tasks Completed",
      value: totals.tasks,
      icon: BarChart3,
      color: "text-green-500",
      bgColor: "bg-green-50",
    },
    {
      label: "Time Saved",
      value: `${totals.timeSaved}m`,
      icon: Clock,
      color: "text-[#5e17eb]",
      bgColor: "bg-[#5e17eb]/10",
    },
  ];

  return (
    <Card>
      <CardHeader className="pb-3">
        <CardTitle className="text-base">Performance Metrics</CardTitle>
      </CardHeader>
      <CardContent>
        <div className="grid grid-cols-2 md:grid-cols-4 gap-3">
          {stats.map((stat) => (
            <div key={stat.label} className={`${stat.bgColor} rounded-lg p-3 text-center`}>
              <stat.icon className={`${stat.color} mx-auto mb-1`} size={20} />
              <div className="text-lg font-semibold">{stat.value}</div>
              <div className="text-xs text-gray-500">{stat.label}</div>
            </div>
          ))}
        </div>
        {totals.cost > 0 && (
          <div className="mt-3 text-xs text-gray-500 text-center">
            Total API cost: ${totals.cost.toFixed(4)}
          </div>
        )}
      </CardContent>
    </Card>
  );
}
