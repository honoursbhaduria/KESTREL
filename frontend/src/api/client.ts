/**
 * Typed API client wrapper with automatic JWT refresh token rotation.
 */

export interface User {
  id: string
  email: string
  full_name: string
  is_active: boolean
  created_at: string
}

export interface Organization {
  id: string
  name: string
  slug: string
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  user: User
  org: Organization
}

export interface Project {
  id: string
  org_id: string
  name: string
  description: string | null
  status: string
  ruleset_id?: string | null
  created_at: string
  updated_at: string
}

export interface RoadSide {
  edge_index: number
  road_width_mm: number
}

export interface Plot {
  id: string
  project_id: string
  boundary: [number, number][]
  original_geo_boundary?: [number, number][] | null
  north_angle_deg: number
  road_sides: RoadSide[]
  plot_area_mm2: number
  created_at: string
  updated_at: string
}

export interface RuleDefinition {
  id: string
  title: string
  clause: string
  category: string
  applies_to: string
  check: string
  params: Record<string, unknown>
  severity: 'fail' | 'review'
  verified: boolean
  notes: string
}

export interface Ruleset {
  id: string
  name: string
  jurisdiction: string
  version: string
  description: string
  rules: RuleDefinition[]
}

export interface RulesetSummary {
  id: string
  name: string
  jurisdiction: string
  version: string
  description: string
  rule_count: number
}

export interface AppliedRuleRecord {
  rule_id: string
  clause: string
  value: string | number
  verified: boolean
}

export interface Envelope {
  footprint_polygon: [number, number][]
  footprint_area_mm2: number
  max_coverage_mm2: number
  max_builtup_mm2: number
  max_height_mm: number
  max_floors: number
  applied_rules: AppliedRuleRecord[]
  warning?: string | null
}

export interface RuleSearchResult {
  document: string
  section: string
  title: string
  content: string
  score: number
}

export interface Job {
  id: string
  org_id: string
  type: string
  status: 'queued' | 'running' | 'done' | 'failed'
  progress: number
  result: Record<string, unknown> | null
  error: Record<string, unknown> | null
  idempotency_key: string | null
  created_at: string
  updated_at: string
}

const API_BASE_URL = import.meta.env.VITE_API_URL || 'http://localhost:8001'

class ApiClient {
  private accessToken: string | null = null
  private refreshToken: string | null = null
  private user: User | null = null
  private org: Organization | null = null
  private isRefreshing = false
  private refreshSubscribers: ((token: string) => void)[] = []

  constructor() {
    if (typeof window !== 'undefined') {
      this.accessToken = localStorage.getItem('haron_access_token')
      this.refreshToken = localStorage.getItem('haron_refresh_token')
      const storedUser = localStorage.getItem('haron_user')
      if (storedUser) {
        try {
          this.user = JSON.parse(storedUser)
        } catch {
          // ignore parsing error
        }
      }
      const storedOrg = localStorage.getItem('haron_org')
      if (storedOrg) {
        try {
          this.org = JSON.parse(storedOrg)
        } catch {
          // ignore parsing error
        }
      }
    }
  }

  public setAuth(data: AuthTokens): void {
    this.accessToken = data.access_token
    this.refreshToken = data.refresh_token
    this.user = data.user
    this.org = data.org

    if (typeof window !== 'undefined') {
      localStorage.setItem('haron_access_token', data.access_token)
      localStorage.setItem('haron_refresh_token', data.refresh_token)
      localStorage.setItem('haron_user', JSON.stringify(data.user))
      localStorage.setItem('haron_org', JSON.stringify(data.org))
    }
  }

  public clearAuth(): void {
    this.accessToken = null
    this.refreshToken = null
    this.user = null
    this.org = null

    if (typeof window !== 'undefined') {
      localStorage.removeItem('haron_access_token')
      localStorage.removeItem('haron_refresh_token')
      localStorage.removeItem('haron_user')
      localStorage.removeItem('haron_org')
    }
  }

  public isAuthenticated(): boolean {
    return Boolean(this.accessToken)
  }

  public getUser(): User | null {
    return this.user
  }

  public getOrg(): Organization | null {
    return this.org
  }

  private onTokenRefreshed(newToken: string): void {
    this.refreshSubscribers.forEach((cb) => cb(newToken))
    this.refreshSubscribers = []
  }

  private addRefreshSubscriber(cb: (token: string) => void): void {
    this.refreshSubscribers.push(cb)
  }

  public async request<T>(
    endpoint: string,
    options: RequestInit = {},
    isRetry = false
  ): Promise<T> {
    const url = endpoint.startsWith('http') ? endpoint : `${API_BASE_URL}${endpoint}`
    const headers = new Headers(options.headers || {})

    if (!headers.has('Content-Type') && !(options.body instanceof FormData)) {
      headers.set('Content-Type', 'application/json')
    }

    if (this.accessToken && !headers.has('Authorization')) {
      headers.set('Authorization', `Bearer ${this.accessToken}`)
    }

    const response = await fetch(url, { ...options, headers })

    if (response.status === 401 && !isRetry && this.refreshToken) {
      if (this.isRefreshing) {
        return new Promise<T>((resolve, reject) => {
          this.addRefreshSubscriber(async (newToken) => {
            headers.set('Authorization', `Bearer ${newToken}`)
            try {
              const retryRes = await fetch(url, { ...options, headers })
              if (!retryRes.ok) {
                const err = await retryRes.json().catch(() => ({ message: 'Request failed' }))
                return reject(err)
              }
              const data = await retryRes.json().catch(() => ({}))
              resolve(data as T)
            } catch (err) {
              reject(err)
            }
          })
        })
      }

      this.isRefreshing = true

      try {
        const refreshRes = await fetch(`${API_BASE_URL}/api/v1/auth/refresh`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        })

        if (!refreshRes.ok) {
          this.clearAuth()
          if (typeof window !== 'undefined') {
            window.location.href = '/login'
          }
          throw new Error('Session expired. Please log in again.')
        }

        const newAuth: AuthTokens = await refreshRes.json()
        this.setAuth(newAuth)
        this.onTokenRefreshed(newAuth.access_token)

        headers.set('Authorization', `Bearer ${newAuth.access_token}`)
        const retryRes = await fetch(url, { ...options, headers })
        if (!retryRes.ok) {
          const errData = await retryRes.json().catch(() => ({}))
          throw errData
        }
        return (await retryRes.json().catch(() => ({}))) as T
      } finally {
        this.isRefreshing = false
      }
    }

    if (!response.ok) {
      const errorJson = await response.json().catch(() => ({
        code: 'HTTP_ERROR',
        message: response.statusText,
      }))
      throw errorJson
    }

    if (response.status === 204) {
      return {} as T
    }

    return (await response.json()) as T
  }

  // Auth Methods
  public async register(payload: { email: string; password: string; full_name: string; org_name?: string }): Promise<AuthTokens> {
    const data = await this.request<AuthTokens>('/api/v1/auth/register', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    this.setAuth(data)
    return data
  }

  public async login(payload: { email: string; password: string }): Promise<AuthTokens> {
    const data = await this.request<AuthTokens>('/api/v1/auth/login', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
    this.setAuth(data)
    return data
  }

  public async logout(): Promise<void> {
    if (this.refreshToken) {
      try {
        await this.request('/api/v1/auth/logout', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: this.refreshToken }),
        })
      } catch {
        // ignore logout error
      }
    }
    this.clearAuth()
  }

  // Projects Methods
  public async listProjects(): Promise<{ items: Project[]; total: number }> {
    return this.request<{ items: Project[]; total: number }>('/api/v1/projects')
  }

  public async getProject(id: string): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${id}`)
  }

  public async createProject(payload: { name: string; description?: string }): Promise<Project> {
    return this.request<Project>('/api/v1/projects', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async deleteProject(id: string): Promise<void> {
    return this.request<void>(`/api/v1/projects/${id}`, {
      method: 'DELETE',
    })
  }

  // Phase 2: Plot, Rulesets & Envelope Methods
  public async setPlot(
    projectId: string,
    payload: {
      width_mm?: number
      depth_mm?: number
      boundary?: [number, number][]
      original_geo_boundary?: [number, number][]
      north_angle_deg?: number
      road_sides?: RoadSide[]
    }
  ): Promise<Plot> {
    return this.request<Plot>(`/api/v1/projects/${projectId}/plot`, {
      method: 'PUT',
      body: JSON.stringify(payload),
    })
  }

  public async getPlot(projectId: string): Promise<Plot> {
    return this.request<Plot>(`/api/v1/projects/${projectId}/plot`)
  }

  public async listRulesets(): Promise<RulesetSummary[]> {
    return this.request<RulesetSummary[]>('/api/v1/rulesets')
  }

  public async getRuleset(rulesetId: string): Promise<Ruleset> {
    return this.request<Ruleset>(`/api/v1/rulesets/${rulesetId}`)
  }

  public async setProjectRuleset(projectId: string, rulesetId: string): Promise<Project> {
    return this.request<Project>(`/api/v1/projects/${projectId}/ruleset`, {
      method: 'PUT',
      body: JSON.stringify({ ruleset_id: rulesetId }),
    })
  }

  public async getEnvelope(projectId: string): Promise<Envelope> {
    return this.request<Envelope>(`/api/v1/projects/${projectId}/envelope`)
  }

  public async searchRules(q: string, limit = 5): Promise<RuleSearchResult[]> {
    return this.request<RuleSearchResult[]>(`/api/v1/rules/search?q=${encodeURIComponent(q)}&limit=${limit}`)
  }

  // Jobs Methods
  public async createJob(payload: { type: string; idempotency_key?: string; params?: Record<string, unknown> }): Promise<Job> {
    return this.request<Job>('/api/v1/jobs', {
      method: 'POST',
      body: JSON.stringify(payload),
    })
  }

  public async getJob(id: string): Promise<Job> {
    return this.request<Job>(`/api/v1/jobs/${id}`)
  }
}

export const api = new ApiClient()
