import { useState } from "react";
import { TaskCard } from "./task-card";
import { useMutation, useQuery } from "@tanstack/react-query";
import { apiRequest, queryClient } from "@/lib/queryClient";
import { Dialog, DialogContent, DialogHeader, DialogTitle, DialogFooter, DialogDescription } from "./ui/dialog";
import { AlertDialog, AlertDialogAction, AlertDialogCancel, AlertDialogContent, AlertDialogDescription, AlertDialogFooter, AlertDialogHeader, AlertDialogTitle } from "./ui/alert-dialog";
import { Button } from "./ui/button";
import { Input } from "./ui/input";
import { Textarea } from "./ui/textarea";
import { Label } from "./ui/label";
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from "./ui/select";
import { DragDropContext, Droppable, Draggable, DropResult } from "react-beautiful-dnd";
import { useToast } from "@/hooks/use-toast";

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

type Agent = {
  id: string;
  name: string;
  role: string;
};

// Define column types for the board
type ColumnId = "todo" | "in-progress" | "done";

interface Column {
  id: ColumnId;
  title: string;
  taskIds: string[];
  color: string;
}

type TaskMap = {
  [key: string]: Task;
};

export function TaskBoard() {
  const [isTaskDialogOpen, setIsTaskDialogOpen] = useState(false);
  const [isDeleteDialogOpen, setIsDeleteDialogOpen] = useState(false);
  const [isEditing, setIsEditing] = useState(false);
  const [currentTaskId, setCurrentTaskId] = useState<string | null>(null);
  const [taskToDeleteId, setTaskToDeleteId] = useState<string | null>(null);
  const [parentTaskId, setParentTaskId] = useState<string | null>(null);
  const [taskForm, setTaskForm] = useState({
    title: "",
    description: "",
    startDate: "",
    dueDate: "",
    instructions: "",
    priority: "medium",
    agentId: "",
    parentTaskId: ""
  });
  
  const { toast } = useToast();

  const { data: tasks = [], isLoading: tasksLoading } = useQuery<Task[]>({
    queryKey: ["/api/tasks"],
  });

  const { data: agents = [] } = useQuery<Agent[]>({
    queryKey: ["/api/agents"],
  });

  // Transform tasks into a map for easier access
  const tasksMap: TaskMap = {};
  tasks.forEach(task => {
    tasksMap[task.id] = task;
  });

  // Define columns for the board
  const columns: { [key in ColumnId]: Column } = {
    "todo": {
      id: "todo",
      title: "To Do",
      taskIds: tasks.filter(task => task.status === "todo").map(task => task.id),
      color: "bg-gray-400"
    },
    "in-progress": {
      id: "in-progress",
      title: "In Progress",
      taskIds: tasks.filter(task => task.status === "in-progress").map(task => task.id),
      color: "bg-yellow-400"
    },
    "done": {
      id: "done",
      title: "Done",
      taskIds: tasks.filter(task => task.status === "done").map(task => task.id),
      color: "bg-green-500"
    }
  };

  // Define the column order
  const columnOrder: ColumnId[] = ["todo", "in-progress", "done"];

  const createTaskMutation = useMutation({
    mutationFn: async (taskData: any) => {
      const res = await apiRequest("POST", "/api/tasks", taskData);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/tasks"] });
      setIsTaskDialogOpen(false);
      resetTaskForm();
    }
  });

  const updateTaskStatusMutation = useMutation({
    mutationFn: async ({ taskId, status }: { taskId: string, status: string }) => {
      const res = await apiRequest("PATCH", `/api/tasks/${taskId}`, { status });
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/tasks"] });
    }
  });

  const updateTaskMutation = useMutation({
    mutationFn: async ({ taskId, taskData }: { taskId: string, taskData: any }) => {
      const res = await apiRequest("PATCH", `/api/tasks/${taskId}`, taskData);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/tasks"] });
      setIsTaskDialogOpen(false);
      resetTaskForm();
    }
  });
  
  const deleteTaskMutation = useMutation({
    mutationFn: async (taskId: string) => {
      const res = await apiRequest("DELETE", `/api/tasks/${taskId}`);
      return res.json();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["/api/tasks"] });
    }
  });

  const resetTaskForm = () => {
    setTaskForm({
      title: "",
      description: "",
      startDate: "",
      dueDate: "",
      instructions: "",
      priority: "medium",
      agentId: "",
      parentTaskId: ""
    });
    setIsEditing(false);
    setCurrentTaskId(null);
    setParentTaskId(null);
  };
  
  const handleAddSubtask = (parentTask: Task) => {
    setParentTaskId(parentTask.id);
    setTaskForm({
      title: "",
      description: "",
      startDate: "",
      dueDate: new Date().toISOString().split('T')[0], // Default to today
      instructions: "",
      priority: "medium",
      agentId: parentTask.agent?.id || "",
      parentTaskId: parentTask.id
    });
    setIsTaskDialogOpen(true);
  };

  const handleTaskDialogOpen = (editing = false, task?: Task) => {
    setIsEditing(editing);
    
    if (editing && task) {
      setCurrentTaskId(task.id);
      setTaskForm({
        title: task.title,
        description: task.description,
        startDate: task.startDate ? new Date(task.startDate).toISOString().split('T')[0] : "",
        dueDate: new Date(task.dueDate).toISOString().split('T')[0], // Format date for input
        instructions: task.instructions || "",
        priority: task.priority || "medium",
        agentId: task.agent?.id || "",
        parentTaskId: task.parentTaskId || ""
      });
    } else {
      resetTaskForm();
    }
    
    setIsTaskDialogOpen(true);
  };

  const handleTaskSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    
    if (isEditing && currentTaskId) {
      updateTaskMutation.mutate({ 
        taskId: currentTaskId, 
        taskData: taskForm 
      });
    } else {
      createTaskMutation.mutate(taskForm);
    }
  };

  const moveTask = (taskId: string, newStatus: "todo" | "in-progress" | "done") => {
    updateTaskStatusMutation.mutate({ taskId, status: newStatus });
  };

  const getBadgeVariantFromRole = (role: string) => {
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

  const handleDragEnd = (result: DropResult) => {
    const { destination, source, draggableId } = result;

    // If there's no destination or the item was dropped back in its original position
    if (!destination || 
        (destination.droppableId === source.droppableId && 
         destination.index === source.index)) {
      return;
    }

    // If the task was moved to a different column
    if (destination.droppableId !== source.droppableId) {
      // Update the task status in the backend
      const newStatus = destination.droppableId as "todo" | "in-progress" | "done";
      moveTask(draggableId, newStatus);
    }
  };

  return (
    <>
      <div className="flex items-center justify-between mb-4">
        <h2 className="text-lg font-semibold text-gray-800">Task Board</h2>
        <Button 
          onClick={() => handleTaskDialogOpen(false)}
          className="text-sm flex items-center space-x-1 text-primary bg-transparent hover:bg-primary/10"
        >
          <i className="ri-add-line"></i>
          <span>Add Task</span>
        </Button>
      </div>

      <DragDropContext onDragEnd={handleDragEnd}>
        <div className="grid grid-cols-1 md:grid-cols-3 gap-6 mb-6">
          {columnOrder.map(columnId => {
            const column = columns[columnId];
            const columnTasks = column.taskIds.map(taskId => tasksMap[taskId]);
            
            return (
              <div 
                key={column.id} 
                className="bg-white rounded-lg shadow p-4 border border-gray-200 flex flex-col"
              >
                <div className="flex items-center justify-between mb-4">
                  <h3 className="font-medium text-gray-700 flex items-center">
                    <span className={`w-3 h-3 rounded-full ${column.color} mr-2`}></span>
                    {column.title}
                  </h3>
                  <span className="bg-gray-100 text-gray-600 text-xs font-medium px-2 py-1 rounded">
                    {column.taskIds.length}
                  </span>
                </div>
                
                <Droppable droppableId={column.id}>
                  {(provided, snapshot) => (
                    <div 
                      ref={provided.innerRef}
                      {...provided.droppableProps}
                      className={`flex-1 space-y-3 min-h-[200px] ${snapshot.isDraggingOver ? 'bg-gray-50' : ''}`}
                    >
                      {columnTasks.map((task, index) => (
                        <Draggable 
                          key={task.id} 
                          draggableId={task.id} 
                          index={index}
                        >
                          {(provided, snapshot) => (
                            <div
                              ref={provided.innerRef}
                              {...provided.draggableProps}
                              {...provided.dragHandleProps}
                              style={{
                                ...provided.draggableProps.style,
                                opacity: snapshot.isDragging ? 0.8 : 1
                              }}
                              className={`${snapshot.isDragging ? 'shadow-lg' : ''}`}
                            >
                              <TaskCard 
                                task={task}
                                onEdit={(task) => handleTaskDialogOpen(true, task)}
                                onAddSubtask={handleAddSubtask}
                                onDelete={(taskId) => {
                                  setTaskToDeleteId(taskId);
                                  setIsDeleteDialogOpen(true);
                                }}
                                badgeVariant={task.agent ? getBadgeVariantFromRole(task.agent.role) : undefined}
                                isDone={task.status === 'done'}
                              />
                            </div>
                          )}
                        </Draggable>
                      ))}
                      {provided.placeholder}
                    </div>
                  )}
                </Droppable>
              </div>
            );
          })}
        </div>
      </DragDropContext>

      <Dialog open={isTaskDialogOpen} onOpenChange={setIsTaskDialogOpen}>
        <DialogContent className="max-w-full w-[90vw] h-[90vh] overflow-y-auto">
          <DialogHeader>
            <DialogTitle>{isEditing ? "Edit Task" : "Add New Task"}</DialogTitle>
          </DialogHeader>
          <form onSubmit={handleTaskSubmit}>
            <div className="space-y-4 py-2">
              <div className="space-y-2">
                <Label htmlFor="title">Task Title</Label>
                <Input 
                  id="title"
                  value={taskForm.title}
                  onChange={(e) => setTaskForm({...taskForm, title: e.target.value})}
                  placeholder="Enter task title"
                  required
                />
              </div>
              
              <div className="space-y-2">
                <Label htmlFor="description">Description</Label>
                <Textarea 
                  id="description"
                  value={taskForm.description}
                  onChange={(e) => setTaskForm({...taskForm, description: e.target.value})}
                  placeholder="Describe the task..."
                  className="min-h-[120px]"
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="startDate">Start Date</Label>
                <Input 
                  id="startDate"
                  type="date"
                  value={taskForm.startDate}
                  onChange={(e) => setTaskForm({...taskForm, startDate: e.target.value})}
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="dueDate">Due Date</Label>
                <Input 
                  id="dueDate"
                  type="date"
                  value={taskForm.dueDate}
                  onChange={(e) => setTaskForm({...taskForm, dueDate: e.target.value})}
                  required
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="instructions">Instructions for Agent</Label>
                <Textarea
                  id="instructions"
                  value={taskForm.instructions}
                  onChange={(e) => setTaskForm({...taskForm, instructions: e.target.value})}
                  placeholder="Provide specific instructions for the assigned agent..."
                  className="min-h-[200px]"
                />
              </div>

              <div className="space-y-2">
                <Label htmlFor="priority">Priority</Label>
                <Select 
                  value={taskForm.priority} 
                  onValueChange={(value) => setTaskForm({...taskForm, priority: value})}
                >
                  <SelectTrigger id="priority">
                    <SelectValue placeholder="Select priority" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="low">Low</SelectItem>
                    <SelectItem value="medium">Medium</SelectItem>
                    <SelectItem value="high">High</SelectItem>
                    <SelectItem value="urgent">Urgent</SelectItem>
                  </SelectContent>
                </Select>
              </div>

              <div className="space-y-2">
                <Label htmlFor="agent">Assign to Agent</Label>
                <Select 
                  value={taskForm.agentId} 
                  onValueChange={(value) => setTaskForm({...taskForm, agentId: value})}
                >
                  <SelectTrigger id="agent">
                    <SelectValue placeholder="Select an agent" />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value="none">Unassigned</SelectItem>
                    {agents.map(agent => (
                      <SelectItem key={agent.id} value={agent.id}>{agent.name}</SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </div>
            </div>
            
            <DialogFooter className="mt-6">
              <Button 
                type="button" 
                variant="outline" 
                onClick={() => {
                  setIsTaskDialogOpen(false);
                  resetTaskForm();
                }}
              >
                Cancel
              </Button>
              <Button 
                type="submit" 
                disabled={createTaskMutation.isPending || updateTaskMutation.isPending}
              >
                {isEditing 
                  ? (updateTaskMutation.isPending ? "Updating..." : "Update Task")
                  : (createTaskMutation.isPending ? "Creating..." : "Create Task")
                }
              </Button>
            </DialogFooter>
          </form>
        </DialogContent>
      </Dialog>

      <AlertDialog open={isDeleteDialogOpen} onOpenChange={setIsDeleteDialogOpen}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Are you sure?</AlertDialogTitle>
            <AlertDialogDescription>
              This will permanently delete the task and all its subtasks. This action cannot be undone.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancel</AlertDialogCancel>
            <AlertDialogAction
              className="bg-red-600 hover:bg-red-700 text-white"
              onClick={() => {
                if (taskToDeleteId) {
                  deleteTaskMutation.mutate(taskToDeleteId);
                  toast({
                    title: "Task deleted",
                    description: "The task and its subtasks have been deleted.",
                  });
                  setTaskToDeleteId(null);
                }
              }}
            >
              Delete
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </>
  );
}