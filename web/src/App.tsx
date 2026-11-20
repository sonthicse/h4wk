import { MutationCache, QueryCache, QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { BrowserRouter, Navigate, Route, Routes } from 'react-router'
import { UnauthorizedError } from '@/api/client'
import AppLayout from '@/components/AppLayout'
import RequireLogin from '@/components/RequireLogin'
import CapturePage from '@/pages/CapturePage'
import CollectPage from '@/pages/CollectPage'
import DashboardPage from '@/pages/DashboardPage'
import EntitiesPage from '@/pages/EntitiesPage'
import FindingsPage from '@/pages/FindingsPage'
import LoginPage from '@/pages/LoginPage'
import FindingReviewPage from '@/pages/FindingReviewPage'
import ReviewQueuePage from '@/pages/ReviewQueuePage'
import AIProvidersPage from '@/pages/settings/AIProvidersPage'
import SettingsLayout from '@/pages/settings/SettingsLayout'
import SourcesPage from '@/pages/settings/SourcesPage'
import VideoDetailPage from '@/pages/VideoDetailPage'
import VideosPage from '@/pages/VideosPage'
import WatchlistPage from '@/pages/WatchlistPage'

// Phiên hết hạn giữa chừng (API trả 401): kiểm tra lại /api/auth/me để RequireLogin chuyển sang /login.
// Bỏ qua lỗi của chính query ['me'], nếu không sẽ gọi lại /api/auth/me mãi và trang kẹt ở "Loading…".
function onError(error: Error, queryKey?: readonly unknown[]) {
  if (error instanceof UnauthorizedError && queryKey?.[0] !== 'me') {
    queryClient.invalidateQueries({ queryKey: ['me'] })
  }
}

const queryClient = new QueryClient({
  queryCache: new QueryCache({ onError: (error, query) => onError(error, query.queryKey) }),
  mutationCache: new MutationCache({ onError: (error) => onError(error) }),
})

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <BrowserRouter>
        <Routes>
          <Route path="/login" element={<LoginPage />} />
          <Route element={<RequireLogin />}>
            <Route element={<AppLayout />}>
              <Route path="/" element={<Navigate to="/dashboard" replace />} />
              <Route path="/dashboard" element={<DashboardPage />} />
              <Route path="/collect" element={<CollectPage />} />
              <Route path="/findings" element={<FindingsPage />} />
              <Route path="/review" element={<ReviewQueuePage />} />
              <Route path="/review/findings" element={<FindingReviewPage />} />
              <Route path="/watchlist" element={<WatchlistPage />} />
              <Route path="/entities" element={<EntitiesPage />} />
              <Route path="/videos" element={<VideosPage />} />
              <Route path="/videos/:videoId" element={<VideoDetailPage />} />
              <Route path="/videos/:videoId/captures/:captureId" element={<CapturePage />} />
              <Route path="/settings" element={<SettingsLayout />}>
                <Route index element={<Navigate to="sources" replace />} />
                <Route path="sources" element={<SourcesPage />} />
                <Route path="ai" element={<AIProvidersPage />} />
              </Route>
            </Route>
          </Route>
        </Routes>
      </BrowserRouter>
    </QueryClientProvider>
  )
}
