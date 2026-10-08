// Client for the FastAPI backend (backend/main.py). Vite proxies /api and /media to it in dev.

export type StockStatus = 'in_stock' | 'low_stock' | 'sold_out'

export interface SizeStock {
  size: string
  quantity: number
  status: StockStatus
}

export interface ProductSummary {
  product_id: string
  name: string
  category: string
  garment_type: string
  price: number
  short_description: string | null
  image_url: string
  total_stock: number
  sizes_in_stock: string[]
}

export interface ProductDetail extends ProductSummary {
  description: string | null
  garment_color: string | null
  design_colors: string[]
  search_tags: string[]
  inventory: SizeStock[]
}

/** A product card as sent by /api/chat (subset of ProductSummary). */
export type CardProduct = Pick<
  ProductSummary,
  'product_id' | 'name' | 'category' | 'price' | 'image_url' | 'short_description' | 'sizes_in_stock'
>

/** Search matches the page shows as a results grid (Problem 7 API contract). */
export interface ProductResults {
  title: string
  query: string
  total_matches: number
  products: CardProduct[]
}

export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  products?: CardProduct[]
}

export interface ChatReply {
  reply: string
  products: CardProduct[]
  results: ProductResults | null
}

async function getJson<T>(url: string): Promise<T> {
  const res = await fetch(url)
  if (!res.ok) throw new Error(res.status === 404 ? 'not_found' : `Request failed (${res.status})`)
  return res.json() as Promise<T>
}

export function fetchProducts(): Promise<ProductSummary[]> {
  return getJson<ProductSummary[]>('/api/products')
}

export function fetchProduct(productId: string): Promise<ProductDetail> {
  return getJson<ProductDetail>(`/api/products/${encodeURIComponent(productId)}`)
}

// ---------- Accounts (session cookie is HttpOnly and set by the backend) ----------

export interface User {
  id: number
  first_name: string
  last_name: string
  email: string
}

export interface SignupInput {
  first_name: string
  last_name: string
  email: string
  password: string
  confirm_password: string
}

/** Error carrying the backend's shopper-friendly message (FastAPI `detail`). */
export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function postJson<T>(url: string, body?: unknown): Promise<T> {
  const res = await fetch(url, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    const message = typeof data?.detail === 'string' ? data.detail : 'Something went wrong. Please try again.'
    throw new ApiError(res.status, message)
  }
  return (res.status === 204 ? undefined : await res.json()) as T
}

export const signup = (input: SignupInput) => postJson<User>('/api/auth/signup', input)
export const login = (email: string, password: string) => postJson<User>('/api/auth/login', { email, password })
export const logout = () => postJson<void>('/api/auth/logout')

export async function fetchCurrentUser(): Promise<User | null> {
  const res = await fetch('/api/auth/me')
  return res.ok ? ((await res.json()) as User) : null
}

/** A logged-in shopper's saved chat (Problem 8). Guests get an empty list. */
export async function fetchChatHistory(): Promise<ChatMessage[]> {
  const res = await fetch('/api/chat/history')
  if (!res.ok) return []
  const rows = (await res.json()) as { role: 'user' | 'assistant'; content: string; products: CardProduct[] }[]
  return rows.map(({ role, content, products }) => ({ role, content, products }))
}

/** Send one chat message to the agent (POST /api/chat). `history` = earlier turns only. */
export async function sendChatMessage(
  message: string,
  history: ChatMessage[],
  currentProductId: string | null,
): Promise<ChatReply> {
  const res = await fetch('/api/chat', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      message,
      history: history.map(({ role, content }) => ({ role, content })),
      current_product_id: currentProductId,
    }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => null)
    throw new ApiError(res.status, typeof data?.detail === 'string' ? data.detail : 'The shop assistant is unavailable.')
  }
  return res.json() as Promise<ChatReply>
}

// Keep "T-Shirt" on one line in headings (non-breaking hyphen); the data itself is unchanged.
export const displayName = (name: string) => name.replace(/T-Shirt/g, 'T‑Shirt')

export const formatPrice = (price: number) =>
  new Intl.NumberFormat('en-US', { style: 'currency', currency: 'USD' }).format(price)
