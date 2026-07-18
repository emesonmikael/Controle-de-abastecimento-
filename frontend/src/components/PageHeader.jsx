import React from "react";

/** Reusable page header for CRUD screens */
export const PageHeader = ({ title, description, actions }) => (
  <div className="flex flex-col sm:flex-row sm:items-end sm:justify-between gap-4">
    <div>
      <h1 className="text-3xl font-bold text-slate-900">{title}</h1>
      {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
    </div>
    {actions && <div className="flex gap-2">{actions}</div>}
  </div>
);

export const EmptyState = ({ title, description, action }) => (
  <div className="border border-dashed border-slate-200 rounded-lg p-10 text-center bg-white" data-testid="empty-state">
    <h3 className="text-lg font-semibold text-slate-900">{title}</h3>
    {description && <p className="text-sm text-slate-500 mt-1">{description}</p>}
    {action && <div className="mt-4">{action}</div>}
  </div>
);
