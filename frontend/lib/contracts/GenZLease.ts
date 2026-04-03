import { GenLayerContractBase, normalizeMapLike } from "./base";
import type { TransactionReceipt } from "./types";
import type {
  DisputePrecedentMatch,
  LandlordProfile,
  LeaseAgreement,
  PlatformStats,
  PropertyListing,
  ListPropertyInput,
  RaiseDisputeInput,
  RequestLeaseInput,
  TenantProfile,
  UpdateListingTermsInput,
} from "./genzlease-types";

class GenZLease extends GenLayerContractBase {
  async getListing(listingId: string): Promise<PropertyListing | null> {
    const result = await this.read("get_listing", [listingId]);
    if (!result) return null;
    return normalizeMapLike<PropertyListing>(result);
  }

  async getLease(leaseId: string): Promise<LeaseAgreement | null> {
    const result = await this.read("get_lease", [leaseId]);
    if (!result) return null;
    return normalizeMapLike<LeaseAgreement>(result);
  }

  async getPlatformStats(): Promise<PlatformStats> {
    const result = await this.read("get_platform_stats", []);
    return normalizeMapLike<PlatformStats>(result);
  }

  async getTenantProfile(tenantAddress: string): Promise<TenantProfile | null> {
    const result = await this.read("get_tenant_profile", [tenantAddress]);
    if (!result) return null;
    return normalizeMapLike<TenantProfile>(result);
  }

  async getLandlordProfile(landlordAddress: string): Promise<LandlordProfile | null> {
    const result = await this.read("get_landlord_profile", [landlordAddress]);
    if (!result) return null;
    return normalizeMapLike<LandlordProfile>(result);
  }

  async searchDisputePrecedents(query: string, k = 5): Promise<DisputePrecedentMatch[]> {
    const result = await this.read("search_dispute_precedents", [query, k]);
    return normalizeMapLike<DisputePrecedentMatch[]>(result) || [];
  }

  async withdrawFees(): Promise<TransactionReceipt> {
    const txHash = await this.write("withdraw_fees", []);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async setPaused(paused: boolean): Promise<TransactionReceipt> {
    const txHash = await this.write("set_paused", [paused]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async listProperty(input: ListPropertyInput): Promise<TransactionReceipt> {
    const txHash = await this.write("list_property", [
      input.titleNumber,
      input.ownerFullName,
      input.propertyAddress,
      input.postcode,
      input.pricePerMonth,
      input.minDurationMonths,
      input.maxDurationMonths,
      input.depositMonths,
      input.availableFrom,
      input.bedrooms,
      input.bathrooms,
      input.propertyType,
      input.description,
      input.amenities ?? "[]",
      input.imagesIpfs ?? "[]",
      input.availableTo ?? 0,
    ]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async updateListingTerms(input: UpdateListingTermsInput): Promise<TransactionReceipt> {
    const txHash = await this.write("update_listing_terms", [
      input.listingId,
      input.pricePerMonth ?? BigInt(0),
      input.availableFrom ?? 0,
      input.availableTo ?? 0,
      input.minDurationMonths ?? 0,
      input.maxDurationMonths ?? 0,
      input.description ?? "",
      input.amenities ?? "",
      input.imagesIpfs ?? "",
    ]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async verifyOwnership(listingId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("verify_ownership", [listingId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async requestLease(input: RequestLeaseInput): Promise<TransactionReceipt> {
    const txHash = await this.write("request_lease", [
      input.listingId,
      input.startDate,
      input.durationMonths,
      input.messageToLandlord ?? "",
    ]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async acceptLease(leaseId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("accept_lease", [leaseId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async payDepositAndFirstMonth(leaseId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("pay_deposit_and_first_month", [leaseId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async payMonthlyRent(leaseId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("pay_monthly_rent", [leaseId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async claimRent(leaseId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("claim_rent", [leaseId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async completeLease(leaseId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("complete_lease", [leaseId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async raiseDispute(input: RaiseDisputeInput): Promise<TransactionReceipt> {
    const txHash = await this.write("raise_dispute", [
      input.leaseId,
      input.reason,
      input.evidenceUrls,
    ]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }

  async resolveDispute(leaseId: string): Promise<TransactionReceipt> {
    const txHash = await this.write("resolve_dispute", [leaseId]);
    return (await this.waitForAccepted(txHash)) as TransactionReceipt;
  }
}

export default GenZLease;
