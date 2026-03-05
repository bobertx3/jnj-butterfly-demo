export interface Action {
  id: number;
  account_id: string;
  contact_id: string | null;
  action_type: string;
  title: string;
  description: string | null;
  priority: string;
  status: string;
  due_date: string | null;
  created_at: string;
  updated_at: string;
}

export interface Contact {
  id: number;
  contact_id: string;
  name: string;
  role_specialty: string | null;
  institution: string | null;
  priority_score: number;
  intent_score: number;
  risk_level: string;
  preferred_channel: string;
  last_touch_days: number;
  last_interaction_channel: string | null;
  last_interaction_date: string | null;
  last_interaction_summary: string | null;
  last_products_discussed: string | null;
  next_follow_up_objective: string | null;
  trx_volume_3m: number | null;
  nrx_volume_3m: number | null;
  site_visits: number | null;
  webinar_signups: number | null;
  rx_growth_3m_pct: number | null;
  territory_id: string | null;
  updated_at: string;
}

export interface NbaRecommendation {
  contact_id: string;
  recommendation_text: string | null;
  email_draft_subject: string | null;
  email_draft_body: string | null;
  generated_at: string | null;
}

export interface Stats {
  assigned_contacts: number;
  growth_opportunities: number;
  at_risk_accounts: number;
  at_risk_avg_priority?: number;
}

export interface LlmStatus {
  llm_configured: boolean;
}

export type TabId = "overview" | "nba" | "genie";

export interface GenieStatus {
  configured: boolean;
  space_id: string | null;
  message?: string;
}

export interface GenieAskResponse {
  conversation_id?: string | null;
  message_id?: string | null;
  status: string;
  text_response: string;
  sql?: string | null;
  description?: string | null;
  columns?: string[] | null;
  data?: unknown[] | null;
  row_count?: number | null;
  error?: string;
  /** Raw Genie API message when request was sent with debug: true */
  _raw_message?: unknown;
}

