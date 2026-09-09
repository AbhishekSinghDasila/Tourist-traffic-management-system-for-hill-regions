import { Navigate, Route, Routes } from 'react-router-dom'
import { AuthProvider } from './context/AuthContext'
import { ProtectedRoute } from './components/routing/ProtectedRoute'
import Landing from './pages/Landing'
import Login from './pages/Login'
import Register from './pages/Register'
import ComplaintFormPage from './pages/ComplaintFormPage'
import Unauthorized from './pages/Unauthorized'
import NotFound from './pages/NotFound'
import TouristDashboard from './pages/tourist/TouristDashboard'
import CitizenDashboard from './pages/citizen/CitizenDashboard'
import PoliceDashboard from './pages/police/PoliceDashboard'
import AdminPanel from './pages/admin/AdminPanel'
import EmergencyDashboard from './pages/emergency/EmergencyDashboard'

export default function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<Landing />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route path="/complaints/new" element={<ComplaintFormPage />} />
        <Route path="/unauthorized" element={<Unauthorized />} />

        <Route
          path="/tourist"
          element={
            <ProtectedRoute roles={['tourist']}>
              <TouristDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/citizen"
          element={
            <ProtectedRoute roles={['citizen']}>
              <CitizenDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/police"
          element={
            <ProtectedRoute roles={['police']}>
              <PoliceDashboard />
            </ProtectedRoute>
          }
        />
        <Route
          path="/admin"
          element={
            <ProtectedRoute roles={['admin']}>
              <AdminPanel />
            </ProtectedRoute>
          }
        />
        <Route
          path="/emergency"
          element={
            <ProtectedRoute roles={['emergency_team']}>
              <EmergencyDashboard />
            </ProtectedRoute>
          }
        />

        <Route path="/404" element={<NotFound />} />
        <Route path="*" element={<Navigate to="/404" replace />} />
      </Routes>
    </AuthProvider>
  )
}
