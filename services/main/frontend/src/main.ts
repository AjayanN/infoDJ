import 'zone.js';

import { CommonModule } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { Component, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, Routes } from '@angular/router';

import {
  CurrentUser,
  CompanyProfileResponse,
  BusinessModelResponse,
  OperatingKpiResponse,
  ManagementPromiseResponse,
  StrategyMilestoneResponse,
  EarningsResponse,
  CapitalAllocationResponse,
  DashboardSection,
  DashboardResponse,
  HistoryRow,
  InfoDjApiService,
  PaginationMeta,
  RazorpayCheckoutResponse,
  RazorpayOrder,
  SearchResponse,
  SearchSuggestion,
  Subscription
} from './app/services/infodj-api.service';
import {
  businessModelComponentLabel,
  businessModelRelationshipLabel,
  companyProfileItemLabel,
  companyProfileSectionLabel,
  managementPromiseLabel
} from './app/company-profile.utils';

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => { open: () => void };
  }
}

type AuthView = 'login' | 'signup' | 'forgot' | 'reset';
type AppPage = 'dashboard' | 'company' | 'business-model' | 'operating-kpis' | 'management-promises' | 'strategy-milestones' | 'earnings' | 'capital-allocation' | 'profile' | 'subscription';
type DashboardViewId =
  | 'company-intelligence'
  | 'turn-impact'
  | 'patterns'
  | 'companies-like-mine'
  | 'risk-signals'
  | 'source-confidence'
  | 'latest-moves'
  | 'business-questions'
  | 'strategy-scorecard'
  | 'compare-turns';

type DashboardView = {
  id: DashboardViewId;
  name: string;
  shortName: string;
  status: DashboardAvailability;
  purpose: string;
  requiredData: string[];
  gapSource: string;
  nextAction: string;
};

type DashboardAvailability = 'available' | 'unavailable';
type SearchResultGroup = 'companies' | 'events' | 'strategic_turns';
type DashboardSectionKey =
  | 'latest_moves'
  | 'strategic_turns'
  | 'patterns'
  | 'risk_signals'
  | 'turn_impact'
  | 'scorecards'
  | 'compare'
  | 'company_situations';

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
  dashboardView = signal<DashboardViewId>('company-intelligence');
  dashboardCompanySlug = signal('');
  menuOpen = signal(false);
  token = signal(localStorage.getItem('infodj_token') || '');
  currentUser = signal<CurrentUser | null>(null);
  history = signal<HistoryRow[]>([]);
  dashboard = signal<DashboardResponse | null>(null);
  companyProfile = signal<CompanyProfileResponse | null>(null);
  businessModel = signal<BusinessModelResponse | null>(null);
  operatingKpis = signal<OperatingKpiResponse | null>(null);
  managementPromises = signal<ManagementPromiseResponse | null>(null);
  strategyMilestones = signal<StrategyMilestoneResponse | null>(null);
  earnings = signal<EarningsResponse | null>(null);
  capitalAllocation = signal<CapitalAllocationResponse | null>(null);
  searchResults = signal<SearchResponse | null>(null);
  searchPages = signal<Record<SearchResultGroup, number>>({
    companies: 1,
    events: 1,
    strategic_turns: 1
  });
  dashboardPages = signal<Record<DashboardSectionKey, number>>({
    latest_moves: 1,
    strategic_turns: 1,
    patterns: 1,
    risk_signals: 1,
    turn_impact: 1,
    scorecards: 1,
    compare: 1,
    company_situations: 1
  });
  suggestions = signal<SearchSuggestion[]>([]);
  checkoutOrder = signal<RazorpayOrder | null>(null);
  healthStatus = signal('');
  message = signal('');
  error = signal('');
  loading = signal(false);
  dashboardLoading = signal(false);
  searchLoading = signal(false);
  companyLoading = signal(false);
  businessModelLoading = signal(false);
  operatingKpiLoading = signal(false);
  managementPromiseLoading = signal(false);
  strategyMilestoneLoading = signal(false);
  earningsLoading = signal(false);
  capitalAllocationLoading = signal(false);
  companyProfileDate = '';
  businessModelDate = '';
  businessModelCompareDate = '';
  readonly businessModelComponentOrder = ['PAYER', 'USER', 'OFFERING', 'REVENUE', 'CHANNEL', 'GEOGRAPHY', 'PARTNER', 'COST', 'ASSET'];
  businessModelTypeFilter = '';
  operatingKpiMetric = '';
  operatingKpiSegment = '';
  operatingKpiGeography = '';
  operatingKpiStart = '';
  operatingKpiEnd = '';
  operatingKpiComparableOnly = false;
  managementPromiseStatus = '';
  managementPromiseType = '';
  managementPromiseDue = '';
  managementPromiseAsOf = '';
  managementPromiseSlug = '';
  strategyMilestoneStatus = '';
  strategyMilestoneType = '';
  strategyMilestoneOrigin = '';
  strategyMilestoneView = 'all';
  strategyMilestoneSlug = '';
  earningsPeriod = '';
  capitalAllocationPeriod = '';
  readonly companyProfileSectionOrder = [
    'summary',
    'business_model',
    'subsidiaries',
    'brands',
    'segments',
    'products',
    'customer_groups',
    'revenue_sources',
    'geographies',
    'leadership',
    'competitors',
    'strategic_priorities'
  ];

  username = '';
  email = '';
  password = '';
  resetUid = '';
  resetToken = '';
  searchQuery = '';
  avatarPreview = '';
  avatarFilename = '';

  tiers = [
    { id: 'FREE', name: 'Free', price: '0 INR', paid: false, description: 'Inspect limited company history and account setup.' },
    { id: 'PRO', name: 'Pro', price: '999 INR', paid: true, description: 'For active operators reviewing strategic turns.' },
    { id: 'ANALYST', name: 'Analyst', price: '2499 INR', paid: true, description: 'For deeper research workflows and broader access.' }
  ];

  dashboardViews: DashboardView[] = [
    {
      id: 'company-intelligence',
      name: 'Company Coverage Overview',
      shortName: 'Coverage',
      status: 'available',
      purpose: 'Company coverage, sector concentration, source refreshes, and evidence-backed search.',
      requiredData: ['Companies', 'Source documents', 'Business events', 'Strategic turns', 'Ingestion jobs'],
      gapSource: 'ingestion.companies',
      nextAction: 'Use the current dashboard feed and search while company-level timeline APIs are built.'
    },
    {
      id: 'turn-impact',
      name: 'Strategic Turn Impact',
      shortName: 'Impact',
      status: 'unavailable',
      purpose: 'Market reaction and financial movement after a dated strategic move.',
      requiredData: ['Event date', 'Ticker', 'Daily prices', 'Peer/index benchmarks', 'SEC companyfacts'],
      gapSource: 'market-prices + financial-facts',
      nextAction: 'Add market price and SEC companyfacts ingestion before showing impact windows.'
    },
    {
      id: 'patterns',
      name: 'Strategic Pattern',
      shortName: 'Patterns',
      status: 'available',
      purpose: 'Reusable strategic patterns with reviewed examples and confidence.',
      requiredData: ['Reviewed turn types', 'Pattern labels', 'Outcome notes', 'Impact metrics'],
      gapSource: 'pattern-taxonomy',
      nextAction: 'Create reviewed pattern taxonomy and connect turns to patterns.'
    },
    {
      id: 'companies-like-mine',
      name: 'Situation Benchmarks',
      shortName: 'Benchmarks',
      status: 'available',
      purpose: 'Benchmark a company situation against similar historical situations.',
      requiredData: ['Industry', 'Stage', 'Revenue range', 'Business model', 'Pressure trigger'],
      gapSource: 'benchmark-dimensions',
      nextAction: 'Add benchmark filter metadata and similarity reason fields.'
    },
    {
      id: 'risk-signals',
      name: 'Risk Signals',
      shortName: 'Risk',
      status: 'available',
      purpose: 'Evidence-backed warning signs and what companies did next.',
      requiredData: ['Financial facts', 'Market benchmarks', 'Leadership events', 'Layoffs/restructuring', 'Regulatory events'],
      gapSource: 'risk-signal-calculations',
      nextAction: 'Add source-backed risk calculations before rendering a heatmap.'
    },
    {
      id: 'source-confidence',
      name: 'Source Confidence',
      shortName: 'Confidence',
      status: 'available',
      purpose: 'Data trust, source gaps, extraction status, and review status.',
      requiredData: ['Source types', 'Extraction confidence', 'Date confidence', 'Review status', 'Conflict notes'],
      gapSource: 'data-quality',
      nextAction: 'Add data-quality APIs and persisted source gap records.'
    },
    {
      id: 'latest-moves',
      name: 'Event Scanner',
      shortName: 'Latest',
      status: 'available',
      purpose: 'Latest dated strategic moves from SEC, news metadata, and other source feeds.',
      requiredData: ['Daily GDELT/news metadata', 'SEC updates', 'Press releases', 'Category labels'],
      gapSource: 'events.latest',
      nextAction: 'Add latest events feed with category, sector, and date filters.'
    },
    {
      id: 'business-questions',
      name: 'Founder / Business Questions',
      shortName: 'Questions',
      status: 'available',
      purpose: 'Evidence-backed answers for founder, operator, investor, and student questions.',
      requiredData: ['Question templates', 'Indexed event facts', 'Pattern library', 'Cited examples'],
      gapSource: 'questions.answer',
      nextAction: 'Add question templates and answer API with event/source citations.'
    },
    {
      id: 'strategy-scorecard',
      name: 'Strategy Scorecard',
      shortName: 'Scorecard',
      status: 'available',
      purpose: 'Evidence-backed score dimensions for each strategic turn.',
      requiredData: ['Impact windows', 'Financial facts', 'Benchmarks', 'Reviewed outcomes', 'Confidence reasons'],
      gapSource: 'turns.scorecard',
      nextAction: 'Add scorecard model and evidence-backed score rebuild API.'
    },
    {
      id: 'compare-turns',
      name: 'Compare Strategic Turns',
      shortName: 'Compare',
      status: 'available',
      purpose: 'Side-by-side comparison of strategic moves across timing, context, and results.',
      requiredData: ['Comparable turns', 'Company stage', 'Market condition', 'Pressure trigger', 'Impact charts'],
      gapSource: 'compare.strategic-turns',
      nextAction: 'Add compare-turns API and turn suggestion search.'
    }
  ];

  constructor() {
    this.consumeAuthCallback();
    this.consumePasswordResetLink();
    if (this.token()) {
      this.loadMe();
      this.loadHistory();
      this.loadDashboard();
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
    if (page === 'dashboard') {
      this.dashboardCompanySlug.set('');
      this.loadDashboard();
    }
  }

  toggleMenu(): void {
    this.menuOpen.update((open) => !open);
  }

  setDashboardView(view: DashboardViewId): void {
    this.dashboardView.set(view);
    if (this.dashboardCompanySlug() && !this.supportsCompanyDashboardScope(view)) {
      this.dashboardCompanySlug.set('');
    }
    const sectionKey = this.dashboardSectionKey(view);
    if (sectionKey && this.dashboard()) {
      this.loadDashboard(sectionKey, this.dashboardPages()[sectionKey]);
    }
  }

  activeDashboardView(): DashboardView {
    return this.dashboardViews.find((view) => view.id === this.dashboardView()) || this.dashboardViews[0];
  }

  supportsCompanyDashboardScope(view: DashboardViewId): boolean {
    return ['companies-like-mine', 'risk-signals', 'latest-moves', 'business-questions'].includes(view);
  }

  activeDashboardStatus(): DashboardAvailability {
    return this.dashboardStatus(this.activeDashboardView());
  }

  dashboardStatus(view: DashboardView): DashboardAvailability {
    const dash = this.dashboard();
    if (!dash) {
      return view.status;
    }
    if (view.id === 'company-intelligence') {
      return dash.ingestion.available && dash.summary.company_count > 0 ? 'available' : 'unavailable';
    }
    if (view.id === 'source-confidence') {
      return dash.dashboards.source_confidence.events.total > 0 || dash.dashboards.source_confidence.turns.total > 0
        ? 'available'
        : 'unavailable';
    }
    const section = this.dashboardSection(view.id);
    return section?.status || 'unavailable';
  }

  dashboardSection(viewId: DashboardViewId): DashboardSection<any> | null {
    const sections = this.dashboard()?.dashboards.sections;
    if (!sections) {
      return null;
    }
    const sectionKey = this.dashboardSectionKey(viewId);
    return sectionKey ? sections[sectionKey] || null : null;
  }

  dashboardSectionKey(viewId: DashboardViewId): DashboardSectionKey | null {
    const sectionMap: Record<DashboardViewId, DashboardSectionKey | null> = {
      'company-intelligence': null,
      'turn-impact': 'turn_impact',
      patterns: 'patterns',
      'companies-like-mine': 'company_situations',
      'risk-signals': 'risk_signals',
      'source-confidence': null,
      'latest-moves': 'latest_moves',
      'business-questions': 'latest_moves',
      'strategy-scorecard': 'scorecards',
      'compare-turns': 'compare'
    };
    return sectionMap[viewId];
  }

  sectionGaps(viewId: DashboardViewId = this.dashboardView()) {
    const dashboardKey = this.sourceGapDashboardKey(viewId);
    return this.dashboardSection(viewId)?.source_gaps || this.dashboard()?.source_gaps.filter((gap) => gap.dashboard === dashboardKey) || [];
  }

  dashboardGapAction(): string {
    return this.dashboardSection(this.dashboardView())?.next_action || this.activeDashboardView().nextAction;
  }

  dashboardSectionRange(viewId: DashboardViewId): string {
    const section = this.dashboardSection(viewId);
    if (!section || section.eligible_count === 0) {
      return '0 of 0';
    }
    const start = (section.page - 1) * section.page_size + 1;
    const end = Math.min(section.page * section.page_size, section.eligible_count);
    return `${start}-${end} of ${section.eligible_count}`;
  }

  searchRange(meta: PaginationMeta): string {
    if (!meta || meta.total === 0) {
      return '0 of 0';
    }
    const start = (meta.page - 1) * meta.page_size + 1;
    const end = Math.min(meta.page * meta.page_size, meta.total);
    return `${start}-${end} of ${meta.total}`;
  }

  sourceGapDashboardKey(viewId: DashboardViewId): string {
    const dashboardMap: Record<DashboardViewId, string> = {
      'company-intelligence': 'company_intelligence',
      'turn-impact': 'turn_impact',
      patterns: 'patterns',
      'companies-like-mine': 'company_situations',
      'risk-signals': 'risk_signals',
      'source-confidence': 'source_confidence',
      'latest-moves': 'latest_moves',
      'business-questions': 'business_questions',
      'strategy-scorecard': 'scorecards',
      'compare-turns': 'compare'
    };
    return dashboardMap[viewId];
  }

  pageTitle(): string {
    if (this.activePage() === 'company') {
      return this.companyProfile()?.company.name || 'Company 360';
    }
    if (this.activePage() === 'business-model') {
      return `${this.businessModel()?.company.name || 'Company'} Business Model`;
    }
    if (this.activePage() === 'operating-kpis') {
      return `${this.operatingKpis()?.company.name || 'Company'} Operating KPIs`;
    }
    if (this.activePage() === 'management-promises') {
      return `${this.managementPromises()?.company.name || 'Company'} Management Promises`;
    }
    if (this.activePage() === 'strategy-milestones') {
      return `${this.strategyMilestones()?.company.name || 'Company'} Strategy Milestones`;
    }
    if (this.activePage() === 'earnings') {
      return `${this.earnings()?.company.name || 'Company'} Earnings Intelligence`;
    }
    if (this.activePage() === 'capital-allocation') {
      return `${this.capitalAllocation()?.company.name || 'Company'} Capital Allocation`;
    }
    if (this.activePage() === 'profile') {
      return 'Profile';
    }
    if (this.activePage() === 'subscription') {
      return 'Subscription';
    }
    return 'Dashboard';
  }

  pageDescription(): string {
    if (this.activePage() === 'company') {
      return 'Source-backed company structure, strategic priorities, recent changes, and evidence coverage.';
    }
    if (this.activePage() === 'business-model') {
      return 'Who pays, who uses the offering, how it is delivered, where revenue comes from, and what changed over time.';
    }
    if (this.activePage() === 'operating-kpis') {
      return 'Company-specific operating drivers, definitions, trends, quality flags, alerts, and source evidence.';
    }
    if (this.activePage() === 'management-promises') {
      return 'Original management commitments, deadlines, evaluation rules, revisions, outcomes, and source evidence.';
    }
    if (this.activePage() === 'strategy-milestones') {
      return 'Expected execution steps, due dates, dependencies, blockers, status history, outcomes, and evidence.';
    }
    if (this.activePage() === 'earnings') {
      return 'Quarterly measured results, period changes, linked strategy, guidance, risks, and source gaps.';
    }
    if (this.activePage() === 'capital-allocation') {
      return 'Where management deployed capital across capex, R&D, buybacks, dividends, debt, acquisitions, and cash-flow context.';
    }
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

  loadDashboard(sectionKey: DashboardSectionKey | '' = '', page = 1): void {
    if (!this.token()) {
      return;
    }
    this.dashboardLoading.set(true);
    this.api.dashboard(this.token(), sectionKey, page, 12, this.dashboardCompanySlug()).subscribe({
      next: (response) => {
        this.dashboard.set(response);
        this.dashboardLoading.set(false);
        if (!response.ingestion.available) {
          this.error.set('Ingestion data is currently unavailable.');
        } else if (this.error() === 'Ingestion data is currently unavailable.') {
          this.error.set('');
        }
      },
      error: (response) => {
        this.dashboardLoading.set(false);
        this.showError(response);
      }
    });
  }

  setDashboardSectionPage(viewId: DashboardViewId, page: number): void {
    const sectionKey = this.dashboardSectionKey(viewId);
    if (!sectionKey || page < 1) {
      return;
    }
    this.dashboardPages.update((pages) => ({ ...pages, [sectionKey]: page }));
    this.loadDashboard(sectionKey, page);
  }

  updateSearchSuggestions(): void {
    const query = this.searchQuery.trim();
    if (query.length < 2) {
      this.suggestions.set([]);
      return;
    }
    this.api.suggest(this.token(), query).subscribe({
      next: (response) => this.suggestions.set(response.suggestions),
      error: () => this.suggestions.set([])
    });
  }

  runSearch(query = this.searchQuery): void {
    const normalized = query.trim();
    if (!normalized) {
      this.error.set('Enter a search query.');
      return;
    }
    this.searchQuery = normalized;
    this.searchLoading.set(true);
    this.suggestions.set([]);
    const pages = { companies: 1, events: 1, strategic_turns: 1 };
    this.searchPages.set(pages);
    this.api.search(this.token(), normalized, {
      company_page: pages.companies,
      event_page: pages.events,
      turn_page: pages.strategic_turns
    }).subscribe({
      next: (response) => {
        this.searchResults.set(response);
        this.searchLoading.set(false);
        this.error.set('');
      },
      error: (response) => {
        this.searchLoading.set(false);
        this.showError(response);
      }
    });
  }

  setSearchPage(group: SearchResultGroup, page: number): void {
    const normalized = this.searchQuery.trim();
    if (!normalized || page < 1) {
      return;
    }
    const pages = { ...this.searchPages(), [group]: page };
    this.searchPages.set(pages);
    this.searchLoading.set(true);
    this.api.search(this.token(), normalized, {
      company_page: pages.companies,
      event_page: pages.events,
      turn_page: pages.strategic_turns
    }).subscribe({
      next: (response) => {
        this.searchResults.set(response);
        this.searchLoading.set(false);
        this.error.set('');
      },
      error: (response) => {
        this.searchLoading.set(false);
        this.showError(response);
      }
    });
  }

  useSuggestion(suggestion: SearchSuggestion): void {
    if (suggestion.type === 'company' && suggestion.slug) {
      this.openCompany(suggestion.slug);
      return;
    }
    this.runSearch(suggestion.label);
  }

  openCompany(slug: string, asOf = ''): void {
    if (!slug || !this.token()) {
      return;
    }
    this.activePage.set('company');
    this.menuOpen.set(false);
    this.companyLoading.set(true);
    this.companyProfile.set(null);
    this.error.set('');
    this.api.companyProfile(this.token(), slug, asOf).subscribe({
      next: (response) => {
        this.companyProfile.set(response);
        this.companyProfileDate = response.profile?.effective_date || '';
        this.companyLoading.set(false);
      },
      error: (response) => {
        this.companyLoading.set(false);
        this.showError(response);
      }
    });
  }

  selectCompanyProfileDate(): void {
    const company = this.companyProfile()?.company;
    if (company && this.companyProfileDate) {
      this.openCompany(company.slug, this.companyProfileDate);
    }
  }

  openCompanyDashboard(view: DashboardViewId): void {
    const company = this.companyProfile()?.company;
    if (!company) {
      return;
    }
    this.dashboardView.set(view);
    this.dashboardCompanySlug.set(company.slug);
    this.dashboardPages.update((pages) => ({
      ...pages,
      latest_moves: 1,
      risk_signals: 1,
      company_situations: 1
    }));
    this.activePage.set('dashboard');
    this.menuOpen.set(false);
    this.message.set('');
    this.error.set('');
    const sectionKey = this.dashboardSectionKey(view);
    this.loadDashboard(sectionKey || '', 1);
  }

  clearDashboardCompanyScope(): void {
    const sectionKey = this.dashboardSectionKey(this.dashboardView());
    this.dashboardCompanySlug.set('');
    if (sectionKey) {
      this.dashboardPages.update((pages) => ({ ...pages, [sectionKey]: 1 }));
    }
    this.loadDashboard(sectionKey || '', 1);
  }

  printCompanyProfile(): void {
    window.print();
  }

  openBusinessModel(slug: string, asOf = '', compareTo = ''): void {
    if (!slug || !this.token()) {
      return;
    }
    this.activePage.set('business-model');
    this.menuOpen.set(false);
    this.businessModelLoading.set(true);
    this.error.set('');
    this.api.businessModel(this.token(), slug, asOf, compareTo).subscribe({
      next: (response) => {
        this.businessModel.set(response);
        this.businessModelDate = response.snapshot?.effective_date || '';
        this.businessModelCompareDate = response.comparison_snapshot?.effective_date || '';
        this.businessModelLoading.set(false);
      },
      error: (response) => {
        this.businessModelLoading.set(false);
        this.showError(response);
      }
    });
  }

  reloadBusinessModel(): void {
    const company = this.businessModel()?.company;
    if (company) {
      this.openBusinessModel(company.slug, this.businessModelDate, this.businessModelCompareDate);
    }
  }

  openOperatingKpis(slug: string, metric = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('operating-kpis');
    this.menuOpen.set(false);
    this.operatingKpiLoading.set(true);
    this.error.set('');
    this.api.operatingKpis(
      this.token(), slug, metric || this.operatingKpiMetric, this.operatingKpiSegment,
      this.operatingKpiGeography, this.operatingKpiStart, this.operatingKpiEnd, this.operatingKpiComparableOnly
    ).subscribe({
      next: (response) => {
        this.operatingKpis.set(response);
        this.operatingKpiMetric = response.selected_metric?.slug || '';
        this.operatingKpiLoading.set(false);
      },
      error: (response) => { this.operatingKpiLoading.set(false); this.showError(response); }
    });
  }

  reloadOperatingKpis(): void {
    const company = this.operatingKpis()?.company;
    if (company) this.openOperatingKpis(company.slug, this.operatingKpiMetric);
  }

  openManagementPromises(slug: string, promise = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('management-promises');
    this.menuOpen.set(false);
    this.managementPromiseLoading.set(true);
    this.error.set('');
    this.api.managementPromises(
      this.token(), slug, this.managementPromiseStatus, this.managementPromiseType,
      this.managementPromiseDue, this.managementPromiseAsOf, promise || this.managementPromiseSlug
    ).subscribe({
      next: (response) => {
        this.managementPromises.set(response);
        this.managementPromiseSlug = response.selected_promise?.slug || '';
        this.managementPromiseLoading.set(false);
      },
      error: (response) => { this.managementPromiseLoading.set(false); this.showError(response); }
    });
  }

  reloadManagementPromises(): void {
    const company = this.managementPromises()?.company;
    if (company) this.openManagementPromises(company.slug, this.managementPromiseSlug);
  }

  selectManagementPromise(slug: string): void {
    const company = this.managementPromises()?.company;
    if (company) {
      this.managementPromiseSlug = slug;
      this.openManagementPromises(company.slug, slug);
    }
  }

  openStrategyMilestones(slug: string, milestone = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('strategy-milestones');
    this.menuOpen.set(false);
    this.strategyMilestoneLoading.set(true);
    this.error.set('');
    this.api.strategyMilestones(
      this.token(), slug, this.strategyMilestoneStatus, this.strategyMilestoneType,
      this.strategyMilestoneOrigin, this.strategyMilestoneView, milestone || this.strategyMilestoneSlug
    ).subscribe({
      next: (response) => {
        this.strategyMilestones.set(response);
        this.strategyMilestoneSlug = response.selected_milestone?.slug || '';
        this.strategyMilestoneLoading.set(false);
      },
      error: (response) => { this.strategyMilestoneLoading.set(false); this.showError(response); }
    });
  }

  reloadStrategyMilestones(): void {
    const company = this.strategyMilestones()?.company;
    if (company) this.openStrategyMilestones(company.slug, this.strategyMilestoneSlug);
  }

  selectStrategyMilestone(slug: string): void {
    const company = this.strategyMilestones()?.company;
    if (company) {
      this.strategyMilestoneSlug = slug;
      this.openStrategyMilestones(company.slug, slug);
    }
  }

  openEarnings(slug: string, period = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('earnings');
    this.menuOpen.set(false);
    this.earningsLoading.set(true);
    this.error.set('');
    this.api.earnings(this.token(), slug, period || this.earningsPeriod).subscribe({
      next: (response) => {
        this.earnings.set(response);
        this.earningsPeriod = response.selected_period?.key || '';
        this.earningsLoading.set(false);
      },
      error: (response) => { this.earningsLoading.set(false); this.showError(response); }
    });
  }

  reloadEarnings(): void {
    const company = this.earnings()?.company;
    if (company) this.openEarnings(company.slug, this.earningsPeriod);
  }

  printEarningsBrief(): void {
    window.print();
  }

  openCapitalAllocation(slug: string, period = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('capital-allocation');
    this.menuOpen.set(false);
    this.capitalAllocationLoading.set(true);
    this.error.set('');
    this.api.capitalAllocation(this.token(), slug, period || this.capitalAllocationPeriod).subscribe({
      next: (response) => {
        this.capitalAllocation.set(response);
        this.capitalAllocationPeriod = response.selected_period?.key || '';
        this.capitalAllocationLoading.set(false);
      },
      error: (response) => { this.capitalAllocationLoading.set(false); this.showError(response); }
    });
  }

  reloadCapitalAllocation(): void {
    const company = this.capitalAllocation()?.company;
    if (company) this.openCapitalAllocation(company.slug, this.capitalAllocationPeriod);
  }

  printCapitalAllocationBrief(): void {
    window.print();
  }

  promiseLabel(value: string): string {
    return managementPromiseLabel(value);
  }

  kpiBarWidth(value: number, series: { value: number }[]): number {
    const maximum = Math.max(...series.map((row) => Math.abs(row.value)), 1);
    return Math.max(2, Math.round((Math.abs(value) / maximum) * 100));
  }

  businessModelComponentLabel(type: string): string {
    return businessModelComponentLabel(type);
  }

  businessModelRelationshipLabel(type: string): string {
    return businessModelRelationshipLabel(type);
  }

  profileSectionLabel(key: string): string {
    return companyProfileSectionLabel(key);
  }

  profileItemLabel(item: unknown): string {
    return companyProfileItemLabel(item);
  }

  sectorShare(eventCount: number, dash: DashboardResponse): number {
    return this.percentOf(eventCount, Math.max(...dash.sector_counts.map((sector) => sector.event_count), 1));
  }

  companyShare(eventCount: number, dash: DashboardResponse): number {
    return this.percentOf(eventCount, Math.max(...dash.top_companies.map((company) => company.event_count), 1));
  }

  coverageShare(value: number, dash: DashboardResponse): number {
    const total = dash.summary.source_count + dash.summary.event_count + dash.summary.strategic_turn_count;
    return this.percentOf(value, total || 1);
  }

  impactWindowWidth(returnPct: number | null): number {
    const value = Math.abs(returnPct || 0);
    return Math.max(8, Math.min(100, Math.round(value * 6)));
  }

  impactWindowTone(returnPct: number | null): string {
    if ((returnPct || 0) < 0) {
      return 'negative';
    }
    if ((returnPct || 0) > 0) {
      return 'positive';
    }
    return 'neutral';
  }

  impactLinePoints(windows: { days: number; return_pct: number | null }[]): string {
    return windows
      .map((_window, index) => `${this.impactLineX(windows, index).toFixed(1)},${this.impactLineY(windows, index).toFixed(1)}`)
      .join(' ');
  }

  impactLineX(windows: { days: number; return_pct: number | null }[], index: number): number {
    const width = 180;
    const padding = 8;
    return windows.length === 1 ? width / 2 : padding + (index * (width - padding * 2)) / (windows.length - 1);
  }

  impactLineY(windows: { return_pct: number | null }[], index: number): number {
    const values = windows.map((window) => window.return_pct || 0);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    const range = max - min || 1;
    return 8 + ((max - (windows[index]?.return_pct || 0)) / range) * (58 - 16);
  }

  impactZeroLineY(windows: { return_pct: number | null }[]): number {
    const values = windows.map((window) => window.return_pct || 0);
    const min = Math.min(...values, 0);
    const max = Math.max(...values, 0);
    const range = max - min || 1;
    return Math.round(8 + ((max - 0) / range) * (58 - 16));
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
    this.loadDashboard();
  }

  private clearSession(message: string): void {
    localStorage.removeItem('infodj_token');
    this.token.set('');
    this.currentUser.set(null);
    this.history.set([]);
    this.dashboard.set(null);
    this.searchResults.set(null);
    this.suggestions.set([]);
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

  private percentOf(value: number, total: number): number {
    if (!total) {
      return 0;
    }
    return Math.max(2, Math.round((value / total) * 100));
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
