import type { TransactionReceipt } from "./types";

export interface PropertyListing {
  listing_id: string;
  title_number: string;
  owner: string;
  property_address: string;
  postcode: string;
  price_per_month: string;
  min_duration_months: number;
  max_duration_months: number;
  deposit_months: number;
  available_from: number;
  available_to: number;
  bedrooms: number;
  bathrooms: number;
  property_type: string;
  description: string;
  amenities: string;
  images_ipfs: string;
  verification_status: string;
  hmlr_tenure: string;
  encumbrances_found: boolean;
  verification_notes: string;
  listing_status: string;
  verified_at: number;
  active_lease_id: string;
  total_leases: number;
  total_revenue: string;
}

export interface LeaseAgreement {
  lease_id: string;
  listing_id: string;
  landlord: string;
  tenant: string;
  start_date: number;
  end_date: number;
  duration_months: number;
  monthly_rent: string;
  total_rent: string;
  deposit_amount: string;
  escrow_balance: string;
  rent_paid_to: number;
  next_payment_due: number;
  status: string;
  dispute_raised_by: string;
  dispute_reason: string;
  dispute_outcome: string;
  landlord_split_bps: number;
  ai_reasoning: string;
  callback_posted: boolean;
}

export interface PlatformStats {
  total_listings: number;
  total_leases_created: number;
  total_leases_completed: number;
  total_disputes: number;
  total_escrow: string;
  total_fees_collected: string;
  total_precedents: number;
  platform_fee_bps: number;
  paused: boolean;
}

export interface TenantProfile {
  tenant: string;
  total_leases: number;
  completed_leases: number;
  disputed_leases: number;
  disputes_won: number;
  total_spent: string;
  reputation_score: number;
}

export interface LandlordProfile {
  landlord: string;
  total_listings: number;
  verified_listings: number;
  total_leases: number;
  completed_leases: number;
  disputed_leases: number;
  total_revenue: string;
  reputation_score: number;
}

export interface DisputePrecedentMatch {
  dispute_summary: string;
  outcome: string;
  landlord_split_pct: number;
  similarity: number;
}

export interface ListPropertyInput {
  titleNumber: string;
  ownerFullName: string;
  propertyAddress: string;
  postcode: string;
  pricePerMonth: bigint;
  minDurationMonths: number;
  maxDurationMonths: number;
  depositMonths: number;
  availableFrom: number;
  bedrooms: number;
  bathrooms: number;
  propertyType: string;
  description: string;
  amenities?: string;
  imagesIpfs?: string;
  availableTo?: number;
}

export interface UpdateListingTermsInput {
  listingId: string;
  pricePerMonth?: bigint;
  availableFrom?: number;
  availableTo?: number;
  minDurationMonths?: number;
  maxDurationMonths?: number;
  description?: string;
  amenities?: string;
  imagesIpfs?: string;
}

export interface RequestLeaseInput {
  listingId: string;
  startDate: number;
  durationMonths: number;
  messageToLandlord?: string;
}

export interface RaiseDisputeInput {
  leaseId: string;
  reason: string;
  evidenceUrls: string[];
}

export interface GenZLeaseWriteResult extends TransactionReceipt {
  hash: string;
}
