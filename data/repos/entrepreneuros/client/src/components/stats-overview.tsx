import { Card, CardContent } from "@/components/ui/card";
import { cn } from "@/lib/utils";
import { ArrowDownIcon, ArrowUpIcon } from "lucide-react";

type StatsOverviewProps = {
  title: string;
  value: number | string;
  description: string;
  trend?: {
    value: number;
    isUpward: boolean;
    label: string;
  };
  icon?: string;
  className?: string;
};

export function StatsOverview({
  title,
  value,
  description,
  trend,
  icon,
  className,
}: StatsOverviewProps) {
  return (
    <Card className={cn("overflow-hidden", className)}>
      <CardContent className="p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-sm font-medium text-gray-500">{title}</h3>
          {icon && <i className={`${icon} text-xl text-gray-400`}></i>}
        </div>
        <div className="mt-2 flex items-baseline">
          <p className="text-2xl font-semibold">{value}</p>
          
          {trend && (
            <div className="ml-2 flex items-baseline text-sm font-medium">
              <span 
                className={cn(
                  "flex items-center",
                  trend.isUpward ? "text-green-600" : "text-red-600"
                )}
              >
                {trend.isUpward ? (
                  <ArrowUpIcon className="h-3 w-3 mr-0.5" />
                ) : (
                  <ArrowDownIcon className="h-3 w-3 mr-0.5" />
                )}
                {trend.value > 0 ? `${trend.value}%` : null}
              </span>
              
              <span className="text-gray-500 ml-1">
                {trend.label}
              </span>
            </div>
          )}
        </div>
        <p className="mt-1 text-sm text-gray-500">{description}</p>
      </CardContent>
    </Card>
  );
}