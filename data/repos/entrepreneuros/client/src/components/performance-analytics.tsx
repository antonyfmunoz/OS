import { useState } from "react";
import { useQuery } from "@tanstack/react-query";
import { 
  Card, 
  CardContent, 
  CardDescription, 
  CardHeader, 
  CardTitle 
} from "@/components/ui/card";
import { Tabs, TabsContent, TabsList, TabsTrigger } from "@/components/ui/tabs";
import { Skeleton } from "@/components/ui/skeleton";
import { StatsOverview } from "./stats-overview";
import {
  PieChart,
  Pie,
  Cell,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  LineChart,
  Line,
  ResponsiveContainer,
} from "recharts";

type AnalyticsData = {
  agentPerformance: Array<{
    id: string;
    name: string;
    role: string;
    icon: string;
    tasksCompleted: number;
    tasksInProgress: number;
    tasksPending: number;
    totalTasks: number;
    messageCount: number;
    activityScore: number;
    completionRate: number;
    averageCompletionTime: number;
    tasksByPriority: {
      high: number;
      medium: number;
      low: number;
    };
  }>;
  taskCompletionTrends: Array<{
    date: string;
    created: number;
    completed: number;
  }>;
  taskDistributionByStatus: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  taskDistributionByType: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  taskDistributionByPriority: Array<{
    name: string;
    value: number;
    color: string;
  }>;
  overallStats: {
    totalAgents: number;
    totalTasks: number;
    completedTasks: number;
    totalMessages: number;
    averageTasksPerAgent: number;
    messagesPerDay: number;
    tasksPerDay: number;
    completionRate: number;
    averageTaskAge: number;
    taskGrowthRate: number;
  };
  // Optional fields for comparison data
  previousPeriod?: {
    timeLabel: string;
    startDate: string;
    endDate: string;
    taskCount: number;
    completedTasksCount: number;
    messageCount: number;
    completionRate: number;
    taskDistributionByStatus: Array<{
      name: string;
      value: number;
      color: string;
    }>;
  };
  comparisons?: {
    taskCountChange: number;
    taskCountChangePercent: number;
    completedTasksChange: number;
    completionRateChange: number;
    messageCountChange: number;
  };
};

export function PerformanceAnalytics() {
  const [timeRange, setTimeRange] = useState<"7days" | "30days" | "90days" | "365days">("7days");
  const [showComparison, setShowComparison] = useState(false);
  
  const { data, isLoading, error } = useQuery<AnalyticsData>({
    queryKey: ["/api/analytics", timeRange, showComparison],
    queryFn: async () => {
      const response = await fetch(`/api/analytics?timeRange=${timeRange}&showComparison=${showComparison}`);
      if (!response.ok) {
        throw new Error("Failed to fetch analytics data");
      }
      return response.json();
    },
  });
  
  if (isLoading) {
    return <AnalyticsLoadingSkeleton />;
  }
  
  if (error) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h3 className="text-lg font-semibold text-red-600">Error loading analytics</h3>
          <p className="text-sm text-gray-500">
            {error instanceof Error ? error.message : "An unknown error occurred"}
          </p>
        </div>
      </div>
    );
  }
  
  if (!data) {
    return (
      <div className="flex items-center justify-center h-full">
        <div className="text-center">
          <h3 className="text-lg font-semibold">No analytics data available</h3>
          <p className="text-sm text-gray-500">
            Start creating agents and tasks to see analytics
          </p>
        </div>
      </div>
    );
  }
  
  return (
    <div className="space-y-6">
      <div className="flex flex-col md:flex-row justify-between items-start md:items-center space-y-2 md:space-y-0">
        <h2 className="text-xl font-semibold">Performance Dashboard</h2>
        <div className="flex flex-col md:flex-row items-start md:items-center space-y-2 md:space-y-0 md:space-x-4">
          <button
            onClick={() => setShowComparison(!showComparison)}
            className={`flex items-center space-x-2 px-3 py-2 text-sm border rounded-md transition-colors ${
              showComparison 
                ? "bg-blue-100 text-blue-700 border-blue-300 hover:bg-blue-200" 
                : "bg-white text-gray-700 border-gray-300 hover:bg-gray-100"
            }`}
          >
            <i className="ri-history-line"></i>
            <span>{showComparison ? "Hide Historical Comparison" : "Show Historical Comparison"}</span>
          </button>
          
          <div className="flex items-center space-x-2">
            <span className="text-sm text-gray-500">Time Period:</span>
            <Tabs 
              defaultValue={timeRange} 
              className="w-auto" 
              onValueChange={(value) => setTimeRange(value as "7days" | "30days" | "90days" | "365days")}
            >
              <TabsList>
                <TabsTrigger value="7days">7 Days</TabsTrigger>
                <TabsTrigger value="30days">30 Days</TabsTrigger>
                <TabsTrigger value="90days">90 Days</TabsTrigger>
                <TabsTrigger value="365days">1 Year</TabsTrigger>
              </TabsList>
            </Tabs>
          </div>
        </div>
      </div>
      
      {/* Enhanced Overall Stats Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        <StatsOverview
          title="Active Agents"
          value={data.overallStats.totalAgents}
          description="Currently active agents"
          trend={{
            value: data.overallStats.averageTasksPerAgent,
            isUpward: true,
            label: `avg. ${data.overallStats.averageTasksPerAgent} tasks/agent`
          }}
          icon="ri-robot-line"
        />
        
        <StatsOverview
          title="Tasks"
          value={data.overallStats.totalTasks}
          description={`${data.overallStats.completedTasks} completed`}
          trend={{
            value: data.comparisons ? Math.abs(data.comparisons.taskCountChangePercent) : Math.abs(data.overallStats.taskGrowthRate * 100),
            isUpward: data.comparisons ? data.comparisons.taskCountChange >= 0 : data.overallStats.taskGrowthRate >= 0,
            label: data.comparisons 
              ? `${data.comparisons.taskCountChange >= 0 ? '+' : ''}${data.comparisons.taskCountChange} tasks vs previous` 
              : `${data.overallStats.taskGrowthRate >= 0 ? 'growth' : 'decrease'} from last period`
          }}
          icon="ri-task-line"
        />
        
        <StatsOverview
          title="Completion Rate"
          value={`${Math.round(data.overallStats.completionRate * 100)}%`}
          description={`${data.overallStats.completedTasks} of ${data.overallStats.totalTasks} tasks`}
          trend={{
            value: data.comparisons ? Math.abs(data.comparisons.completionRateChange * 100) : data.overallStats.tasksPerDay,
            isUpward: data.comparisons ? data.comparisons.completionRateChange >= 0 : true,
            label: data.comparisons 
              ? `${data.comparisons.completionRateChange >= 0 ? '+' : ''}${(data.comparisons.completionRateChange * 100).toFixed(1)}% vs previous` 
              : `${data.overallStats.tasksPerDay.toFixed(1)} tasks/day`
          }}
          icon="ri-check-double-line"
        />
        
        <StatsOverview
          title="Activity"
          value={data.overallStats.totalMessages}
          description="Total messages"
          trend={{
            value: data.comparisons ? Math.abs(data.comparisons.messageCountChange) : data.overallStats.messagesPerDay,
            isUpward: data.comparisons ? data.comparisons.messageCountChange >= 0 : true,
            label: data.comparisons 
              ? `${data.comparisons.messageCountChange >= 0 ? '+' : ''}${data.comparisons.messageCountChange} msgs vs previous` 
              : `${data.overallStats.messagesPerDay.toFixed(1)} msgs/day`
          }}
          icon="ri-message-3-line"
        />
      </div>
      
      {/* Additional Stats Row */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">Avg. Task Age</p>
                <h3 className="text-2xl font-bold">{data.overallStats.averageTaskAge.toFixed(1)} days</h3>
              </div>
              <div className="p-2 bg-amber-100 rounded-full">
                <i className="ri-timer-line text-amber-600 text-xl"></i>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">Task Growth Rate</p>
                <h3 className="text-2xl font-bold">
                  <span className={data.overallStats.taskGrowthRate >= 0 ? "text-green-600" : "text-red-600"}>
                    {(data.overallStats.taskGrowthRate * 100).toFixed(0)}%
                  </span>
                </h3>
              </div>
              <div className={`p-2 ${data.overallStats.taskGrowthRate >= 0 ? "bg-green-100" : "bg-red-100"} rounded-full`}>
                <i className={`${data.overallStats.taskGrowthRate >= 0 ? "ri-arrow-up-line text-green-600" : "ri-arrow-down-line text-red-600"} text-xl`}></i>
              </div>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardContent className="p-4">
            <div className="flex justify-between items-center">
              <div>
                <p className="text-sm text-muted-foreground">Tasks Per Agent</p>
                <h3 className="text-2xl font-bold">{data.overallStats.averageTasksPerAgent.toFixed(1)}</h3>
              </div>
              <div className="p-2 bg-[#5e17eb]/10 rounded-full">
                <i className="ri-stack-line text-[#5e17eb] text-xl"></i>
              </div>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Task Completion Trends */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Task Completion Trends</CardTitle>
            <CardDescription>
              Track task creation and completion rates over time
            </CardDescription>
          </div>
          
          {showComparison && (
            <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-sm font-medium flex items-center">
              <i className="ri-time-line mr-1.5"></i>
              <span>Showing comparison with previous {timeRange === '7days' ? 'week' : 
                  timeRange === '30days' ? 'month' : 
                  timeRange === '90days' ? 'quarter' : 'year'}</span>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="w-full h-80">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart
                data={data.taskCompletionTrends}
                margin={{
                  top: 5,
                  right: 30,
                  left: 20,
                  bottom: 30,
                }}
              >
                <CartesianGrid strokeDasharray="3 3" />
                <XAxis 
                  dataKey="date"
                  tickFormatter={(value) => {
                    const date = new Date(value);
                    // Adjust date format based on the time range
                    if (timeRange === '365days') {
                      return date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        year: 'numeric' 
                      });
                    } else if (timeRange === '90days') {
                      // For 90 days, show abbreviated month and day
                      return date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric',
                      });
                    } else {
                      // For 7 and 30 days, show month/day
                      return date.toLocaleDateString('en-US', { 
                        month: 'short', 
                        day: 'numeric' 
                      });
                    }
                  }}
                  angle={-45}
                  textAnchor="end"
                  height={70}
                  // For 365 days, reduce the number of ticks to prevent overcrowding
                  interval={timeRange === '365days' ? 30 : (timeRange === '90days' ? 6 : 0)}
                />
                <YAxis />
                <Tooltip 
                  formatter={(value, name, props) => {
                    return [value, name === 'created' ? 'Tasks Created' : 'Tasks Completed'];
                  }}
                  labelFormatter={(label) => {
                    const date = new Date(label);
                    if (timeRange === '365days') {
                      return date.toLocaleDateString('en-US', { 
                        year: 'numeric',
                        month: 'long', 
                        day: 'numeric'
                      });
                    } else {
                      return date.toLocaleDateString('en-US', { 
                        weekday: 'short',
                        year: 'numeric',
                        month: 'long', 
                        day: 'numeric'
                      });
                    }
                  }}
                />
                <Legend />
                <Line
                  type="monotone"
                  dataKey="created"
                  name="Tasks Created"
                  stroke="#3b82f6"
                  activeDot={{ r: 8 }}
                  strokeWidth={2}
                />
                <Line
                  type="monotone"
                  dataKey="completed"
                  name="Tasks Completed"
                  stroke="#22c55e"
                  strokeWidth={2}
                />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </CardContent>
      </Card>
      
      {/* Task Distribution */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle>Task Status Distribution</CardTitle>
              <CardDescription>Breakdown of tasks by status</CardDescription>
            </div>
            {showComparison && (
              <div className="bg-blue-50 px-2 py-1 rounded text-blue-700 text-xs">
                <i className="ri-time-line mr-1"></i>
                Comparison active
              </div>
            )}
          </CardHeader>
          <CardContent>
            {showComparison && data.previousPeriod ? (
              <div className="w-full">
                <div className="mb-2 flex justify-between items-center">
                  <span className="text-sm font-medium">Current Period</span>
                  <span className="text-sm font-medium">Previous Period</span>
                </div>
                <div className="w-full grid grid-cols-2 gap-4">
                  <div className="h-64 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data.taskDistributionByStatus}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          outerRadius={70}
                          fill="#5e17eb"
                          dataKey="value"
                          nameKey="name"
                          label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                        >
                          {data.taskDistributionByStatus.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => [value, "Tasks"]} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="h-64 flex items-center justify-center">
                    <ResponsiveContainer width="100%" height="100%">
                      <PieChart>
                        <Pie
                          data={data.previousPeriod.taskDistributionByStatus}
                          cx="50%"
                          cy="50%"
                          labelLine={false}
                          outerRadius={70}
                          fill="#5e17eb"
                          dataKey="value"
                          nameKey="name"
                          label={({ name, percent }) => `${(percent * 100).toFixed(0)}%`}
                        >
                          {data.previousPeriod.taskDistributionByStatus.map((entry, index) => (
                            <Cell key={`cell-${index}`} fill={entry.color} />
                          ))}
                        </Pie>
                        <Tooltip formatter={(value) => [value, "Tasks"]} />
                        <Legend />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                </div>
              </div>
            ) : (
              <div className="w-full h-64 flex items-center justify-center">
                <ResponsiveContainer width="100%" height="100%">
                  <PieChart>
                    <Pie
                      data={data.taskDistributionByStatus}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      outerRadius={80}
                      fill="#5e17eb"
                      dataKey="value"
                      nameKey="name"
                      label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                    >
                      {data.taskDistributionByStatus.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={entry.color} />
                      ))}
                    </Pie>
                    <Tooltip formatter={(value) => [value, "Tasks"]} />
                    <Legend />
                  </PieChart>
                </ResponsiveContainer>
              </div>
            )}
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle>Task Type Distribution</CardTitle>
              <CardDescription>Breakdown of tasks by type</CardDescription>
            </div>
            {showComparison && (
              <div className="bg-blue-50 px-2 py-1 rounded text-blue-700 text-xs">
                <i className="ri-time-line mr-1"></i>
                Comparison active
              </div>
            )}
          </CardHeader>
          <CardContent>
            <div className="w-full h-64 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.taskDistributionByType}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#5e17eb"
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  >
                    {data.taskDistributionByType.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [value, "Tasks"]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
        
        <Card>
          <CardHeader className="flex flex-row items-center justify-between space-y-0 pb-2">
            <div>
              <CardTitle>Task Priority Distribution</CardTitle>
              <CardDescription>Breakdown of tasks by priority</CardDescription>
            </div>
            {showComparison && (
              <div className="bg-blue-50 px-2 py-1 rounded text-blue-700 text-xs">
                <i className="ri-time-line mr-1"></i>
                Comparison active
              </div>
            )}
          </CardHeader>
          <CardContent>
            <div className="w-full h-64 flex items-center justify-center">
              <ResponsiveContainer width="100%" height="100%">
                <PieChart>
                  <Pie
                    data={data.taskDistributionByPriority}
                    cx="50%"
                    cy="50%"
                    labelLine={false}
                    outerRadius={80}
                    fill="#5e17eb"
                    dataKey="value"
                    nameKey="name"
                    label={({ name, percent }) => `${name}: ${(percent * 100).toFixed(0)}%`}
                  >
                    {data.taskDistributionByPriority.map((entry, index) => (
                      <Cell key={`cell-${index}`} fill={entry.color} />
                    ))}
                  </Pie>
                  <Tooltip formatter={(value) => [value, "Tasks"]} />
                  <Legend />
                </PieChart>
              </ResponsiveContainer>
            </div>
          </CardContent>
        </Card>
      </div>
      
      {/* Agent Performance */}
      <Card>
        <CardHeader className="flex flex-row items-center justify-between">
          <div>
            <CardTitle>Agent Performance</CardTitle>
            <CardDescription>
              Detailed performance metrics for each agent
            </CardDescription>
          </div>
          
          {showComparison && (
            <div className="px-3 py-1.5 bg-blue-50 text-blue-700 rounded-md text-sm font-medium flex items-center">
              <i className="ri-time-line mr-1.5"></i>
              <span>Comparing with previous period</span>
            </div>
          )}
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {data.agentPerformance.map((agent) => (
              <div key={agent.id} className="border rounded-lg p-4 space-y-4">
                <div className="flex items-center space-x-3">
                  <div className={`p-2 rounded-full ${agent.role === 'executive' ? 'bg-blue-100' : 'bg-gray-100'}`}>
                    <i className={`${agent.icon || 'ri-robot-line'} text-xl ${agent.role === 'executive' ? 'text-blue-600' : 'text-gray-600'}`}></i>
                  </div>
                  <div>
                    <h4 className="font-semibold">{agent.name}</h4>
                    <p className="text-sm text-gray-500 capitalize">{agent.role}</p>
                  </div>
                  <div className="flex items-center space-x-4 ml-auto">
                    <div className="text-center">
                      <span className="font-medium text-lg">{agent.activityScore}</span>
                      <p className="text-xs text-gray-500">Activity Score</p>
                    </div>
                    <div className="text-center">
                      <span className="font-medium text-lg">{Math.round(agent.completionRate * 100)}%</span>
                      <p className="text-xs text-gray-500">Completion Rate</p>
                    </div>
                  </div>
                </div>
                
                <div className="grid grid-cols-1 md:grid-cols-4 gap-4">
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Task Status</p>
                    <div className="flex items-center justify-between mb-2">
                      <span className="text-xs font-medium text-green-600">
                        {agent.tasksCompleted} Completed
                      </span>
                      <span className="text-xs font-medium text-amber-600">
                        {agent.tasksInProgress} In Progress
                      </span>
                      <span className="text-xs font-medium text-gray-600">
                        {agent.tasksPending} Pending
                      </span>
                    </div>
                    <div className="h-3 bg-gray-200 rounded-full overflow-hidden flex">
                      <div 
                        className="h-full bg-green-500" 
                        style={{ width: `${(agent.tasksCompleted / (agent.totalTasks || 1)) * 100}%` }}
                      />
                      <div 
                        className="h-full bg-amber-500" 
                        style={{ width: `${(agent.tasksInProgress / (agent.totalTasks || 1)) * 100}%` }}
                      />
                      <div 
                        className="h-full bg-gray-400" 
                        style={{ width: `${(agent.tasksPending / (agent.totalTasks || 1)) * 100}%` }}
                      />
                    </div>
                    
                    <div className="flex items-center justify-between mb-2 mt-3">
                      <span className="text-xs">In Progress</span>
                      <span className="text-xs font-medium">{agent.tasksInProgress}</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-yellow-500" 
                        style={{ width: `${(agent.tasksInProgress / (agent.tasksCompleted + agent.tasksInProgress + agent.tasksPending || 1)) * 100}%` }}
                      />
                    </div>
                    
                    <div className="flex items-center justify-between mb-2 mt-3">
                      <span className="text-xs">Pending</span>
                      <span className="text-xs font-medium">{agent.tasksPending}</span>
                    </div>
                    <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                      <div 
                        className="h-full bg-gray-500" 
                        style={{ width: `${(agent.tasksPending / (agent.tasksCompleted + agent.tasksInProgress + agent.tasksPending || 1)) * 100}%` }}
                      />
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Priority Distribution</p>
                    <div className="space-y-3">
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs flex items-center">
                            <div className="w-2 h-2 rounded-full bg-red-500 mr-1"></div>
                            High
                          </span>
                          <span className="text-xs font-medium">{agent.tasksByPriority.high}</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-red-500" 
                            style={{ width: `${(agent.tasksByPriority.high / (agent.tasksByPriority.high + agent.tasksByPriority.medium + agent.tasksByPriority.low || 1)) * 100}%` }}
                          />
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs flex items-center">
                            <div className="w-2 h-2 rounded-full bg-yellow-500 mr-1"></div>
                            Medium
                          </span>
                          <span className="text-xs font-medium">{agent.tasksByPriority.medium}</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-yellow-500" 
                            style={{ width: `${(agent.tasksByPriority.medium / (agent.tasksByPriority.high + agent.tasksByPriority.medium + agent.tasksByPriority.low || 1)) * 100}%` }}
                          />
                        </div>
                      </div>
                      
                      <div>
                        <div className="flex items-center justify-between mb-1">
                          <span className="text-xs flex items-center">
                            <div className="w-2 h-2 rounded-full bg-green-500 mr-1"></div>
                            Low
                          </span>
                          <span className="text-xs font-medium">{agent.tasksByPriority.low}</span>
                        </div>
                        <div className="h-2 bg-gray-200 rounded-full overflow-hidden">
                          <div 
                            className="h-full bg-green-500" 
                            style={{ width: `${(agent.tasksByPriority.low / (agent.tasksByPriority.high + agent.tasksByPriority.medium + agent.tasksByPriority.low || 1)) * 100}%` }}
                          />
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Performance Metrics</p>
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs mb-1">Average Completion Time</p>
                        <div className="flex items-center">
                          <span className="text-lg font-medium">
                            {agent.averageCompletionTime.toFixed(1)} hrs
                          </span>
                        </div>
                      </div>
                      
                      <div>
                        <p className="text-xs mb-1">Tasks Completed</p>
                        <div className="flex items-center">
                          <span className="text-lg font-medium">
                            {agent.tasksCompleted}
                          </span>
                        </div>
                      </div>
                    </div>
                  </div>
                  
                  <div>
                    <p className="text-sm text-gray-500 mb-1">Activity</p>
                    <div className="space-y-4">
                      <div>
                        <p className="text-xs mb-1">Messages</p>
                        <div className="flex items-center">
                          <span className="text-lg font-medium">
                            {agent.messageCount}
                          </span>
                          <div className="ml-2 px-2 py-1 rounded-full bg-blue-100 text-blue-700 text-xs">
                            Communication
                          </div>
                        </div>
                      </div>
                      
                      <div>
                        <p className="text-xs mb-1">Total Tasks</p>
                        <div className="flex items-center">
                          <span className="text-lg font-medium">
                            {agent.totalTasks}
                          </span>
                          <div className="ml-2 px-2 py-1 rounded-full bg-[#5e17eb]/10 text-[#5e17eb] text-xs">
                            Workload
                          </div>
                        </div>
                      </div>
                    </div>
                  </div>
                </div>
              </div>
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}

function AnalyticsLoadingSkeleton() {
  return (
    <div className="space-y-6">
      <div className="flex justify-between items-center">
        <Skeleton className="h-8 w-64" />
        <Skeleton className="h-10 w-48" />
      </div>
      
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
        {Array(4).fill(0).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-5 w-24" />
              <Skeleton className="h-8 w-16" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-4 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
      
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-48" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <Skeleton className="h-80 w-full" />
        </CardContent>
      </Card>
      
      <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
        {Array(3).fill(0).map((_, i) => (
          <Card key={i}>
            <CardHeader>
              <Skeleton className="h-6 w-40" />
              <Skeleton className="h-4 w-32" />
            </CardHeader>
            <CardContent>
              <Skeleton className="h-64 w-full" />
            </CardContent>
          </Card>
        ))}
      </div>
      
      <Card>
        <CardHeader>
          <Skeleton className="h-6 w-36" />
          <Skeleton className="h-4 w-64" />
        </CardHeader>
        <CardContent>
          <div className="space-y-6">
            {Array(3).fill(0).map((_, i) => (
              <Skeleton key={i} className="h-40 w-full" />
            ))}
          </div>
        </CardContent>
      </Card>
    </div>
  );
}