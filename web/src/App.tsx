import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import AppLayout from '@/components/AppLayout'
import CasesPage from '@/pages/CasesPage'
import CollectPage from '@/pages/CollectPage'
import FindingsPage from '@/pages/FindingsPage'
import LoginPage from '@/pages/LoginPage'
import PlaceholderPage from '@/pages/PlaceholderPage'

const queryClient = new QueryClient()

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<AppLayout />}>
            <Route path="/" element={<Navigate to="/cases" replace />} />
            <Route path="/cases" element={<CasesPage />} />
            <Route path="/cases/:caseId">
              <Route index element={<Navigate to="dashboard" replace />} />
              <Route path="dashboard" element={<PlaceholderPage title="Dashboard" task="T31, T35" />} />
              <Route path="collect" element={<CollectPage />} />
              <Route path="findings" element={<FindingsPage />} />
              <Route path="videos/:videoId" element={<PlaceholderPage title="Video detail" task="T26, T27" />} />
              <Route path="review" element={<PlaceholderPage title="Review queue" task="T28" />} />
              <Route path="watchlist" element={<PlaceholderPage title="Watchlist" task="T31" />} />
              <Route path="entities" element={<PlaceholderPage title="Entities" task="T39" />} />
            </Route>
            <Route path="/settings" element={<PlaceholderPage title="Settings" task="T33, T34" />} />
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
