import { HttpClient, HttpHeaders } from '@angular/common/http';
import { Injectable, inject } from '@angular/core';

import { environment } from '../../environments/environment';
import { dashboardRequestParams } from '../company-profile.utils';

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

export type SourceGap = {
  key: string;
  label?: string;
  dashboard?: string;
  reason: string;
  source: string;
  next_action: string;
  resolution_candidates?: {
    candidate_type: string;
    evidence_text: string;
    confidence_score: number;
    extraction_status: string;
    review_status: string;
    next_action: string;
    source: {
      id: number;
      source_api: string;
      title: string;
      publisher: string;
      url: string;
      published_date: string | null;
    };
  }[];
};

export type DashboardEvent = SearchEventResult & {
  signal?: string;
  calculation_method?: string;
  confidence_score?: number;
};

export type DashboardTurn = SearchTurnResult & {
  company?: string;
  company_slug?: string;
  confidence_score?: number;
  score_status?: string;
  score_reason?: string;
  market_reaction?: MarketImpactWindow[];
  financial_facts?: FinancialFactSummary[];
};

export type PatternSummary = {
  pattern: string;
  sample_size: number;
  avg_confidence: number;
  confidence_status: string;
  examples: DashboardTurn[];
};

export type SourceConfidenceSummary = {
  events: {
    total: number;
    with_date: number;
    with_source: number;
    avg_confidence: number;
  };
  turns: {
    total: number;
    published: number;
    avg_confidence: number;
  };
  source_types: { source_api: string; count: number }[];
  source_statuses: { status: string; count: number }[];
  event_reviews: { review_status: string; count: number }[];
  market_prices?: {
    total: number;
    companies: number;
    latest_price_date: string | null;
  };
  financial_facts?: {
    total: number;
    companies: number;
    latest_filed: string | null;
  };
};

export type CompanySituation = DashboardCompany & {
  match_dimensions: string[];
  peer_source?: string;
  relationship_type?: string;
  evidence_text?: string;
  is_in_universe?: boolean;
};

export type CompareExample = {
  turn_type: string;
  sample_size: number;
  company_count: number;
  turns: DashboardTurn[];
};

export type MarketImpactWindow = {
  window: string;
  days: number;
  price_date: string;
  close_price: number;
  return_pct: number | null;
};

export type FinancialFactSummary = {
  id: number;
  concept: string;
  label: string;
  unit: string;
  fy: number | null;
  fp: string;
  filed: string | null;
  frame: string;
  value: number;
};

export type MarketImpact = {
  event: DashboardEvent;
  company: string;
  company_slug: string;
  ticker: string;
  event_date: string;
  base_price: {
    price_date: string;
    close_price: number;
    provider: string;
  };
  windows: MarketImpactWindow[];
  financial_facts: FinancialFactSummary[];
  quality: {
    eligible: boolean;
    status: string;
    reasons: string[];
  };
};

export type DashboardSection<T> = {
  key: string;
  status: 'available' | 'unavailable';
  eligible_count: number;
  raw_count: number;
  excluded_count: number;
  page: number;
  page_size: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
  items: T[];
  source_gaps: SourceGap[];
  required_data: string[];
  next_action: string;
};

export type DashboardSections = {
  latest_moves?: DashboardSection<DashboardEvent>;
  strategic_turns?: DashboardSection<DashboardTurn>;
  patterns?: DashboardSection<PatternSummary>;
  risk_signals?: DashboardSection<DashboardEvent>;
  turn_impact?: DashboardSection<MarketImpact>;
  scorecards?: DashboardSection<DashboardTurn>;
  compare?: DashboardSection<CompareExample>;
  company_situations?: DashboardSection<CompanySituation>;
};

export type DashboardData = {
  scope: {
    company: string;
    company_slug: string;
    sector: string;
    country: string;
  } | null;
  latest_events: DashboardEvent[];
  latest_turns: DashboardTurn[];
  patterns: PatternSummary[];
  risk_signals: DashboardEvent[];
  turn_impact: MarketImpact[];
  source_confidence: SourceConfidenceSummary;
  scorecard_candidates: DashboardTurn[];
  company_situations: CompanySituation[];
  compare_examples: CompareExample[];
  source_gaps: { key: string; reason: string; source: string; next_action: string }[];
  sections: DashboardSections;
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
    dashboard_data_error: string;
  };
  source_gaps: SourceGap[];
  dashboards: DashboardData;
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
  pagination: {
    companies: PaginationMeta;
    events: PaginationMeta;
    strategic_turns: PaginationMeta;
  };
};

export type PaginationMeta = {
  page: number;
  page_size: number;
  total: number;
  total_pages: number;
  has_next: boolean;
  has_previous: boolean;
};

export type SearchSuggestion = {
  type: string;
  label: string;
  slug: string;
  sector: string;
  description: string;
};

export type CompanyProfileSection = {
  status: 'available' | 'unavailable';
  items: unknown[];
  text: string;
  source: 'company_profile' | 'business_model_map';
};

export type CompanyProfileSource = {
  id: number;
  source_api: string;
  title: string;
  publisher: string;
  url: string;
  published_date: string | null;
  snippet: string;
  status: string;
  updated_at: string;
};

export type CompanyProfileResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: DashboardCompany & {
    aliases: string[];
    website: string;
    founded_date: string | null;
    description: string;
    is_active: boolean;
  };
  profile: {
    id: number;
    effective_date: string;
    status: string;
    confidence_score: number;
    evidence_text: string;
    source_id: number | null;
  } | null;
  snapshot_history: {
    id: number;
    effective_date: string;
    status: string;
    confidence_score: number;
    selected: boolean;
  }[];
  sections: Record<string, CompanyProfileSection>;
  highlights: {
    latest_events: DashboardEvent[];
    latest_turns: DashboardTurn[];
    financial_facts: FinancialFactSummary[];
  };
  changes: {
    section: string;
    previous_effective_date: string;
    current_effective_date: string;
    previous: unknown;
    current: unknown;
  }[];
  conflicts: {
    snapshot_id: number;
    effective_date: string;
    differing_sections: string[];
    source_id: number | null;
    status: string;
  }[];
  evidence: CompanyProfileSource[];
  coverage: {
    completeness_percent: number;
    available_sections: number;
    total_sections: number;
    source_count: number;
    snapshot_count: number;
    last_updated: string | null;
  };
  source_gaps: SourceGap[];
};

export type BusinessModelComponent = {
  id: number;
  component_type: string;
  component_type_label: string;
  name: string;
  description: string;
  scope: string;
  evidence_text: string;
  is_inferred: boolean;
  confidence_score: number;
};

export type BusinessModelRelationship = {
  id: number;
  from_component_id: number;
  from_name: string;
  to_component_id: number;
  to_name: string;
  relationship_type: string;
  description: string;
  evidence_text: string;
  is_inferred: boolean;
  confidence_score: number;
};

export type BusinessModelSnapshot = {
  id: number;
  effective_date: string;
  status: string;
  summary: string;
  confidence_score: number;
  source_id: number | null;
  components: BusinessModelComponent[];
  component_groups: Record<string, BusinessModelComponent[]>;
  relationships: BusinessModelRelationship[];
};

export type BusinessModelResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: BusinessModelSnapshot | null;
  snapshot_history: {
    id: number;
    effective_date: string;
    status: string;
    summary: string;
    confidence_score: number;
    component_count: number;
    relationship_count: number;
    selected: boolean;
  }[];
  comparison_snapshot: BusinessModelSnapshot | null;
  peer_models: {
    company: string;
    company_slug: string;
    effective_date: string;
    summary: string;
    component_count: number;
    shared_components: { component_type: string; name: string }[];
    shared_component_type_count: number;
    component_type_overlap_percent: number;
    compatibility_status: 'comparable' | 'partial' | 'incompatible';
    compatibility_label: string;
    comparison_warning: string;
    comparison_basis: string;
    confidence_score: number;
  }[];
  related_surfaces: {
    key: string;
    label: string;
    status: 'available' | 'unavailable';
    destination: string;
  }[];
  changes: {
    from_date: string | null;
    to_date: string | null;
    components_added: { component_type: string; name: string }[];
    components_removed: { component_type: string; name: string }[];
    relationships_added: { from_name: string; relationship_type: string; to_name: string }[];
    relationships_removed: { from_name: string; relationship_type: string; to_name: string }[];
  };
  coverage: {
    completeness_percent: number;
    component_count: number;
    relationship_count: number;
    required_component_types: number;
    available_component_types: number;
    last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type KpiDefinition = {
  id: number; slug: string; name: string; description: string; unit: string; cadence: string;
  value_type: string; scope: string; aliases: string[]; formula: string; peer_comparable: boolean;
  definition_history: { effective_date: string; definition: string; scope: string; change_note: string; source_id: number | null }[];
  targets: { target_date: string; target_value: number; condition: string; status: string }[];
};

export type KpiObservation = {
  id: number; period_start: string; period_end: string; fiscal_year: number | null; fiscal_period: string;
  value: number; segment: string; geography: string; evidence_text: string; source_id: number | null;
  is_estimated: boolean; is_restatement: boolean; is_non_comparable: boolean; definition_changed: boolean;
  confidence_score: number;
};

export type OperatingKpiResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  dictionary: KpiDefinition[];
  selected_metric: KpiDefinition | null;
  series: KpiObservation[];
  missing_periods: string[];
  filters: { segments: string[]; geographies: string[]; selected_segment: string; selected_geography: string; selected_start: string; selected_end: string; comparable_only: boolean };
  alerts: { period_end: string | null; type: string; change_percent: number | null; message: string }[];
  event_overlays: DashboardEvent[];
  peer_comparisons: { company: string; company_slug: string; metric: string; unit: string; comparable: boolean }[];
  export_rows: Record<string, unknown>[];
  coverage: { metric_count: number; observation_count: number; reported_count: number; calculated_count: number; last_period: string | null };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type ManagementPromiseUpdate = {
  id: number; update_date: string; status: string; summary: string;
  previous_target_end_date: string | null; revised_target_end_date: string | null;
  evidence_text: string; is_contradiction_candidate: boolean; contradiction_note: string;
  confidence_score: number; review_status: string;
  source: CompanyProfileSource | null;
};

export type ManagementPromise = {
  id: number; slug: string; title: string; promise_type: string; original_statement: string;
  speaker: string; speaker_role: string; statement_date: string; target_start_date: string | null;
  target_end_date: string | null; metric_name: string; baseline_value: number | null;
  target_value: number | null; unit: string; scope: string; conditions: string;
  evaluation_rule: string; current_status: string; confidence_score: number; review_status: string;
  evidence_text: string; source: CompanyProfileSource | null;
  linked_kpi: { slug: string; name: string } | null;
  linked_strategic_turn: { id: number; title: string } | null;
  updates: ManagementPromiseUpdate[];
};

export type ManagementPromiseResponse = {
  status: 'available' | 'unavailable';
  company: CompanyProfileResponse['company'];
  promises: ManagementPromise[];
  selected_promise: ManagementPromise | null;
  filters: { statuses: string[]; types: string[]; selected_status: string; selected_type: string; selected_due: string; selected_as_of: string };
  coverage: { promise_count: number; due_soon_count: number; overdue_count: number; source_count: number; last_updated: string };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type StrategyMilestoneStatusUpdate = {
  status_date: string; status: string; summary: string; blocker: string; evidence_text: string;
  confidence_score: number; source: CompanyProfileSource;
};

export type StrategyMilestone = {
  id: number; slug: string; title: string; milestone_type: string; origin: string; current_status: string;
  expected_start_date: string | null; expected_end_date: string | null; date_precision: string; owner: string;
  success_condition: string; blocker: string; outcome_review: string; evidence_text: string;
  confidence_score: number; review_status: string; source: CompanyProfileSource;
  linked_promise: { slug: string; title: string } | null;
  linked_kpi: { slug: string; name: string } | null;
  linked_strategic_turn: { id: number; title: string } | null;
  related_entities: { type: string; label: string; id?: string }[];
  dependencies: { slug: string; title: string; relationship: string; description: string }[];
  status_history: StrategyMilestoneStatusUpdate[];
};

export type StrategyMilestoneResponse = {
  status: 'available' | 'unavailable';
  company: CompanyProfileResponse['company'];
  milestones: StrategyMilestone[];
  selected_milestone: StrategyMilestone | null;
  filters: {
    statuses: string[]; types: string[]; origins: string[]; selected_status: string;
    selected_type: string; selected_origin: string; selected_view: string;
  };
  coverage: {
    milestone_count: number; upcoming_count: number; overdue_count: number;
    completed_count: number; unknown_date_count: number; source_count: number;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type EarningsMetric = {
  concept: string; label: string; unit: string; value: number; previous_value: number | null;
  change_pct: number | null; comparison_status: 'available' | 'unavailable'; source: string;
};

export type EarningsGuidanceComparison = {
  metric_name: string; forecast_value: number; actual_value: number; variance_pct: number | null;
  unit: string; comparison_status: string; forecast_evidence: string; actual_evidence: string;
  confidence_score: number; forecast_source: CompanyProfileSource; actual_source: CompanyProfileSource;
};

export type EarningsPeriodSummary = {
  id: number; key: string; accession_number: string; fiscal_year: number; fiscal_period: string;
  period_start: string | null; period_end: string; filed_date: string; headline: string;
  confidence_score: number; source: CompanyProfileSource;
};

export type EarningsResponse = {
  status: 'available' | 'unavailable';
  company: CompanyProfileResponse['company'];
  periods: EarningsPeriodSummary[];
  selected_period: (EarningsPeriodSummary & {
    previous_period: EarningsPeriodSummary | null;
    measured_results: EarningsMetric[];
    operating_kpis: { slug: string; name: string; unit: string; period_end: string; value: number; previous_value: number | null; change_pct: number | null; quality_flags: string[] }[];
    management_explanation: string | null;
    infodj_interpretation: string | null;
    unanswered_questions: string[];
    disclosure_changes: { added: { concept: string; unit: string; label: string }[]; removed: { concept: string; unit: string; label: string }[] };
    guidance_comparison: {
      status: 'available' | 'unavailable'; items: EarningsGuidanceComparison[];
      linked_promises: ManagementPromise[]; reason: string;
    };
    promises: ManagementPromise[];
    strategic_turns: DashboardTurn[];
    risk_signals: DashboardEvent[];
    document_set: { document_type: string; source: CompanyProfileSource }[];
    export_rows: EarningsMetric[];
  }) | null;
  source_gaps: SourceGap[];
};

export type CapitalAllocationItem = {
  id: number;
  category: string;
  category_label: string;
  label: string;
  value: number | null;
  unit: string;
  concept: string;
  evidence_text: string;
  is_context: boolean;
  is_calculated: boolean;
  calculation_method: string;
  confidence_score: number;
  share_of_total_deployment: number | null;
  share_of_operating_cash_flow: number | null;
  source: CompanyProfileSource | null;
  source_fact: { id: number; concept: string; label: string; accession_number: string } | null;
};

export type CapitalAllocationPeriod = {
  id: number;
  key: string;
  fiscal_year: number;
  fiscal_period: string;
  period_start: string | null;
  period_end: string;
  filed_date: string | null;
  accession_number: string;
  cadence: string;
  headline: string;
  total_deployment: number | null;
  operating_cash_flow: number | null;
  cash_balance: number | null;
  free_cash_flow: number | null;
  calculation_note: string;
  review_status: string;
};

export type CapitalAllocationResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  periods: CapitalAllocationPeriod[];
  selected_period: (CapitalAllocationPeriod & {
    deployment_items: CapitalAllocationItem[];
    context_items: CapitalAllocationItem[];
    category_totals: {
      category: string; category_label: string; value: number; item_count: number; share_of_total_deployment: number | null;
    }[];
    allocation_mix: {
      category: string; category_label: string; value: number; share_of_total_deployment: number | null;
    }[];
    cash_flow_context: {
      operating_cash_flow: number | null;
      cash_balance: number | null;
      free_cash_flow: number | null;
      total_deployment: number | null;
      deployment_to_operating_cash_flow_pct: number | null;
      deployment_to_cash_balance_pct: number | null;
    };
    related_strategy: {
      strategic_turns: DashboardTurn[];
      management_promises: ManagementPromise[];
    };
  }) | null;
  filters: { selected_period: string; categories: string[] };
  coverage: {
    period_count: number;
    deployment_item_count: number;
    context_item_count: number;
    missing_category_count: number;
    last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type CompetitivePeer = {
  id: number;
  peer_name: string;
  peer_company: DashboardCompany | null;
  relationship_type: string;
  relationship_label: string;
  scope: string;
  geography: string;
  product_overlap: string[];
  customer_overlap: string[];
  evidence_text: string;
  is_in_universe: boolean;
  confidence_score: number;
};

export type CompetitiveDimension = {
  id: number;
  dimension_type: string;
  dimension_label: string;
  label: string;
  description: string;
  evidence_text: string;
  peer_id: number | null;
  peer_name: string;
  confidence_score: number;
  source: CompanyProfileSource | null;
};

export type CompetitivePositionResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number;
    effective_date: string;
    status: string;
    summary: string;
    methodology: string;
    confidence_score: number;
    source: CompanyProfileSource | null;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; confidence_score: number; peer_count: number; selected: boolean }[];
  peer_map: CompetitivePeer[];
  comparison: Record<string, CompetitiveDimension[]>;
  competitive_actions: DashboardEvent[];
  market_share: { status: 'available' | 'unavailable'; series: unknown[]; reason: string };
  moat_evidence: CompetitiveDimension[];
  opposing_evidence: CompetitiveDimension[];
  filters: { relationships: string[]; selected_relationship: string; as_of: string };
  coverage: {
    peer_count: number;
    in_universe_peer_count: number;
    dimension_count: number;
    competitive_action_count: number;
    source_count: number;
    last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type ProductOffering = {
  id: number; parent_id: number | null; offering_type: string; offering_type_label: string;
  name: string; description: string; availability: string; geography: string; customer_segment: string;
  evidence_text: string; confidence_score: number; price_count: number;
};

export type ProductChange = {
  id: number; offering_id: number | null; offering_name: string; change_type: string; change_type_label: string;
  title: string; announcement_date: string | null; effective_date: string | null; before_state: string; after_state: string;
  evidence_text: string; confidence_score: number; source: CompanyProfileSource | null; linked_event: DashboardEvent | null;
};

export type PriceObservation = {
  id: number; offering_id: number; offering_name: string; observed_date: string; effective_date: string | null;
  amount: number; currency: string; billing_period: string; geography: string; customer_segment: string;
  tax_treatment: string; is_promotional: boolean; evidence_text: string; confidence_score: number; source: CompanyProfileSource | null;
};

export type ProductPricingResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; chronology_note: string;
    confidence_score: number; source: CompanyProfileSource | null;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; confidence_score: number; offering_count: number; change_count: number; selected: boolean }[];
  offerings: ProductOffering[];
  changes: ProductChange[];
  price_observations: PriceObservation[];
  price_context: { status: 'available' | 'unavailable'; reason: string; promotion_policy: string };
  comparison: { change_id: number; title: string; change_type: string; announcement_date: string | null; effective_date: string | null; before: string; after: string }[];
  filters: { types: string[]; selected_type: string; as_of: string };
  coverage: { offering_count: number; change_count: number; price_observation_count: number; source_count: number; last_updated: string };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type AcquisitionLifecycleEvent = {
  id: number; stage: string; stage_label: string; event_date: string | null; title: string; description: string;
  price_revision: number | null; currency: string; evidence_text: string; confidence_score: number; review_status: string;
  source: CompanyProfileSource | null;
  linked_milestone: { id: number; slug: string; title: string; current_status: string } | null;
  linked_product_change: { id: number; title: string; change_type: string } | null;
};

export type AcquisitionLifecycleDeal = {
  id: number; slug: string; target_name: string; target_company: DashboardCompany | null;
  transaction_type: string; transaction_type_label: string; current_stage: string; current_stage_label: string;
  outcome_category: string; outcome_category_label: string; announcement_date: string | null; expected_close_date: string | null;
  close_date: string | null; purchase_price: number | null; currency: string; payment_form: string; approvals: string[];
  conditions: string[]; management_rationale: string; promised_synergies: string; integration_summary: string;
  outcome_review: string; confidence_score: number; review_status: string; source: CompanyProfileSource | null;
  linked_event: DashboardEvent | null; linked_strategic_turn: { id: number; title: string; turn_type: string } | null;
  updated_at: string; stage_event_count: number; stage_events?: AcquisitionLifecycleEvent[];
};

export type AcquisitionLifecycleResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  deals: AcquisitionLifecycleDeal[];
  selected_deal: AcquisitionLifecycleDeal | null;
  portfolio?: {
    by_stage: { key: string; label: string; count: number }[];
    by_outcome: { key: string; label: string; count: number }[];
    by_transaction_type: { key: string; label: string; count: number }[];
  };
  filters: {
    stages: string[]; transaction_types: string[]; outcomes: string[];
    selected_stage: string; selected_transaction_type: string; selected_outcome: string; selected_deal: string;
  };
  coverage: { deal_count: number; stage_event_count: number; deal_term_count: number; source_count: number; last_updated: string | null };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type CustomerSupplierDependency = {
  id: number; dependency_type: string; dependency_type_label: string; counterparty_name: string;
  counterparty_company: DashboardCompany | null; is_named_counterparty: boolean;
  materiality_band: string; materiality_band_label: string; disclosure_confidence: string; disclosure_confidence_label: string;
  concentration_percent: number | null; geography: string; product_scope: string; relationship_summary: string; risk_summary: string;
  evidence_text: string; confidence_score: number; source: CompanyProfileSource | null; contract_term_count: number;
};

export type DependencyContractTerm = {
  id: number; dependency_id: number; counterparty_name: string; term_type: string; term_type_label: string;
  effective_date: string | null; expiration_date: string | null; description: string; evidence_text: string;
  confidence_score: number; review_status: string; source: CompanyProfileSource | null;
};

export type CustomerSupplierDependencyResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; methodology: string;
    confidence_score: number; source: CompanyProfileSource | null;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; confidence_score: number; dependency_count: number; selected: boolean }[];
  dependencies: CustomerSupplierDependency[];
  map: Record<string, CustomerSupplierDependency[]>;
  contract_terms: DependencyContractTerm[];
  filters: { types: string[]; confidence_levels: string[]; selected_type: string; selected_confidence: string; as_of: string };
  coverage: { dependency_count: number; named_counterparty_count: number; category_only_count: number; contract_term_count: number; source_count: number; last_updated: string };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type GeographicExpansionMarket = {
  id: number;
  geography: string;
  market_type: string;
  current_status: string;
  current_status_label: string;
  entry_date: string | null;
  exit_date: string | null;
  local_partnerships: string[];
  regulatory_barriers: string[];
  revenue_contribution: number | null;
  revenue_currency: string;
  revenue_period: string;
  expansion_rationale: string;
  outcome_summary: string;
  evidence_text: string;
  confidence_score: number;
  review_status: string;
  source: CompanyProfileSource | null;
  linked_event: DashboardEvent | null;
};

export type GeographicExpansionResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; methodology: string;
    confidence_score: number; source: CompanyProfileSource | null;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; confidence_score: number; market_count: number; selected: boolean }[];
  markets: GeographicExpansionMarket[];
  timeline: { market_id: number; geography: string; entry_date: string | null; exit_date: string | null; status: string; summary: string }[];
  filters: { statuses: string[]; market_types: string[]; selected_status: string; selected_market_type: string; as_of: string };
  coverage: {
    market_count: number; entered_count: number; exited_count: number; revenue_contribution_count: number;
    partnership_count: number; regulatory_barrier_count: number; source_count: number; last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type OwnershipPosition = {
  id: number;
  holder_name: string;
  holder_type: string;
  holder_type_label: string;
  position_type: string;
  position_type_label: string;
  economic_ownership_pct: number | null;
  voting_power_pct: number | null;
  shares_owned: number | null;
  share_class: string;
  filing_date: string | null;
  report_period: string;
  disclosure_form: string;
  evidence_text: string;
  confidence_score: number;
  source: CompanyProfileSource | null;
};

export type InsiderTransaction = {
  id: number;
  insider_name: string;
  insider_role: string;
  transaction_type: string;
  transaction_type_label: string;
  transaction_date: string | null;
  shares: number | null;
  price: number | null;
  value: number | null;
  planned_sale: boolean;
  plan_reference: string;
  ownership_after: number | null;
  evidence_text: string;
  confidence_score: number;
  source: CompanyProfileSource | null;
};

export type OwnershipInsiderResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number;
    effective_date: string;
    status: string;
    summary: string;
    methodology: string;
    confidence_score: number;
    source: CompanyProfileSource | null;
    updated_at: string;
  } | null;
  snapshot_history: {
    id: number;
    effective_date: string;
    status: string;
    is_current: boolean;
    position_count: number;
    transaction_count: number;
  }[];
  positions: OwnershipPosition[];
  insider_transactions: InsiderTransaction[];
  control_context: {
    status: 'available' | 'unavailable';
    economic_ownership_available: boolean;
    voting_power_available: boolean;
    reason: string;
  };
  filters: {
    holder_types: string[];
    transaction_types: string[];
    selected_holder_type: string;
    selected_transaction_type: string;
    as_of: string;
  };
  coverage: {
    position_count: number;
    insider_context_count: number;
    ownership_percent_count: number;
    voting_control_count: number;
    institutional_position_count: number;
    transaction_count: number;
    planned_sale_count: number;
    source_count: number;
    last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type ValuationObservation = {
  id: number;
  measure: string;
  measure_label: string;
  value: number | null;
  unit: string;
  currency: string;
  market_price: { ticker: string; provider: string; price_date: string; close_price: number | null } | null;
  numerator: number | null;
  numerator_label: string;
  denominator: number | null;
  denominator_label: string;
  formula: string;
  source_period: string;
  applicability: string;
  applicability_label: string;
  unavailable_reason: string;
  evidence_text: string;
  source_facts: { id: number; concept: string; label: string; unit: string; fy: number | null; fp: string; filed: string | null; accession_number: string }[];
  confidence_score: number;
  review_status: string;
  source: CompanyProfileSource | null;
};

export type ValuationContextResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; methodology: string;
    disclaimer: string; currency: string; confidence_score: number; source: CompanyProfileSource | null;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; observation_count: number; applicable_count: number; selected: boolean }[];
  observations: ValuationObservation[];
  historical_ranges: { measure: string; measure_label: string; min_value: number | null; max_value: number | null; observation_count: number; range_note: string }[];
  peer_comparisons: {
    id: number; peer_name: string; peer_company: CompanyProfileResponse['company'] | null;
    measure: string; measure_label: string; peer_value: number | null; company_value: number | null;
    comparison_note: string; applicability: string; evidence_text: string; confidence_score: number;
  }[];
  event_snapshots: {
    id: number; event_id: number | null; event_date: string; event_label: string; measure: string;
    measure_label: string; before_value: number | null; after_value: number | null;
    before_date: string | null; after_date: string | null; context_note: string; confidence_score: number;
  }[];
  filters: { measures: string[]; selected_measure: string; as_of: string };
  coverage: {
    observation_count: number; applicable_count: number; unavailable_count: number; peer_comparison_count: number;
    event_snapshot_count: number; source_count: number; last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type RegulatoryLitigationResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; methodology: string;
    legal_guardrail: string; confidence_score: number; source: CompanyProfileSource | null; updated_at: string;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; matter_count: number; open_or_pending_count: number; selected: boolean }[];
  matters: {
    id: number; title: string; matter_type: string; matter_type_label: string; jurisdiction: string; authority: string;
    business_area: string; stage: string; stage_label: string; matter_status: string; matter_status_label: string;
    materiality: string; materiality_label: string; opened_date: string | null; next_date: string | null;
    next_date_type: string; allegation_or_issue: string; company_response: string; interim_decision: string;
    final_outcome: string; exposure_context: string; evidence_text: string; confidence_score: number;
    review_status: string; source: CompanyProfileSource | null; linked_event: DashboardEvent | null;
  }[];
  calendar: { date: string; date_type: string; matter_id: number; title: string; status: string }[];
  summary: {
    by_type: { key: string; count: number }[];
    by_status: { key: string; count: number }[];
    by_materiality: { key: string; count: number }[];
    open_matters: string[];
  };
  filters: { matter_types: string[]; statuses: string[]; selected_matter_type: string; selected_status: string; as_of: string };
  coverage: {
    matter_count: number; open_or_pending_count: number; dated_matter_count: number; next_date_count: number;
    exposure_context_count: number; source_count: number; last_updated: string;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type SectorThemeResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; methodology: string;
    confidence_score: number; source: CompanyProfileSource | null; updated_at: string;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; exposure_count: number; operating_exposure_count: number; selected: boolean }[];
  taxonomy: {
    id: number; slug: string; name: string; taxonomy_type: string; taxonomy_type_label: string;
    parent_slug: string; description: string; aliases: string[];
  }[];
  exposures: {
    id: number;
    theme: { id: number; slug: string; name: string; taxonomy_type: string; parent_slug: string };
    exposure_type: string; exposure_type_label: string; materiality: string; materiality_label: string;
    evidence_date: string | null; evidence_summary: string; evidence_text: string; exposure_rationale: string;
    confidence_score: number; review_status: string; source: CompanyProfileSource | null;
    linked_event: DashboardEvent | null; linked_kpi: OperatingKpiResponse['dictionary'][number] | null;
    linked_capital_allocation_item: { id: number; category: string; category_label: string; label: string; value: number | null; unit: string; evidence_text: string } | null;
  }[];
  theme_pages: {
    theme: { slug: string; name: string; description: string };
    exposure_count: number; operating_exposure_count: number; exposure_types: string[]; latest_evidence_date: string | null;
  }[];
  related: {
    events: DashboardEvent[];
    kpis: OperatingKpiResponse['dictionary'];
    capital_allocation: { id: number; category: string; category_label: string; label: string; value: number | null; unit: string; evidence_text: string }[];
    risk_signals: DashboardEvent[];
  };
  summary: {
    by_theme: { slug: string; name: string; count: number }[];
    by_exposure_type: { key: string; count: number }[];
    by_materiality: { key: string; count: number }[];
  };
  filters: { themes: string[]; exposure_types: string[]; selected_theme: string; selected_exposure_type: string; as_of: string };
  coverage: {
    exposure_count: number; operating_exposure_count: number; event_link_count: number; kpi_link_count: number;
    capital_link_count: number; source_count: number; last_updated: string | null;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type MacroSensitivityRow = {
  id: number; factor: { id: number; slug: string; name: string; category: string };
  channel: string; channel_label: string; direction: string; direction_label: string;
  evidence_type: string; evidence_type_label: string; materiality: string; materiality_label: string;
  evidence_date: string | null; evidence_summary: string; evidence_text: string; method: string;
  sample_size: number; period_start: string | null; period_end: string | null; lag_assumption: string;
  limitation_note: string; confidence_score: number; review_status: string; source: CompanyProfileSource | null;
  linked_event: DashboardEvent | null; linked_theme_exposure: SectorThemeResponse['exposures'][number] | null;
};

export type MacroSensitivityResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number; effective_date: string; status: string; summary: string; methodology: string;
    limitation_note: string; confidence_score: number; source: CompanyProfileSource | null; updated_at: string;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; sensitivity_count: number; stress_example_count: number; selected: boolean }[];
  factors: { id: number; slug: string; name: string; category: string; category_label: string; description: string; canonical_series: string[] }[];
  sensitivities: MacroSensitivityRow[];
  calculated_relationships: MacroSensitivityRow[];
  stress_examples: {
    id: number; label: string; period_start: string | null; period_end: string | null;
    macro_context: string; company_observation: string; limitation_note: string;
    confidence_score: number; source: CompanyProfileSource | null;
  }[];
  summary: {
    by_factor: { slug: string; name: string; count: number }[];
    by_channel: { key: string; count: number }[];
    by_direction: { key: string; count: number }[];
    by_evidence_type: { key: string; count: number }[];
  };
  filters: { factors: string[]; channels: string[]; selected_factor: string; selected_channel: string; as_of: string };
  coverage: {
    sensitivity_count: number; management_disclosed_count: number; calculated_placeholder_count: number;
    stress_example_count: number; source_count: number; last_updated: string | null;
  };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
};

export type ThesisEvidence = {
  id: number;
  side: string;
  side_label: string;
  evidence_type: string;
  evidence_type_label: string;
  company_slug: string;
  external_id: string;
  title: string;
  summary: string;
  source_url: string;
  source_date: string | null;
  source_payload: Record<string, unknown>;
  user_note: string;
  separation_note: string;
  updated_at: string;
};

export type StrategyThesis = {
  id: number;
  title: string;
  company_slug: string;
  company_name: string;
  statement: string;
  state: string;
  state_label: string;
  time_horizon: string;
  review_date: string | null;
  confidence_score: number;
  confidence_reason: string;
  assumptions: string[];
  is_shared: boolean;
  shared_label: string;
  balance: { supporting: number; opposing: number; neutral: number; total: number; support_ratio: number; opposition_ratio: number };
  evidence?: ThesisEvidence[];
  milestones?: { id: number; title: string; due_date: string | null; status: string; status_label: string; success_criteria: string; linked_evidence_id: number | null }[];
  indicators?: { id: number; name: string; direction: string; direction_label: string; target: string; current_value: string; source_hint: string }[];
  revisions?: { id: number; previous_state: string; new_state: string; previous_confidence_score: number | null; new_confidence_score: number; reason: string; changed_by: string; created_at: string }[];
  privacy_note?: string;
  updated_at: string;
  created_at: string;
};

export type ThesisListResponse = {
  theses: StrategyThesis[];
  summary: { total: number; by_state: { state: string; label: string; count: number }[] };
  states: { value: string; label: string }[];
  evidence_sides: { value: string; label: string }[];
  evidence_types: { value: string; label: string }[];
};

export type ThesisSuggestionsResponse = {
  suggestions: {
    evidence_type: string;
    company_slug: string;
    external_id: string;
    title: string;
    summary: string;
    source_url?: string;
    source_date?: string;
    source_payload: Record<string, unknown>;
  }[];
  source: string;
  source_gaps: { key: string; reason: string; next_action: string }[];
};

export type WatchlistItem = {
  id: number;
  entity_type: string;
  entity_type_label: string;
  entity_id: string;
  label: string;
  company_slug: string;
  is_active: boolean;
};

export type Watchlist = {
  id: number;
  name: string;
  description: string;
  is_active: boolean;
  item_count: number;
  notification_count: number;
  unread_count: number;
  updated_at: string;
  items?: WatchlistItem[];
  rules?: { id: number; category: string; category_label: string; is_enabled: boolean; minimum_severity: string }[];
};

export type NotificationAlert = {
  id: number;
  watchlist_id: number | null;
  watchlist_name: string;
  watch_item_label: string;
  category: string;
  category_label: string;
  severity: string;
  severity_label: string;
  status: string;
  title: string;
  what_changed: string;
  why_it_matters: string;
  previous_state: string;
  source_label: string;
  source_url: string;
  source_date: string | null;
  duplicate_count: number;
  generated_at: string;
};

export type WatchlistResponse = {
  watchlists: Watchlist[];
  summary: { total: number; active: number; followed_items: number };
  entity_types: { value: string; label: string }[];
  alert_categories: { value: string; label: string }[];
  delivery_preference: { in_product_enabled: boolean; email_enabled: boolean; email_frequency: string; timezone: string; quiet_hours_start: string | null; quiet_hours_end: string | null };
};

export type NotificationResponse = {
  notifications: NotificationAlert[];
  summary: { total: number; unread: number; read: number; archived: number };
  quality: { total_alerts: number; duplicate_group_count: number; duplicate_group_ratio: number; feedback_count: number; noise_monitoring_note: string };
  statuses: { value: string; label: string }[];
  categories: { value: string; label: string }[];
};

export type Briefing = {
  id: number;
  cadence: string;
  cadence_label: string;
  status: string;
  period_start: string;
  period_end: string;
  title: string;
  summary: string;
  ranking_note: string;
  scope_summary: string;
  source_gap_count: number;
  notification_count: number;
  email_rendered_at: string | null;
  generated_at: string;
  items?: {
    id: number;
    notification_id: number | null;
    section: string;
    section_label: string;
    rank: number;
    title: string;
    what_changed: string;
    why_it_matters: string;
    what_next: string;
    evidence_label: string;
    evidence_url: string;
    source_date: string | null;
    metadata: Record<string, unknown>;
  }[];
  delivery_logs?: { id: number; channel: string; status: string; detail: string; created_at: string }[];
};

export type BriefingResponse = {
  briefings: Briefing[];
  summary: { total: number; daily: number; weekly: number };
  cadences: { value: string; label: string }[];
  statuses: { value: string; label: string }[];
};

export type ScenarioSet = {
  id: number;
  title: string;
  company_slug: string;
  company_name: string;
  thesis: string;
  horizon_start: string | null;
  horizon_end: string | null;
  status: string;
  status_label: string;
  source_type: string;
  source_type_label: string;
  non_prediction_note: string;
  is_shared: boolean;
  updated_at: string;
  created_at: string;
  cases?: {
    id: number;
    kind: string;
    kind_label: string;
    title: string;
    narrative: string;
    qualitative_outcome: string;
    low_value: number | null;
    high_value: number | null;
    unit: string;
    probability_label: string;
    assumptions: {
      id: number;
      driver_type: string;
      driver_type_label: string;
      driver_label: string;
      assumption: string;
      rationale: string;
      evidence_type: string;
      evidence_id: string;
      evidence_label: string;
      evidence_url: string;
      confidence_label: string;
    }[];
  }[];
  indicators?: { id: number; name: string; driver_type: string; target: string; current_value: string; status: string; status_label: string; source_hint: string }[];
  actual_results?: { id: number; result_date: string; metric_label: string; actual_value: string; comparison_note: string; evidence_label: string; evidence_url: string }[];
  revisions?: { id: number; previous_status: string; new_status: string; reason: string; created_at: string; changed_by: string }[];
  differences?: { driver_type: string; driver_label: string; cases: Record<string, string> }[];
};

export type ScenarioListResponse = {
  scenario_sets: ScenarioSet[];
  templates: { kind: string; required_fields: string[] }[];
  statuses: { value: string; label: string }[];
  driver_types: { value: string; label: string }[];
  non_prediction_note: string;
};

export type ContradictionCase = {
  id: number;
  company_slug: string;
  company_name: string;
  title: string;
  category: string;
  category_label: string;
  conflict_type: string;
  conflict_type_label: string;
  review_label: string;
  review_label_display: string;
  materiality: string;
  materiality_label: string;
  confidence_score: number;
  neutral_summary: string;
  explanation: string;
  correction_path: string;
  human_review_required: boolean;
  is_published: boolean;
  neutrality_note: string;
  updated_at: string;
  claims?: {
    id: number;
    label: string;
    claim_text: string;
    claim_date: string | null;
    speaker: string;
    scope: string;
    source_label: string;
    source_url: string;
    source_type: string;
    source_payload: Record<string, unknown>;
  }[];
  resolutions?: { id: number; previous_label: string; new_label: string; explanation: string; changed_by: string; created_at: string }[];
};

export type ContradictionListResponse = {
  cases: ContradictionCase[];
  categories: { value: string; label: string }[];
  conflict_types: { value: string; label: string }[];
  review_labels: { value: string; label: string }[];
  materialities: { value: string; label: string }[];
  neutrality_note: string;
};

export type StrategyFailureCase = {
  id: number;
  title: string;
  company_slug: string;
  company_name: string;
  sector: string;
  category: string;
  category_label: string;
  classification: string;
  classification_label: string;
  stage: string;
  stage_label: string;
  decision_date: string | null;
  review_start: string | null;
  review_end: string | null;
  minimum_evidence: string;
  elapsed_time_definition: string;
  decision_context: string;
  management_rationale: string;
  original_thesis: string;
  expected_result: string;
  execution_issue: string;
  outcome_definition: string;
  actual_outcome: string;
  counterexamples: string;
  lessons: string;
  correction_path: string;
  editorial_status: string;
  editorial_status_label: string;
  evidence_count: number;
  warning_sign_count: number;
  confidence_score: number;
  is_published: boolean;
  guardrail_note: string;
  updated_at: string;
  created_at: string;
  evidence?: { id: number; evidence_type: string; label: string; summary: string; evidence_date: string | null; source_url: string; source_payload: Record<string, unknown> }[];
  warning_signs?: { id: number; signal_date: string | null; signal: string; why_it_mattered: string; observable_at_time: boolean; source_label: string; source_url: string }[];
  related_links?: { id: number; feature_type: string; feature_type_label: string; object_label: string; object_id: string; relationship_note: string; source_url: string }[];
  reviews?: { id: number; previous_status: string; new_status: string; classification: string; note: string; changed_by: string; created_at: string }[];
  quality?: { checks: Record<string, boolean>; ready_for_review: boolean };
};

export type StrategyFailureListResponse = {
  cases: StrategyFailureCase[];
  categories: { value: string; label: string }[];
  classifications: { value: string; label: string }[];
  stages: { value: string; label: string }[];
  editorial_statuses: { value: string; label: string }[];
  related_feature_types: { value: string; label: string }[];
  guardrail_note: string;
};

export type FoundationStandardsResponse = {
  status: string;
  purpose: string;
  pilot: { company_slug: string; company_name: string; review_period_start: string; review_period_end: string; reason: string };
  rules: { key: string; label: string; summary: string; requirements: string[] }[];
  states: { key: string; label: string; meaning: string }[];
  review_workflows: { key: string; label: string; steps: string[] }[];
  freshness: { information_type: string; expectation: string }[];
};

export type LeadershipDecisionResponse = {
  status: 'available' | 'partial' | 'unavailable';
  company: CompanyProfileResponse['company'];
  snapshot: {
    id: number;
    effective_date: string;
    status: string;
    summary: string;
    methodology: string;
    non_causation_note: string;
    confidence_score: number;
    source: CompanyProfileSource | null;
    updated_at: string;
  } | null;
  snapshot_history: { id: number; effective_date: string; status: string; is_current: boolean; role_count: number; decision_count: number }[];
  roles: {
    id: number; leader_name: string; role_title: string; role_type: string; role_type_label: string;
    transition_type: string; transition_type_label: string; start_date: string | null; end_date: string | null;
    interim_status: boolean; co_leadership: boolean; stated_priorities: string[]; evidence_text: string;
    confidence_score: number; source: CompanyProfileSource | null; linked_event: DashboardEvent | null;
  }[];
  decisions: {
    id: number; title: string; decision_type: string; decision_type_label: string; decision_date: string | null;
    leader_name: string; summary: string; evidence_text: string; confidence_score: number;
    source: CompanyProfileSource | null; linked_event: DashboardEvent | null; linked_strategic_turn: DashboardTurn | null;
  }[];
  timeline: { date: string; type: string; label: string; summary: string }[];
  performance_context: { status: 'available' | 'unavailable'; non_causation_note: string; reason: string };
  filters: { role_types: string[]; decision_types: string[]; selected_role_type: string; selected_decision_type: string; as_of: string };
  coverage: { role_count: number; decision_count: number; dated_role_count: number; priority_count: number; linked_turn_count: number; source_count: number; last_updated: string };
  evidence: CompanyProfileSource[];
  source_gaps: SourceGap[];
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

  dashboard(token: string, section = '', page = 1, limit = 12, company = '') {
    return this.http.get<DashboardResponse>(`${this.apiBaseUrl}/dashboard`, {
      headers: this.authHeaders(token),
      params: dashboardRequestParams(section, page, limit, company)
    });
  }

  categories(token: string) {
    return this.http.get<{ categories: SectorCount[] }>(`${this.apiBaseUrl}/categories`, {
      headers: this.authHeaders(token)
    });
  }

  search(
    token: string,
    query: string,
    pages: { company_page: number; event_page: number; turn_page: number } = {
      company_page: 1,
      event_page: 1,
      turn_page: 1
    },
    limit = 10
  ) {
    return this.http.get<SearchResponse>(`${this.apiBaseUrl}/search`, {
      headers: this.authHeaders(token),
      params: {
        q: query,
        language: 'en',
        limit: String(limit),
        company_page: String(pages.company_page),
        event_page: String(pages.event_page),
        turn_page: String(pages.turn_page)
      }
    });
  }

  suggest(token: string, query: string) {
    return this.http.get<{ suggestions: SearchSuggestion[] }>(`${this.apiBaseUrl}/search/suggest`, {
      headers: this.authHeaders(token),
      params: { q: query, language: 'en' }
    });
  }

  companyProfile(token: string, slug: string, asOf = '') {
    const params: Record<string, string> = {};
    if (asOf) {
      params['as_of'] = asOf;
    }
    return this.http.get<CompanyProfileResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/profile`, {
      headers: this.authHeaders(token),
      params
    });
  }

  businessModel(token: string, slug: string, asOf = '', compareTo = '') {
    const params: Record<string, string> = {};
    if (asOf) {
      params['as_of'] = asOf;
    }
    if (compareTo) {
      params['compare_to'] = compareTo;
    }
    return this.http.get<BusinessModelResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/business-model`, {
      headers: this.authHeaders(token),
      params
    });
  }

  operatingKpis(token: string, slug: string, metric = '', segment = '', geography = '', start = '', end = '', comparableOnly = false) {
    const params: Record<string, string> = {};
    if (metric) params['metric'] = metric;
    if (segment) params['segment'] = segment;
    if (geography) params['geography'] = geography;
    if (start) params['start'] = start;
    if (end) params['end'] = end;
    if (comparableOnly) params['comparable_only'] = 'true';
    return this.http.get<OperatingKpiResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/operating-kpis`, {
      headers: this.authHeaders(token), params
    });
  }

  managementPromises(token: string, slug: string, status = '', type = '', due = '', asOf = '', promise = '') {
    const params: Record<string, string> = {};
    if (status) params['status'] = status;
    if (type) params['type'] = type;
    if (due) params['due'] = due;
    if (asOf) params['as_of'] = asOf;
    if (promise) params['promise'] = promise;
    return this.http.get<ManagementPromiseResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/management-promises`, {
      headers: this.authHeaders(token), params
    });
  }

  strategyMilestones(token: string, slug: string, status = '', type = '', origin = '', view = 'all', milestone = '') {
    const params: Record<string, string> = {};
    if (status) params['status'] = status;
    if (type) params['type'] = type;
    if (origin) params['origin'] = origin;
    if (view && view !== 'all') params['view'] = view;
    if (milestone) params['milestone'] = milestone;
    return this.http.get<StrategyMilestoneResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/strategy-milestones`, {
      headers: this.authHeaders(token), params
    });
  }

  earnings(token: string, slug: string, period = '') {
    const params: Record<string, string> = {};
    if (period) params['period'] = period;
    return this.http.get<EarningsResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/earnings`, {
      headers: this.authHeaders(token), params
    });
  }

  capitalAllocation(token: string, slug: string, period = '') {
    const params: Record<string, string> = {};
    if (period) params['period'] = period;
    return this.http.get<CapitalAllocationResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/capital-allocation`, {
      headers: this.authHeaders(token), params
    });
  }

  competitivePosition(token: string, slug: string, asOf = '', relationship = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (relationship) params['relationship'] = relationship;
    return this.http.get<CompetitivePositionResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/competitive-position`, {
      headers: this.authHeaders(token), params
    });
  }

  productPricing(token: string, slug: string, asOf = '', type = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (type) params['type'] = type;
    return this.http.get<ProductPricingResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/product-pricing`, {
      headers: this.authHeaders(token), params
    });
  }

  acquisitionLifecycle(token: string, slug: string, stage = '', transactionType = '', outcome = '', deal = '') {
    const params: Record<string, string> = {};
    if (stage) params['stage'] = stage;
    if (transactionType) params['transaction_type'] = transactionType;
    if (outcome) params['outcome'] = outcome;
    if (deal) params['deal'] = deal;
    return this.http.get<AcquisitionLifecycleResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/acquisition-lifecycle`, {
      headers: this.authHeaders(token), params
    });
  }

  customerSupplierDependency(token: string, slug: string, asOf = '', type = '', confidence = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (type) params['type'] = type;
    if (confidence) params['confidence'] = confidence;
    return this.http.get<CustomerSupplierDependencyResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/customer-supplier-dependency`, {
      headers: this.authHeaders(token), params
    });
  }

  geographicExpansion(token: string, slug: string, asOf = '', status = '', marketType = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (status) params['status'] = status;
    if (marketType) params['market_type'] = marketType;
    return this.http.get<GeographicExpansionResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/geographic-expansion`, {
      headers: this.authHeaders(token), params
    });
  }

  ownershipInsider(token: string, slug: string, asOf = '', holderType = '', transactionType = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (holderType) params['holder_type'] = holderType;
    if (transactionType) params['transaction_type'] = transactionType;
    return this.http.get<OwnershipInsiderResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/ownership-insider`, {
      headers: this.authHeaders(token), params
    });
  }

  valuationContext(token: string, slug: string, asOf = '', measure = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (measure) params['measure'] = measure;
    return this.http.get<ValuationContextResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/valuation-context`, {
      headers: this.authHeaders(token), params
    });
  }

  regulatoryLitigation(token: string, slug: string, asOf = '', matterType = '', status = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (matterType) params['matter_type'] = matterType;
    if (status) params['status'] = status;
    return this.http.get<RegulatoryLitigationResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/regulatory-litigation`, {
      headers: this.authHeaders(token), params
    });
  }

  sectorThemes(token: string, slug: string, asOf = '', theme = '', exposureType = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (theme) params['theme'] = theme;
    if (exposureType) params['exposure_type'] = exposureType;
    return this.http.get<SectorThemeResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/sector-themes`, {
      headers: this.authHeaders(token), params
    });
  }

  macroSensitivity(token: string, slug: string, asOf = '', factor = '', channel = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (factor) params['factor'] = factor;
    if (channel) params['channel'] = channel;
    return this.http.get<MacroSensitivityResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/macro-sensitivity`, {
      headers: this.authHeaders(token), params
    });
  }

  theses(token: string, state = '', company = '', query = '') {
    const params: Record<string, string> = {};
    if (state) params['state'] = state;
    if (company) params['company'] = company;
    if (query) params['q'] = query;
    return this.http.get<ThesisListResponse>(`${this.apiBaseUrl}/theses`, {
      headers: this.authHeaders(token),
      params
    });
  }

  createThesis(token: string, payload: Record<string, unknown>) {
    return this.http.post<{ thesis: StrategyThesis }>(`${this.apiBaseUrl}/theses`, payload, {
      headers: this.authHeaders(token)
    });
  }

  thesis(token: string, id: number) {
    return this.http.get<{ thesis: StrategyThesis }>(`${this.apiBaseUrl}/theses/${id}`, {
      headers: this.authHeaders(token)
    });
  }

  addThesisEvidence(token: string, thesisId: number, payload: Record<string, unknown>) {
    return this.http.post<{ evidence: ThesisEvidence; balance: StrategyThesis['balance'] }>(
      `${this.apiBaseUrl}/theses/${thesisId}/evidence`,
      payload,
      { headers: this.authHeaders(token) }
    );
  }

  addThesisMilestone(token: string, thesisId: number, payload: Record<string, unknown>) {
    return this.http.post<{ milestone: NonNullable<StrategyThesis['milestones']>[number] }>(
      `${this.apiBaseUrl}/theses/${thesisId}/milestones`,
      payload,
      { headers: this.authHeaders(token) }
    );
  }

  addThesisIndicator(token: string, thesisId: number, payload: Record<string, unknown>) {
    return this.http.post<{ indicator: NonNullable<StrategyThesis['indicators']>[number] }>(
      `${this.apiBaseUrl}/theses/${thesisId}/indicators`,
      payload,
      { headers: this.authHeaders(token) }
    );
  }

  updateThesisConfidence(token: string, thesisId: number, payload: Record<string, unknown>) {
    return this.http.post<{ thesis: StrategyThesis }>(`${this.apiBaseUrl}/theses/${thesisId}/confidence`, payload, {
      headers: this.authHeaders(token)
    });
  }

  thesisEvidenceSuggestions(token: string, query: string, company = '') {
    const params: Record<string, string> = {};
    if (query) params['q'] = query;
    if (company) params['company'] = company;
    return this.http.get<ThesisSuggestionsResponse>(`${this.apiBaseUrl}/theses/evidence-suggestions`, {
      headers: this.authHeaders(token),
      params
    });
  }

  watchlists(token: string) {
    return this.http.get<WatchlistResponse>(`${this.apiBaseUrl}/watchlists`, { headers: this.authHeaders(token) });
  }

  createWatchlist(token: string, payload: Record<string, unknown>) {
    return this.http.post<{ watchlist: Watchlist }>(`${this.apiBaseUrl}/watchlists`, payload, { headers: this.authHeaders(token) });
  }

  watchlist(token: string, id: number) {
    return this.http.get<{ watchlist: Watchlist }>(`${this.apiBaseUrl}/watchlists/${id}`, { headers: this.authHeaders(token) });
  }

  addWatchlistItem(token: string, watchlistId: number, payload: Record<string, unknown>) {
    return this.http.post<{ item: WatchlistItem }>(`${this.apiBaseUrl}/watchlists/${watchlistId}/items`, payload, { headers: this.authHeaders(token) });
  }

  followCompany(token: string, companySlug: string, companyName: string) {
    return this.http.post<{ watchlist: Watchlist; status: string }>(
      `${this.apiBaseUrl}/watchlists/follow-company`,
      { company_slug: companySlug, company_name: companyName },
      { headers: this.authHeaders(token) }
    );
  }

  notifications(token: string, status = '', category = '') {
    const params: Record<string, string> = {};
    if (status) params['status'] = status;
    if (category) params['category'] = category;
    return this.http.get<NotificationResponse>(`${this.apiBaseUrl}/notifications`, { headers: this.authHeaders(token), params });
  }

  refreshNotifications(token: string) {
    return this.http.post<{ status: string; stats: Record<string, number>; summary: NotificationResponse['summary'] }>(
      `${this.apiBaseUrl}/notifications/refresh`,
      {},
      { headers: this.authHeaders(token) }
    );
  }

  updateNotification(token: string, id: number, status: string) {
    return this.http.patch<{ notification: NotificationAlert }>(`${this.apiBaseUrl}/notifications/${id}`, { status }, { headers: this.authHeaders(token) });
  }

  alertFeedback(token: string, id: number, rating: string) {
    return this.http.post(`${this.apiBaseUrl}/notifications/${id}/feedback`, { rating }, { headers: this.authHeaders(token) });
  }

  briefings(token: string, cadence = '', status = '') {
    const params: Record<string, string> = {};
    if (cadence) params['cadence'] = cadence;
    if (status) params['status'] = status;
    return this.http.get<BriefingResponse>(`${this.apiBaseUrl}/briefings`, { headers: this.authHeaders(token), params });
  }

  generateBriefing(token: string, cadence: string, refreshAlerts = true) {
    return this.http.post<{ briefing: Briefing }>(
      `${this.apiBaseUrl}/briefings`,
      { cadence, refresh_alerts: refreshAlerts },
      { headers: this.authHeaders(token) }
    );
  }

  briefing(token: string, id: number) {
    return this.http.get<{ briefing: Briefing }>(`${this.apiBaseUrl}/briefings/${id}`, { headers: this.authHeaders(token) });
  }

  updateBriefing(token: string, id: number, status: string) {
    return this.http.patch<{ briefing: Briefing }>(`${this.apiBaseUrl}/briefings/${id}`, { status }, { headers: this.authHeaders(token) });
  }

  briefingFeedback(token: string, id: number, rating: string) {
    return this.http.post(`${this.apiBaseUrl}/briefings/${id}/feedback`, { rating }, { headers: this.authHeaders(token) });
  }

  scenarios(token: string, company = '', status = '') {
    const params: Record<string, string> = {};
    if (company) params['company'] = company;
    if (status) params['status'] = status;
    return this.http.get<ScenarioListResponse>(`${this.apiBaseUrl}/scenarios`, { headers: this.authHeaders(token), params });
  }

  createScenario(token: string, payload: Record<string, unknown>) {
    return this.http.post<{ scenario_set: ScenarioSet }>(`${this.apiBaseUrl}/scenarios`, payload, { headers: this.authHeaders(token) });
  }

  scenario(token: string, id: number) {
    return this.http.get<{ scenario_set: ScenarioSet }>(`${this.apiBaseUrl}/scenarios/${id}`, { headers: this.authHeaders(token) });
  }

  updateScenario(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.patch<{ scenario_set: ScenarioSet }>(`${this.apiBaseUrl}/scenarios/${id}`, payload, { headers: this.authHeaders(token) });
  }

  addScenarioAssumption(token: string, scenarioId: number, caseId: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/scenarios/${scenarioId}/cases/${caseId}/assumptions`, payload, { headers: this.authHeaders(token) });
  }

  addScenarioIndicator(token: string, scenarioId: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/scenarios/${scenarioId}/indicators`, payload, { headers: this.authHeaders(token) });
  }

  addScenarioActual(token: string, scenarioId: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/scenarios/${scenarioId}/actual-results`, payload, { headers: this.authHeaders(token) });
  }

  contradictions(token: string, company = '', reviewLabel = '', category = '') {
    const params: Record<string, string> = {};
    if (company) params['company'] = company;
    if (reviewLabel) params['review_label'] = reviewLabel;
    if (category) params['category'] = category;
    return this.http.get<ContradictionListResponse>(`${this.apiBaseUrl}/contradictions`, { headers: this.authHeaders(token), params });
  }

  createContradiction(token: string, payload: Record<string, unknown>) {
    return this.http.post<{ case: ContradictionCase }>(`${this.apiBaseUrl}/contradictions`, payload, { headers: this.authHeaders(token) });
  }

  contradiction(token: string, id: number) {
    return this.http.get<{ case: ContradictionCase }>(`${this.apiBaseUrl}/contradictions/${id}`, { headers: this.authHeaders(token) });
  }

  addContradictionClaim(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/contradictions/${id}/claims`, payload, { headers: this.authHeaders(token) });
  }

  reviewContradiction(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.post<{ case: ContradictionCase }>(`${this.apiBaseUrl}/contradictions/${id}/review`, payload, { headers: this.authHeaders(token) });
  }

  strategyFailures(token: string, company = '', category = '', classification = '', stage = '') {
    const params: Record<string, string> = {};
    if (company) params['company'] = company;
    if (category) params['category'] = category;
    if (classification) params['classification'] = classification;
    if (stage) params['stage'] = stage;
    return this.http.get<StrategyFailureListResponse>(`${this.apiBaseUrl}/strategy-failures`, { headers: this.authHeaders(token), params });
  }

  createStrategyFailure(token: string, payload: Record<string, unknown>) {
    return this.http.post<{ case: StrategyFailureCase }>(`${this.apiBaseUrl}/strategy-failures`, payload, { headers: this.authHeaders(token) });
  }

  strategyFailure(token: string, id: number) {
    return this.http.get<{ case: StrategyFailureCase }>(`${this.apiBaseUrl}/strategy-failures/${id}`, { headers: this.authHeaders(token) });
  }

  addStrategyFailureEvidence(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/strategy-failures/${id}/evidence`, payload, { headers: this.authHeaders(token) });
  }

  addStrategyFailureWarning(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/strategy-failures/${id}/warning-signs`, payload, { headers: this.authHeaders(token) });
  }

  addStrategyFailureLink(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.post(`${this.apiBaseUrl}/strategy-failures/${id}/related-links`, payload, { headers: this.authHeaders(token) });
  }

  reviewStrategyFailure(token: string, id: number, payload: Record<string, unknown>) {
    return this.http.post<{ case: StrategyFailureCase }>(`${this.apiBaseUrl}/strategy-failures/${id}/review`, payload, { headers: this.authHeaders(token) });
  }

  foundationStandards(token: string) {
    return this.http.get<FoundationStandardsResponse>(`${this.apiBaseUrl}/foundations/standards`, { headers: this.authHeaders(token) });
  }

  leadershipDecisions(token: string, slug: string, asOf = '', roleType = '', decisionType = '') {
    const params: Record<string, string> = {};
    if (asOf) params['as_of'] = asOf;
    if (roleType) params['role_type'] = roleType;
    if (decisionType) params['decision_type'] = decisionType;
    return this.http.get<LeadershipDecisionResponse>(`${this.apiBaseUrl}/companies/${encodeURIComponent(slug)}/leadership-decisions`, {
      headers: this.authHeaders(token), params
    });
  }

  private authHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Token ${token}` });
  }
}
