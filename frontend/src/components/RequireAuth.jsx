import React from "react";
import { Navigate } from "react-router-dom";
import { isAuthenticated } from "../hooks/useAuth";

export default function RequireAuth({ children }) {
  if (!isAuthenticated()) {
    return <Navigate to="/login" replace />;
  }

  return children;
}
