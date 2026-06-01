import 'zone.js';

import { CommonModule } from '@angular/common';
import { HttpClient, HttpClientModule, HttpHeaders } from '@angular/common/http';
import { Component, computed, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, Routes } from '@angular/router';

import { environment } from './environments/environment';

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
    <div class="app-shell">
      <header class="topbar">
        <div>
          <p class="eyebrow">InfoDJ Admin</p>
          <h1>Account and Subscription</h1>
        </div>
        <nav class="top-actions" aria-label="Primary">
          <button type="button" class="ghost-button" (click)="loadHealth()">Check API</button>
          <button type="button" class="ghost-button" (click)="loadMe()" [disabled]="!token()">Refresh Account</button>
          <button type="button" class="danger-button" (click)="logout()" [disabled]="!token()">Logout</button>
        </nav>
      </header>

      <section class="status-strip" *ngIf="message() || error() || healthStatus()">
        <div class="status-card ok" *ngIf="healthStatus()">{{ healthStatus() }}</div>
        <div class="status-card ok" *ngIf="message()">{{ message() }}</div>
        <div class="status-card error" *ngIf="error()">{{ error() }}</div>
      </section>

      <main class="workspace">
        <section class="panel auth-panel">
          <div class="panel-header">
            <div>
              <p class="section-kicker">Access</p>
              <h2>{{ authMode() === 'login' ? 'Login' : 'Create account' }}</h2>
            </div>
            <div class="segmented">
              <button type="button" [class.active]="authMode() === 'login'" (click)="authMode.set('login')">Login</button>
              <button type="button" [class.active]="authMode() === 'signup'" (click)="authMode.set('signup')">Signup</button>
            </div>
          </div>

          <form class="form-grid" (ngSubmit)="authMode() === 'login' ? login() : signup()">
            <label>
              Username
              <input name="username" [(ngModel)]="username" autocomplete="username" required />
            </label>
            <label *ngIf="authMode() === 'signup'">
              Email
              <input name="email" [(ngModel)]="email" autocomplete="email" type="email" required />
            </label>
            <label>
              Password
              <input name="password" [(ngModel)]="password" autocomplete="current-password" type="password" required />
            </label>
            <button type="submit" class="primary-button" [disabled]="loading()">
              {{ authMode() === 'login' ? 'Login' : 'Create account' }}
            </button>
          </form>
        </section>

        <section class="panel account-panel">
          <div class="panel-header">
            <div>
              <p class="section-kicker">Profile</p>
              <h2>Current account</h2>
            </div>
          </div>

          <div class="empty-state" *ngIf="!currentUser()">
            Login or create an account to inspect subscription state and payment actions.
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
                [disabled]="!token() || loading()"
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
            <p>
              The backend created this order. The next frontend step will mount Razorpay Checkout and submit
              payment details back to the verification endpoint.
            </p>
          </div>
        </section>

        <section class="panel history-panel">
          <div class="panel-header">
            <div>
              <p class="section-kicker">Audit</p>
              <h2>Subscription history</h2>
            </div>
            <button type="button" class="ghost-button" (click)="loadHistory()" [disabled]="!token()">Reload</button>
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
        <span>Main backend APIs only. Razorpay secrets stay server-side.</span>
      </footer>
    </div>
  `
})
class AppComponent {
  private readonly http = inject(HttpClient);
  private readonly apiBaseUrl = environment.apiBaseUrl;

  authMode = signal<'login' | 'signup'>('signup');
  token = signal(localStorage.getItem('infodj_token') || '');
  currentUser = signal<CurrentUser | null>(null);
  history = signal<HistoryRow[]>([]);
  checkoutOrder = signal<{ key_id: string; order_id: string; amount: number; currency: string } | null>(null);
  healthStatus = signal('');
  message = signal('');
  error = signal('');
  loading = signal(false);
  isAuthenticated = computed(() => Boolean(this.token()));

  username = '';
  email = '';
  password = '';

  tiers = [
    { id: 'FREE', name: 'Free', price: '0 INR', paid: false, description: 'Inspect limited company history and account setup.' },
    { id: 'PRO', name: 'Pro', price: '999 INR', paid: true, description: 'For active operators reviewing strategic turns.' },
    { id: 'ANALYST', name: 'Analyst', price: '2499 INR', paid: true, description: 'For deeper research workflows and broader access.' }
  ];

  constructor() {
    if (this.token()) {
      this.loadMe();
      this.loadHistory();
    }
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

  logout(): void {
    if (!this.token()) {
      return;
    }
    this.http.post(`${this.apiBaseUrl}/auth/logout`, {}, { headers: this.authHeaders() }).subscribe({
      next: () => {
        localStorage.removeItem('infodj_token');
        this.token.set('');
        this.currentUser.set(null);
        this.history.set([]);
        this.checkoutOrder.set(null);
        this.message.set('Logged out.');
      },
      error: () => {
        localStorage.removeItem('infodj_token');
        this.token.set('');
        this.currentUser.set(null);
      }
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
      error: (response) => this.showError(response)
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
        },
        error: (response) => this.showError(response)
      })
    );
  }

  private acceptSession(token: string, user: CurrentUser, message: string): void {
    localStorage.setItem('infodj_token', token);
    this.token.set(token);
    this.currentUser.set(user);
    this.message.set(message);
    this.error.set('');
    this.loadHistory();
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
}

bootstrapApplication(AppComponent, {
  providers: [provideRouter(routes)]
}).catch((error) => console.error(error));
