import { Badge } from "@/components/ui/badge";
import { VariantProps } from "class-variance-authority";
import { cn } from "@/lib/utils";
import { useState } from "react";
import { ChevronDown, ChevronRight, Plus } from "lucide-react";

type Task = {
  id: string;
  title: string;
  description: string;
  startDate?: string;
  dueDate: string;
  status: "todo" | "in-progress" | "done";
  priority: "low" | "medium" | "high" | "urgent";
  instructions?: string;
  parentTaskId?: string;
  subtasks?: Task[];
  agent: {
    id: string;
    name: string;
    role: string;
  } | null;
};

type TaskCardProps = {
  task: Task;
  onMoveLeft?: () => void;
  onMoveRight?: () => void;
  onEdit?: (task: Task) => void;
  onAddSubtask?: (parentTask: Task) => void;
  onDelete?: (taskId: string) => void;
  badgeVariant?: VariantProps<typeof Badge>["variant"];
  isDone?: boolean;
  depth?: number;
};

export function TaskCard({ 
  task, 
  onMoveLeft, 
  onMoveRight, 
  onEdit, 
  onAddSubtask,
  onDelete,
  badgeVariant = "default", 
  isDone = false,
  depth = 0
}: TaskCardProps) {
  const [expanded, setExpanded] = useState(true);
  const formatDate = () => {
    const today = new Date();
    const tomorrow = new Date(today);
    tomorrow.setDate(tomorrow.getDate() + 1);
    
    const dueDate = new Date(task.dueDate);
    const hasStartDate = !!task.startDate;
    const startDate = hasStartDate ? new Date(task.startDate!) : null;
    
    if (isDone) {
      return (
        <div className="flex items-center text-xs space-x-1 text-gray-500">
          <i className="ri-check-line text-green-500"></i>
          <span>Completed</span>
        </div>
      );
    }
    
    // Check if task has a start date that's in the future
    if (hasStartDate && startDate && startDate > today) {
      const startDiffTime = startDate.getTime() - today.getTime();
      const startDiffDays = Math.ceil(startDiffTime / (1000 * 60 * 60 * 24));
      
      if (startDate.toDateString() === tomorrow.toDateString()) {
        return (
          <div className="flex items-center text-xs space-x-1 text-blue-500">
            <i className="ri-calendar-line"></i>
            <span>Starts tomorrow</span>
          </div>
        );
      } else {
        return (
          <div className="flex items-center text-xs space-x-1 text-blue-500">
            <i className="ri-calendar-line"></i>
            <span>Starts in {startDiffDays} days</span>
          </div>
        );
      }
    }
    
    // If the task has started (or has no start date), show due date info
    if (dueDate.toDateString() === today.toDateString()) {
      return (
        <div className="flex items-center text-xs space-x-1 text-gray-500">
          <i className="ri-time-line"></i>
          <span>Due today</span>
        </div>
      );
    } else if (dueDate.toDateString() === tomorrow.toDateString()) {
      return (
        <div className="flex items-center text-xs space-x-1 text-gray-500">
          <i className="ri-time-line"></i>
          <span>Due tomorrow</span>
        </div>
      );
    } else {
      // Calculate difference in days
      const diffTime = dueDate.getTime() - today.getTime();
      const diffDays = Math.ceil(diffTime / (1000 * 60 * 60 * 24));
      
      if (diffDays < 0) {
        return (
          <div className="flex items-center text-xs space-x-1 text-red-500">
            <i className="ri-alarm-warning-line"></i>
            <span>Overdue by {Math.abs(diffDays)} days</span>
          </div>
        );
      } else {
        return (
          <div className="flex items-center text-xs space-x-1 text-gray-500">
            <i className="ri-time-line"></i>
            <span>Due in {diffDays} days</span>
          </div>
        );
      }
    }
  };

  const priorityIcon = () => {
    const colorClass = {
      low: "text-gray-400",
      medium: "text-blue-500",
      high: "text-orange-500",
      urgent: "text-red-500"
    };
    
    return (
      <div className="flex items-center space-x-1 text-xs" title={`Priority: ${task.priority}`}>
        <i className={`ri-flag-2-line ${colorClass[task.priority]}`}></i>
        <span className={`capitalize ${colorClass[task.priority]}`}>{task.priority}</span>
      </div>
    );
  };

  const hasSubtasks = task.subtasks && task.subtasks.length > 0;
  
  return (
    <div className={`${depth > 0 ? 'pl-' + (depth * 4) : ''}`}>
      <div className="bg-gray-50 p-3 rounded border border-gray-200 shadow-sm hover:shadow transition-shadow">
        <div className="flex justify-between items-start mb-2">
          <div className="flex items-center">
            {hasSubtasks && (
              <button 
                className="mr-2 text-gray-500 p-1 hover:bg-gray-200 rounded-full"
                onClick={() => setExpanded(!expanded)}
              >
                {expanded ? <ChevronDown size={16} /> : <ChevronRight size={16} />}
              </button>
            )}
            <h4 className="font-medium text-gray-800">{task.title}</h4>
          </div>
          {formatDate()}
        </div>
        <p className="text-sm text-gray-600 mb-2">{task.description}</p>
        {task.instructions && (
          <div className="mb-3">
            <p className="text-xs font-medium text-gray-500 mb-1">Instructions:</p>
            <p className="text-xs text-gray-600 bg-gray-100 p-2 rounded">{task.instructions}</p>
          </div>
        )}
        <div className="flex items-center justify-between mb-2">
          <Badge variant={badgeVariant}>
            {task.agent ? task.agent.name : 'Unassigned'}
          </Badge>
          {priorityIcon()}
        </div>
        <div className="flex justify-between">
          {onAddSubtask && (
            <button 
              className="text-gray-500 hover:text-green-600 flex items-center text-xs gap-1" 
              title="Add subtask"
              onClick={() => onAddSubtask(task)}
            >
              <Plus size={14} />
              <span>Add subtask</span>
            </button>
          )}
          <div className="flex">
            {onEdit && (
              <button 
                className="text-gray-500 hover:text-blue-600 ml-2" 
                title="Edit task"
                onClick={() => onEdit(task)}
              >
                <i className="ri-edit-line"></i>
              </button>
            )}
            {onDelete && (
              <button 
                className="text-gray-500 hover:text-red-600 ml-2" 
                title="Delete task"
                onClick={() => onDelete(task.id)}
              >
                <i className="ri-delete-bin-line"></i>
              </button>
            )}
            {onMoveLeft && (
              <button 
                className="text-gray-400 hover:text-gray-600 ml-2" 
                title="Move back"
                onClick={onMoveLeft}
              >
                <i className="ri-arrow-left-line"></i>
              </button>
            )}
            {onMoveRight && (
              <button 
                className="text-primary hover:text-blue-700 ml-2" 
                title="Move forward"
                onClick={onMoveRight}
              >
                <i className="ri-arrow-right-line"></i>
              </button>
            )}
          </div>
        </div>
      </div>
      
      {/* Render subtasks if they exist and are expanded */}
      {hasSubtasks && expanded && (
        <div className="mt-2 space-y-2">
          {task.subtasks!.map(subtask => (
            <TaskCard
              key={subtask.id}
              task={subtask}
              onEdit={onEdit}
              onAddSubtask={onAddSubtask}
              onDelete={onDelete}
              badgeVariant={badgeVariant}
              isDone={subtask.status === "done"}
              depth={depth + 1}
            />
          ))}
        </div>
      )}
    </div>
  );
}
