import { Component } from "react";

export default class ErrorBoundary extends Component {
  state = { hasError: false };

  static getDerivedStateFromError() {
    return { hasError: true };
  }

  componentDidCatch(error, info) {
    console.error("ErrorBoundary caught:", error, info);
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="flex min-h-screen items-center justify-center p-6 text-center">
          <div>
            <h2 className="text-xl font-bold text-slate-800 dark:text-slate-100">Something went wrong</h2>
            <p className="mt-2 text-slate-500">Try refreshing the page.</p>
            <button className="btn-primary mt-4" onClick={() => this.setState({ hasError: false })}>
              Retry
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}

