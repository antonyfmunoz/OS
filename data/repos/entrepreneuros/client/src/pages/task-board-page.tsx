import { Layout } from "@/components/layout";
import { TaskBoard } from "@/components/task-board";

export default function TaskBoardPage() {
  return (
    <Layout title="Task Board">
      <div>
        <TaskBoard />
      </div>
    </Layout>
  );
}
