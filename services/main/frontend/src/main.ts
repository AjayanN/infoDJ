import 'zone.js';

import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, Routes } from '@angular/router';

import { environment } from './environments/environment';

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => { open: () => void };
  }
}

type AuthView = 'login' | 'signup' | 'forgot' | 'reset';

type RazorpayCheckoutResponse = {
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_signature: string;
};

type RazorpayCheckoutOptions = {
  key: string;
  amount: number;
  currency: string;
  name: string;
  description: string;
  order_id: string;
  prefill: {
    name: string;
    email: string;
  };
  theme: {
    color: string;
  };
  handler: (response: RazorpayCheckoutResponse) => void;
  modal: {
    ondismiss: () => void;
  };
};

const routes: Routes = [
  { path: 'admin', loadChildren: () => import('./app/admin/routes').then((m) => m.ADMIN_ROUTES) },
  { path: 'companies', loadChildren: () => import('./app/companies/routes').then((m) => m.COMPANY_ROUTES) },
  { path: 'events', loadChildren: () => import('./app/events/routes').then((m) => m.EVENT_ROUTES) },
  { path: 'strategic-turns', loadChildren: () => import('./app/strategic-turns/routes').then((m) => m.STRATEGIC_TURN_ROUTES) }
];

type Subscription = {
  tier: string;
  status: string;
  razorpay_order_id: string;
  razorpay_payment_id: string;
  razorpay_subscription_id: string;
};

type UserProfile = {
  display_name: string;
  company_name: string;
  role: string;
  email_updates_enabled: boolean;
  product_updates_enabled: boolean;
  research_digest_enabled: boolean;
};

type CurrentUser = {
  id: number;
  username: string;
  email: string;
  profile: UserProfile;
  subscription: Subscription;
};

type HistoryRow = {
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

@Component({
  selector: 'infodj-root',
  standalone: true,
  imports: [CommonModule, FormsModule, HttpClientModule],
  template: `
    <ng-container *ngIf="!token(); else authenticatedApp">
      <main class="auth-page">
        <section class="auth-card">
          <div class="auth-brand">
            <p class="eyebrow">InfoDJ Admin</p>
            <h1>{{ authTitle() }}</h1>
            <p>Use an account to access the admin workspace, subscription controls, and company intelligence screens.</p>
          </div>

          <section class="status-strip compact" *ngIf="message() || error()">
            <div class="status-card ok" *ngIf="message()">{{ message() }}</div>
            <div class="status-card error" *ngIf="error()">{{ error() }}</div>
          </section>

          <div class="segmented auth-tabs" *ngIf="authView() !== 'reset'">
            <button type="button" [class.active]="authView() === 'login'" (click)="setAuthView('login')">Login</button>
            <button type="button" [class.active]="authView() === 'signup'" (click)="setAuthView('signup')">Signup</button>
          </div>

          <form class="form-grid" *ngIf="authView() === 'login'" (ngSubmit)="login()">
            <label>
              Username
              <input name="username" [(ngModel)]="username" autocomplete="username" required />
            </label>
            <label>
              Password
              <input name="password" [(ngModel)]="password" autocomplete="current-password" type="password" required />
            </label>
            <button type="submit" class="primary-button" [disabled]="loading()">Login</button>
            <button type="button" class="ghost-button full-width" (click)="startGoogleLogin()" [disabled]="loading()">Continue with Google</button>
            <button type="button" class="link-button" (click)="setAuthView('forgot')">Forgot password?</button>
          </form>

          <form class="form-grid" *ngIf="authView() === 'signup'" (ngSubmit)="signup()">
            <label>
              Username
              <input name="signup_username" [(ngModel)]="username" autocomplete="username" required />
            </label>
            <label>
              Email
              <input name="signup_email" [(ngModel)]="email" autocomplete="email" type="email" required />
            </label>
            <label>
              Password
              <input name="signup_password" [(ngModel)]="password" autocomplete="new-password" type="password" required />
            </label>
            <button type="submit" class="primary-button" [disabled]="loading()">Create account</button>
            <button type="button" class="ghost-button full-width" (click)="startGoogleLogin()" [disabled]="loading()">Continue with Google</button>
          </form>

          <form class="form-grid" *ngIf="authView() === 'forgot'" (ngSubmit)="requestPasswordReset()">
            <label>
              Account email
              <input name="reset_email" [(ngModel)]="email" autocomplete="email" type="email" required />
            </label>
            <button type="submit" class="primary-button" [disabled]="loading()">Send reset link</button>
            <button type="button" class="link-button" (click)="setAuthView('login')">Back to login</button>
          </form>

          <form class="form-grid" *ngIf="authView() === 'reset'" (ngSubmit)="confirmPasswordReset()">
            <label>
              New password
              <input name="new_password" [(ngModel)]="password" autocomplete="new-password" type="password" required />
            </label>
            <button type="submit" class="primary-button" [disabled]="loading()">Update password</button>
          </form>
        </section>
      </main>
    </ng-container>

    <ng-template #authenticatedApp>
      <div class="app-shell">
        <header class="topbar">
          <div>
            <p class="eyebrow">InfoDJ Admin</p>
            <h1>Account and Subscription</h1>
          </div>
          <nav class="top-actions" aria-label="Primary">
            <button type="button" class="ghost-button" (click)="loadHealth()">Check API</button>
            <button type="button" class="ghost-button" (click)="loadMe()">Refresh Account</button>
            <button type="button" class="danger-button" (click)="logout()">Logout</button>
          </nav>
        </header>

        <section class="status-strip" *ngIf="message() || error() || healthStatus()">
          <div class="status-card ok" *ngIf="healthStatus()">{{ healthStatus() }}</div>
          <div class="status-card ok" *ngIf="message()">{{ message() }}</div>
          <div class="status-card error" *ngIf="error()">{{ error() }}</div>
        </section>

        <main class="workspace authenticated-workspace">
          <section class="panel account-panel">
            <div class="panel-header">
              <div>
                <p class="section-kicker">Profile</p>
                <h2>Current account</h2>
              </div>
            </div>

            <div class="account-grid" *ngIf="currentUser() as user">
              <div class="metric">
                <span>User</span>
                <strong>{{ user.username }}</strong>
              </div>
              <div class="metric">
                <span>Email</span>
                <strong>{{ user.email }}</strong>
              </div>
              <div class="metric">
                <span>Tier</span>
                <strong>{{ user.subscription.tier }}</strong>
              </div>
              <div class="metric">
                <span>Status</span>
                <strong>{{ user.subscription.status }}</strong>
              </div>
            </div>
          </section>

          <section class="panel subscription-panel">
            <div class="panel-header">
              <div>
                <p class="section-kicker">Subscription</p>
                <h2>Plan controls</h2>
              </div>
            </div>

            <div class="tier-grid">
              <article class="tier-card" *ngFor="let tier of tiers">
                <div>
                  <h3>{{ tier.name }}</h3>
                  <p>{{ tier.description }}</p>
                </div>
                <div class="tier-price">{{ tier.price }}</div>
                <button
                  type="button"
                  class="primary-button"
                  [disabled]="loading()"
                  (click)="tier.paid ? checkout(tier.id) : changeTier(tier.id)"
                >
                  {{ tier.paid ? 'Start checkout' : 'Use free tier' }}
                </button>
              </article>
            </div>

            <div class="checkout-box" *ngIf="checkoutOrder() as order">
              <h3>Razorpay checkout order</h3>
              <dl>
                <div><dt>Order ID</dt><dd>{{ order.order_id }}</dd></div>
                <div><dt>Amount</dt><dd>{{ order.amount / 100 | number:'1.0-0' }} {{ order.currency }}</dd></div>
                <div><dt>Key ID</dt><dd>{{ order.key_id }}</dd></div>
              </dl>
              <div class="checkout-actions">
                <button type="button" class="primary-button" (click)="openRazorpayCheckout(order)" [disabled]="loading()">
                  Pay with Razorpay
                </button>
                <button type="button" class="ghost-button" (click)="checkoutOrder.set(null)">Dismiss</button>
              </div>
              <p>Continue to Razorpay to complete payment and verify it server-side.</p>
            </div>
          </section>

          <section class="panel history-panel">
            <div class="panel-header">
              <div>
                <p class="section-kicker">Audit</p>
                <h2>Subscription history</h2>
              </div>
              <button type="button" class="ghost-button" (click)="loadHistory()">Reload</button>
            </div>

            <div class="empty-state" *ngIf="history().length === 0">
              No subscription changes loaded.
            </div>

            <table *ngIf="history().length > 0">
              <thead>
                <tr>
                  <th>When</th>
                  <th>Provider</th>
                  <th>Tier</th>
                  <th>Status</th>
                  <th>Reason</th>
                </tr>
              </thead>
              <tbody>
                <tr *ngFor="let row of history()">
                  <td>{{ row.created_at | date:'medium' }}</td>
                  <td>{{ row.provider }}</td>
                  <td>{{ row.old_tier }} -> {{ row.new_tier }}</td>
                  <td>{{ row.old_status }} -> {{ row.new_status }}</td>
                  <td>{{ row.reason }}</td>
                </tr>
              </tbody>
            </table>
          </section>
        </main>

        <footer class="footer">
          <span>InfoDJ Sprint 1</span>
          <span>Main backend APIs only. Razorpay and Google secrets stay server-side.</span>
        </footer>
      </div>
    </ng-template>
  `
})
class AppComponent {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  authView = signal<AuthView>('login');
  token = signal(localStorage.getItem('infodj_token') || '');
  currentUser = signal<CurrentUser | null>(null);
  history = signal<HistoryRow[]>([]);
  checkoutOrder = signal<{ key_id: string; order_id: string; amount: number; currency: string } | null>(null);
  healthStatus = signal('');
  message = signal('');
  error = signal('');
  loading = signal(false);

  username = '';
  email = '';
  password = '';
  resetUid = '';
  resetToken = '';

  tiers = [
    { id: 'FREE', name: 'Free', price: '0 INR', paid: false, description: 'Inspect limited company history and account setup.' },
    { id: 'PRO', name: 'Pro', price: '999 INR', paid: true, description: 'For active operators reviewing strategic turns.' },
    { id: 'ANALYST', name: 'Analyst', price: '2499 INR', paid: true, description: 'For deeper research workflows and broader access.' }
  ];

  constructor() {
    this.consumeAuthCallback();
    this.consumePasswordResetLink();
    if (this.token()) {
      this.loadMe();
      this.loadHistory();
    }
  }

  authTitle(): string {
    if (this.authView() === 'signup') {
      return 'Create an account';
    }
    if (this.authView() === 'forgot') {
      return 'Reset your password';
    }
    if (this.authView() === 'reset') {
      return 'Choose a new password';
    }
    return 'Login to continue';
  }

  setAuthView(view: AuthView): void {
    this.authView.set(view);
    this.message.set('');
    this.error.set('');
  }

  signup(): void {
    this.withRequest(() =>
      this.http.post<{ token: string; user: CurrentUser }>(`${this.apiBaseUrl}/auth/signup`, {
        username: this.username,
        email: this.email,
        password: this.password
      }).subscribe({
        next: (response) => this.acceptSession(response.token, response.user, 'Account created.'),
        error: (response) => this.showError(response)
      })
    );
  }

  login(): void {
    this.withRequest(() =>
      this.http.post<{ token: string; user: CurrentUser }>(`${this.apiBaseUrl}/auth/login`, {
        username: this.username,
        password: this.password
      }).subscribe({
        next: (response) => this.acceptSession(response.token, response.user, 'Logged in.'),
        error: (response) => this.showError(response)
      })
    );
  }

  startGoogleLogin(): void {
    this.withRequest(() =>
      this.http.get<{ auth_url: string }>(`${this.apiBaseUrl}/auth/google/url`).subscribe({
        next: (response) => {
          window.location.href = response.auth_url;
        },
        error: (response) => this.showError(response)
      })
    );
  }

  requestPasswordReset(): void {
    this.withRequest(() =>
      this.http.post<{ status: string }>(`${this.apiBaseUrl}/auth/password-reset/request`, {
        email: this.email
      }).subscribe({
        next: () => {
          this.message.set('If the email exists, a reset link has been sent.');
          this.error.set('');
        },
        error: (response) => this.showError(response)
      })
    );
  }

  confirmPasswordReset(): void {
    this.withRequest(() =>
      this.http.post<{ status: string }>(`${this.apiBaseUrl}/auth/password-reset/confirm`, {
        uid: this.resetUid,
        token: this.resetToken,
        password: this.password
      }).subscribe({
        next: () => {
          this.password = '';
          this.authView.set('login');
          this.message.set('Password updated. Login with the new password.');
          window.history.replaceState({}, document.title, '/');
        },
        error: (response) => this.showError(response)
      })
    );
  }

  logout(): void {
    this.http.post(`${this.apiBaseUrl}/auth/logout`, {}, { headers: this.authHeaders() }).subscribe({
      next: () => this.clearSession('Logged out.'),
      error: () => this.clearSession('Logged out.')
    });
  }

  loadHealth(): void {
    this.http.get<{ service: string; status: string }>(`${this.apiBaseUrl}/health`).subscribe({
      next: (response) => {
        this.healthStatus.set(`${response.service}: ${response.status}`);
        this.error.set('');
      },
      error: (response) => this.showError(response)
    });
  }

  loadMe(): void {
    this.http.get<{ user: CurrentUser }>(`${this.apiBaseUrl}/auth/me`, { headers: this.authHeaders() }).subscribe({
      next: (response) => {
        this.currentUser.set(response.user);
        this.error.set('');
      },
      error: () => this.clearSession('Session expired. Login again.')
    });
  }

  loadHistory(): void {
    this.http.get<{ history: HistoryRow[] }>(`${this.apiBaseUrl}/subscription/history`, { headers: this.authHeaders() }).subscribe({
      next: (response) => this.history.set(response.history),
      error: (response) => this.showError(response)
    });
  }

  changeTier(tier: string): void {
    this.withRequest(() =>
      this.http.post<{ subscription: Subscription }>(
        `${this.apiBaseUrl}/subscription/change`,
        { tier, reason: 'frontend_plan_change' },
        { headers: this.authHeaders() }
      ).subscribe({
        next: (response) => {
          this.patchSubscription(response.subscription);
          this.message.set(`Subscription changed to ${response.subscription.tier}.`);
          this.loadHistory();
        },
        error: (response) => this.showError(response)
      })
    );
  }

  checkout(tier: string): void {
    this.withRequest(() =>
      this.http.post<{ razorpay: { key_id: string; order_id: string; amount: number; currency: string }; subscription: Subscription }>(
        `${this.apiBaseUrl}/subscription/checkout`,
        { tier },
        { headers: this.authHeaders() }
      ).subscribe({
        next: (response) => {
          this.checkoutOrder.set(response.razorpay);
          this.patchSubscription(response.subscription);
          this.message.set('Razorpay order created.');
          this.loadHistory();
          this.openRazorpayCheckout(response.razorpay);
        },
        error: (response) => this.showError(response)
      })
    );
  }

  openRazorpayCheckout(order: { key_id: string; order_id: string; amount: number; currency: string }): void {
    const user = this.currentUser();
    if (!user) {
      this.error.set('Login is required before checkout.');
      return;
    }
    this.withRequest(() => {
      this.loadRazorpayScript()
        .then(() => {
          if (!window.Razorpay) {
            throw new Error('Razorpay Checkout did not load.');
          }
          const checkout = new window.Razorpay({
            key: order.key_id,
            amount: order.amount,
            currency: order.currency,
            name: 'InfoDJ',
            description: `${user.subscription.tier} subscription`,
            order_id: order.order_id,
            prefill: {
              name: user.username,
              email: user.email
            },
            theme: {
              color: '#0b6bcb'
            },
            handler: (response) => this.verifyPayment(response),
            modal: {
              ondismiss: () => {
                this.loading.set(false);
                this.message.set('Checkout closed before payment completion.');
              }
            }
          });
          this.loading.set(false);
          checkout.open();
        })
        .catch((error: Error) => {
          this.loading.set(false);
          this.error.set(error.message || 'Unable to load Razorpay Checkout.');
        });
    });
  }

  verifyPayment(payment: RazorpayCheckoutResponse): void {
    this.withRequest(() =>
      this.http.post<{ subscription: Subscription }>(
        `${this.apiBaseUrl}/subscription/verify-payment`,
        payment,
        { headers: this.authHeaders() }
      ).subscribe({
        next: (response) => {
          this.patchSubscription(response.subscription);
          this.checkoutOrder.set(null);
          this.message.set('Payment verified. Subscription is active.');
          this.loadHistory();
        },
        error: (response) => this.showError(response)
      })
    );
  }

  private consumeAuthCallback(): void {
    const url = new URL(window.location.href);
    const token = url.searchParams.get('token');
    if (window.location.pathname === '/auth/callback' && token) {
      localStorage.setItem('infodj_token', token);
      this.token.set(token);
      window.history.replaceState({}, document.title, '/');
      this.message.set('Google login confirmed.');
    }
  }

  private consumePasswordResetLink(): void {
    const url = new URL(window.location.href);
    const uid = url.searchParams.get('uid') || '';
    const token = url.searchParams.get('token') || '';
    if (window.location.pathname === '/reset-password' && uid && token) {
      this.resetUid = uid;
      this.resetToken = token;
      this.authView.set('reset');
    }
  }

  private acceptSession(token: string, user: CurrentUser, message: string): void {
    localStorage.setItem('infodj_token', token);
    this.token.set(token);
    this.currentUser.set(user);
    this.message.set(message);
    this.error.set('');
    this.password = '';
    this.loadHistory();
  }

  private clearSession(message: string): void {
    localStorage.removeItem('infodj_token');
    this.token.set('');
    this.currentUser.set(null);
    this.history.set([]);
    this.checkoutOrder.set(null);
    this.authView.set('login');
    this.message.set(message);
  }

  private patchSubscription(subscription: Subscription): void {
    const user = this.currentUser();
    if (user) {
      this.currentUser.set({ ...user, subscription });
    }
  }

  private authHeaders(): HttpHeaders {
    return new HttpHeaders({ Authorization: `Token ${this.token()}` });
  }

  private withRequest(start: () => void): void {
    this.loading.set(true);
    this.message.set('');
    this.error.set('');
    start();
    setTimeout(() => this.loading.set(false), 400);
  }

  private showError(response: { error?: { error?: string; detail?: string }; message?: string }): void {
    this.loading.set(false);
    this.message.set('');
    this.error.set(response.error?.error || response.error?.detail || response.message || 'Request failed.');
  }

  private loadRazorpayScript(): Promise<void> {
    if (window.Razorpay) {
      return Promise.resolve();
    }
    const existing = document.querySelector<HTMLScriptElement>('script[data-razorpay-checkout]');
    if (existing) {
      return new Promise((resolve, reject) => {
        existing.addEventListener('load', () => resolve(), { once: true });
        existing.addEventListener('error', () => reject(new Error('Unable to load Razorpay Checkout.')), { once: true });
      });
    }
    return new Promise((resolve, reject) => {
      const script = document.createElement('script');
      script.src = 'https://checkout.razorpay.com/v1/checkout.js';
      script.async = true;
      script.dataset['razorpayCheckout'] = 'true';
      script.onload = () => resolve();
      script.onerror = () => reject(new Error('Unable to load Razorpay Checkout.'));
      document.body.appendChild(script);
    });
  }
}

bootstrapApplication(AppComponent, {
  providers: [provideRouter(routes)]
}).catch((error) => console.error(error));
