import { Link } from "wouter";
import { Badge } from "@/components/ui/badge";
import { cn } from "@/lib/utils";

type AgentCardProps = {
  id: string;
  name: string;
  role: string;
  icon: string;
  latestActivity: string;
  tasks: Array<{
    id: string;
    title: string;
    status: "todo" | "in-progress" | "done";
  }>;
};

export function AgentCard({ id, name, role, icon, latestActivity, tasks }: AgentCardProps) {
  const getHeaderColor = (role: string) => {
    switch (role) {
      case "marketing":
        return "bg-primary";
      case "support":
        return "bg-secondary";
      case "content":
        return "bg-accent";
      case "operations":
        return "bg-gray-600";
      case "executive":
        return "bg-blue-600";
      case "assistant":
        return "bg-indigo-600";
      default:
        return "bg-gray-600";
    }
  };

  const getBadgeVariant = (role: string) => {
    switch (role) {
      case "marketing":
        return "marketing";
      case "support":
        return "support";
      case "content":
        return "content";
      case "operations":
        return "operations";
      default:
        return "default";
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case "todo":
        return "text-yellow-500";
      case "in-progress":
        return "text-yellow-500";
      case "done":
        return "text-green-500";
      default:
        return "text-gray-500";
    }
  };

  const getIconClass = (icon: string) => {
    return icon || "ri-robot-line";
  };

  return (
    <div className="bg-white rounded-lg shadow border border-gray-200 overflow-hidden">
      <div className={cn("p-4 text-white flex items-center justify-between", getHeaderColor(role))}>
        <div className="flex items-center space-x-2">
          <i className={cn("text-xl", getIconClass(icon))}></i>
          <h3 className="font-semibold">{name}</h3>
        </div>
        <div className="flex space-x-1">
          {/* Chat button */}
          <Link href={`/agent-chat/${id}`}>
            <button className="p-1 hover:bg-white/20 rounded" title="Chat with agent">
              <i className="ri-chat-1-line"></i>
            </button>
          </Link>
          
          {/* Info button - forcing visibility for all agents */}
          <Link href={`/agent-programming/${id}`}>
            <button className="p-1 hover:bg-white/20 rounded" title="View agent information">
              <i className="ri-information-line text-white"></i>
            </button>
          </Link>
        </div>
      </div>
      
      <div className="p-4">
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">LATEST ACTIVITY</p>
          <p className="text-sm text-gray-700">{latestActivity}</p>
        </div>
        
        <div className="mb-3">
          <p className="text-xs text-gray-500 mb-1">ACTIVE TASKS</p>
          <div className="space-y-1">
            {tasks && tasks.length > 0 ? (
              tasks.map((task) => (
                <div key={task.id} className="text-sm flex items-center">
                  <i className={cn("ri-checkbox-blank-circle-fill mr-1 text-xs", getStatusColor(task.status))}></i>
                  <span>{task.title}</span>
                </div>
              ))
            ) : (
              <p className="text-sm text-gray-500 italic">No active tasks</p>
            )}
          </div>
        </div>
        
        <div className="text-right">
          <Link href={`/agent-chat/${id}`}>
            <button className={cn("text-sm font-medium hover:text-blue-700", {
              "text-primary": role === "marketing",
              "text-secondary": role === "support",
              "text-accent": role === "content",
              "text-blue-600": role === "executive",
              "text-indigo-600": role === "assistant",
              "text-gray-600": role === "operations" || !role,
            })}>
              View Details →
            </button>
          </Link>
        </div>
      </div>
    </div>
  );
}
