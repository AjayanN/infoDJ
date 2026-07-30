import 'zone.js';

import { CommonModule } from '@angular/common';
import { provideHttpClient } from '@angular/common/http';
import { Component, HostListener, inject, signal } from '@angular/core';
import { FormsModule } from '@angular/forms';
import { bootstrapApplication } from '@angular/platform-browser';
import { provideRouter, Routes } from '@angular/router';
import { finalize, timeout } from 'rxjs';

import {
  CurrentUser,
  CompanyProfileResponse,
  BusinessModelResponse,
  BusinessModelRelationship,
  KpiDefinition,
  OperatingKpiResponse,
  ManagementPromiseResponse,
  StrategyMilestoneResponse,
  EarningsResponse,
  CapitalAllocationResponse,
  CompetitivePositionResponse,
  ProductPricingResponse,
  AcquisitionLifecycleResponse,
  CustomerSupplierDependencyResponse,
  GeographicExpansionResponse,
  OwnershipInsiderResponse,
  ValuationContextResponse,
  RegulatoryLitigationResponse,
  SectorThemeResponse,
  MacroSensitivityResponse,
  StrategyThesis,
  ThesisListResponse,
  ThesisSuggestionsResponse,
  Watchlist,
  WatchlistResponse,
  NotificationResponse,
  Briefing,
  BriefingResponse,
  ScenarioSet,
  ScenarioListResponse,
  ContradictionCase,
  ContradictionListResponse,
  StrategyFailureCase,
  StrategyFailureListResponse,
  FoundationStandardsResponse,
  LeadershipDecisionResponse,
  DashboardSection,
  DashboardEvent,
  DashboardResponse,
  CompanyProfileSource,
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
  deduplicateSourceLensRecords,
  managementPromiseLabel,
  sourceLensWhyUsed
} from './app/company-profile.utils';

declare global {
  interface Window {
    Razorpay?: new (options: RazorpayCheckoutOptions) => { open: () => void };
  }
}

type AuthView = 'login' | 'signup' | 'forgot' | 'reset';
type AppPage = 'dashboard' | 'company' | 'business-model' | 'operating-kpis' | 'management-promises' | 'strategy-milestones' | 'earnings' | 'capital-allocation' | 'competitive-position' | 'product-pricing' | 'acquisition-lifecycle' | 'customer-supplier-dependency' | 'geographic-expansion' | 'leadership-decisions' | 'ownership-insider' | 'valuation-context' | 'regulatory-litigation' | 'sector-themes' | 'macro-sensitivity' | 'strategy-theses' | 'watchlists' | 'briefings' | 'scenarios' | 'contradictions' | 'strategy-failures' | 'foundations' | 'profile' | 'subscription';
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
type CompanyFeatureId =
  | 'business-model' | 'operating-kpis' | 'management-promises' | 'strategy-milestones' | 'earnings'
  | 'capital-allocation' | 'competitive-position' | 'product-pricing' | 'acquisition-lifecycle'
  | 'customer-supplier-dependency' | 'geographic-expansion' | 'leadership-decisions' | 'ownership-insider'
  | 'valuation-context' | 'regulatory-litigation' | 'sector-themes' | 'macro-sensitivity' | 'strategy-theses'
  | 'follow-alerts' | 'scenarios' | 'contradictions' | 'strategy-failures' | 'compare-peers' | 'latest-moves' | 'risk-signals';
type CompanyFeature = {
  id: CompanyFeatureId;
  category: 'Business model' | 'Performance' | 'Strategy' | 'Market position' | 'Risk' | 'Ownership' | 'User workspace';
  title: string;
  purpose: string;
  keywords: string;
};
type SearchResultGroup = 'companies' | 'events' | 'strategic_turns';
type ValueFlowNode = { key: string; name: string; x: number; y: number };
type ValueFlowEdge = { key: string; from: ValueFlowNode; to: ValueFlowNode; label: string; x: number; y: number };
type ValueFlowDrag = { nodeKey: string; space: DOMRect } | null;
type ValueFlowFocus = { type: 'edge' | 'node'; key: string } | null;
type ValueFlowGraph = { nodes: ValueFlowNode[]; edges: ValueFlowEdge[] };
type KpiEventGroup = { type: string; label: string; count: number; latestDate: string; events: DashboardEvent[]; hiddenCount: number };
type LatestMoveFilter = 'all' | 'product' | 'pricing' | 'acquisition' | 'geography' | 'leadership' | 'regulation' | 'capital' | 'competition';
type LatestMoveGroup = { type: string; label: string; events: DashboardEvent[] };
type LatestMoveContext = { feature: CompanyFeatureId; label: string; note: string };
type RiskSignalGroup = { key: string; label: string; events: DashboardEvent[] };
type KpiMetricGroup = { key: string; label: string; variants: KpiDefinition[]; selected: boolean; defaultSlug: string };
type BlockedKpiPeer = OperatingKpiResponse['blocked_peer_metrics'][number];
type KpiBlockerReason = { key: string; label: string; count: number };
type KpiPeerBlockerGroup = { company: string; companySlug: string; total: number; reasons: KpiBlockerReason[]; examples: BlockedKpiPeer[]; hiddenCount: number };
type PromiseBoardLane = { key: string; label: string; description: string; promises: ManagementPromiseResponse['promises'] };
type CompetitivePeerLane = { label: string; peers: CompetitivePositionResponse['peer_map'] };
type ProductOfferingFamily = { label: string; offerings: ProductPricingResponse['offerings'] };
type DependencyRelationshipLane = { key: string; label: string; dependencies: CustomerSupplierDependencyResponse['dependencies'] };
type GeographicMarketLane = { key: string; label: string; description: string; markets: GeographicExpansionResponse['markets'] };
type AcquisitionLifecycleLane = { label: string; deals: AcquisitionLifecycleResponse['deals'] };
type MilestoneInitiativeLane = { label: string; description: string; milestones: StrategyMilestoneResponse['milestones'] };
type SourceLensState = { title: string; sources: CompanyProfileSource[] } | null;
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
  latestMoveFilter = signal<LatestMoveFilter>('all');
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
  competitivePosition = signal<CompetitivePositionResponse | null>(null);
  productPricing = signal<ProductPricingResponse | null>(null);
  acquisitionLifecycle = signal<AcquisitionLifecycleResponse | null>(null);
  customerSupplierDependency = signal<CustomerSupplierDependencyResponse | null>(null);
  geographicExpansion = signal<GeographicExpansionResponse | null>(null);
  ownershipInsider = signal<OwnershipInsiderResponse | null>(null);
  valuationContext = signal<ValuationContextResponse | null>(null);
  regulatoryLitigation = signal<RegulatoryLitigationResponse | null>(null);
  sectorThemes = signal<SectorThemeResponse | null>(null);
  macroSensitivity = signal<MacroSensitivityResponse | null>(null);
  thesisWorkspace = signal<ThesisListResponse | null>(null);
  selectedThesis = signal<StrategyThesis | null>(null);
  thesisSuggestions = signal<ThesisSuggestionsResponse | null>(null);
  watchlists = signal<WatchlistResponse | null>(null);
  selectedWatchlist = signal<Watchlist | null>(null);
  notifications = signal<NotificationResponse | null>(null);
  briefings = signal<BriefingResponse | null>(null);
  selectedBriefing = signal<Briefing | null>(null);
  scenarios = signal<ScenarioListResponse | null>(null);
  selectedScenario = signal<ScenarioSet | null>(null);
  contradictions = signal<ContradictionListResponse | null>(null);
  selectedContradiction = signal<ContradictionCase | null>(null);
  strategyFailures = signal<StrategyFailureListResponse | null>(null);
  selectedStrategyFailure = signal<StrategyFailureCase | null>(null);
  foundationStandards = signal<FoundationStandardsResponse | null>(null);
  leadershipDecisions = signal<LeadershipDecisionResponse | null>(null);
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
  competitivePositionLoading = signal(false);
  productPricingLoading = signal(false);
  acquisitionLifecycleLoading = signal(false);
  customerSupplierDependencyLoading = signal(false);
  geographicExpansionLoading = signal(false);
  ownershipInsiderLoading = signal(false);
  valuationContextLoading = signal(false);
  regulatoryLitigationLoading = signal(false);
  sectorThemesLoading = signal(false);
  macroSensitivityLoading = signal(false);
  thesisWorkspaceLoading = signal(false);
  watchlistLoading = signal(false);
  briefingLoading = signal(false);
  scenarioLoading = signal(false);
  contradictionLoading = signal(false);
  strategyFailureLoading = signal(false);
  foundationLoading = signal(false);
  leadershipDecisionLoading = signal(false);
  companyProfileDate = '';
  companyFeatureQuery = '';
  businessModelDate = '';
  businessModelCompareDate = '';
  readonly businessModelComponentOrder = ['PAYER', 'USER', 'OFFERING', 'REVENUE', 'CHANNEL', 'GEOGRAPHY', 'PARTNER', 'COST', 'ASSET'];
  businessModelTypeFilter = '';
  valueFlowFocus = signal<ValueFlowFocus>(null);
  sourceLens = signal<SourceLensState>(null);
  valueFlowGraph = signal<ValueFlowGraph>({ nodes: [], edges: [] });
  valueFlowNodeOverrides = signal<Record<string, { x: number; y: number }>>({});
  private valueFlowDrag: ValueFlowDrag = null;
  operatingKpiMetric = '';
  operatingKpiSegment = '';
  operatingKpiGeography = '';
  operatingKpiStart = '';
  operatingKpiEnd = '';
  operatingKpiComparableOnly = false;
  selectedKpiVariants: Record<string, string> = {};
  operatingKpiMetricGroups = signal<KpiMetricGroup[]>([]);
  operatingKpiEventGroups = signal<KpiEventGroup[]>([]);
  operatingKpiBlockerReasons = signal<KpiBlockerReason[]>([]);
  operatingKpiBlockedPeerGroups = signal<KpiPeerBlockerGroup[]>([]);
  private operatingKpiRequestId = 0;
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
  capitalAllocationCadence = 'QUARTERLY';
  competitivePositionDate = '';
  competitiveRelationship = '';
  productPricingDate = '';
  productOfferingType = '';
  acquisitionStage = '';
  acquisitionTransactionType = '';
  acquisitionOutcome = '';
  acquisitionDeal = '';
  dependencyDate = '';
  dependencyType = '';
  dependencyConfidence = '';
  geographicExpansionDate = '';
  geographicExpansionStatus = '';
  geographicExpansionMarketType = '';
  ownershipInsiderDate = '';
  ownershipHolderType = '';
  insiderTransactionType = '';
  valuationContextDate = '';
  valuationMeasure = '';
  regulatoryLitigationDate = '';
  regulatoryMatterType = '';
  regulatoryMatterStatus = '';
  sectorThemesDate = '';
  sectorThemeFilter = '';
  sectorThemeExposureType = '';
  macroSensitivityDate = '';
  macroFactorFilter = '';
  macroChannelFilter = '';
  thesisFilterState = '';
  thesisFilterCompany = '';
  thesisSearchQuery = '';
  thesisTitle = '';
  thesisStatement = '';
  thesisCompanySlug = '';
  thesisCompanyName = '';
  thesisTimeHorizon = '';
  thesisReviewDate = '';
  thesisConfidence = 50;
  thesisAssumptions = '';
  thesisEvidenceSide = 'SUPPORTING';
  thesisEvidenceType = 'NOTE';
  thesisEvidenceTitle = '';
  thesisEvidenceSummary = '';
  thesisEvidenceUrl = '';
  thesisEvidenceDate = '';
  thesisEvidenceNote = '';
  thesisMilestoneTitle = '';
  thesisMilestoneDue = '';
  thesisMilestoneCriteria = '';
  thesisIndicatorName = '';
  thesisIndicatorDirection = 'QUALITATIVE';
  thesisIndicatorTarget = '';
  thesisIndicatorCurrent = '';
  thesisIndicatorSource = '';
  thesisRevisionState = 'ACTIVE';
  thesisRevisionConfidence = 50;
  thesisRevisionReason = '';
  watchlistName = '';
  watchlistDescription = '';
  watchItemType = 'COMPANY';
  watchItemId = '';
  watchItemLabel = '';
  watchItemCompanySlug = '';
  notificationStatusFilter = '';
  notificationCategoryFilter = '';
  briefingCadence = 'DAILY';
  briefingStatusFilter = '';
  scenarioCompanyFilter = '';
  scenarioStatusFilter = '';
  scenarioTitle = '';
  scenarioCompanySlug = '';
  scenarioCompanyName = '';
  scenarioThesis = '';
  scenarioHorizonStart = '';
  scenarioHorizonEnd = '';
  scenarioCaseKind = 'BASE';
  scenarioDriverType = 'KPI';
  scenarioDriverLabel = '';
  scenarioAssumption = '';
  scenarioRationale = '';
  scenarioEvidenceLabel = '';
  scenarioEvidenceUrl = '';
  scenarioIndicatorName = '';
  scenarioIndicatorTarget = '';
  scenarioIndicatorCurrent = '';
  scenarioIndicatorStatus = 'UNKNOWN';
  scenarioActualDate = '';
  scenarioActualMetric = '';
  scenarioActualValue = '';
  scenarioActualNote = '';
  contradictionCompanyFilter = '';
  contradictionReviewFilter = '';
  contradictionCategoryFilter = '';
  contradictionTitle = '';
  contradictionCompanySlug = '';
  contradictionCompanyName = '';
  contradictionCategory = 'SOURCE_VS_SOURCE';
  contradictionConflictType = 'CONTRADICTION';
  contradictionMateriality = 'MEDIUM';
  contradictionSummary = '';
  contradictionClaimALabel = 'Claim A';
  contradictionClaimAText = '';
  contradictionClaimADate = '';
  contradictionClaimASource = '';
  contradictionClaimBLabel = 'Claim B';
  contradictionClaimBText = '';
  contradictionClaimBDate = '';
  contradictionClaimBSource = '';
  contradictionReviewLabel = 'APPARENT_CONFLICT';
  contradictionExplanation = '';
  contradictionCorrectionPath = '';
  contradictionPublish = false;
  failureCompanyFilter = '';
  failureCategoryFilter = '';
  failureClassificationFilter = '';
  failureStageFilter = '';
  failureTitle = '';
  failureCompanySlug = '';
  failureCompanyName = '';
  failureSector = '';
  failureCategory = 'EXECUTION_BREAKDOWN';
  failureClassification = 'TOO_EARLY';
  failureStage = 'THESIS';
  failureDecisionDate = '';
  failureReviewStart = '';
  failureReviewEnd = '';
  failureMinimumEvidence = '';
  failureElapsedTime = '';
  failureDecisionContext = '';
  failureManagementRationale = '';
  failureOriginalThesis = '';
  failureExpectedResult = '';
  failureExecutionIssue = '';
  failureOutcomeDefinition = '';
  failureActualOutcome = '';
  failureCounterexamples = '';
  failureLessons = '';
  failureCorrectionPath = '';
  failureEvidenceLabel = '';
  failureEvidenceSummary = '';
  failureEvidenceDate = '';
  failureEvidenceUrl = '';
  failureWarningSignal = '';
  failureWarningWhy = '';
  failureWarningDate = '';
  failureLinkType = 'MILESTONE';
  failureLinkLabel = '';
  failureLinkNote = '';
  failureReviewStatus = 'IN_REVIEW';
  failureReviewNote = '';
  failurePublish = false;
  leadershipDecisionDate = '';
  leadershipRoleType = '';
  leadershipDecisionType = '';
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
  readonly companyDossierBlocks = [
    { title: 'What it sells', description: 'Reviewed offerings and the business lines used to describe them.', sections: ['products', 'brands', 'segments'] },
    { title: 'Who it serves', description: 'Reviewed customer groups and audience context.', sections: ['customer_groups'] },
    { title: 'How it earns', description: 'Reviewed business model and revenue sources.', sections: ['business_model', 'revenue_sources'] },
    { title: 'Where it operates', description: 'Reviewed geographic presence and corporate structure.', sections: ['geographies', 'subsidiaries'] },
    { title: 'Who runs it', description: 'Reviewed leadership and stated strategic priorities.', sections: ['leadership', 'strategic_priorities'] },
    { title: 'Who it competes with', description: 'Reviewed competitors named in the company profile.', sections: ['competitors'] }
  ];
  readonly companyAtGlanceGroups = [
    { label: 'Products', sections: ['products', 'brands'] },
    { label: 'Customers', sections: ['customer_groups'] },
    { label: 'Revenue', sections: ['revenue_sources'] },
    { label: 'Geographies', sections: ['geographies'] },
    { label: 'Leadership', sections: ['leadership'] },
    { label: 'Competitors', sections: ['competitors'] }
  ];

  readonly companyFeatureCategories: CompanyFeature['category'][] = [
    'Business model', 'Performance', 'Strategy', 'Market position', 'Risk', 'Ownership', 'User workspace'
  ];
  readonly companyFeatures: CompanyFeature[] = [
    { id: 'business-model', category: 'Business model', title: 'Business model map', purpose: 'Trace who pays, what is delivered, and how value reaches customers.', keywords: 'revenue payer user offering channel business model' },
    { id: 'operating-kpis', category: 'Performance', title: 'Operating KPI tracker', purpose: 'Review the operating measures that explain execution and change.', keywords: 'metrics kpi operating performance growth retention usage' },
    { id: 'earnings', category: 'Performance', title: 'Earnings intelligence', purpose: 'Read quarterly results, guidance, risks, and management commentary.', keywords: 'earnings quarter guidance results financial' },
    { id: 'capital-allocation', category: 'Performance', title: 'Capital allocation', purpose: 'See where cash is directed across investment, debt, and returns.', keywords: 'capital capex buyback dividend debt cash acquisition' },
    { id: 'valuation-context', category: 'Performance', title: 'Valuation context', purpose: 'Compare disclosed valuation inputs and peer context without investment advice.', keywords: 'valuation market cap pe ps ev price multiple' },
    { id: 'management-promises', category: 'Strategy', title: 'Management promise tracker', purpose: 'Check stated commitments against updates, deadlines, and outcomes.', keywords: 'promise commitment target guidance management delivery' },
    { id: 'strategy-milestones', category: 'Strategy', title: 'Strategy milestone tracker', purpose: 'Follow execution steps, dependencies, delays, and completion evidence.', keywords: 'strategy milestone execution initiative timeline' },
    { id: 'acquisition-lifecycle', category: 'Strategy', title: 'Acquisition lifecycle', purpose: 'Review deal rationale, approvals, integration progress, and outcomes.', keywords: 'acquisition deal merger m&a integration' },
    { id: 'product-pricing', category: 'Market position', title: 'Product and pricing history', purpose: 'Track offering changes, packaging, launches, and price context.', keywords: 'product pricing plan feature launch packaging catalog' },
    { id: 'competitive-position', category: 'Market position', title: 'Competitive position', purpose: 'Map competitors, overlap, responses, and moat evidence.', keywords: 'competitor competition moat market peer' },
    { id: 'customer-supplier-dependency', category: 'Market position', title: 'Customer and supplier dependency', purpose: 'Inspect concentration, platforms, counterparties, and contract dependencies.', keywords: 'customer supplier dependency platform channel concentration' },
    { id: 'geographic-expansion', category: 'Market position', title: 'Geographic expansion', purpose: 'See market presence, entries, exits, partners, and barriers.', keywords: 'geography country expansion region market international' },
    { id: 'regulatory-litigation', category: 'Risk', title: 'Regulatory and litigation calendar', purpose: 'Track matters, known dates, disclosed exposure, and sources.', keywords: 'regulatory litigation lawsuit legal investigation compliance' },
    { id: 'sector-themes', category: 'Risk', title: 'Sector and theme intelligence', purpose: 'Connect external themes to company evidence, events, and signals.', keywords: 'sector theme ai cloud regulation demand exposure' },
    { id: 'macro-sensitivity', category: 'Risk', title: 'Macro sensitivity profile', purpose: 'Review disclosed exposure to rates, inflation, demand, and supply conditions.', keywords: 'macro inflation rates recession currency commodity supply chain' },
    { id: 'leadership-decisions', category: 'Ownership', title: 'Leadership decision record', purpose: 'Review leadership changes, tenure, and source-backed decisions.', keywords: 'leadership executive ceo board management decision' },
    { id: 'ownership-insider', category: 'Ownership', title: 'Ownership and insider activity', purpose: 'Separate economic ownership, voting control, and disclosed transactions.', keywords: 'ownership insider holder voting control shares' },
    { id: 'strategy-theses', category: 'User workspace', title: 'Strategy thesis workspace', purpose: 'Capture a private research view with evidence, milestones, and revisions.', keywords: 'thesis workspace research notes' },
    { id: 'scenarios', category: 'User workspace', title: 'Scenario explorer', purpose: 'Organize evidence-backed best, base, and worst-case assumptions.', keywords: 'scenario forecast assumptions base best worst' },
    { id: 'contradictions', category: 'User workspace', title: 'Contradiction view', purpose: 'Compare reviewed claims that need clarification or reconciliation.', keywords: 'contradiction conflict claim evidence' },
    { id: 'strategy-failures', category: 'User workspace', title: 'Strategy failure library', purpose: 'Study reviewed execution breakdowns, warning signs, and lessons.', keywords: 'failure execution lessons warning' },
    { id: 'follow-alerts', category: 'User workspace', title: 'Follow for alerts', purpose: 'Add this company to your alert and briefing workspace.', keywords: 'follow alert notification briefing watchlist' },
    { id: 'compare-peers', category: 'Market position', title: 'Compare peers', purpose: 'Open comparable company situations for this company.', keywords: 'peer compare benchmark competitors' },
    { id: 'latest-moves', category: 'Strategy', title: 'Latest moves', purpose: 'Scan the latest source-backed strategic events for this company.', keywords: 'latest moves events news changes' },
    { id: 'risk-signals', category: 'Risk', title: 'Risk signals', purpose: 'Review source-backed warning signals in company context.', keywords: 'risk warning signal exposure' }
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

  setLatestMoveFilter(filter: LatestMoveFilter): void {
    this.latestMoveFilter.set(filter);
  }

  latestMoveFilters(): { id: LatestMoveFilter; label: string }[] {
    return [
      { id: 'all', label: 'All moves' },
      { id: 'product', label: 'Product' },
      { id: 'pricing', label: 'Pricing' },
      { id: 'acquisition', label: 'Acquisition' },
      { id: 'geography', label: 'Geography' },
      { id: 'leadership', label: 'Leadership' },
      { id: 'regulation', label: 'Regulation' },
      { id: 'capital', label: 'Capital' },
      { id: 'competition', label: 'Competition' }
    ];
  }

  latestMoveGroups(events: DashboardEvent[]): LatestMoveGroup[] {
    const filter = this.latestMoveFilter();
    const visible = events.filter((event) => filter === 'all' || this.latestMoveCategory(event) === filter);
    const byType = new Map<string, DashboardEvent[]>();
    for (const event of visible) {
      const type = event.event_type || 'UNCLASSIFIED';
      byType.set(type, [...(byType.get(type) || []), event]);
    }
    return [...byType.entries()].map(([type, groupedEvents]) => ({
      type,
      label: this.promiseLabel(type),
      events: groupedEvents
    }));
  }

  latestMoveCategory(event: DashboardEvent): LatestMoveFilter {
    const terms = `${event.event_type} ${event.decision_theme}`.toLowerCase();
    if (/price|pricing|packag|subscription/.test(terms)) return 'pricing';
    if (/product|launch|platform|service|feature/.test(terms)) return 'product';
    if (/acqui|merger|deal|purchase/.test(terms)) return 'acquisition';
    if (/geograph|market entry|international|region|country/.test(terms)) return 'geography';
    if (/leadership|chief executive|ceo|executive|board|appoint/.test(terms)) return 'leadership';
    if (/regulat|litigat|legal|antitrust|compliance/.test(terms)) return 'regulation';
    if (/capital|dividend|buyback|repurchase|investment|capex/.test(terms)) return 'capital';
    if (/compet|rival|moat|market share/.test(terms)) return 'competition';
    return 'all';
  }

  latestMoveContext(event: DashboardEvent): LatestMoveContext {
    const category = this.latestMoveCategory(event);
    const contexts: Record<LatestMoveFilter, LatestMoveContext> = {
      all: { feature: 'strategy-milestones', label: 'Open execution context', note: 'Review this move beside the company execution record.' },
      product: { feature: 'product-pricing', label: 'Open product context', note: 'Review the related offering and pricing history.' },
      pricing: { feature: 'product-pricing', label: 'Open pricing context', note: 'Review the related offering and pricing history.' },
      acquisition: { feature: 'acquisition-lifecycle', label: 'Open deal context', note: 'Review the related deal lifecycle and outcomes.' },
      geography: { feature: 'geographic-expansion', label: 'Open market context', note: 'Review the related market footprint and expansion evidence.' },
      leadership: { feature: 'leadership-decisions', label: 'Open leadership context', note: 'Review the related leadership record and source-backed decisions.' },
      regulation: { feature: 'regulatory-litigation', label: 'Open regulatory context', note: 'Review known matters, dates, and source records.' },
      capital: { feature: 'capital-allocation', label: 'Open capital context', note: 'Review the company capital-allocation record.' },
      competition: { feature: 'competitive-position', label: 'Open competitive context', note: 'Review competitive actions and moat evidence.' }
    };
    return contexts[category];
  }

  openLatestMoveContext(event: DashboardEvent): void {
    const context = this.latestMoveContext(event);
    switch (context.feature) {
      case 'product-pricing': this.openProductPricing(event.company_slug); break;
      case 'acquisition-lifecycle': this.openAcquisitionLifecycle(event.company_slug); break;
      case 'geographic-expansion': this.openGeographicExpansion(event.company_slug); break;
      case 'leadership-decisions': this.openLeadershipDecisions(event.company_slug); break;
      case 'regulatory-litigation': this.openRegulatoryLitigation(event.company_slug); break;
      case 'capital-allocation': this.openCapitalAllocation(event.company_slug); break;
      case 'competitive-position': this.openCompetitivePosition(event.company_slug); break;
      default: this.openStrategyMilestones(event.company_slug); break;
    }
  }

  riskSignalGroups(events: DashboardEvent[]): RiskSignalGroup[] {
    const grouped = new Map<string, DashboardEvent[]>();
    for (const event of events) {
      const key = this.riskSignalCategory(event);
      grouped.set(key, [...(grouped.get(key) || []), event]);
    }
    return [...grouped.entries()].map(([key, groupedEvents]) => ({
      key,
      label: this.promiseLabel(key),
      events: groupedEvents
    }));
  }

  riskSignalCategory(event: DashboardEvent): string {
    const terms = `${event.signal || ''} ${event.event_type} ${event.decision_theme}`.toLowerCase();
    if (/regulat|legal|litigat|antitrust|compliance/.test(terms)) return 'REGULATORY_AND_LITIGATION';
    if (/compet|rival|market_share/.test(terms)) return 'COMPETITION';
    if (/macro|inflation|interest|currency|demand/.test(terms)) return 'MACRO';
    if (/supplier|customer|platform|dependency|concentration/.test(terms)) return 'DEPENDENCY';
    if (/leadership|executive|board/.test(terms)) return 'LEADERSHIP';
    if (/valuation|market_price|multiple/.test(terms)) return 'VALUATION_CONTEXT';
    if (/kpi|revenue|margin|deteriorat/.test(terms)) return 'KPI_DETERIORATION';
    return 'BUSINESS_MODEL';
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
    if (this.activePage() === 'competitive-position') {
      return `${this.competitivePosition()?.company.name || 'Company'} Competitive Position`;
    }
    if (this.activePage() === 'product-pricing') {
      return `${this.productPricing()?.company.name || 'Company'} Product and Pricing`;
    }
    if (this.activePage() === 'acquisition-lifecycle') {
      return `${this.acquisitionLifecycle()?.company.name || 'Company'} Acquisition Lifecycle`;
    }
    if (this.activePage() === 'customer-supplier-dependency') {
      return `${this.customerSupplierDependency()?.company.name || 'Company'} Customer and Supplier Dependency`;
    }
    if (this.activePage() === 'geographic-expansion') {
      return `${this.geographicExpansion()?.company.name || 'Company'} Geographic Expansion Map`;
    }
    if (this.activePage() === 'ownership-insider') {
      return `${this.ownershipInsider()?.company.name || 'Company'} Ownership and Insider Activity`;
    }
    if (this.activePage() === 'valuation-context') {
      return `${this.valuationContext()?.company.name || 'Company'} Valuation Context`;
    }
    if (this.activePage() === 'regulatory-litigation') {
      return `${this.regulatoryLitigation()?.company.name || 'Company'} Regulatory and Litigation Calendar`;
    }
    if (this.activePage() === 'sector-themes') {
      return `${this.sectorThemes()?.company.name || 'Company'} Sector and Theme Intelligence`;
    }
    if (this.activePage() === 'macro-sensitivity') {
      return `${this.macroSensitivity()?.company.name || 'Company'} Macro Sensitivity Profile`;
    }
    if (this.activePage() === 'strategy-theses') {
      return 'Strategy Thesis Workspace';
    }
    if (this.activePage() === 'watchlists') {
      return 'Watchlists and Alerts';
    }
    if (this.activePage() === 'briefings') {
      return 'Daily and Weekly Briefings';
    }
    if (this.activePage() === 'scenarios') {
      return 'Scenario Explorer';
    }
    if (this.activePage() === 'contradictions') {
      return 'Contradiction View';
    }
    if (this.activePage() === 'strategy-failures') {
      return 'Strategy Failure Library';
    }
    if (this.activePage() === 'foundations') {
      return 'Foundation Standards';
    }
    if (this.activePage() === 'leadership-decisions') {
      return `${this.leadershipDecisions()?.company.name || 'Company'} Leadership Decision Record`;
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
    if (this.activePage() === 'competitive-position') {
      return 'Competitor sets, overlap dimensions, competitive actions, moat evidence, opposing evidence, and source gaps.';
    }
    if (this.activePage() === 'product-pricing') {
      return 'Product catalog, plan and feature history, packaging changes, price context, chronology, and source gaps.';
    }
    if (this.activePage() === 'acquisition-lifecycle') {
      return 'Acquisition portfolio, deal stages, management rationale, approvals, integration progress, outcomes, and source gaps.';
    }
    if (this.activePage() === 'customer-supplier-dependency') {
      return 'Customer, supplier, platform, distributor, licensor, infrastructure, and contract dependencies with evidence and source gaps.';
    }
    if (this.activePage() === 'geographic-expansion') {
      return 'Countries and regions entered or exited, partnerships, regulatory barriers, revenue contribution, outcomes, evidence, and source gaps.';
    }
    if (this.activePage() === 'ownership-insider') {
      return 'Ownership context, economic versus voting control, institutional and insider rows where disclosed, transaction-plan gaps, and evidence.';
    }
    if (this.activePage() === 'valuation-context') {
      return 'Historical and peer valuation context with formulas, source inputs, event-aligned snapshots, and no investment advice.';
    }
    if (this.activePage() === 'regulatory-litigation') {
      return 'Regulatory reviews, investigations, litigation, approvals, deadlines, exposure context, evidence, and legal guardrails.';
    }
    if (this.activePage() === 'sector-themes') {
      return 'Evidence-based sector and theme exposure across events, KPIs, risks, capital allocation, and narrative-only context.';
    }
    if (this.activePage() === 'macro-sensitivity') {
      return 'Macro factors, exposure channels, disclosed sensitivities, calculated-relationship limitations, and stress-period examples.';
    }
    if (this.activePage() === 'strategy-theses') {
      return 'Private thesis workspace for assumptions, evidence balance, milestones, indicators, confidence updates, and revision history.';
    }
    if (this.activePage() === 'watchlists') {
      return 'Follow companies and topics, refresh source-backed alerts, and review grouped notifications.';
    }
    if (this.activePage() === 'briefings') {
      return 'Personalized daily and weekly summaries of material followed-company changes, evidence, next steps, and coverage gaps.';
    }
    if (this.activePage() === 'scenarios') {
      return 'Best, base, and worst case assumption workspace with linked evidence and non-prediction guardrails.';
    }
    if (this.activePage() === 'contradictions') {
      return 'Neutral claim comparison queue for reviewed contradictions, clarifications, revisions, and normal evolution.';
    }
    if (this.activePage() === 'strategy-failures') {
      return 'Reviewed case-study library for failed or underperforming strategic moves, warning signs, outcomes, and lessons.';
    }
    if (this.activePage() === 'foundations') {
      return 'Shared Phase 2 rules for evidence, claims, metrics, periods, identity, confidence, review, state labels, and freshness.';
    }
    if (this.activePage() === 'leadership-decisions') {
      return 'Leadership roles, tenure context, stated priorities, material decisions, succession events, evidence, and non-causation guardrails.';
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

  filteredCompanyFeatures(category: CompanyFeature['category']): CompanyFeature[] {
    const query = this.companyFeatureQuery.trim().toLowerCase();
    return this.companyFeatures.filter((feature) => feature.category === category && (
      !query || `${feature.title} ${feature.purpose} ${feature.keywords}`.toLowerCase().includes(query)
    ));
  }

  hasCompanyFeatureResults(): boolean {
    return this.companyFeatureCategories.some((category) => this.filteredCompanyFeatures(category).length > 0);
  }

  openCompanyFeature(feature: CompanyFeature): void {
    const company = this.companyProfile()?.company;
    if (!company) {
      return;
    }
    switch (feature.id) {
      case 'business-model': this.openBusinessModel(company.slug); break;
      case 'operating-kpis': this.openOperatingKpis(company.slug); break;
      case 'management-promises': this.openManagementPromises(company.slug); break;
      case 'strategy-milestones': this.openStrategyMilestones(company.slug); break;
      case 'earnings': this.openEarnings(company.slug); break;
      case 'capital-allocation': this.openCapitalAllocation(company.slug); break;
      case 'competitive-position': this.openCompetitivePosition(company.slug); break;
      case 'product-pricing': this.openProductPricing(company.slug); break;
      case 'acquisition-lifecycle': this.openAcquisitionLifecycle(company.slug); break;
      case 'customer-supplier-dependency': this.openCustomerSupplierDependency(company.slug); break;
      case 'geographic-expansion': this.openGeographicExpansion(company.slug); break;
      case 'leadership-decisions': this.openLeadershipDecisions(company.slug); break;
      case 'ownership-insider': this.openOwnershipInsider(company.slug); break;
      case 'valuation-context': this.openValuationContext(company.slug); break;
      case 'regulatory-litigation': this.openRegulatoryLitigation(company.slug); break;
      case 'sector-themes': this.openSectorThemes(company.slug); break;
      case 'macro-sensitivity': this.openMacroSensitivity(company.slug); break;
      case 'strategy-theses': this.openStrategyTheses(company.slug, company.name); break;
      case 'follow-alerts': this.followCompanyForAlerts(company.slug, company.name); break;
      case 'scenarios': this.openScenarios(company.slug, company.name); break;
      case 'contradictions': this.openContradictions(company.slug, company.name); break;
      case 'strategy-failures': this.openStrategyFailures(company.slug, company.name, company.sector); break;
      case 'compare-peers': this.openCompanyDashboard('companies-like-mine'); break;
      case 'latest-moves': this.openCompanyDashboard('latest-moves'); break;
      case 'risk-signals': this.openCompanyDashboard('risk-signals'); break;
    }
  }

  isCompanyFeaturePage(): boolean {
    return [
      'business-model', 'operating-kpis', 'management-promises', 'strategy-milestones', 'earnings', 'capital-allocation',
      'competitive-position', 'product-pricing', 'acquisition-lifecycle', 'customer-supplier-dependency', 'geographic-expansion',
      'leadership-decisions', 'ownership-insider', 'valuation-context', 'regulatory-litigation', 'sector-themes', 'macro-sensitivity',
      'strategy-theses', 'scenarios', 'contradictions', 'strategy-failures'
    ].includes(this.activePage());
  }

  changeCompany(): void {
    this.setActivePage('dashboard');
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
        this.valueFlowFocus.set(null);
        this.valueFlowDrag = null;
        this.valueFlowNodeOverrides.set({});
        this.valueFlowGraph.set(this.buildValueFlowGraph(response.snapshot?.relationships || []));
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

  compareBusinessModelToLastMaterialChange(): void {
    const model = this.businessModel();
    const materialDate = model?.changes.last_material_change_date;
    if (!model || !materialDate) {
      return;
    }
    this.businessModelCompareDate = materialDate;
    this.openBusinessModel(model.company.slug, this.businessModelDate, materialDate);
  }

  openOperatingKpis(slug: string, metric = ''): void {
    if (!slug || !this.token()) return;
    const requestId = ++this.operatingKpiRequestId;
    this.activePage.set('operating-kpis');
    this.menuOpen.set(false);
    this.operatingKpiLoading.set(true);
    this.error.set('');
    this.api.operatingKpis(
      this.token(), slug, metric || this.operatingKpiMetric, this.operatingKpiSegment,
      this.operatingKpiGeography, this.operatingKpiStart, this.operatingKpiEnd, this.operatingKpiComparableOnly
    ).pipe(
      timeout({ first: 45000 }),
      finalize(() => {
        if (requestId === this.operatingKpiRequestId) {
          this.operatingKpiLoading.set(false);
        }
      })
    ).subscribe({
      next: (response) => {
        if (requestId !== this.operatingKpiRequestId) return;
        this.operatingKpis.set(response);
        this.operatingKpiMetric = response.selected_metric?.slug || '';
        this.syncSelectedKpiVariant(response.selected_metric);
        this.operatingKpiMetricGroups.set(this.buildKpiMetricGroups(response.dictionary, response.selected_metric?.slug || ''));
        this.operatingKpiEventGroups.set(this.buildKpiEventGroups(response.event_overlays));
        this.operatingKpiBlockerReasons.set(this.buildKpiBlockerReasons(response.blocked_peer_metrics));
        this.operatingKpiBlockedPeerGroups.set(this.buildKpiBlockedPeerGroups(response.blocked_peer_metrics));
      },
      error: (response) => {
        if (requestId !== this.operatingKpiRequestId) return;
        if ((response as { name?: string }).name === 'TimeoutError') {
          this.error.set('Operating KPI data did not respond within 45 seconds. Please retry after the ingestion service is idle.');
          return;
        }
        this.showError(response);
      }
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

  capitalPeriodsForCadence(view: CapitalAllocationResponse) {
    return view.periods.filter((period) => period.cadence === this.capitalAllocationCadence);
  }

  setCapitalAllocationCadence(cadence: string): void {
    this.capitalAllocationCadence = cadence;
    const view = this.capitalAllocation();
    const period = view ? this.capitalPeriodsForCadence(view)[0] : null;
    if (!period) return;
    this.capitalAllocationPeriod = period.key;
    this.reloadCapitalAllocation();
  }

  printCapitalAllocationBrief(): void {
    window.print();
  }

  openCompetitivePosition(slug: string, asOf = '', relationship = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('competitive-position');
    this.menuOpen.set(false);
    this.competitivePositionLoading.set(true);
    this.error.set('');
    this.api.competitivePosition(this.token(), slug, asOf || this.competitivePositionDate, relationship || this.competitiveRelationship).subscribe({
      next: (response) => {
        this.competitivePosition.set(response);
        this.competitivePositionDate = response.snapshot?.effective_date || '';
        this.competitiveRelationship = response.filters?.selected_relationship || '';
        this.competitivePositionLoading.set(false);
      },
      error: (response) => { this.competitivePositionLoading.set(false); this.showError(response); }
    });
  }

  reloadCompetitivePosition(): void {
    const company = this.competitivePosition()?.company;
    if (company) this.openCompetitivePosition(company.slug, this.competitivePositionDate, this.competitiveRelationship);
  }

  printCompetitivePositionBrief(): void {
    window.print();
  }

  openProductPricing(slug: string, asOf = '', type = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('product-pricing');
    this.menuOpen.set(false);
    this.productPricingLoading.set(true);
    this.error.set('');
    this.api.productPricing(this.token(), slug, asOf || this.productPricingDate, type || this.productOfferingType).subscribe({
      next: (response) => {
        this.productPricing.set(response);
        this.productPricingDate = response.snapshot?.effective_date || '';
        this.productOfferingType = response.filters?.selected_type || '';
        this.productPricingLoading.set(false);
      },
      error: (response) => { this.productPricingLoading.set(false); this.showError(response); }
    });
  }

  reloadProductPricing(): void {
    const company = this.productPricing()?.company;
    if (company) this.openProductPricing(company.slug, this.productPricingDate, this.productOfferingType);
  }

  printProductPricingBrief(): void {
    window.print();
  }

  openAcquisitionLifecycle(slug: string, stage = '', transactionType = '', outcome = '', deal = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('acquisition-lifecycle');
    this.menuOpen.set(false);
    this.acquisitionLifecycleLoading.set(true);
    this.error.set('');
    this.api.acquisitionLifecycle(
      this.token(),
      slug,
      stage || this.acquisitionStage,
      transactionType || this.acquisitionTransactionType,
      outcome || this.acquisitionOutcome,
      deal || this.acquisitionDeal
    ).subscribe({
      next: (response) => {
        this.acquisitionLifecycle.set(response);
        this.acquisitionStage = response.filters?.selected_stage || '';
        this.acquisitionTransactionType = response.filters?.selected_transaction_type || '';
        this.acquisitionOutcome = response.filters?.selected_outcome || '';
        this.acquisitionDeal = response.selected_deal?.slug || '';
        this.acquisitionLifecycleLoading.set(false);
      },
      error: (response) => { this.acquisitionLifecycleLoading.set(false); this.showError(response); }
    });
  }

  reloadAcquisitionLifecycle(): void {
    const company = this.acquisitionLifecycle()?.company;
    if (company) {
      this.openAcquisitionLifecycle(company.slug, this.acquisitionStage, this.acquisitionTransactionType, this.acquisitionOutcome, this.acquisitionDeal);
    }
  }

  selectAcquisitionDeal(slug: string): void {
    const company = this.acquisitionLifecycle()?.company;
    if (company) this.openAcquisitionLifecycle(company.slug, this.acquisitionStage, this.acquisitionTransactionType, this.acquisitionOutcome, slug);
  }

  printAcquisitionLifecycleBrief(): void {
    window.print();
  }

  openCustomerSupplierDependency(slug: string, asOf = '', type = '', confidence = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('customer-supplier-dependency');
    this.menuOpen.set(false);
    this.customerSupplierDependencyLoading.set(true);
    this.error.set('');
    this.api.customerSupplierDependency(
      this.token(),
      slug,
      asOf || this.dependencyDate,
      type || this.dependencyType,
      confidence || this.dependencyConfidence
    ).subscribe({
      next: (response) => {
        this.customerSupplierDependency.set(response);
        this.dependencyDate = response.snapshot?.effective_date || '';
        this.dependencyType = response.filters?.selected_type || '';
        this.dependencyConfidence = response.filters?.selected_confidence || '';
        this.customerSupplierDependencyLoading.set(false);
      },
      error: (response) => { this.customerSupplierDependencyLoading.set(false); this.showError(response); }
    });
  }

  reloadCustomerSupplierDependency(): void {
    const company = this.customerSupplierDependency()?.company;
    if (company) this.openCustomerSupplierDependency(company.slug, this.dependencyDate, this.dependencyType, this.dependencyConfidence);
  }

  printCustomerSupplierDependencyBrief(): void {
    window.print();
  }

  openGeographicExpansion(slug: string, asOf = '', status = '', marketType = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('geographic-expansion');
    this.menuOpen.set(false);
    this.geographicExpansionLoading.set(true);
    this.error.set('');
    this.api.geographicExpansion(
      this.token(),
      slug,
      asOf || this.geographicExpansionDate,
      status || this.geographicExpansionStatus,
      marketType || this.geographicExpansionMarketType
    ).subscribe({
      next: (response) => {
        this.geographicExpansion.set(response);
        this.geographicExpansionDate = response.snapshot?.effective_date || '';
        this.geographicExpansionStatus = response.filters?.selected_status || '';
        this.geographicExpansionMarketType = response.filters?.selected_market_type || '';
        this.geographicExpansionLoading.set(false);
      },
      error: (response) => { this.geographicExpansionLoading.set(false); this.showError(response); }
    });
  }

  reloadGeographicExpansion(): void {
    const company = this.geographicExpansion()?.company;
    if (company) this.openGeographicExpansion(company.slug, this.geographicExpansionDate, this.geographicExpansionStatus, this.geographicExpansionMarketType);
  }

  printGeographicExpansionBrief(): void {
    window.print();
  }

  openOwnershipInsider(slug: string, asOf = '', holderType = '', transactionType = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('ownership-insider');
    this.menuOpen.set(false);
    this.ownershipInsiderLoading.set(true);
    this.error.set('');
    this.api.ownershipInsider(
      this.token(),
      slug,
      asOf || this.ownershipInsiderDate,
      holderType || this.ownershipHolderType,
      transactionType || this.insiderTransactionType
    ).subscribe({
      next: (response) => {
        this.ownershipInsider.set(response);
        this.ownershipInsiderDate = response.snapshot?.effective_date || '';
        this.ownershipHolderType = response.filters?.selected_holder_type || '';
        this.insiderTransactionType = response.filters?.selected_transaction_type || '';
        this.ownershipInsiderLoading.set(false);
      },
      error: (response) => { this.ownershipInsiderLoading.set(false); this.showError(response); }
    });
  }

  reloadOwnershipInsider(): void {
    const company = this.ownershipInsider()?.company;
    if (company) this.openOwnershipInsider(company.slug, this.ownershipInsiderDate, this.ownershipHolderType, this.insiderTransactionType);
  }

  printOwnershipInsiderBrief(): void {
    window.print();
  }

  openValuationContext(slug: string, asOf = '', measure = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('valuation-context');
    this.menuOpen.set(false);
    this.valuationContextLoading.set(true);
    this.error.set('');
    this.api.valuationContext(
      this.token(),
      slug,
      asOf || this.valuationContextDate,
      measure || this.valuationMeasure
    ).subscribe({
      next: (response) => {
        this.valuationContext.set(response);
        this.valuationContextDate = response.snapshot?.effective_date || '';
        this.valuationMeasure = response.filters?.selected_measure || '';
        this.valuationContextLoading.set(false);
      },
      error: (response) => { this.valuationContextLoading.set(false); this.showError(response); }
    });
  }

  reloadValuationContext(): void {
    const company = this.valuationContext()?.company;
    if (company) this.openValuationContext(company.slug, this.valuationContextDate, this.valuationMeasure);
  }

  selectValuationMeasure(measure: string): void {
    if (measure === this.valuationMeasure) return;
    this.valuationMeasure = measure;
    this.reloadValuationContext();
  }

  printValuationContextBrief(): void {
    window.print();
  }

  openRegulatoryLitigation(slug: string, asOf = '', matterType = '', status = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('regulatory-litigation');
    this.menuOpen.set(false);
    this.regulatoryLitigationLoading.set(true);
    this.error.set('');
    this.api.regulatoryLitigation(
      this.token(),
      slug,
      asOf || this.regulatoryLitigationDate,
      matterType || this.regulatoryMatterType,
      status || this.regulatoryMatterStatus
    ).subscribe({
      next: (response) => {
        this.regulatoryLitigation.set(response);
        this.regulatoryLitigationDate = response.snapshot?.effective_date || '';
        this.regulatoryMatterType = response.filters?.selected_matter_type || '';
        this.regulatoryMatterStatus = response.filters?.selected_status || '';
        this.regulatoryLitigationLoading.set(false);
      },
      error: (response) => { this.regulatoryLitigationLoading.set(false); this.showError(response); }
    });
  }

  reloadRegulatoryLitigation(): void {
    const company = this.regulatoryLitigation()?.company;
    if (company) this.openRegulatoryLitigation(company.slug, this.regulatoryLitigationDate, this.regulatoryMatterType, this.regulatoryMatterStatus);
  }

  printRegulatoryLitigationBrief(): void {
    window.print();
  }

  openSectorThemes(slug: string, asOf = '', theme = '', exposureType = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('sector-themes');
    this.menuOpen.set(false);
    this.sectorThemesLoading.set(true);
    this.error.set('');
    this.api.sectorThemes(
      this.token(),
      slug,
      asOf || this.sectorThemesDate,
      theme || this.sectorThemeFilter,
      exposureType || this.sectorThemeExposureType
    ).subscribe({
      next: (response) => {
        this.sectorThemes.set(response);
        this.sectorThemesDate = response.snapshot?.effective_date || '';
        this.sectorThemeFilter = response.filters?.selected_theme || '';
        this.sectorThemeExposureType = response.filters?.selected_exposure_type || '';
        this.sectorThemesLoading.set(false);
      },
      error: (response) => { this.sectorThemesLoading.set(false); this.showError(response); }
    });
  }

  reloadSectorThemes(): void {
    const company = this.sectorThemes()?.company;
    if (company) this.openSectorThemes(company.slug, this.sectorThemesDate, this.sectorThemeFilter, this.sectorThemeExposureType);
  }

  printSectorThemesBrief(): void {
    window.print();
  }

  openMacroSensitivity(slug: string, asOf = '', factor = '', channel = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('macro-sensitivity');
    this.menuOpen.set(false);
    this.macroSensitivityLoading.set(true);
    this.error.set('');
    this.api.macroSensitivity(
      this.token(),
      slug,
      asOf || this.macroSensitivityDate,
      factor || this.macroFactorFilter,
      channel || this.macroChannelFilter
    ).subscribe({
      next: (response) => {
        this.macroSensitivity.set(response);
        this.macroSensitivityDate = response.snapshot?.effective_date || '';
        this.macroFactorFilter = response.filters?.selected_factor || '';
        this.macroChannelFilter = response.filters?.selected_channel || '';
        this.macroSensitivityLoading.set(false);
      },
      error: (response) => { this.macroSensitivityLoading.set(false); this.showError(response); }
    });
  }

  reloadMacroSensitivity(): void {
    const company = this.macroSensitivity()?.company;
    if (company) this.openMacroSensitivity(company.slug, this.macroSensitivityDate, this.macroFactorFilter, this.macroChannelFilter);
  }

  printMacroSensitivityBrief(): void {
    window.print();
  }

  openStrategyTheses(companySlug = '', companyName = ''): void {
    if (!this.token()) return;
    this.activePage.set('strategy-theses');
    this.menuOpen.set(false);
    if (companySlug) {
      this.thesisFilterCompany = companySlug;
      this.thesisCompanySlug = companySlug;
      this.thesisCompanyName = companyName;
    }
    this.loadStrategyTheses();
  }

  loadStrategyTheses(): void {
    if (!this.token()) return;
    this.thesisWorkspaceLoading.set(true);
    this.error.set('');
    this.api.theses(this.token(), this.thesisFilterState, this.thesisFilterCompany, this.thesisSearchQuery).subscribe({
      next: (response) => {
        this.thesisWorkspace.set(response);
        const selected = this.selectedThesis();
        if (!selected && response.theses.length > 0) {
          this.selectThesis(response.theses[0].id);
        }
        this.thesisWorkspaceLoading.set(false);
      },
      error: (response) => { this.thesisWorkspaceLoading.set(false); this.showError(response); }
    });
  }

  selectThesis(id: number): void {
    if (!this.token()) return;
    this.api.thesis(this.token(), id).subscribe({
      next: (response) => {
        this.selectedThesis.set(response.thesis);
        this.thesisRevisionState = response.thesis.state || 'ACTIVE';
        this.thesisRevisionConfidence = response.thesis.confidence_score || 50;
      },
      error: (response) => this.showError(response)
    });
  }

  createStrategyThesis(): void {
    if (!this.token()) return;
    this.api.createThesis(this.token(), {
      title: this.thesisTitle,
      company_slug: this.thesisCompanySlug,
      company_name: this.thesisCompanyName,
      statement: this.thesisStatement,
      state: 'ACTIVE',
      time_horizon: this.thesisTimeHorizon,
      review_date: this.thesisReviewDate,
      confidence_score: this.thesisConfidence,
      assumptions: this.thesisAssumptions.split('\n').map((row) => row.trim()).filter(Boolean)
    }).subscribe({
      next: (response) => {
        this.message.set('Thesis created.');
        this.selectedThesis.set(response.thesis);
        this.thesisTitle = '';
        this.thesisStatement = '';
        this.thesisAssumptions = '';
        this.loadStrategyTheses();
      },
      error: (response) => this.showError(response)
    });
  }

  addThesisEvidence(): void {
    const thesis = this.selectedThesis();
    if (!this.token() || !thesis) return;
    this.api.addThesisEvidence(this.token(), thesis.id, {
      side: this.thesisEvidenceSide,
      evidence_type: this.thesisEvidenceType,
      company_slug: this.thesisCompanySlug || thesis.company_slug,
      title: this.thesisEvidenceTitle,
      summary: this.thesisEvidenceSummary,
      source_url: this.thesisEvidenceUrl,
      source_date: this.thesisEvidenceDate,
      user_note: this.thesisEvidenceNote
    }).subscribe({
      next: () => {
        this.message.set('Evidence attached.');
        this.thesisEvidenceTitle = '';
        this.thesisEvidenceSummary = '';
        this.thesisEvidenceUrl = '';
        this.thesisEvidenceNote = '';
        this.selectThesis(thesis.id);
      },
      error: (response) => this.showError(response)
    });
  }

  addThesisMilestone(): void {
    const thesis = this.selectedThesis();
    if (!this.token() || !thesis) return;
    this.api.addThesisMilestone(this.token(), thesis.id, {
      title: this.thesisMilestoneTitle,
      due_date: this.thesisMilestoneDue,
      success_criteria: this.thesisMilestoneCriteria
    }).subscribe({
      next: () => {
        this.message.set('Milestone added.');
        this.thesisMilestoneTitle = '';
        this.thesisMilestoneCriteria = '';
        this.selectThesis(thesis.id);
      },
      error: (response) => this.showError(response)
    });
  }

  addThesisIndicator(): void {
    const thesis = this.selectedThesis();
    if (!this.token() || !thesis) return;
    this.api.addThesisIndicator(this.token(), thesis.id, {
      name: this.thesisIndicatorName,
      direction: this.thesisIndicatorDirection,
      target: this.thesisIndicatorTarget,
      current_value: this.thesisIndicatorCurrent,
      source_hint: this.thesisIndicatorSource
    }).subscribe({
      next: () => {
        this.message.set('Indicator added.');
        this.thesisIndicatorName = '';
        this.thesisIndicatorTarget = '';
        this.thesisIndicatorCurrent = '';
        this.thesisIndicatorSource = '';
        this.selectThesis(thesis.id);
      },
      error: (response) => this.showError(response)
    });
  }

  updateThesisConfidence(): void {
    const thesis = this.selectedThesis();
    if (!this.token() || !thesis) return;
    this.api.updateThesisConfidence(this.token(), thesis.id, {
      state: this.thesisRevisionState,
      confidence_score: this.thesisRevisionConfidence,
      reason: this.thesisRevisionReason
    }).subscribe({
      next: (response) => {
        this.message.set('Confidence history updated.');
        this.selectedThesis.set(response.thesis);
        this.thesisRevisionReason = '';
        this.loadStrategyTheses();
      },
      error: (response) => this.showError(response)
    });
  }

  loadThesisEvidenceSuggestions(): void {
    if (!this.token()) return;
    this.api.thesisEvidenceSuggestions(this.token(), this.thesisSearchQuery || this.thesisCompanySlug || this.thesisFilterCompany, this.thesisCompanySlug || this.thesisFilterCompany).subscribe({
      next: (response) => this.thesisSuggestions.set(response),
      error: (response) => this.showError(response)
    });
  }

  useThesisSuggestion(suggestion: ThesisSuggestionsResponse['suggestions'][number]): void {
    this.thesisEvidenceType = suggestion.evidence_type;
    this.thesisEvidenceTitle = suggestion.title;
    this.thesisEvidenceSummary = suggestion.summary;
    this.thesisEvidenceUrl = suggestion.source_url || '';
    this.thesisEvidenceDate = suggestion.source_date || '';
    this.thesisCompanySlug = suggestion.company_slug || this.thesisCompanySlug;
  }

  openWatchlists(companySlug = '', companyName = ''): void {
    if (!this.token()) return;
    this.activePage.set('watchlists');
    this.menuOpen.set(false);
    if (companySlug) {
      this.watchItemType = 'COMPANY';
      this.watchItemId = companySlug;
      this.watchItemCompanySlug = companySlug;
      this.watchItemLabel = companyName || companySlug;
    }
    this.loadWatchlists();
    this.loadNotifications();
  }

  loadWatchlists(): void {
    if (!this.token()) return;
    this.watchlistLoading.set(true);
    this.api.watchlists(this.token()).subscribe({
      next: (response) => {
        this.watchlists.set(response);
        if (!this.selectedWatchlist() && response.watchlists.length > 0) this.selectWatchlist(response.watchlists[0].id);
        this.watchlistLoading.set(false);
      },
      error: (response) => { this.watchlistLoading.set(false); this.showError(response); }
    });
  }

  selectWatchlist(id: number): void {
    if (!this.token()) return;
    this.api.watchlist(this.token(), id).subscribe({
      next: (response) => this.selectedWatchlist.set(response.watchlist),
      error: (response) => this.showError(response)
    });
  }

  createWatchlist(): void {
    if (!this.token()) return;
    this.api.createWatchlist(this.token(), { name: this.watchlistName, description: this.watchlistDescription }).subscribe({
      next: (response) => {
        this.message.set('Watchlist created.');
        this.selectedWatchlist.set(response.watchlist);
        this.watchlistName = '';
        this.watchlistDescription = '';
        this.loadWatchlists();
      },
      error: (response) => this.showError(response)
    });
  }

  addWatchItem(): void {
    const watchlist = this.selectedWatchlist();
    if (!this.token() || !watchlist) return;
    this.api.addWatchlistItem(this.token(), watchlist.id, {
      entity_type: this.watchItemType,
      entity_id: this.watchItemId,
      label: this.watchItemLabel,
      company_slug: this.watchItemCompanySlug
    }).subscribe({
      next: () => {
        this.message.set('Watch item added.');
        this.selectWatchlist(watchlist.id);
        this.loadWatchlists();
      },
      error: (response) => this.showError(response)
    });
  }

  followCompanyForAlerts(slug: string, name: string): void {
    if (!this.token()) return;
    this.api.followCompany(this.token(), slug, name).subscribe({
      next: (response) => {
        this.message.set(`${name} followed for alerts.`);
        this.selectedWatchlist.set(response.watchlist);
        this.openWatchlists(slug, name);
      },
      error: (response) => this.showError(response)
    });
  }

  loadNotifications(): void {
    if (!this.token()) return;
    this.api.notifications(this.token(), this.notificationStatusFilter, this.notificationCategoryFilter).subscribe({
      next: (response) => this.notifications.set(response),
      error: (response) => this.showError(response)
    });
  }

  refreshNotifications(): void {
    if (!this.token()) return;
    this.api.refreshNotifications(this.token()).subscribe({
      next: (response) => {
        this.message.set(`Alerts refreshed: ${response.stats['notifications_created'] || 0} created, ${response.stats['notifications_updated'] || 0} updated.`);
        this.loadNotifications();
        this.loadWatchlists();
      },
      error: (response) => this.showError(response)
    });
  }

  markNotification(id: number, status: string): void {
    if (!this.token()) return;
    this.api.updateNotification(this.token(), id, status).subscribe({
      next: () => this.loadNotifications(),
      error: (response) => this.showError(response)
    });
  }

  rateNotification(id: number, rating: string): void {
    if (!this.token()) return;
    this.api.alertFeedback(this.token(), id, rating).subscribe({
      next: () => {
        this.message.set('Alert feedback saved.');
        this.loadNotifications();
      },
      error: (response) => this.showError(response)
    });
  }

  openBriefings(): void {
    if (!this.token()) return;
    this.activePage.set('briefings');
    this.menuOpen.set(false);
    this.loadBriefings();
  }

  loadBriefings(): void {
    if (!this.token()) return;
    this.briefingLoading.set(true);
    this.api.briefings(this.token(), this.briefingCadence, this.briefingStatusFilter).subscribe({
      next: (response) => {
        this.briefings.set(response);
        if (!this.selectedBriefing() && response.briefings.length > 0) this.selectBriefing(response.briefings[0].id);
        this.briefingLoading.set(false);
      },
      error: (response) => { this.briefingLoading.set(false); this.showError(response); }
    });
  }

  generateBriefing(): void {
    if (!this.token()) return;
    this.briefingLoading.set(true);
    this.api.generateBriefing(this.token(), this.briefingCadence, true).subscribe({
      next: (response) => {
        this.message.set(`${response.briefing.cadence_label} briefing generated.`);
        this.selectedBriefing.set(response.briefing);
        this.briefingLoading.set(false);
        this.loadBriefings();
      },
      error: (response) => { this.briefingLoading.set(false); this.showError(response); }
    });
  }

  selectBriefing(id: number): void {
    if (!this.token()) return;
    this.api.briefing(this.token(), id).subscribe({
      next: (response) => this.selectedBriefing.set(response.briefing),
      error: (response) => this.showError(response)
    });
  }

  archiveBriefing(id: number): void {
    if (!this.token()) return;
    this.api.updateBriefing(this.token(), id, 'ARCHIVED').subscribe({
      next: (response) => {
        this.selectedBriefing.set(response.briefing);
        this.loadBriefings();
      },
      error: (response) => this.showError(response)
    });
  }

  rateBriefing(id: number, rating: string): void {
    if (!this.token()) return;
    this.api.briefingFeedback(this.token(), id, rating).subscribe({
      next: () => this.message.set('Briefing feedback saved.'),
      error: (response) => this.showError(response)
    });
  }

  openScenarios(companySlug = '', companyName = ''): void {
    if (!this.token()) return;
    this.activePage.set('scenarios');
    this.menuOpen.set(false);
    if (companySlug) {
      this.scenarioCompanyFilter = companySlug;
      this.scenarioCompanySlug = companySlug;
      this.scenarioCompanyName = companyName;
    }
    this.loadScenarios();
  }

  loadScenarios(): void {
    if (!this.token()) return;
    this.scenarioLoading.set(true);
    this.api.scenarios(this.token(), this.scenarioCompanyFilter, this.scenarioStatusFilter).subscribe({
      next: (response) => {
        this.scenarios.set(response);
        if (!this.selectedScenario() && response.scenario_sets.length > 0) this.selectScenario(response.scenario_sets[0].id);
        this.scenarioLoading.set(false);
      },
      error: (response) => { this.scenarioLoading.set(false); this.showError(response); }
    });
  }

  createScenario(): void {
    if (!this.token()) return;
    this.api.createScenario(this.token(), {
      title: this.scenarioTitle,
      company_slug: this.scenarioCompanySlug,
      company_name: this.scenarioCompanyName,
      thesis: this.scenarioThesis,
      horizon_start: this.scenarioHorizonStart,
      horizon_end: this.scenarioHorizonEnd,
      status: 'ACTIVE'
    }).subscribe({
      next: (response) => {
        this.message.set('Scenario set created.');
        this.selectedScenario.set(response.scenario_set);
        this.scenarioTitle = '';
        this.scenarioThesis = '';
        this.loadScenarios();
      },
      error: (response) => this.showError(response)
    });
  }

  selectScenario(id: number): void {
    if (!this.token()) return;
    this.api.scenario(this.token(), id).subscribe({
      next: (response) => this.selectedScenario.set(response.scenario_set),
      error: (response) => this.showError(response)
    });
  }

  addScenarioAssumption(): void {
    const scenario = this.selectedScenario();
    const scenarioCase = scenario?.cases?.find((row) => row.kind === this.scenarioCaseKind);
    if (!this.token() || !scenario || !scenarioCase) return;
    this.api.addScenarioAssumption(this.token(), scenario.id, scenarioCase.id, {
      driver_type: this.scenarioDriverType,
      driver_label: this.scenarioDriverLabel,
      assumption: this.scenarioAssumption,
      rationale: this.scenarioRationale,
      evidence_label: this.scenarioEvidenceLabel,
      evidence_url: this.scenarioEvidenceUrl
    }).subscribe({
      next: () => {
        this.message.set('Scenario assumption added.');
        this.scenarioAssumption = '';
        this.scenarioRationale = '';
        this.selectScenario(scenario.id);
      },
      error: (response) => this.showError(response)
    });
  }

  addScenarioIndicator(): void {
    const scenario = this.selectedScenario();
    if (!this.token() || !scenario) return;
    this.api.addScenarioIndicator(this.token(), scenario.id, {
      name: this.scenarioIndicatorName,
      driver_type: this.scenarioDriverType,
      target: this.scenarioIndicatorTarget,
      current_value: this.scenarioIndicatorCurrent,
      status: this.scenarioIndicatorStatus
    }).subscribe({
      next: () => {
        this.message.set('Scenario indicator added.');
        this.scenarioIndicatorName = '';
        this.selectScenario(scenario.id);
      },
      error: (response) => this.showError(response)
    });
  }

  addScenarioActual(): void {
    const scenario = this.selectedScenario();
    if (!this.token() || !scenario) return;
    this.api.addScenarioActual(this.token(), scenario.id, {
      result_date: this.scenarioActualDate,
      metric_label: this.scenarioActualMetric,
      actual_value: this.scenarioActualValue,
      comparison_note: this.scenarioActualNote,
      evidence_label: this.scenarioEvidenceLabel,
      evidence_url: this.scenarioEvidenceUrl
    }).subscribe({
      next: () => {
        this.message.set('Actual result comparison added.');
        this.scenarioActualMetric = '';
        this.scenarioActualValue = '';
        this.scenarioActualNote = '';
        this.selectScenario(scenario.id);
      },
      error: (response) => this.showError(response)
    });
  }

  updateScenarioStatus(status: string): void {
    const scenario = this.selectedScenario();
    if (!this.token() || !scenario) return;
    this.api.updateScenario(this.token(), scenario.id, { status, reason: `Scenario marked ${status}.` }).subscribe({
      next: (response) => {
        this.selectedScenario.set(response.scenario_set);
        this.loadScenarios();
      },
      error: (response) => this.showError(response)
    });
  }

  openContradictions(companySlug = '', companyName = ''): void {
    if (!this.token()) return;
    this.activePage.set('contradictions');
    this.menuOpen.set(false);
    if (companySlug) {
      this.contradictionCompanyFilter = companySlug;
      this.contradictionCompanySlug = companySlug;
      this.contradictionCompanyName = companyName;
    }
    this.loadContradictions();
  }

  loadContradictions(): void {
    if (!this.token()) return;
    this.contradictionLoading.set(true);
    this.api.contradictions(this.token(), this.contradictionCompanyFilter, this.contradictionReviewFilter, this.contradictionCategoryFilter).subscribe({
      next: (response) => {
        this.contradictions.set(response);
        if (!this.selectedContradiction() && response.cases.length > 0) this.selectContradiction(response.cases[0].id);
        this.contradictionLoading.set(false);
      },
      error: (response) => { this.contradictionLoading.set(false); this.showError(response); }
    });
  }

  createContradiction(): void {
    if (!this.token()) return;
    this.api.createContradiction(this.token(), {
      title: this.contradictionTitle,
      company_slug: this.contradictionCompanySlug,
      company_name: this.contradictionCompanyName,
      category: this.contradictionCategory,
      conflict_type: this.contradictionConflictType,
      materiality: this.contradictionMateriality,
      neutral_summary: this.contradictionSummary,
      claims: [
        { label: this.contradictionClaimALabel, claim_text: this.contradictionClaimAText, claim_date: this.contradictionClaimADate, source_label: this.contradictionClaimASource },
        { label: this.contradictionClaimBLabel, claim_text: this.contradictionClaimBText, claim_date: this.contradictionClaimBDate, source_label: this.contradictionClaimBSource }
      ]
    }).subscribe({
      next: (response) => {
        this.message.set('Contradiction review case created.');
        this.selectedContradiction.set(response.case);
        this.contradictionTitle = '';
        this.contradictionSummary = '';
        this.contradictionClaimAText = '';
        this.contradictionClaimBText = '';
        this.loadContradictions();
      },
      error: (response) => this.showError(response)
    });
  }

  selectContradiction(id: number): void {
    if (!this.token()) return;
    this.api.contradiction(this.token(), id).subscribe({
      next: (response) => this.selectedContradiction.set(response.case),
      error: (response) => this.showError(response)
    });
  }

  reviewContradiction(): void {
    const selected = this.selectedContradiction();
    if (!this.token() || !selected) return;
    this.api.reviewContradiction(this.token(), selected.id, {
      review_label: this.contradictionReviewLabel,
      conflict_type: this.contradictionConflictType,
      explanation: this.contradictionExplanation,
      correction_path: this.contradictionCorrectionPath,
      is_published: this.contradictionPublish
    }).subscribe({
      next: (response) => {
        this.message.set('Contradiction review saved.');
        this.selectedContradiction.set(response.case);
        this.loadContradictions();
      },
      error: (response) => this.showError(response)
    });
  }

  openStrategyFailures(companySlug = '', companyName = '', sector = ''): void {
    if (!this.token()) return;
    this.activePage.set('strategy-failures');
    this.menuOpen.set(false);
    if (companySlug) {
      this.failureCompanyFilter = companySlug;
      this.failureCompanySlug = companySlug;
      this.failureCompanyName = companyName;
      this.failureSector = sector;
    }
    this.loadStrategyFailures();
  }

  loadStrategyFailures(): void {
    if (!this.token()) return;
    this.strategyFailureLoading.set(true);
    this.api.strategyFailures(this.token(), this.failureCompanyFilter, this.failureCategoryFilter, this.failureClassificationFilter, this.failureStageFilter).subscribe({
      next: (response) => {
        this.strategyFailures.set(response);
        if (!this.selectedStrategyFailure() && response.cases.length > 0) this.selectStrategyFailure(response.cases[0].id);
        this.strategyFailureLoading.set(false);
      },
      error: (response) => { this.strategyFailureLoading.set(false); this.showError(response); }
    });
  }

  createStrategyFailure(): void {
    if (!this.token()) return;
    this.api.createStrategyFailure(this.token(), {
      title: this.failureTitle,
      company_slug: this.failureCompanySlug,
      company_name: this.failureCompanyName,
      sector: this.failureSector,
      category: this.failureCategory,
      classification: this.failureClassification,
      stage: this.failureStage,
      decision_date: this.failureDecisionDate,
      review_start: this.failureReviewStart,
      review_end: this.failureReviewEnd,
      minimum_evidence: this.failureMinimumEvidence,
      elapsed_time_definition: this.failureElapsedTime,
      decision_context: this.failureDecisionContext,
      management_rationale: this.failureManagementRationale,
      original_thesis: this.failureOriginalThesis,
      expected_result: this.failureExpectedResult,
      execution_issue: this.failureExecutionIssue,
      outcome_definition: this.failureOutcomeDefinition,
      actual_outcome: this.failureActualOutcome,
      counterexamples: this.failureCounterexamples,
      lessons: this.failureLessons,
      correction_path: this.failureCorrectionPath,
      evidence: [{ label: this.failureEvidenceLabel, summary: this.failureEvidenceSummary, evidence_date: this.failureEvidenceDate, source_url: this.failureEvidenceUrl }],
      warning_signs: [{ signal: this.failureWarningSignal, why_it_mattered: this.failureWarningWhy, signal_date: this.failureWarningDate }]
    }).subscribe({
      next: (response) => {
        this.message.set('Strategy failure case created.');
        this.selectedStrategyFailure.set(response.case);
        this.failureTitle = '';
        this.failureDecisionContext = '';
        this.failureManagementRationale = '';
        this.failureOriginalThesis = '';
        this.failureExpectedResult = '';
        this.failureExecutionIssue = '';
        this.failureOutcomeDefinition = '';
        this.failureActualOutcome = '';
        this.failureCounterexamples = '';
        this.failureLessons = '';
        this.failureEvidenceLabel = '';
        this.failureEvidenceSummary = '';
        this.failureWarningSignal = '';
        this.failureWarningWhy = '';
        this.loadStrategyFailures();
      },
      error: (response) => this.showError(response)
    });
  }

  selectStrategyFailure(id: number): void {
    if (!this.token()) return;
    this.api.strategyFailure(this.token(), id).subscribe({
      next: (response) => this.selectedStrategyFailure.set(response.case),
      error: (response) => this.showError(response)
    });
  }

  addStrategyFailureEvidence(): void {
    const selected = this.selectedStrategyFailure();
    if (!this.token() || !selected) return;
    this.api.addStrategyFailureEvidence(this.token(), selected.id, {
      label: this.failureEvidenceLabel,
      summary: this.failureEvidenceSummary,
      evidence_date: this.failureEvidenceDate,
      source_url: this.failureEvidenceUrl
    }).subscribe({
      next: () => {
        this.message.set('Failure evidence added.');
        this.failureEvidenceLabel = '';
        this.failureEvidenceSummary = '';
        this.selectStrategyFailure(selected.id);
        this.loadStrategyFailures();
      },
      error: (response) => this.showError(response)
    });
  }

  addStrategyFailureWarning(): void {
    const selected = this.selectedStrategyFailure();
    if (!this.token() || !selected) return;
    this.api.addStrategyFailureWarning(this.token(), selected.id, {
      signal: this.failureWarningSignal,
      why_it_mattered: this.failureWarningWhy,
      signal_date: this.failureWarningDate,
      observable_at_time: true
    }).subscribe({
      next: () => {
        this.message.set('Warning sign added.');
        this.failureWarningSignal = '';
        this.failureWarningWhy = '';
        this.selectStrategyFailure(selected.id);
        this.loadStrategyFailures();
      },
      error: (response) => this.showError(response)
    });
  }

  addStrategyFailureLink(): void {
    const selected = this.selectedStrategyFailure();
    if (!this.token() || !selected) return;
    this.api.addStrategyFailureLink(this.token(), selected.id, {
      feature_type: this.failureLinkType,
      object_label: this.failureLinkLabel,
      relationship_note: this.failureLinkNote
    }).subscribe({
      next: () => {
        this.message.set('Related record linked.');
        this.failureLinkLabel = '';
        this.failureLinkNote = '';
        this.selectStrategyFailure(selected.id);
      },
      error: (response) => this.showError(response)
    });
  }

  reviewStrategyFailure(): void {
    const selected = this.selectedStrategyFailure();
    if (!this.token() || !selected) return;
    this.api.reviewStrategyFailure(this.token(), selected.id, {
      editorial_status: this.failureReviewStatus,
      classification: this.failureClassification,
      note: this.failureReviewNote,
      correction_path: this.failureCorrectionPath,
      is_published: this.failurePublish
    }).subscribe({
      next: (response) => {
        this.message.set('Strategy failure review saved.');
        this.selectedStrategyFailure.set(response.case);
        this.loadStrategyFailures();
      },
      error: (response) => this.showError(response)
    });
  }

  openFoundations(): void {
    if (!this.token()) return;
    this.activePage.set('foundations');
    this.menuOpen.set(false);
    this.loadFoundations();
  }

  loadFoundations(): void {
    if (!this.token()) return;
    this.foundationLoading.set(true);
    this.api.foundationStandards(this.token()).subscribe({
      next: (response) => {
        this.foundationStandards.set(response);
        this.foundationLoading.set(false);
      },
      error: (response) => { this.foundationLoading.set(false); this.showError(response); }
    });
  }

  openLeadershipDecisions(slug: string, asOf = '', roleType = '', decisionType = ''): void {
    if (!slug || !this.token()) return;
    this.activePage.set('leadership-decisions');
    this.menuOpen.set(false);
    this.leadershipDecisionLoading.set(true);
    this.error.set('');
    this.api.leadershipDecisions(
      this.token(),
      slug,
      asOf || this.leadershipDecisionDate,
      roleType || this.leadershipRoleType,
      decisionType || this.leadershipDecisionType
    ).subscribe({
      next: (response) => {
        this.leadershipDecisions.set(response);
        this.leadershipDecisionDate = response.snapshot?.effective_date || '';
        this.leadershipRoleType = response.filters?.selected_role_type || '';
        this.leadershipDecisionType = response.filters?.selected_decision_type || '';
        this.leadershipDecisionLoading.set(false);
      },
      error: (response) => { this.leadershipDecisionLoading.set(false); this.showError(response); }
    });
  }

  reloadLeadershipDecisions(): void {
    const company = this.leadershipDecisions()?.company;
    if (company) this.openLeadershipDecisions(company.slug, this.leadershipDecisionDate, this.leadershipRoleType, this.leadershipDecisionType);
  }

  printLeadershipDecisionBrief(): void {
    window.print();
  }

  promiseLabel(value: string): string {
    return managementPromiseLabel(value);
  }

  kpiBarWidth(value: number, series: { value: number }[]): number {
    const maximum = Math.max(...series.map((row) => Math.abs(row.value)), 1);
    return Math.max(2, Math.round((Math.abs(value) / maximum) * 100));
  }

  private buildKpiMetricGroups(metrics: KpiDefinition[], selectedSlug = ''): KpiMetricGroup[] {
    const grouped = new Map<string, KpiDefinition[]>();
    for (const metric of metrics) {
      const label = this.kpiMetricFamilyLabel(metric.name);
      grouped.set(label, [...(grouped.get(label) || []), metric]);
    }
    return Array.from(grouped.entries())
      .map(([label, variants]) => {
        const sorted = [...variants].sort((a, b) => this.kpiVariantRank(a) - this.kpiVariantRank(b) || a.name.localeCompare(b.name));
        const selectedVariant = sorted.find((metric) => metric.slug === selectedSlug);
        return {
          key: this.kpiMetricFamilyKey(label),
          label,
          variants: sorted,
          selected: Boolean(selectedVariant),
          defaultSlug: selectedVariant?.slug || sorted[0]?.slug || '',
        };
      })
      .sort((a, b) => Number(b.selected) - Number(a.selected) || a.label.localeCompare(b.label));
  }

  trackKpiMetricGroup(_index: number, group: KpiMetricGroup): string {
    return group.key;
  }

  selectedKpiVariant(group: KpiMetricGroup): string {
    const selected = this.selectedKpiVariants[group.key];
    if (selected && group.variants.some((metric) => metric.slug === selected)) {
      return selected;
    }
    return group.defaultSlug;
  }

  managementPromiseStatusBoard(promises: ManagementPromiseResponse['promises']): PromiseBoardLane[] {
    const lanes = [
      { key: 'active', label: 'Active', description: 'Announced, underway, revised, or still too early to judge.', statuses: ['ANNOUNCED', 'IN_PROGRESS', 'REVISED', 'TOO_EARLY'] },
      { key: 'delivered', label: 'Delivered', description: 'Achieved in full or in part against the reviewed rule.', statuses: ['ACHIEVED', 'PARTIALLY_ACHIEVED'] },
      { key: 'at-risk', label: 'At risk', description: 'Delayed, missed, withdrawn, or no longer disclosed.', statuses: ['DELAYED', 'MISSED', 'WITHDRAWN', 'NO_LONGER_DISCLOSED'] },
      { key: 'unverifiable', label: 'Unverifiable', description: 'Evidence is insufficient to classify delivery.', statuses: ['UNVERIFIABLE'] }
    ];
    return lanes.map((lane) => ({ ...lane, promises: promises.filter((promise) => lane.statuses.includes(promise.current_status)) }));
  }

  competitivePeerLanes(peers: CompetitivePositionResponse['peer_map']): CompetitivePeerLane[] {
    const lanes = new Map<string, CompetitivePositionResponse['peer_map']>();
    for (const peer of peers) {
      const label = peer.relationship_label || 'Other relationship';
      lanes.set(label, [...(lanes.get(label) || []), peer]);
    }
    return Array.from(lanes, ([label, lanePeers]) => ({ label, peers: lanePeers }));
  }

  productOfferingFamilies(offerings: ProductPricingResponse['offerings']): ProductOfferingFamily[] {
    const families = new Map<string, ProductPricingResponse['offerings']>();
    for (const offering of offerings) {
      const label = offering.offering_type_label || 'Other offering';
      families.set(label, [...(families.get(label) || []), offering]);
    }
    return Array.from(families, ([label, familyOfferings]) => ({ label, offerings: familyOfferings }));
  }

  dependencyRelationshipLanes(dependencies: CustomerSupplierDependencyResponse['dependencies']): DependencyRelationshipLane[] {
    const lanes = new Map<string, CustomerSupplierDependencyResponse['dependencies']>();
    for (const dependency of dependencies) {
      const key = dependency.dependency_type || 'other';
      lanes.set(key, [...(lanes.get(key) || []), dependency]);
    }
    return Array.from(lanes, ([key, laneDependencies]) => ({
      key,
      label: laneDependencies[0]?.dependency_type_label || this.promiseLabel(key),
      dependencies: laneDependencies,
    }));
  }

  geographicMarketLanes(markets: GeographicExpansionResponse['markets']): GeographicMarketLane[] {
    const lanes = [
      { key: 'current', label: 'Current presence', description: 'Markets currently recorded as active or operating.', statuses: ['ACTIVE', 'OPERATING', 'PRESENT', 'CURRENT'] },
      { key: 'entered', label: 'Entered or expanding', description: 'Markets with a reviewed entry, launch, or scale-up status.', statuses: ['ANNOUNCED', 'ENTERED', 'LAUNCHED', 'EXPANDING', 'SCALE_UP'] },
      { key: 'exited', label: 'Exited or reduced', description: 'Markets recorded as reduced, exited, or discontinued.', statuses: ['REDUCED', 'EXITED', 'DISCONTINUED'] },
    ];
    const classified = new Set<string>();
    const result: GeographicMarketLane[] = lanes.map((lane) => {
      const laneMarkets = markets.filter((market) => lane.statuses.includes(market.current_status));
      laneMarkets.forEach((market) => classified.add(String(market.id)));
      return { key: lane.key, label: lane.label, description: lane.description, markets: laneMarkets };
    });
    const detailLimited = markets.filter((market) => !classified.has(String(market.id)));
    if (detailLimited.length) {
      result.push({ key: 'detail-limited', label: 'Detail limited', description: 'Reviewed presence is available, but the current market status is not classified above.', markets: detailLimited });
    }
    return result.filter((lane) => lane.markets.length > 0);
  }

  acquisitionLifecycleLanes(deals: AcquisitionLifecycleResponse['deals']): AcquisitionLifecycleLane[] {
    const lanes = new Map<string, AcquisitionLifecycleResponse['deals']>();
    for (const deal of deals) {
      const label = deal.current_stage_label || 'Stage unavailable';
      lanes.set(label, [...(lanes.get(label) || []), deal]);
    }
    return Array.from(lanes, ([label, laneDeals]) => ({ label, deals: laneDeals }));
  }

  milestoneInitiativeLanes(milestones: StrategyMilestoneResponse['milestones']): MilestoneInitiativeLane[] {
    const lanes = new Map<string, MilestoneInitiativeLane>();
    for (const milestone of milestones) {
      const anchor = milestone.linked_strategic_turn?.title || milestone.linked_promise?.title;
      const label = anchor || 'No linked initiative';
      const description = milestone.linked_strategic_turn
        ? 'Linked to a reviewed strategic turn.'
        : milestone.linked_promise
          ? 'Linked to a reviewed management promise.'
          : 'No reviewed strategic turn or promise is linked.';
      const lane = lanes.get(label) || { label, description, milestones: [] };
      lane.milestones.push(milestone);
      lanes.set(label, lane);
    }
    return Array.from(lanes.values());
  }

  setSelectedKpiVariant(groupKey: string, slug: string): void {
    this.selectedKpiVariants = { ...this.selectedKpiVariants, [groupKey]: slug };
  }

  private syncSelectedKpiVariant(metric: KpiDefinition | null): void {
    if (!metric) {
      return;
    }
    const key = this.kpiMetricFamilyKey(this.kpiMetricFamilyLabel(metric.name));
    this.setSelectedKpiVariant(key, metric.slug);
  }

  kpiMetricFamilyLabel(name: string): string {
    return name.replace(/\s+\((Annual|Quarterly)\)$/i, '').trim();
  }

  kpiMetricFamilyKey(label: string): string {
    return label.toLowerCase().replace(/[^a-z0-9]+/g, '-');
  }

  kpiVariantLabel(metric: KpiDefinition): string {
    return `${this.promiseLabel(metric.cadence)} · ${this.promiseLabel(metric.value_type)} · ${metric.unit}`;
  }

  private kpiVariantRank(metric: KpiDefinition): number {
    const cadenceRank: Record<string, number> = { QUARTERLY: 1, ANNUAL: 2 };
    const typeRank: Record<string, number> = { REPORTED: 1, CALCULATED: 2 };
    return (cadenceRank[metric.cadence] || 9) * 10 + (typeRank[metric.value_type] || 9);
  }

  private buildKpiEventGroups(events: DashboardEvent[]): KpiEventGroup[] {
    const grouped = new Map<string, DashboardEvent[]>();
    for (const event of events) {
      const key = event.event_type || 'OTHER';
      grouped.set(key, [...(grouped.get(key) || []), event]);
    }
    return Array.from(grouped.entries())
      .map(([type, rows]) => {
        const sorted = [...rows].sort((a, b) => this.dateSortValue(b.event_date) - this.dateSortValue(a.event_date));
        return {
          type,
          label: this.promiseLabel(type),
          count: sorted.length,
          latestDate: sorted[0]?.event_date || 'Date unavailable',
          events: sorted.slice(0, 3),
          hiddenCount: Math.max(0, sorted.length - 3),
        };
      })
      .sort((a, b) => this.dateSortValue(b.latestDate) - this.dateSortValue(a.latestDate) || a.label.localeCompare(b.label));
  }

  trackKpiEventGroup(_index: number, group: KpiEventGroup): string {
    return group.type;
  }

  private buildKpiBlockerReasons(peers: BlockedKpiPeer[]): KpiBlockerReason[] {
    const counts = new Map<string, number>();
    for (const peer of peers) {
      for (const reason of this.kpiPeerReasonParts(peer.reason)) {
        counts.set(reason, (counts.get(reason) || 0) + 1);
      }
    }
    return Array.from(counts.entries())
      .map(([label, count]) => ({ key: this.kpiMetricFamilyKey(label), label, count }))
      .sort((a, b) => b.count - a.count || a.label.localeCompare(b.label));
  }

  private buildKpiBlockedPeerGroups(peers: BlockedKpiPeer[]): KpiPeerBlockerGroup[] {
    const grouped = new Map<string, BlockedKpiPeer[]>();
    for (const peer of peers) {
      grouped.set(peer.company_slug || peer.company, [...(grouped.get(peer.company_slug || peer.company) || []), peer]);
    }
    return Array.from(grouped.values())
      .map((rows) => {
        const reasons = this.buildKpiBlockerReasons(rows).slice(0, 4);
        const examples = rows
          .slice()
          .sort((a, b) => a.metric.localeCompare(b.metric))
          .slice(0, 5);
        return {
          company: rows[0]?.company || 'Peer company',
          companySlug: rows[0]?.company_slug || rows[0]?.company || '',
          total: rows.length,
          reasons,
          examples,
          hiddenCount: Math.max(0, rows.length - examples.length),
        };
      })
      .sort((a, b) => b.total - a.total || a.company.localeCompare(b.company));
  }

  kpiPeerReasonParts(reason: string): string[] {
    return reason
      .split(';')
      .map((part) => part.trim())
      .filter(Boolean);
  }

  trackKpiBlockerReason(_index: number, reason: KpiBlockerReason): string {
    return reason.key;
  }

  trackKpiPeerBlockerGroup(_index: number, group: KpiPeerBlockerGroup): string {
    return group.companySlug || group.company;
  }

  kpiEventSummary(event: DashboardEvent): string {
    const summary = event.actual_change || event.source_claim || 'Event summary unavailable.';
    return this.stripCompanyPrefix(summary, event.company);
  }

  private stripCompanyPrefix(summary: string, company = ''): string {
    const candidates = [company, company.split(/\s+/).find((part) => part.toLowerCase() !== 'the') || '']
      .filter((value, index, values) => value && values.indexOf(value) === index)
      .map((value) => this.escapeRegExp(value));
    if (candidates.length === 0) {
      return summary;
    }
    const prefix = new RegExp(`^(${candidates.join('|')})(?:'s|’s)?\\s+`, 'i');
    const cleaned = summary.replace(prefix, '');
    return cleaned ? cleaned.charAt(0).toUpperCase() + cleaned.slice(1) : summary;
  }

  private escapeRegExp(value: string): string {
    return value.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
  }

  private dateSortValue(value: string | null): number {
    if (!value || value === 'Date unavailable') {
      return 0;
    }
    const timestamp = Date.parse(value);
    return Number.isNaN(timestamp) ? 0 : timestamp;
  }

  businessModelComponentLabel(type: string): string {
    return businessModelComponentLabel(type);
  }

  businessModelRelationshipLabel(type: string): string {
    return businessModelRelationshipLabel(type);
  }

  buildValueFlowGraph(relationships: BusinessModelRelationship[]): ValueFlowGraph {
    const nodes = this.buildValueFlowNodes(relationships);
    return {
      nodes,
      edges: this.buildValueFlowEdges(relationships, nodes)
    };
  }

  businessModelFlowNodes(relationships: BusinessModelRelationship[]): ValueFlowNode[] {
    return this.buildValueFlowNodes(relationships);
  }

  businessModelFlowEdges(relationships: BusinessModelRelationship[]): ValueFlowEdge[] {
    return this.buildValueFlowEdges(relationships, this.buildValueFlowNodes(relationships));
  }

  private buildValueFlowNodes(relationships: BusinessModelRelationship[]): ValueFlowNode[] {
    const names = new Map<string, string>();
    for (const relationship of relationships) {
      this.addValueFlowName(names, relationship.from_name);
      this.addValueFlowName(names, relationship.to_name);
    }
    const entries = Array.from(names.entries());
    const total = entries.length;
    if (total === 0) {
      return [];
    }
    if (total === 1) {
      const [key, name] = entries[0];
      const override = this.valueFlowNodeOverrides()[key];
      return [{ key, name, x: override?.x ?? 50, y: override?.y ?? 50 }];
    }
    return entries.map(([key, name], index) => {
      const layout = this.valueFlowNodePosition(index, total);
      const override = this.valueFlowNodeOverrides()[key];
      return {
        key,
        name,
        x: override?.x ?? layout.x,
        y: override?.y ?? layout.y
      };
    });
  }

  private buildValueFlowEdges(relationships: BusinessModelRelationship[], nodes: ValueFlowNode[]): ValueFlowEdge[] {
    const nodeMap = new Map(nodes.map((node) => [node.key, node]));
    return relationships
      .map((relationship, index) => {
        const from = nodeMap.get(this.valueFlowKey(relationship.from_name));
        const to = nodeMap.get(this.valueFlowKey(relationship.to_name));
        if (!from || !to) {
          return null;
        }
        return {
          key: `${relationship.id}-${index}`,
          from,
          to,
          label: this.businessModelRelationshipLabel(relationship.relationship_type),
          x: Math.round(((from.x + to.x) / 2) * 10) / 10,
          y: Math.round(((from.y + to.y) / 2) * 10) / 10
        };
      })
      .filter((edge): edge is ValueFlowEdge => Boolean(edge));
  }

  focusValueFlowEdge(edgeKey: string): void {
    this.valueFlowFocus.set({ type: 'edge', key: edgeKey });
  }

  focusValueFlowNode(nodeKey: string): void {
    this.valueFlowFocus.set({ type: 'node', key: nodeKey });
  }

  clearValueFlowFocus(): void {
    this.valueFlowFocus.set(null);
  }

  focusedValueFlowEdge(): ValueFlowEdge | null {
    const focus = this.valueFlowFocus();
    return focus?.type === 'edge' ? this.valueFlowGraph().edges.find((edge) => edge.key === focus.key) || null : null;
  }

  focusedValueFlowNode(): { name: string; connections: string[] } | null {
    const focus = this.valueFlowFocus();
    if (focus?.type !== 'node') {
      return null;
    }
    const node = this.valueFlowGraph().nodes.find((item) => item.key === focus.key);
    if (!node) {
      return null;
    }
    const connections = [...new Set(this.valueFlowGraph().edges.flatMap((edge) => {
      if (edge.from.key === node.key) return [edge.to.name];
      if (edge.to.key === node.key) return [edge.from.name];
      return [];
    }))];
    return { name: node.name, connections };
  }

  isValueFlowEdgeDimmed(edge: ValueFlowEdge): boolean {
    const focus = this.valueFlowFocus();
    if (!focus) {
      return false;
    }
    if (focus.type === 'edge') {
      return focus.key !== edge.key;
    }
    return edge.from.key !== focus.key && edge.to.key !== focus.key;
  }

  isValueFlowNodeDimmed(node: ValueFlowNode): boolean {
    const focus = this.valueFlowFocus();
    if (!focus) {
      return false;
    }
    if (focus.type === 'node') {
      return focus.key !== node.key && !this.valueFlowGraph().edges.some((edge) => (
        (edge.from.key === focus.key && edge.to.key === node.key) ||
        (edge.to.key === focus.key && edge.from.key === node.key)
      ));
    }
    const activeEdge = this.valueFlowGraph().edges.find((edge) => edge.key === focus.key);
    return !activeEdge || (activeEdge.from.key !== node.key && activeEdge.to.key !== node.key);
  }

  startValueFlowNodeDrag(event: MouseEvent, node: ValueFlowNode): void {
    const space = (event.currentTarget as HTMLElement).closest('.value-flow-space');
    if (!space) {
      return;
    }
    event.preventDefault();
    this.valueFlowDrag = { nodeKey: node.key, space: space.getBoundingClientRect() };
    this.moveValueFlowNode(event);
  }

  @HostListener('document:mousemove', ['$event'])
  moveValueFlowNode(event: MouseEvent): void {
    if (!this.valueFlowDrag) {
      return;
    }
    event.preventDefault();
    const { nodeKey, space } = this.valueFlowDrag;
    const x = this.clampValueFlowPosition(((event.clientX - space.left) / space.width) * 100);
    const y = this.clampValueFlowPosition(((event.clientY - space.top) / space.height) * 100);
    this.valueFlowNodeOverrides.set({
      ...this.valueFlowNodeOverrides(),
      [nodeKey]: { x, y }
    });
    this.valueFlowGraph.update((graph) => {
      const nodes = graph.nodes.map((node) => node.key === nodeKey ? { ...node, x, y } : node);
      const nodeMap = new Map(nodes.map((node) => [node.key, node]));
      const edges = graph.edges.map((edge) => {
        const from = nodeMap.get(edge.from.key) || edge.from;
        const to = nodeMap.get(edge.to.key) || edge.to;
        return {
          ...edge,
          from,
          to,
          x: Math.round(((from.x + to.x) / 2) * 10) / 10,
          y: Math.round(((from.y + to.y) / 2) * 10) / 10
        };
      });
      return { nodes, edges };
    });
  }

  @HostListener('document:mouseup')
  stopValueFlowNodeDrag(): void {
    this.valueFlowDrag = null;
  }

  profileSectionLabel(key: string): string {
    return companyProfileSectionLabel(key);
  }

  profileItemLabel(item: unknown): string {
    return companyProfileItemLabel(item);
  }

  openSourceLens(title: string, sources: CompanyProfileSource[]): void {
    this.sourceLens.set({ title, sources: deduplicateSourceLensRecords(sources) });
  }

  openEarningsSourceLens(documents: { source: CompanyProfileSource }[]): void {
    this.openSourceLens('Period evidence', documents.map((document) => document.source));
  }

  closeSourceLens(): void {
    this.sourceLens.set(null);
  }

  sourceLensWhyUsed(source: CompanyProfileSource): string {
    return sourceLensWhyUsed(source);
  }

  @HostListener('document:keydown.escape')
  closeSourceLensOnEscape(): void {
    if (this.sourceLens()) this.closeSourceLens();
  }

  dossierEntries(company: CompanyProfileResponse, sectionKeys: string[]): { key: string; label: string; text: string; items: string[] }[] {
    return sectionKeys
      .map((key) => {
        const section = company.sections[key];
        return {
          key,
          label: this.profileSectionLabel(key),
          text: section?.text || '',
          items: (section?.items || []).map((item) => this.profileItemLabel(item))
        };
      })
      .filter((entry) => entry.text || entry.items.length > 0);
  }

  dossierChips(company: CompanyProfileResponse, sectionKeys: string[]): string[] {
    return [...new Set(
      sectionKeys.flatMap((key) => (company.sections[key]?.items || []).map((item) => this.profileItemLabel(item)))
    )].slice(0, 8);
  }

  sourceFreshness(company: CompanyProfileResponse): string {
    const datedSource = company.evidence
      .filter((source) => source.published_date || source.updated_at)
      .sort((left, right) => String(right.published_date || right.updated_at).localeCompare(String(left.published_date || left.updated_at)))[0];
    if (!datedSource) {
      return 'No dated source available';
    }
    return datedSource.published_date ? `Latest source: ${datedSource.published_date}` : `Latest source update: ${datedSource.updated_at}`;
  }

  financialBriefFacts(company: CompanyProfileResponse): CompanyProfileResponse['highlights']['financial_facts'] {
    const seen = new Set<string>();
    return company.highlights.financial_facts.filter((fact) => {
      const key = `${fact.label || fact.concept}|${fact.fy}|${fact.fp}`;
      if (seen.has(key)) return false;
      seen.add(key);
      return true;
    }).slice(0, 4);
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

  private addValueFlowName(names: Map<string, string>, name: string): void {
    const normalized = this.valueFlowKey(name);
    if (normalized && !names.has(normalized)) {
      names.set(normalized, name);
    }
  }

  private valueFlowKey(name: string): string {
    return String(name || '').trim().replace(/\s+/g, ' ').toLowerCase();
  }

  private valueFlowNodePosition(index: number, total: number): { x: number; y: number } {
    if (total <= 8) {
      return this.valueFlowRingPosition(index, total, 40, 36, 0);
    }
    const outerCount = Math.ceil(total * 0.62);
    if (index < outerCount) {
      return this.valueFlowRingPosition(index, outerCount, 43, 38, 0);
    }
    return this.valueFlowRingPosition(index - outerCount, total - outerCount, 24, 22, Math.PI / Math.max(total - outerCount, 1));
  }

  private valueFlowRingPosition(index: number, total: number, radiusX: number, radiusY: number, offset: number): { x: number; y: number } {
    const angle = -Math.PI / 2 + offset + (index * 2 * Math.PI) / Math.max(total, 1);
    return {
      x: Math.round((50 + Math.cos(angle) * radiusX) * 10) / 10,
      y: Math.round((50 + Math.sin(angle) * radiusY) * 10) / 10
    };
  }

  private clampValueFlowPosition(value: number): number {
    return Math.round(Math.max(4, Math.min(96, value)) * 10) / 10;
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
