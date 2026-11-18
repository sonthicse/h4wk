import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import AppLayout from '@/components/AppLayout'
import CapturePage from '@/pages/CapturePage'
import CasesPage from '@/pages/CasesPage'
import CollectPage from '@/pages/CollectPage'
import DashboardPage from '@/pages/DashboardPage'
import EntitiesPage from '@/pages/EntitiesPage'
import FindingsPage from '@/pages/FindingsPage'
import LoginPage from '@/pages/LoginPage'
import ReviewQueuePage from '@/pages/ReviewQueuePage'
import AIProvidersPage from '@/pages/settings/AIProvidersPage'
import SettingsLayout from '@/pages/settings/SettingsLayout'
import SourcesPage from '@/pages/settings/SourcesPage'
import VideoDetailPage from '@/pages/VideoDetailPage'
import WatchlistPage from '@/pages/WatchlistPage'

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
              <Route path="dashboard" element={<DashboardPage />} />
              <Route path="collect" element={<CollectPage />} />
              <Route path="findings" element={<FindingsPage />} />
              <Route path="videos/:videoId" element={<VideoDetailPage />} />
              <Route path="videos/:videoId/captures/:captureId" element={<CapturePage />} />
              <Route path="review" element={<ReviewQueuePage />} />
              <Route path="watchlist" element={<WatchlistPage />} />
              <Route path="entities" element={<EntitiesPage />} />
            </Route>
            <Route path="/settings" element={<SettingsLayout />}>
              <Route index element={<Navigate to="sources" replace />} />
              <Route path="sources" element={<SourcesPage />} />
              <Route path="ai" element={<AIProvidersPage />} />
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
