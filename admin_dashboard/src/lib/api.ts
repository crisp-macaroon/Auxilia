import { API_BASE_URL } from '@/lib/constants';
import { ADMIN_TOKEN_COOKIE } from '@/lib/auth';

type FetchOptions = {
  cache?: RequestCache;
};

async function getAuthHeaders(): Promise<Record<string, string>> {
  if (typeof window !== 'undefined') {
    return {};
  }

  const { cookies } = await import('next/headers');
  const cookieStore = await cookies();
  const token = cookieStore.get(ADMIN_TOKEN_COOKIE)?.value;
  return token ? { Authorization: `Bearer ${token}` } : {};
}

async function apiFetch<T>(path: string, options?: FetchOptions): Promise<T> {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}${path}`, {
    cache: options?.cache ?? 'no-store',
    headers,
  });

  if (!response.ok) {
    throw new Error(`API request failed: ${response.status}`);
  }

  return response.json() as Promise<T>;
}

export type DashboardStatsResponse = {
  total_policies: number;
  active_policies: number;
  total_claims: number;
  pending_claims: number;
  total_premium_collected: number;
  total_claims_paid: number;
  active_riders: number;
  avg_risk_score: number;
  active_triggers: number;
  loss_ratio: number;
};

export type ClaimsChartResponse = {
  data: Array<{
    date: string | null;
    total: number;
    approved: number;
    rejected: number;
  }>;
  days: number;
};

export type RecentClaimsResponse = {
  claims: Array<{
    id: string;
    rider_name: string;
    zone_id: string;
    trigger_type: string;
    amount: number;
    status: string;
    created_at: string;
  }>;
};

export type LiveTriggersResponse = {
  triggers: Array<{
    zone_id: string;
    zone_name: string;
    trigger_type: string;
    current_value: number;
    threshold: number;
    source: string;
    severity: string;
    last_updated: string;
  }>;
  count: number;
};

export type ZoneStatsResponse = {
  zones: Array<{
    zone_id: string;
    name: string;
    city: string;
    active_policies: number;
    total_claims: number;
    total_payouts: number;
    active_triggers: number;
  }>;
};

export type ClaimListItem = {
  id: string;
  policy_id: string;
  rider_id: string;
  trigger_type: string;
  trigger_value: number;
  threshold: number;
  amount: number;
  status: string;
  fraud_score: number;
  ai_decision?: string | null;
  tx_hash?: string | null;
  created_at: string;
  processed_at?: string | null;
};

export type PolicyListItem = {
  id: string;
  rider_id: string;
  zone_id: string;
  persona: 'qcommerce' | 'food_delivery';
  premium: number;
  coverage: number;
  start_date: string;
  end_date: string;
  status: string;
  tx_hash?: string | null;
  created_at: string;
};

export type RiderListItem = {
  id: string;
  name: string;
  phone: string;
  email?: string | null;
  persona: 'qcommerce' | 'food_delivery';
  zone_id: string;
  latitude?: number | null;
  longitude?: number | null;
  risk_score: number;
  status: string;
  created_at: string;
};

export type ClaimStatsResponse = {
  total_claims: number;
  pending_claims: number;
  approved_claims: number;
  rejected_claims: number;
  total_payout: number;
  average_fraud_score: number;
  by_trigger_type: Record<string, number>;
};

export type PolicyStatsResponse = {
  total_policies: number;
  active_policies: number;
  total_premium_collected: number;
  total_coverage_liability: number;
};

export type ZoneListItem = {
  id: string;
  name: string;
  city: string;
  latitude: number;
  longitude: number;
  radius_km: number;
  risk_level: string;
  base_premium_factor: number;
  is_active: boolean;
};

export type RiderPoliciesResponse = {
  rider_id: string;
  policies: PolicyListItem[];
};

export type RiderClaimsResponse = {
  rider_id: string;
  claims: ClaimListItem[];
};

export type PolicyDetailsResponse = {
  policy: PolicyListItem;
  rider: RiderListItem | null;
  zone: ZoneListItem | null;
  days_remaining: number;
  is_active: boolean;
};

export type RiderStatsResponse = {
  total_riders: number;
  active_riders: number;
  average_risk_score: number;
  by_persona: {
    qcommerce: number;
    food_delivery: number;
  };
};

export type TriggerStatusResponse = {
  zones: Record<
    string,
    {
      zone_name: string;
      city: string;
      triggers: Array<{
        zone_id: string;
        zone_name: string;
        trigger_type: string;
        current_value: number;
        threshold: number;
        is_active: boolean;
        affected_policies: number;
        last_updated: string;
        source: string;
      }>;
      active_count: number;
      checked_at: string;
    }
  >;
  total_zones: number;
  zones_with_triggers: number;
  checked_at: string;
};

export type RevenueMetricsResponse = {
  period_days: number;
  premium_collected: number;
  claims_paid: number;
  net_revenue: number;
  average_claim: number;
  loss_ratio: number;
};

export type TriggerDistributionResponse = {
  distribution: Array<{
    trigger_type: string;
    count: number;
    total_payout: number;
  }>;
};

export type PersonaBreakdownResponse = {
  personas: Array<{
    persona: string;
    count: number;
    average_risk_score: number;
  }>;
};

export type ZoneHeatmapResponse = {
  city?: string;
  points: Array<{
    zone_id: string;
    zone_name: string;
    city: string;
    latitude: number;
    longitude: number;
    radius_km: number;
    active_riders: number;
    active_policies: number;
    open_claims: number;
    avg_risk_score: number;
    heat_score: number;
  }>;
  count: number;
  generated_at: string;
};

export type ArchitectureResponse = {
  architecture: Record<string, string[]>;
  pipeline: string[];
};

export async function getDashboardStats() {
  return apiFetch<DashboardStatsResponse>('/dashboard/stats');
}

export async function getClaimsChart(days = 7) {
  return apiFetch<ClaimsChartResponse>(`/dashboard/claims-chart?days=${days}`);
}

export async function getRecentClaims(limit = 10) {
  return apiFetch<RecentClaimsResponse>(`/dashboard/recent-claims?limit=${limit}`);
}

export async function getLiveTriggers() {
  return apiFetch<LiveTriggersResponse>('/dashboard/live-triggers');
}

export async function getZoneStats() {
  return apiFetch<ZoneStatsResponse>('/dashboard/zone-stats');
}

export async function getClaims(params?: { status?: string; triggerType?: string }) {
  const search = new URLSearchParams();
  if (params?.status && params.status !== 'all') search.set('status', params.status);
  if (params?.triggerType && params.triggerType !== 'all') search.set('trigger_type', params.triggerType);
  const query = search.toString();
  return apiFetch<ClaimListItem[]>(`/claims/${query ? `?${query}` : ''}`);
}

export async function getClaimStats() {
  return apiFetch<ClaimStatsResponse>('/claims/stats/overview');
}

export async function approveClaim(claimId: string) {
  const headers = await getAuthHeaders();
  return fetch(`${API_BASE_URL}/claims/${claimId}/approve`, { method: 'POST', headers });
}

export async function rejectClaim(claimId: string) {
  const headers = await getAuthHeaders();
  return fetch(`${API_BASE_URL}/claims/${claimId}/reject`, { method: 'POST', headers });
}

export async function getPolicies(params?: { status?: string }) {
  const search = new URLSearchParams();
  if (params?.status && params.status !== 'all') search.set('status', params.status);
  const query = search.toString();
  return apiFetch<PolicyListItem[]>(`/policies/${query ? `?${query}` : ''}`);
}

export async function createPolicy(payload: {
  rider_id: string;
  zone_id: string;
  persona: 'qcommerce' | 'food_delivery';
  duration_days: number;
}) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/policies/`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Create policy failed: ${response.status}`);
  return response.json() as Promise<PolicyListItem>;
}

export async function getPolicyDetails(policyId: string) {
  return apiFetch<PolicyDetailsResponse>(`/policies/${policyId}/details`);
}

export async function cancelPolicy(policyId: string) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/policies/${policyId}/cancel`, { method: 'POST', headers });
  if (!response.ok) throw new Error(`Cancel policy failed: ${response.status}`);
  return response.json() as Promise<{ success: boolean; message: string }>;
}

export async function renewPolicy(policyId: string, durationDays = 7) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/policies/${policyId}/renew?duration_days=${durationDays}`, { method: 'POST', headers });
  if (!response.ok) throw new Error(`Renew policy failed: ${response.status}`);
  return response.json() as Promise<{ success: boolean }>;
}

export async function getPolicyStats() {
  return apiFetch<PolicyStatsResponse>('/policies/stats/overview');
}

export async function getRiders(params?: { status?: string }) {
  const search = new URLSearchParams();
  if (params?.status && params.status !== 'all') search.set('status', params.status);
  const query = search.toString();
  return apiFetch<RiderListItem[]>(`/riders/${query ? `?${query}` : ''}`);
}

export async function getRider(riderId: string) {
  return apiFetch<RiderListItem>(`/riders/${riderId}`);
}

export async function updateRider(
  riderId: string,
  payload: Partial<{
    name: string;
    email: string | null;
    persona: 'qcommerce' | 'food_delivery';
    zone_id: string;
    latitude: number;
    longitude: number;
    status: 'active' | 'inactive' | 'suspended';
  }>
) {
  const headers = await getAuthHeaders();
  const response = await fetch(`${API_BASE_URL}/riders/${riderId}`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json', ...headers },
    body: JSON.stringify(payload),
  });
  if (!response.ok) throw new Error(`Update rider failed: ${response.status}`);
  return response.json() as Promise<RiderListItem>;
}

export async function getRiderPolicies(riderId: string) {
  return apiFetch<RiderPoliciesResponse>(`/riders/${riderId}/policies`);
}

export async function getRiderClaims(riderId: string) {
  return apiFetch<RiderClaimsResponse>(`/riders/${riderId}/claims`);
}

export async function getZones(params?: { city?: string; is_active?: boolean }) {
  const search = new URLSearchParams();
  if (params?.city) search.set('city', params.city);
  if (typeof params?.is_active === 'boolean') search.set('is_active', String(params.is_active));
  const query = search.toString();
  return apiFetch<ZoneListItem[]>(`/zones/${query ? `?${query}` : ''}`);
}

export async function getRiderStats() {
  return apiFetch<RiderStatsResponse>('/riders/stats/overview');
}

export async function getTriggerStatus() {
  return apiFetch<TriggerStatusResponse>('/triggers/status');
}

export async function triggerRefresh() {
  const headers = await getAuthHeaders();
  return fetch(`${API_BASE_URL}/triggers/check`, { method: 'POST', headers });
}

export async function getRevenueMetrics(days = 7) {
  return apiFetch<RevenueMetricsResponse>(`/dashboard/revenue-metrics?days=${days}`);
}

export async function getTriggerDistribution() {
  return apiFetch<TriggerDistributionResponse>('/dashboard/trigger-distribution');
}

export async function getPersonaBreakdown() {
  return apiFetch<PersonaBreakdownResponse>('/dashboard/rider-personas');
}

export async function getZoneHeatmap(city?: string) {
  const query = city ? `?city=${encodeURIComponent(city)}` : '';
  return apiFetch<ZoneHeatmapResponse>(`/dashboard/zone-heatmap${query}`);
}

export async function getArchitecture() {
  return apiFetch<ArchitectureResponse>('/dashboard/architecture');
}
