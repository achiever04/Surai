import React, { useEffect } from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import Sidebar from './components/common/Sidebar';
import Header from './components/common/Header';
import ThemeToggle from './components/common/ThemeToggle';
import ErrorBoundary from './components/common/ErrorBoundary';
import LoginPage from './pages/LoginPage';
import DashboardPage from './pages/DashboardPage';
import CamerasPage from './pages/CamerasPage';
import WatchlistPage from './pages/WatchlistPage';
import EvidencePage from './pages/EvidencePage';
import AnalyticsPage from './pages/AnalyticsPage';
import AuditPage from './pages/AuditPage';
import AlertsPage from './pages/AlertsPage';
import SettingsPage from './pages/SettingsPage';
import LoadingSpinner from './components/common/LoadingSpinner';
import { useAuth } from './context/AuthContext';
import { AppProvider } from './context/AppContext';
import { ThemeProvider } from './context/ThemeContext';
import webSocketService from './services/websocket';

function AppContent() {
  const { isAuthenticated, isLoading } = useAuth();

  // Initialize WebSocket when authenticated
  useEffect(() => {
    if (isAuthenticated) {
      webSocketService.connect();

      // Cleanup on unmount or logout
      return () => {
        webSocketService.disconnect();
      };
    }
  }, [isAuthenticated]);

  if (isLoading) {
    return (
      <div className="h-screen w-full flex items-center justify-center bg-gray-900">
        <LoadingSpinner message="Initializing System..." />
      </div>
    );
  }

  return (
    <BrowserRouter>
      <div className="flex h-screen w-full bg-gray-100 overflow-hidden">
        {!isAuthenticated ? (
          <Routes>
            <Route path="/login" element={<LoginPage />} />
            <Route path="*" element={<Navigate to="/login" replace />} />
          </Routes>
        ) : (
          <>
            <Sidebar />
            <div className="flex-1 flex flex-col min-w-0 overflow-hidden">
              <Header />
              <main className="flex-1 overflow-x-hidden overflow-y-auto bg-gray-100 p-6">
                <Routes>
                  <Route path="/" element={<DashboardPage />} />
                  <Route path="/alerts" element={<AlertsPage />} />
                  <Route path="/cameras" element={<CamerasPage />} />
                  <Route path="/watchlist" element={<WatchlistPage />} />
                  <Route path="/evidence" element={<EvidencePage />} />
                  <Route path="/analytics" element={<AnalyticsPage />} />
                  <Route path="/audit" element={<AuditPage />} />
                  <Route path="/settings" element={<SettingsPage />} />
                  <Route path="*" element={<Navigate to="/" replace />} />
                </Routes>
              </main>
            </div>
            <ThemeToggle />
          </>
        )}
      </div>
    </BrowserRouter>
  );
}

// Wrap everything in providers + ErrorBoundary
export default function App() {
  return (
    <ErrorBoundary>
      <ThemeProvider>
        <AppProvider>
          <AppContent />
        </AppProvider>
      </ThemeProvider>
    </ErrorBoundary>
  );
}