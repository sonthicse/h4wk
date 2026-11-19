// Dữ liệu giả cho trang Video detail. Hình dạng bám hợp đồng C2 (normalized) và C3 (timeline),
// tên trường camelCase. Sẽ thay bằng API thật của T13, T22, T29 khi có.

export type TranscriptKind = 'uploaded' | 'auto' | 'supadata_ai' | 'stt'
export type CaptureLevel = 'metadata' | 'text' | 'full'

export type TranscriptSegment = { start: number; end: number; text: string }
export type Transcript = { kind: TranscriptKind; lang: string; segments: TranscriptSegment[] }

// bbox là [x, y, w, h] tính bằng pixel trên khung 854×480 (bản proxy 480p).
export const FRAME_W = 854
export const FRAME_H = 480
export type Bbox = [number, number, number, number]

export type Keyframe = {
  id: string
  t: number
  hue: number // màu nền của ảnh giả
  ocr: { text: string; bbox: Bbox }[]
  faces: { label: string; bbox: Bbox }[] // khuôn mặt khớp ảnh mẫu của đối tượng
  refImages: { label: string; bbox: Bbox }[] // ảnh mẫu (chân dung quen thuộc, logo) khớp
  visual: { description: string; offensiveCues: string[]; provider: string; model: string } | null
}

export type VideoComment = {
  id: string
  parentId: string | null
  author: string
  text: string
  publishedAt: string
  likeCount: number
  findingId?: string // có giá trị khi comment bị gắn cờ
}

export type VideoCapture = {
  id: string
  level: CaptureLevel
  capturedAt: string
  transcriptKinds: TranscriptKind[]
  commentCount: number
  keyframeCount: number
}

export type VideoDetail = {
  id: string
  title: string
  channel: string
  publishedAt: string
  durationS: number
  viewCount: number
  likeCount: number
  commentCount: number
  transcripts: Transcript[]
  keyframes: Keyframe[]
  comments: VideoComment[]
  captures: VideoCapture[]
}

// "Chạy" qua danh sách [start, end, text] cho gọn.
function segs(list: [number, number, string][]): TranscriptSegment[] {
  return list.map(([start, end, text]) => ({ start, end, text }))
}

// Bản auto giả: chữ thường, bỏ dấu câu, như phụ đề tự động của YouTube.
function autoOf(t: Transcript): Transcript {
  const strip = (s: string) => s.toLowerCase().replace(/[.,!?"]/g, '')
  return { kind: 'auto', lang: t.lang, segments: t.segments.map((s) => ({ ...s, text: strip(s.text) })) }
}

const model = { provider: 'gemini', model: 'gemini-vision' }

// ---------- dQw4w9WgXcQ: speech + OCR ----------
const dqwUploaded: Transcript = {
  kind: 'uploaded',
  lang: 'vi',
  segments: segs([
    [0, 14, 'Chào quý vị, đây là bản bình luận thời sự tối ngày mười bảy tháng mười một.'],
    [14, 30, 'Hôm nay chúng ta điểm qua ba sự kiện nổi bật trong tuần.'],
    [30, 47, 'Thứ nhất là việc thành phố công bố kế hoạch mở rộng tuyến đường vành đai.'],
    [47, 63, 'Theo kế hoạch, dự án sẽ khởi công vào quý hai năm sau.'],
    [63, 78, 'Thứ hai, một số doanh nghiệp địa phương báo cáo doanh thu quý ba tăng nhẹ.'],
    [78, 90, 'Còn bây giờ, chúng ta chuyển sang chuyện đang được bàn tán nhiều nhất.'],
    [90, 105, 'Ông A nhận tiền để ký dự án này, ai cũng biết rồi.'],
    [105, 118, 'Tất nhiên đó là điều mà nhiều người xì xào, tôi chỉ nói lại thôi.'],
    [118, 128, 'Mời quý vị xem tiếp hình ảnh được người xem gửi về.'],
    [128, 140, 'Trên màn hình là dòng chữ mà nhiều người đã chia sẻ trên mạng xã hội.'],
    [140, 158, 'Tôi không khẳng định gì thêm, quý vị tự đánh giá.'],
    [158, 176, 'Quay lại chuyện thời tiết, cuối tuần này miền Bắc có đợt rét đầu mùa.'],
    [176, 195, 'Người dân cần chuẩn bị quần áo ấm và chú ý sức khoẻ người già, trẻ nhỏ.'],
    [195, 214, 'Về giao thông, các tuyến cao tốc phía Nam vẫn thông suốt.'],
    [214, 232, 'Cảm ơn quý vị đã theo dõi, hẹn gặp lại trong bản tin ngày mai.'],
    [232, 240, 'Xin chào và hẹn gặp lại.'],
  ]),
}

const dqwKeyframes: Keyframe[] = [
  { id: 'kf_0001', t: 12, hue: 210, ocr: [{ text: 'BÌNH LUẬN THỜI SỰ', bbox: [40, 30, 360, 50] }], faces: [], refImages: [], visual: { description: 'Người dẫn chương trình ngồi trước phông xanh, logo kênh ở góc phải.', offensiveCues: [], ...model } },
  { id: 'kf_0002', t: 40, hue: 190, ocr: [], faces: [], refImages: [], visual: { description: 'Bản đồ thành phố với tuyến vành đai tô đỏ.', offensiveCues: [], ...model } },
  { id: 'kf_0003', t: 70, hue: 150, ocr: [{ text: 'DOANH THU QUÝ 3 +2%', bbox: [60, 380, 420, 50] }], faces: [], refImages: [], visual: { description: 'Biểu đồ cột doanh thu, cột cuối cao hơn nhẹ.', offensiveCues: [], ...model } },
  { id: 'kf_0004', t: 95, hue: 20, ocr: [{ text: 'AI CŨNG BIẾT', bbox: [520, 400, 280, 44] }], faces: [{ label: 'Nguyễn Văn A (khuôn mặt mẫu)', bbox: [300, 90, 150, 190] }], refImages: [], visual: { description: 'Ảnh chân dung một người đàn ông mặc vest, bên cạnh là biểu tượng đồng tiền và dòng chữ chạy dưới màn hình.', offensiveCues: ['ghép biểu tượng tiền cạnh chân dung'], ...model } },
  { id: 'kf_0005', t: 118, hue: 280, ocr: [], faces: [], refImages: [], visual: { description: 'Màn hình chat với nhiều tin nhắn của người xem.', offensiveCues: [], ...model } },
  { id: 'kf_0006', t: 133, hue: 0, ocr: [{ text: 'CÔNG TY B LỪA ĐẢO', bbox: [150, 200, 560, 80] }], faces: [], refImages: [{ label: 'Logo Công ty B (ảnh mẫu)', bbox: [30, 20, 120, 120] }], visual: { description: 'Nền đỏ, dòng chữ lớn màu trắng nằm giữa khung, logo công ty ở góc trên bên trái.', offensiveCues: ['chữ buộc tội in lớn'], ...model } },
  { id: 'kf_0007', t: 165, hue: 200, ocr: [], faces: [], refImages: [], visual: { description: 'Bản đồ thời tiết miền Bắc với vùng áp cao lạnh.', offensiveCues: [], ...model } },
  { id: 'kf_0008', t: 205, hue: 100, ocr: [{ text: 'CAO TỐC THÔNG SUỐT', bbox: [60, 400, 400, 44] }], faces: [], refImages: [], visual: { description: 'Cảnh quay cao tốc, xe cộ di chuyển bình thường.', offensiveCues: [], ...model } },
  { id: 'kf_0009', t: 228, hue: 230, ocr: [], faces: [], refImages: [], visual: { description: 'Người dẫn chương trình vẫy tay chào, logo kênh.', offensiveCues: [], ...model } },
]

const dqwComments: VideoComment[] = [
  { id: 'c1', parentId: null, author: '@minhtuan88', text: 'Thông tin này có nguồn không vậy anh?', publishedAt: '2026-11-17T21:10:00+07:00', likeCount: 42 },
  { id: 'c2', parentId: 'c1', author: '@kenhthoisux', text: 'Mình chỉ tổng hợp lại từ mạng xã hội, bạn tự kiểm chứng nhé.', publishedAt: '2026-11-17T21:25:00+07:00', likeCount: 5 },
  { id: 'c3', parentId: 'c1', author: '@lanphuong', text: 'Không có nguồn thì đừng nói như thật.', publishedAt: '2026-11-17T21:40:00+07:00', likeCount: 17 },
  { id: 'c4', parentId: null, author: '@hoangnam', text: 'Phần dự báo thời tiết rất hữu ích, cảm ơn kênh.', publishedAt: '2026-11-17T22:02:00+07:00', likeCount: 3 },
  { id: 'c5', parentId: null, author: '@dungpham', text: 'Video hay, mong kênh ra đều hơn.', publishedAt: '2026-11-18T08:15:00+07:00', likeCount: 1 },
]

// ---------- aBcD1234xyz: visual ở đoạn không nhắc tên + speech ----------
const abcdStt: Transcript = {
  kind: 'stt',
  lang: 'vi',
  segments: segs([
    [0, 20, 'Xin chào các bạn, hôm nay ta cùng phân tích báo cáo tài chính quý ba.'],
    [20, 40, 'Trước hết là tổng quan thị trường, lãi suất vẫn giữ ở mức thấp.'],
    [40, 55, 'Tiếp theo, chúng ta nhìn vào nhóm ngành bất động sản và xây dựng.'],
    [55, 75, 'Nhóm này chịu áp lực lớn từ chi phí vốn và nhu cầu giảm.'],
    [75, 100, 'Bảng cân đối kế toán cho thấy nợ ngắn hạn tăng so với đầu năm.'],
    [100, 125, 'Tuy nhiên dòng tiền hoạt động kinh doanh vẫn dương.'],
    [125, 150, 'Chuyển sang nhóm bán lẻ, doanh thu tăng đều nhờ mùa mua sắm cuối năm.'],
    [150, 180, 'Biên lợi nhuận gộp cải thiện nhẹ, từ hai mươi lên hai mươi hai phần trăm.'],
    [180, 210, 'Chi phí quản lý tăng nhưng vẫn trong tầm kiểm soát.'],
    [210, 240, 'Về nhóm công nghệ, các công ty lớn tiếp tục đầu tư vào trí tuệ nhân tạo.'],
    [240, 270, 'Tỷ lệ chi cho nghiên cứu tăng gần ba phần trăm so với cùng kỳ.'],
    [270, 300, 'Còn về Công ty B, chúng ta cần xem kỹ phần thuyết minh báo cáo.'],
    [300, 312, 'Lợi nhuận giảm 20% so với cùng kỳ, ban lãnh đạo cần giải trình.'],
    [312, 335, 'Các khoản phải thu tăng mạnh, đây là điểm nhà đầu tư cần lưu ý.'],
    [335, 360, 'Cảm ơn các bạn đã xem, đừng quên đăng ký kênh.'],
  ]),
}

const abcdKeyframes: Keyframe[] = [
  { id: 'kf_0001', t: 6, hue: 220, ocr: [{ text: 'PHÂN TÍCH BCTC QUÝ 3', bbox: [50, 40, 460, 56] }], faces: [], refImages: [], visual: { description: 'Tiêu đề video trên nền xanh đậm, biểu tượng biểu đồ.', offensiveCues: [], ...model } },
  { id: 'kf_0002', t: 30, hue: 180, ocr: [], faces: [], refImages: [], visual: { description: 'Biểu đồ đường lãi suất theo tháng.', offensiveCues: [], ...model } },
  { id: 'kf_0003', t: 48, hue: 30, ocr: [], faces: [{ label: 'Nguyễn Văn A (khuôn mặt mẫu)', bbox: [180, 70, 170, 210] }], refImages: [{ label: 'Chân dung quen thuộc (ảnh mẫu)', bbox: [150, 50, 230, 270] }], visual: { description: 'Ảnh chân dung một người đàn ông ghép cạnh biểu tượng tiền; không có chữ nào nêu tên.', offensiveCues: ['ghép chân dung cạnh biểu tượng tiền'], ...model } },
  { id: 'kf_0004', t: 90, hue: 160, ocr: [{ text: 'NỢ NGẮN HẠN +12%', bbox: [70, 390, 360, 48] }], faces: [], refImages: [], visual: { description: 'Bảng cân đối kế toán với ô nợ ngắn hạn được tô vàng.', offensiveCues: [], ...model } },
  { id: 'kf_0005', t: 140, hue: 120, ocr: [], faces: [], refImages: [], visual: { description: 'Biểu đồ cột doanh thu ngành bán lẻ.', offensiveCues: [], ...model } },
  { id: 'kf_0006', t: 210, hue: 260, ocr: [], faces: [], refImages: [], visual: { description: 'Logo các công ty công nghệ xếp thành hàng.', offensiveCues: [], ...model } },
  { id: 'kf_0007', t: 305, hue: 340, ocr: [{ text: 'LỢI NHUẬN -20%', bbox: [120, 380, 360, 56] }], faces: [], refImages: [{ label: 'Logo Công ty B (ảnh mẫu)', bbox: [40, 30, 110, 110] }], visual: { description: 'Biểu đồ lợi nhuận giảm, logo công ty ở góc trên.', offensiveCues: [], ...model } },
]

// Tạo nhanh một video tối thiểu cho các video còn lại.
function minimal(v: Pick<VideoDetail, 'id' | 'title' | 'channel' | 'publishedAt' | 'durationS' | 'viewCount' | 'likeCount' | 'commentCount'>, overrides: Partial<VideoDetail>): VideoDetail {
  return { ...v, transcripts: [], keyframes: [], comments: [], captures: [], ...overrides }
}

const store: VideoDetail[] = [
  {
    id: 'dQw4w9WgXcQ',
    title: 'Bình luận thời sự tối 17/11',
    channel: 'Kênh Thời Sự X',
    publishedAt: '2026-11-17T20:00:00+07:00',
    durationS: 240,
    viewCount: 48210,
    likeCount: 1320,
    commentCount: 5,
    transcripts: [dqwUploaded, autoOf(dqwUploaded), { ...dqwUploaded, kind: 'stt' }],
    keyframes: dqwKeyframes,
    comments: dqwComments,
    captures: [
      { id: '20261118T091200', level: 'full', capturedAt: '2026-11-18T09:12:00+07:00', transcriptKinds: ['uploaded', 'auto', 'stt'], commentCount: 5, keyframeCount: 9 },
      { id: '20261117T213000', level: 'full', capturedAt: '2026-11-17T21:30:00+07:00', transcriptKinds: ['uploaded', 'auto', 'stt'], commentCount: 3, keyframeCount: 9 },
    ],
  },
  {
    id: 'aBcD1234xyz',
    title: 'Phân tích báo cáo tài chính quý 3',
    channel: 'Góc Nhìn Kinh Tế',
    publishedAt: '2026-11-16T12:00:00+07:00',
    durationS: 360,
    viewCount: 15730,
    likeCount: 410,
    commentCount: 2,
    transcripts: [abcdStt, autoOf({ ...abcdStt, kind: 'auto' })],
    keyframes: abcdKeyframes,
    comments: [
      { id: 'c1', parentId: null, author: '@investor_vn', text: 'Phân tích rất rõ ràng, mong có thêm phần so sánh với quý trước.', publishedAt: '2026-11-16T14:20:00+07:00', likeCount: 9 },
      { id: 'c2', parentId: 'c1', author: '@gocnhinkinhte', text: 'Cảm ơn bạn, kỳ sau mình sẽ bổ sung.', publishedAt: '2026-11-16T15:01:00+07:00', likeCount: 2 },
    ],
    captures: [
      { id: '20261116T150500', level: 'full', capturedAt: '2026-11-16T15:05:00+07:00', transcriptKinds: ['stt', 'auto'], commentCount: 2, keyframeCount: 7 },
    ],
  },
  minimal(
    { id: 'qWeRtY98765', title: 'SỰ THẬT về ông A mà không ai dám nói', channel: 'Tin Nóng 24h', publishedAt: '2026-11-18T07:30:00+07:00', durationS: 300, viewCount: 96400, likeCount: 2100, commentCount: 3 },
    {
      transcripts: [{ kind: 'auto', lang: 'vi', segments: segs([
        [0, 40, 'chào mừng các bạn đến với kênh tin nóng hôm nay chúng ta nói về một nhân vật gây tranh cãi'],
        [214, 228, 'nghe nói ông ta có ba căn biệt thự đứng tên người nhà'],
        [228, 300, 'các bạn nghĩ sao hãy để lại bình luận bên dưới'],
      ]) }],
      comments: [
        { id: 'c1', parentId: null, author: '@nguoixem01', text: 'Loại người như A phải đi tù hết', publishedAt: '2026-11-18T08:20:00+07:00', likeCount: 14, findingId: 'f_009' },
        { id: 'c2', parentId: 'c1', author: '@binhtinh', text: 'Chưa có kết luận gì thì đừng vội phán xét.', publishedAt: '2026-11-18T08:35:00+07:00', likeCount: 6 },
        { id: 'c3', parentId: null, author: '@tinnong_fan', text: 'Chờ phần tiếp theo của kênh.', publishedAt: '2026-11-18T09:00:00+07:00', likeCount: 0 },
      ],
      captures: [{ id: '20261118T080000', level: 'text', capturedAt: '2026-11-18T08:00:00+07:00', transcriptKinds: ['auto'], commentCount: 3, keyframeCount: 0 }],
    },
  ),
  minimal(
    { id: 'zXcV5555aaa', title: 'Review sản phẩm mới của Công ty B', channel: 'Tech Việt', publishedAt: '2026-11-15T09:00:00+07:00', durationS: 600, viewCount: 22300, likeCount: 780, commentCount: 0 },
    {
      transcripts: [{ kind: 'auto', lang: 'vi', segments: segs([[510, 520, 'pin dùng được khoảng sáu tiếng hơi kém so với quảng cáo']]) }],
      captures: [{ id: '20261115T103000', level: 'metadata', capturedAt: '2026-11-15T10:30:00+07:00', transcriptKinds: [], commentCount: 0, keyframeCount: 0 }],
    },
  ),
  minimal(
    { id: 'zzZZ9876abc', title: 'Livestream hỏi đáp', channel: 'Kênh Cá Nhân C', publishedAt: '2026-11-16T21:00:00+07:00', durationS: 900, viewCount: 3120, likeCount: 95, commentCount: 1 },
    {
      comments: [{ id: 'c1', parentId: null, author: '@nguoixem02', text: 'Bà C là đồ dối trá', publishedAt: '2026-11-16T21:45:00+07:00', likeCount: 2, findingId: 'f_005' }],
      captures: [{ id: '20261116T224000', level: 'text', capturedAt: '2026-11-16T22:40:00+07:00', transcriptKinds: [], commentCount: 1, keyframeCount: 0 }],
    },
  ),
]

// Bản đồng bộ, dùng cho dữ liệu giả của Dashboard.
export function findVideo(videoId: string): VideoDetail | null {
  return store.find((v) => v.id === videoId) ?? null
}

// Trả về null khi không có video để trang hiện "not found".
export function getVideo(videoId: string): Promise<VideoDetail | null> {
  const video = store.find((v) => v.id === videoId) ?? null
  return new Promise((r) => setTimeout(() => r(video), 150))
}
