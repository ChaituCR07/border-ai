import React from 'react';
import { useAuth } from './AuthProvider';

export interface RequirePermissionProps {
  permission: string;
  children: React.ReactNode;
  fallback?: React.ReactNode;
}

export const RequirePermission: React.FC<RequirePermissionProps> = ({
  permission,
  children,
  fallback,
}) => {
  const { hasPermission, isLoading } = useAuth();

  if (isLoading) {
    return null;
  }

  if (!hasPermission(permission)) {
    return fallback ? (
      <>{fallback}</>
    ) : (
      <div className="rounded-md border border-amber-500/30 bg-amber-950/20 p-4 text-amber-200">
        <h4 className="font-semibold text-sm">Access Restricted (403 Forbidden)</h4>
        <p className="text-xs text-amber-300/80 mt-1">
          Your current role does not have the required permission: <code className="font-mono">{permission}</code>
        </p>
      </div>
    );
  }

  return <>{children}</>;
};
