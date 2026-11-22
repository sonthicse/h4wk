import { useQuery } from '@tanstack/react-query'
import { getWatchlistSettings } from '@/api/settings'

// Cấu hình [watchlist] trong sources.toml; chưa tải xong thì dùng giá trị mặc định của backend.
export function useWatchlistSettings() {
  const q = useQuery({ queryKey: ['watchlist-settings'], queryFn: getWatchlistSettings })
  return q.data ?? { check_interval_min: 2, initial_videos: 10, threads_per_channel: 1, worker_threads: 4 }
}
