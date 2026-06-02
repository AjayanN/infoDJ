import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { environment } from '../../environments/environment';

export type Subscription = {
  tier: string;
  status: string;
  pending_tier: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_subscription_id: string;
};

export type UserProfile = {
  display_name: string;
  company_name: string;
  role: string;
  avatar_url: string;
  email_updates_enabled: boolean;
  product_updates_enabled: boolean;
  research_digest_enabled: boolean;
};

export type CurrentUser = {
  id: number;
  username: string;
  email: string;
  profile: UserProfile;
  subscription: Subscription;
};

export type HistoryRow = {
  id: number;
  old_tier: string;
  new_tier: string;
  old_status: string;
  new_status: string;
  reason: string;
  provider: string;
  provider_order_id: string;
  provider_payment_id: string;
  created_at: string;
};

export type AuthResponse = {
  token: string;
  user: CurrentUser;
};

export type HealthResponse = {
  service: string;
  status: string;
};

export type RazorpayOrder = {
  key_id: string;
  order_id: string;
  amount: number;
  currency: string;
};

export type RazorpayCheckoutResponse = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

export type SubscriptionCheckoutResponse = {
  razorpay: RazorpayOrder;
  subscription: Subscription;
};

export type DashboardCompany = {
  id?: number;
  name: string;
  slug: string;
  sector: string;
  country?: string;
  source_count: number;
  event_count: number;
  strategic_turn_count: number;
};

export type SectorCount = {
  sector: string;
  company_count: number;
  source_count: number;
  event_count: number;
  strategic_turn_count: number;
};

export type IngestionJobSummary = {
  id: number;
  company: string | null;
  company_slug: string | null;
  job_type: string;
  source: string;
  status: string;
  sources_found: number;
  sources_inserted: number;
  duplicates_skipped: number;
  articles_extracted: number;
  events_extracted: number;
  turns_created: number;
  error_message: string;
  created_at: string;
  started_at: string | null;
  finished_at: string | null;
};

export type DashboardResponse = {
  summary: {
    company_count: number;
    source_count: number;
    event_count: number;
    strategic_turn_count: number;
    sector_count: number;
  };
  sector_counts: SectorCount[];
  top_companies: DashboardCompany[];
  latest_jobs: IngestionJobSummary[];
  ingestion: {
    available: boolean;
    companies_error: string;
    jobs_error: string;
  };
};

export type SearchEventResult = {
  id: number;
  company: string;
  company_slug: string;
  event_date: string | null;
  event_type: string;
  decision_theme: string;
  actual_change: string;
  source_claim: string;
  first_filing: string | null;
  latest_filing: string | null;
  source_count: number;
  review_status: string;
};

export type SearchTurnResult = {
  id: number;
  title: string;
  turn_type: string;
  start_date: string | null;
  end_date: string | null;
  summary: string;
  decision: string;
  outcome: string;
  review_status: string;
  is_published: boolean;
  source_count: number;
};

export type SearchResponse = {
  query: string;
  language: string;
  results: {
    companies: DashboardCompany[];
    events: SearchEventResult[];
    strategic_turns: SearchTurnResult[];
  };
};

export type SearchSuggestion = {
  type: string;
  label: string;
  slug: string;
  sector: string;
  description: string;
};

@Injectable({ providedIn: 'root' })
export class InfoDjApiService {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  signup(username: string, email: string, password: string) {
    return this.http.post<AuthResponse>(`${this.apiBaseUrl}/auth/signup`, {
      username,
      email,
      password
    });
  }

  login(username: string, password: string) {
    return this.http.post<AuthResponse>(`${this.apiBaseUrl}/auth/login`, {
      username,
      password
    });
  }

  getGoogleAuthUrl() {
    return this.http.get<{ auth_url: string }>(`${this.apiBaseUrl}/auth/google/url`);
  }

  requestPasswordReset(email: string) {
    return this.http.post<{ status: string }>(`${this.apiBaseUrl}/auth/password-reset/request`, { email });
  }

  confirmPasswordReset(uid: string, token: string, password: string) {
    return this.http.post<{ status: string }>(`${this.apiBaseUrl}/auth/password-reset/confirm`, {
      uid,
      token,
      password
    });
  }

  logout(token: string) {
    return this.http.post(`${this.apiBaseUrl}/auth/logout`, {}, { headers: this.authHeaders(token) });
  }

  health() {
    return this.http.get<HealthResponse>(`${this.apiBaseUrl}/health`);
  }

  me(token: string) {
    return this.http.get<{ user: CurrentUser }>(`${this.apiBaseUrl}/auth/me`, { headers: this.authHeaders(token) });
  }

  subscriptionHistory(token: string) {
    return this.http.get<{ history: HistoryRow[] }>(`${this.apiBaseUrl}/subscription/history`, {
      headers: this.authHeaders(token)
    });
  }

  changeTier(token: string, tier: string, reason: string) {
    return this.http.post<{ subscription: Subscription }>(
      `${this.apiBaseUrl}/subscription/change`,
      { tier, reason },
      { headers: this.authHeaders(token) }
    );
  }

  checkout(token: string, tier: string) {
    return this.http.post<SubscriptionCheckoutResponse>(
      `${this.apiBaseUrl}/subscription/checkout`,
      { tier },
      { headers: this.authHeaders(token) }
    );
  }

  verifyPayment(token: string, payment: RazorpayCheckoutResponse) {
    return this.http.post<{ subscription: Subscription }>(
      `${this.apiBaseUrl}/subscription/verify-payment`,
      payment,
      { headers: this.authHeaders(token) }
    );
  }

  uploadAvatar(token: string, avatar: File) {
    const body = new FormData();
    body.append('avatar', avatar);
    return this.http.post<{ user: CurrentUser }>(`${this.apiBaseUrl}/profile/avatar`, body, {
      headers: this.authHeaders(token)
    });
  }

  deleteAvatar(token: string) {
    return this.http.delete<{ user: CurrentUser }>(`${this.apiBaseUrl}/profile/avatar`, {
      headers: this.authHeaders(token)
    });
  }

  dashboard(token: string) {
    return this.http.get<DashboardResponse>(`${this.apiBaseUrl}/dashboard`, {
      headers: this.authHeaders(token)
    });
  }

  categories(token: string) {
    return this.http.get<{ categories: SectorCount[] }>(`${this.apiBaseUrl}/categories`, {
      headers: this.authHeaders(token)
    });
  }

  search(token: string, query: string) {
    return this.http.get<SearchResponse>(`${this.apiBaseUrl}/search`, {
      headers: this.authHeaders(token),
      params: { q: query, language: 'en' }
    });
  }

  suggest(token: string, query: string) {
    return this.http.get<{ suggestions: SearchSuggestion[] }>(`${this.apiBaseUrl}/search/suggest`, {
      headers: this.authHeaders(token),
      params: { q: query, language: 'en' }
    });
  }

  private authHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Token ${token}` });
  }
}
