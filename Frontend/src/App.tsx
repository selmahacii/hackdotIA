import React from 'react';
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { AuthProvider } from './context/AuthContext';
import { WebSocketProvider } from './context/WebSocketContext';
import { ProtectedRoute } from './components/ProtectedRoute';
import { Layout } from './components/Layout/Layout';

// Pages
import { LoginPage } from './pages/LoginPage';
import { DashboardPage } from './pages/DashboardPage';
import { MonitoringPage } from './pages/MonitoringPage';
import { ElderlyListPage } from './pages/ElderlyListPage';
import { ElderlyDetailPage } from './pages/ElderlyDetailPage';
import { AlertsListPage } from './pages/AlertsListPage';
import { AlertDetailPage } from './pages/AlertDetailPage';
import { MeasurementsPage } from './pages/MeasurementsPage';
import { SensorsPage } from './pages/SensorsPage';
import { DevicesPage } from './pages/DevicesPage';
import { AdminUsersPage } from './pages/AdminUsersPage';
import { AdminStatsPage } from './pages/AdminStatsPage';
import { NotFoundPage } from './pages/NotFoundPage';

export const App: React.FC = () => {
  return (
    <BrowserRouter>
      <AuthProvider>
        <WebSocketProvider>
          <Routes>
            {/* Public route */}
            <Route path="/login" element={<LoginPage />} />

            {/* Protected Routes wrapped in standard Layout */}
            <Route
              path="/"
              element={
                <ProtectedRoute>
                  <Layout />
                </ProtectedRoute>
              }
            >
              <Route index element={<Navigate to="/dashboard" replace />} />
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="monitoring" element={<MonitoringPage />} />

              {/* Residents */}
              <Route path="elderly" element={<ElderlyListPage />} />
              <Route path="elderly/:id" element={<ElderlyDetailPage />} />

              {/* Alerts & Incidents */}
              <Route path="alerts" element={<AlertsListPage />} />
              <Route path="alerts/:id" element={<AlertDetailPage />} />

              {/* Telemetry & Sensors */}
              <Route path="measurements" element={<MeasurementsPage />} />
              <Route path="sensors" element={<SensorsPage />} />
              <Route path="devices" element={<DevicesPage />} />

              {/* Admin only routes */}
              <Route
                path="admin"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'SUPERADMIN']}>
                    <AdminStatsPage />
                  </ProtectedRoute>
                }
              />
              <Route
                path="admin/users"
                element={
                  <ProtectedRoute allowedRoles={['ADMIN', 'SUPERADMIN']}>
                    <AdminUsersPage />
                  </ProtectedRoute>
                }
              />

              {/* Fallback inside Layout */}
              <Route path="*" element={<NotFoundPage />} />
            </Route>

            {/* Global fallback */}
            <Route path="*" element={<NotFoundPage />} />
          </Routes>
        </WebSocketProvider>
      </AuthProvider>
    </BrowserRouter>
  );
};

export default App;
