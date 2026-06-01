import { ReactNode, useState, useEffect } from "react";
import { Sidebar } from "./sidebar";
import { Header } from "./header";
import { useIsMobile } from "@/hooks/use-mobile";
import { cn } from "@/lib/utils";
import { Button } from "@/components/ui/button";
import { PanelLeftClose, PanelLeftOpen, Menu } from "lucide-react";

type LayoutProps = {
  children: ReactNode;
  title: string;
};

export function Layout({ children, title }: LayoutProps) {
  const [isSidebarOpen, setIsSidebarOpen] = useState(true);
  const isMobile = useIsMobile();
  
  useEffect(() => {
    if (isMobile) {
      setIsSidebarOpen(false);
    } else {
      setIsSidebarOpen(true);
    }
  }, [isMobile]);

  return (
    <div className="flex h-screen bg-gray-50">
      {isMobile ? (
        <>
          <div
            className={cn(
              "fixed inset-y-0 left-0 z-30 w-64 transform transition-transform duration-300 ease-in-out bg-white shadow-lg",
              isSidebarOpen ? "translate-x-0" : "-translate-x-full"
            )}
          >
            <Sidebar collapsed={false} />
          </div>
          {isSidebarOpen && (
            <div
              className="fixed inset-0 bg-black/50 z-20"
              onClick={() => setIsSidebarOpen(false)}
            />
          )}
        </>
      ) : (
        <div
          className={cn(
            "relative flex-shrink-0 transition-all duration-300 ease-in-out border-r border-gray-200 bg-white",
            isSidebarOpen ? "w-64" : "w-0"
          )}
        >
          <div className={cn(
            "h-full w-64 overflow-hidden transition-opacity duration-200",
            isSidebarOpen ? "opacity-100" : "opacity-0 pointer-events-none"
          )}>
            <Sidebar collapsed={false} />
          </div>
        </div>
      )}

      <div className="flex-1 flex flex-col overflow-hidden min-w-0">
        <Header title={title}>
          <Button
            variant="ghost"
            size="icon"
            onClick={() => setIsSidebarOpen(!isSidebarOpen)}
            className="mr-2 hover:bg-blue-100"
            title={isSidebarOpen ? "Collapse sidebar" : "Expand sidebar"}
          >
            {isMobile ? (
              <Menu className="h-5 w-5 text-gray-700" />
            ) : isSidebarOpen ? (
              <PanelLeftClose className="h-5 w-5 text-gray-700" />
            ) : (
              <PanelLeftOpen className="h-5 w-5 text-gray-700" />
            )}
          </Button>
        </Header>

        <main className="flex-1 overflow-auto p-6">
          {children}
        </main>
      </div>
    </div>
  );
}
