export type UserRole = "usuario" | "admin";

export interface AuthSession {
  access_token: string;
  user_id: string;
  email: string;
  full_name: string;
  role: UserRole;
  department: string;
  expires_in_seconds: number;
}

export interface ReActStep {
  step: number;
  phase: "REASON" | "ACT" | "OBSERVE";
  thought?: string;
  selected_tool?: string;
  invoked_tool?: string;
  tool_args?: Record<string, unknown>;
  status?: string;
  observation_summary?: string;
}

export interface TechnicalTelemetry {
  llm_provider: string;
  llm_model: string;
  circuit_breaker_state: "CLOSED" | "OPEN" | "HALF_OPEN";
  fallback_triggered: boolean;
  prompt_tokens: number;
  completion_tokens: number;
  total_tokens: number;
  estimated_cost_usd: number;
  latency_ms: number;
  react_steps: ReActStep[];
  audit_record_hash: string;
}

export interface ChatResponsePayload {
  session_id: string;
  reply: string;
  timestamp: string;
  remaining_requests_minute: number;
  /** Presente ÚNICAMENTE cuando el rol JWT es 'admin' */
  technical_telemetry?: TechnicalTelemetry;
}

export interface ModalityComparisonItem {
  modality_id: string;
  name: string;
  tokens_usd: number;
  compute_usd: number;
  storage_network_usd: number;
  total_usd: number;
  p95_latency_ms: number;
  availability_sla_pct: number;
  recommended: boolean;
}

export interface AdminDashboardData {
  circuit_breaker: {
    state: "CLOSED" | "OPEN" | "HALF_OPEN";
    failure_count: number;
    failure_threshold: number;
    recovery_timeout_seconds: number;
    primary_provider: string;
    fallback_provider: string;
    last_state_change_utc: string;
  };
  observability_metrics: {
    uptime_seconds: number;
    total_requests: number;
    total_errors: number;
    rate_limited_requests: number;
    error_rate_percent: number;
    availability_percent: number;
    avg_latency_ms: number;
    p95_latency_ms: number;
    avg_indicator_calc_ms: number;
    data_quality_alerts: number;
    provider_calls: Record<string, number>;
  };
  cost_analysis_e6: {
    realtime_usage: {
      total_assistant_turns: number;
      prompt_tokens: number;
      completion_tokens: number;
      total_tokens: number;
      accumulated_cost_usd: number;
      avg_turn_latency_ms: number;
    };
    monthly_projection_800_employees: {
      headcount_employees: number;
      active_daily_users_dau: number;
      monthly_queries_estimated: number;
      monthly_input_tokens: number;
      monthly_output_tokens: number;
      cost_breakdown_usd: {
        tokens_vertex_ai_hybrid: number;
        compute_cloud_run: number;
        database_cloud_sql_pg16: number;
        storage_audit_and_secrets: number;
        network_and_cloud_logging: number;
        total_monthly_usd: number;
        cost_per_employee_usd: number;
      };
    };
    modalities_comparison: ModalityComparisonItem[];
  };
  audit_integrity: {
    is_valid: boolean;
    verified_records: number;
    latest_hash: string;
    status: string;
  };
  recent_audit_logs: Array<{
    id: number;
    event_timestamp: string;
    event_type: string;
    user_id: string;
    user_role: string;
    session_id: string;
    provider_used: string;
    model_used: string;
    total_tokens: number;
    cost_usd: number;
    latency_ms: number;
    circuit_breaker_state: string;
    prev_hash: string;
    record_hash: string;
  }>;
  quantitative_market_snapshot: Array<{
    ticker: string;
    company_name: string;
    currency: string;
    latest_price: number;
    sma_20: number;
    ema_12: number;
    rsi_14: number;
    annualized_volatility_pct: number;
    sharpe_ratio: number;
    max_drawdown_pct: number;
    provider_used: string;
    quality_status: string;
  }>;
}
