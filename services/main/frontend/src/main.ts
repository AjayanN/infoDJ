import 'zone.js';

import { CommonModule } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, Routes } from '@angular/router';

import {
  CurrentUser,
  HistoryRow,
  InfoDjApiService,
  RazorpayCheckoutResponse,
  RazorpayOrder,
  Subscription
} from './app/services/infodj-api.service';

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => { open: () => void };
  }
}

type AuthView = 'login' | 'signup' | 'forgot' | 'reset';
type AppPage = 'dashboard' | 'profile' | 'subscription';

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

@Component({
  selector: 'infodj-root',
  standalone: true,
  imports: [CommonModule, FormsModule],
  templateUrl: './app.component.html'
})
class AppComponent {
  private readonly api = inject(InfoDjApiService);

  authView = signal<AuthView>('login');
  activePage = signal<AppPage>('dashboard');
  menuOpen = signal(false);
  token = signal(localStorage.getItem('infodj_token') || '');
  currentUser = signal<CurrentUser | null>(null);
  history = signal<HistoryRow[]>([]);
  checkoutOrder = signal<RazorpayOrder | null>(null);
  healthStatus = signal('');
  message = signal('');
  error = signal('');
  loading = signal(false);

  username = '';
  email = '';
  password = '';
  resetUid = '';
  resetToken = '';
  avatarPreview = '';
  avatarFilename = '';

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

  setActivePage(page: AppPage): void {
    this.activePage.set(page);
    this.menuOpen.set(false);
    this.message.set('');
    this.error.set('');
    if (page === 'subscription') {
      this.loadHistory();
    }
  }

  toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  pageTitle(): string {
    if (this.activePage() === 'profile') {
      return 'Profile';
    }
    if (this.activePage() === 'subscription') {
      return 'Subscription';
    }
    return 'Dashboard';
  }

  pageDescription(): string {
    if (this.activePage() === 'profile') {
      return 'Manage account details, avatar preview, and subscription access.';
    }
    if (this.activePage() === 'subscription') {
      return 'Review available tiers, start Razorpay checkout, and audit plan changes.';
    }
    return 'A quick operating view for company intelligence, search, and strategic turn analysis.';
  }

  signup(): void {
    this.withRequest(() =>
      this.api.signup(this.username, this.email, this.password).subscribe({
        next: (response) => this.acceptSession(response.token, response.user, 'Account created.'),
        error: (response) => this.showError(response)
      })
    );
  }

  login(): void {
    this.withRequest(() =>
      this.api.login(this.username, this.password).subscribe({
        next: (response) => this.acceptSession(response.token, response.user, 'Logged in.'),
        error: (response) => this.showError(response)
      })
    );
  }

  startGoogleLogin(): void {
    this.withRequest(() =>
      this.api.getGoogleAuthUrl().subscribe({
        next: (response) => {
          window.location.href = response.auth_url;
        },
        error: (response) => this.showError(response)
      })
    );
  }

  requestPasswordReset(): void {
    this.withRequest(() =>
      this.api.requestPasswordReset(this.email).subscribe({
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
      this.api.confirmPasswordReset(this.resetUid, this.resetToken, this.password).subscribe({
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
    this.api.logout(this.token()).subscribe({
      next: () => this.clearSession('Logged out.'),
      error: () => this.clearSession('Logged out.')
    });
  }

  chooseAvatar(event: Event): void {
    const input = event.target as HTMLInputElement;
    const file = input.files?.[0];
    if (!file) {
      return;
    }
    if (!file.type.startsWith('image/')) {
      this.error.set('Choose an image file for the avatar.');
      return;
    }
    this.avatarFilename = file.name;
    this.error.set('');
    const reader = new FileReader();
    reader.onload = () => {
      this.avatarPreview = typeof reader.result === 'string' ? reader.result : '';
      this.uploadAvatar(file);
    };
    reader.onerror = () => this.error.set('Unable to preview the selected avatar.');
    reader.readAsDataURL(file);
  }

  avatarSrc(user: CurrentUser): string {
    return this.avatarPreview || user.profile.avatar_url || '';
  }

  deleteAvatar(): void {
    this.withRequest(() =>
      this.api.deleteAvatar(this.token()).subscribe({
        next: (response) => {
          this.currentUser.set(response.user);
          this.avatarPreview = '';
          this.avatarFilename = '';
          this.message.set('Avatar deleted.');
        },
        error: (response) => this.showError(response)
      })
    );
  }

  loadHealth(): void {
    this.api.health().subscribe({
      next: (response) => {
        this.healthStatus.set(`${response.service}: ${response.status}`);
        this.error.set('');
      },
      error: (response) => this.showError(response)
    });
  }

  loadMe(): void {
    this.api.me(this.token()).subscribe({
      next: (response) => {
        this.currentUser.set(response.user);
        this.error.set('');
      },
      error: () => this.clearSession('Session expired. Login again.')
    });
  }

  loadHistory(): void {
    this.api.subscriptionHistory(this.token()).subscribe({
      next: (response) => this.history.set(response.history),
      error: (response) => this.showError(response)
    });
  }

  changeTier(tier: string): void {
    this.withRequest(() =>
      this.api.changeTier(this.token(), tier, 'frontend_plan_change').subscribe({
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
      this.api.checkout(this.token(), tier).subscribe({
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

  openRazorpayCheckout(order: RazorpayOrder): void {
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
            description: `${user.subscription.pending_tier || user.subscription.tier} subscription`,
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
      this.api.verifyPayment(this.token(), payment).subscribe({
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
    this.activePage.set('dashboard');
    this.menuOpen.set(false);
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
    this.activePage.set('dashboard');
    this.menuOpen.set(false);
    this.avatarPreview = '';
    this.avatarFilename = '';
    this.message.set(message);
  }

  private patchSubscription(subscription: Subscription): void {
    const user = this.currentUser();
    if (user) {
      this.currentUser.set({ ...user, subscription });
    }
  }

  private uploadAvatar(file: File): void {
    this.withRequest(() =>
      this.api.uploadAvatar(this.token(), file).subscribe({
        next: (response) => {
          this.currentUser.set(response.user);
          this.avatarPreview = '';
          this.avatarFilename = file.name;
          this.message.set('Avatar saved.');
        },
        error: (response) => this.showError(response)
      })
    );
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
  providers: [provideHttpClient(), provideRouter(routes)]
}).catch((error) => console.error(error));
