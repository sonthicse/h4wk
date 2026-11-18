// Dữ liệu giả để dựng giao diện trước khi có API. Tên trường bám theo SPEC 10.6;
// sẽ thay bằng kiểu sinh từ OpenAPI (`npm run gen:api`) khi T4 xong.

export type Case = {
  id: string
  name: string
  entities: string[]
  videoCount: number
  openFindings: number
  updatedAt: string
}

export type Severity = 'low' | 'medium' | 'high'
export type ReviewStatus = 'pending' | 'confirmed' | 'rejected' | 'needs_info'

export type Finding = {
  id: string
  caseId: string
  videoId: string
  videoTitle: string
  sourceKind: 'speech' | 'ocr' | 'visual' | 'title' | 'description' | 'thumbnail' | 'comment'
  start: number
  end: number
  quote: string
  category: 'insult' | 'unsupported_accusation' | 'fabrication' | 'legitimate_criticism' | 'neutral'
  severity: Severity
  status: ReviewStatus
}

export const cases: Case[] = [
  {
    id: 'c_demo',
    name: 'Demo case',
    entities: ['Nguyễn Văn A', 'Công ty B'],
    videoCount: 14,
    openFindings: 9,
    updatedAt: '2026-11-18T09:12:00Z',
  },
  {
    id: 'c_trial',
    name: 'Trial run',
    entities: ['Trần Thị C'],
    videoCount: 3,
    openFindings: 1,
    updatedAt: '2026-11-16T15:40:00Z',
  },
]

export const findings: Finding[] = [
  {
    id: 'f_001',
    caseId: 'c_demo',
    videoId: 'dQw4w9WgXcQ',
    videoTitle: 'Bình luận thời sự tối 17/11',
    sourceKind: 'speech',
    start: 92.4,
    end: 104.1,
    quote: 'Ông A nhận tiền để ký dự án này, ai cũng biết rồi.',
    category: 'unsupported_accusation',
    severity: 'high',
    status: 'pending',
  },
  {
    id: 'f_002',
    caseId: 'c_demo',
    videoId: 'dQw4w9WgXcQ',
    videoTitle: 'Bình luận thời sự tối 17/11',
    sourceKind: 'ocr',
    start: 131.0,
    end: 136.5,
    quote: 'CÔNG TY B LỪA ĐẢO',
    category: 'fabrication',
    severity: 'high',
    status: 'pending',
  },
  {
    id: 'f_003',
    caseId: 'c_demo',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
    sourceKind: 'visual',
    start: 45.0,
    end: 52.0,
    quote: 'Ảnh chân dung ông A ghép cạnh biểu tượng tiền',
    category: 'insult',
    severity: 'medium',
    status: 'needs_info',
  },
  {
    id: 'f_004',
    caseId: 'c_demo',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
    sourceKind: 'speech',
    start: 301.2,
    end: 309.8,
    quote: 'Lợi nhuận giảm 20% so với cùng kỳ, ban lãnh đạo cần giải trình.',
    category: 'legitimate_criticism',
    severity: 'low',
    status: 'rejected',
  },
  {
    id: 'f_005',
    caseId: 'c_trial',
    videoId: 'zzZZ9876abc',
    videoTitle: 'Livestream hỏi đáp',
    sourceKind: 'comment',
    start: 0,
    end: 0,
    quote: 'Bà C là đồ dối trá',
    category: 'insult',
    severity: 'medium',
    status: 'confirmed',
  },
]
