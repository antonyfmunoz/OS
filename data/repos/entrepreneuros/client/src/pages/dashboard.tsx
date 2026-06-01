import { Layout } from "@/components/layout";
import { AgentCard } from "@/components/agent-card";
import { TaskBoard } from "@/components/task-board";
import { AiFab } from "@/components/ai-fab"; 
import { ActionApprovalPanel } from "@/components/action-approval-panel";
import { useQuery } from "@tanstack/react-query";

type Agent = {
  id: string;
  name: string;
  role: string;
  icon: string;
  latestActivity: string;
  tasks: {
    id: string;
    title: string;
    status: "todo" | "in-progress" | "done";
  }[];
};

export default function Dashboard() {
  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ["/api/agents"],
  });

  return (
    <Layout title="Dashboard">
      <div>
        <ActionApprovalPanel />

        <h2 className="text-lg font-semibold text-gray-800 mb-4">Your Agents</h2>
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4 gap-6 mb-8">
          {agents.map((agent) => (
            <AgentCard
              key={agent.id}
              id={agent.id}
              name={agent.name}
              role={agent.role}
              icon={agent.icon}
              latestActivity={agent.latestActivity}
              tasks={agent.tasks}
            />
          ))}
        </div>
        
        <TaskBoard />
        
        <AiFab />
      </div>
    </Layout>
  );
}
