import { useAuth } from "@/hooks/use-auth";
import { Loader2 } from "lucide-react";
import { Route, Redirect } from "wouter";
import { ReactNode } from "react";

type ProtectedRouteProps = {
  path: string;
} & (
  | { component: () => React.JSX.Element; children?: never }
  | { component?: never; children: (params: any) => ReactNode }
);

export function ProtectedRoute(props: ProtectedRouteProps) {
  const { path, component: Component, children } = props;
  const { user, isLoading } = useAuth();

  if (isLoading) {
    return (
      <Route path={path}>
        <div className="flex items-center justify-center min-h-screen">
          <Loader2 className="h-8 w-8 animate-spin text-border" />
        </div>
      </Route>
    );
  }

  if (!user) {
    return (
      <Route path={path}>
        <Redirect to="/auth" />
      </Route>
    );
  }

  if (Component) {
    return <Route path={path} component={Component} />;
  }

  return <Route path={path}>{children}</Route>;
}