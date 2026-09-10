import React from "react";
import { useNavigate } from "react-router-dom";
import { ErrorScreen } from "../components/ErrorScreen";

/**
 * Catch-all 404 for unknown in-app routes. Rendered inside the authenticated
 * Layout (via ProtectedRoute) so the navigation shell and session are preserved.
 */
export const NotFoundPage: React.FC = () => {
  const navigate = useNavigate();
  return (
    <ErrorScreen
      code="404"
      kind="notfound"
      title="Page Not Found"
      message="This page doesn't exist. It may have been moved, or the link is incorrect. Use the navigation to find what you need."
      actions={[
        { label: "Back to Dashboard", onClick: () => navigate("/dashboard"), variant: "primary" },
        { label: "Go Back", onClick: () => navigate(-1), variant: "secondary" },
      ]}
    />
  );
};

export default NotFoundPage;
