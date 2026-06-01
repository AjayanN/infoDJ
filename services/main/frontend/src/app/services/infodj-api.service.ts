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

  private authHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Token ${token}` });
  }
}
