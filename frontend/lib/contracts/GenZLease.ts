import { GenLayerContractBase, normalizeMapLike } from "./base";
import type { TransactionReceipt } from "./types";
import type {
  DisputePrecedentMatch,
  LandlordProfile,
  LeaseAgreement,
  PlatformStats,
  PropertyListing,
  TenantProfile,
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
}

export default GenZLease;
