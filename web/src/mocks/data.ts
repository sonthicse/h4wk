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
export type SourceKind = 'speech' | 'ocr' | 'visual' | 'title' | 'description' | 'thumbnail' | 'comment'
export type Category = 'insult' | 'unsupported_accusation' | 'fabrication' | 'legitimate_criticism' | 'neutral'
export type Confidence = 'unverified' | 'likely' | 'highly_likely'
export type TriggerVia = 'speech' | 'ocr' | 'title' | 'description' | 'comment' | 'thumbnail' | 'face' | 'ref_image'

export type Finding = {
  id: string
  caseId: string
  videoId: string
  videoTitle: string
  channel: string
  sourceKind: SourceKind
  start: number
  end: number
  quote: string
  entity: string
  category: Category
  severity: Severity
  confidence: Confidence
  analyzer: 'static' | 'llm'
  model: { provider: string; model: string } | null
  triggers: { via: TriggerVia; score: number }[]
  reason: string
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

const llm = { provider: 'anthropic', model: 'claude-sonnet-5-5' }
const vlm = { provider: 'gemini', model: 'gemini-vision' }

export const findings: Finding[] = [
  {
    id: 'f_001',
    caseId: 'c_demo',
    videoId: 'dQw4w9WgXcQ',
    videoTitle: 'Bình luận thời sự tối 17/11',
    channel: 'Kênh Thời Sự X',
    sourceKind: 'speech',
    start: 92.4,
    end: 104.1,
    quote: 'Ông A nhận tiền để ký dự án này, ai cũng biết rồi.',
    entity: 'Nguyễn Văn A',
    category: 'unsupported_accusation',
    severity: 'high',
    confidence: 'highly_likely',
    analyzer: 'llm',
    model: llm,
    triggers: [{ via: 'speech', score: 0.94 }],
    reason: 'Cáo buộc nhận hối lộ được nêu như sự thật, không dẫn nguồn hay bằng chứng.',
    status: 'pending',
  },
  {
    id: 'f_002',
    caseId: 'c_demo',
    videoId: 'dQw4w9WgXcQ',
    videoTitle: 'Bình luận thời sự tối 17/11',
    channel: 'Kênh Thời Sự X',
    sourceKind: 'ocr',
    start: 131.0,
    end: 136.5,
    quote: 'CÔNG TY B LỪA ĐẢO',
    entity: 'Công ty B',
    category: 'fabrication',
    severity: 'high',
    confidence: 'likely',
    analyzer: 'static',
    model: null,
    triggers: [{ via: 'ocr', score: 0.88 }],
    reason: 'Chữ trên hình khớp tên đối tượng và từ khoá "lừa đảo" trong danh sách tĩnh.',
    status: 'pending',
  },
  {
    id: 'f_003',
    caseId: 'c_demo',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
    channel: 'Góc Nhìn Kinh Tế',
    sourceKind: 'visual',
    start: 45.0,
    end: 52.0,
    quote: 'Ảnh chân dung ông A ghép cạnh biểu tượng tiền',
    entity: 'Nguyễn Văn A',
    category: 'insult',
    severity: 'medium',
    confidence: 'likely',
    analyzer: 'llm',
    model: vlm,
    triggers: [
      { via: 'face', score: 0.82 },
      { via: 'ref_image', score: 0.71 },
    ],
    reason: 'Đoạn không nhắc tên nhưng khuôn mặt khớp ảnh mẫu; hình ghép ngụ ý tham nhũng.',
    status: 'needs_info',
  },
  {
    id: 'f_004',
    caseId: 'c_demo',
    videoId: 'aBcD1234xyz',
    videoTitle: 'Phân tích báo cáo tài chính quý 3',
    channel: 'Góc Nhìn Kinh Tế',
    sourceKind: 'speech',
    start: 301.2,
    end: 309.8,
    quote: 'Lợi nhuận giảm 20% so với cùng kỳ, ban lãnh đạo cần giải trình.',
    entity: 'Công ty B',
    category: 'legitimate_criticism',
    severity: 'low',
    confidence: 'highly_likely',
    analyzer: 'llm',
    model: llm,
    triggers: [{ via: 'speech', score: 0.9 }],
    reason: 'Phê bình dựa trên số liệu công khai, không xúc phạm.',
    status: 'rejected',
  },
  {
    id: 'f_006',
    caseId: 'c_demo',
    videoId: 'qWeRtY98765',
    videoTitle: 'SỰ THẬT về ông A mà không ai dám nói',
    channel: 'Tin Nóng 24h',
    sourceKind: 'title',
    start: 0,
    end: 0,
    quote: 'SỰ THẬT về ông A mà không ai dám nói',
    entity: 'Nguyễn Văn A',
    category: 'unsupported_accusation',
    severity: 'medium',
    confidence: 'unverified',
    analyzer: 'static',
    model: null,
    triggers: [{ via: 'title', score: 0.75 }],
    reason: 'Tiêu đề giật gân nhắc tên đối tượng; cần xem nội dung để xác định.',
    status: 'pending',
  },
  {
    id: 'f_007',
    caseId: 'c_demo',
    videoId: 'qWeRtY98765',
    videoTitle: 'SỰ THẬT về ông A mà không ai dám nói',
    channel: 'Tin Nóng 24h',
    sourceKind: 'thumbnail',
    start: 0,
    end: 0,
    quote: 'Thumbnail: ảnh ông A sau song sắt, chữ "SẮP BỊ BẮT"',
    entity: 'Nguyễn Văn A',
    category: 'fabrication',
    severity: 'high',
    confidence: 'likely',
    analyzer: 'llm',
    model: vlm,
    triggers: [
      { via: 'thumbnail', score: 0.86 },
      { via: 'face', score: 0.79 },
    ],
    reason: 'Hình ghép ngụ ý đối tượng sắp bị bắt, không có căn cứ.',
    status: 'pending',
  },
  {
    id: 'f_008',
    caseId: 'c_demo',
    videoId: 'qWeRtY98765',
    videoTitle: 'SỰ THẬT về ông A mà không ai dám nói',
    channel: 'Tin Nóng 24h',
    sourceKind: 'speech',
    start: 214.6,
    end: 228.0,
    quote: 'Nghe nói ông ta có ba căn biệt thự đứng tên người nhà.',
    entity: 'Nguyễn Văn A',
    category: 'unsupported_accusation',
    severity: 'medium',
    confidence: 'likely',
    analyzer: 'llm',
    model: llm,
    triggers: [{ via: 'speech', score: 0.83 }],
    reason: 'Thông tin "nghe nói", không kiểm chứng, gắn với đối tượng.',
    status: 'confirmed',
  },
  {
    id: 'f_009',
    caseId: 'c_demo',
    videoId: 'qWeRtY98765',
    videoTitle: 'SỰ THẬT về ông A mà không ai dám nói',
    channel: 'Tin Nóng 24h',
    sourceKind: 'comment',
    start: 0,
    end: 0,
    quote: 'Loại người như A phải đi tù hết',
    entity: 'Nguyễn Văn A',
    category: 'insult',
    severity: 'low',
    confidence: 'likely',
    analyzer: 'llm',
    model: llm,
    triggers: [{ via: 'comment', score: 0.8 }],
    reason: 'Bình luận xúc phạm của người xem, mức lan truyền thấp.',
    status: 'pending',
  },
  {
    id: 'f_010',
    caseId: 'c_demo',
    videoId: 'zXcV5555aaa',
    videoTitle: 'Review sản phẩm mới của Công ty B',
    channel: 'Tech Việt',
    sourceKind: 'description',
    start: 0,
    end: 0,
    quote: 'Đừng mua hàng của B, toàn hàng giả hàng nhái!!!',
    entity: 'Công ty B',
    category: 'fabrication',
    severity: 'medium',
    confidence: 'unverified',
    analyzer: 'static',
    model: null,
    triggers: [{ via: 'description', score: 0.7 }],
    reason: 'Mô tả video chứa từ khoá "hàng giả" gắn với tên đối tượng.',
    status: 'pending',
  },
  {
    id: 'f_011',
    caseId: 'c_demo',
    videoId: 'zXcV5555aaa',
    videoTitle: 'Review sản phẩm mới của Công ty B',
    channel: 'Tech Việt',
    sourceKind: 'speech',
    start: 512.3,
    end: 518.9,
    quote: 'Pin dùng được khoảng sáu tiếng, hơi kém so với quảng cáo.',
    entity: 'Công ty B',
    category: 'neutral',
    severity: 'low',
    confidence: 'highly_likely',
    analyzer: 'llm',
    model: llm,
    triggers: [{ via: 'speech', score: 0.92 }],
    reason: 'Nhận xét sản phẩm trung lập, có số liệu cụ thể.',
    status: 'pending',
  },
  {
    id: 'f_005',
    caseId: 'c_trial',
    videoId: 'zzZZ9876abc',
    videoTitle: 'Livestream hỏi đáp',
    channel: 'Kênh Cá Nhân C',
    sourceKind: 'comment',
    start: 0,
    end: 0,
    quote: 'Bà C là đồ dối trá',
    entity: 'Trần Thị C',
    category: 'insult',
    severity: 'medium',
    confidence: 'likely',
    analyzer: 'llm',
    model: llm,
    triggers: [{ via: 'comment', score: 0.81 }],
    reason: 'Bình luận xúc phạm trực tiếp đối tượng.',
    status: 'confirmed',
  },
]
