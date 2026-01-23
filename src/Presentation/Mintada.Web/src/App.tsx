import { useEffect } from 'react'
import { BrowserRouter, Routes, Route, Navigate } from 'react-router-dom';
import { OpenAPI } from './api'
import { MainLayout } from './components/Layout/MainLayout'
import { IssuerBrowser } from './components/IssuerBrowser/IssuerBrowser'
import { LandingPage } from './components/LandingPage/LandingPage'

// Initialize API Base URL immediately to avoid race conditions with initial render
OpenAPI.BASE = 'http://localhost:8080';

function App() {
  useEffect(() => {
    // Any other side effects
  }, [])

  return (
    <BrowserRouter>
      <Routes>
        {/* Landing Page - No Sidebar */}
        <Route path="/" element={<MainLayout><LandingPage /></MainLayout>} />

        {/* Catalog Routes - With Sidebar */}
        <Route path="/catalog/issuers" element={<MainLayout><IssuerBrowser /></MainLayout>} />
        <Route path="/catalog/issuers/:issuerSlug" element={<MainLayout><IssuerBrowser /></MainLayout>} />

        {/* Placeholders */}
        <Route path="/catalog/rulers" element={<MainLayout><div style={{ padding: '20px' }}>Rulers Browser (Coming Soon)</div></MainLayout>} />
        <Route path="/catalog/mints" element={<MainLayout><div style={{ padding: '20px' }}>Mints Browser (Coming Soon)</div></MainLayout>} />
        <Route path="/collection" element={<MainLayout><div style={{ padding: '20px' }}>My Collection (Coming Soon)</div></MainLayout>} />

        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
    </BrowserRouter>
  )
}

export default App
