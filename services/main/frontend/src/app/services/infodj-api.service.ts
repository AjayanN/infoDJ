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

  private authHeaders(token: string): HttpHeaders {
    return new HttpHeaders({ Authorization: `Token ${token}` });
  }
}
