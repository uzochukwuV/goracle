"use client";

import { useMemo } from "react";
import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import GenZLease from "../contracts/GenZLease";
import type { DisputePrecedentMatch, LandlordProfile, LeaseAgreement, PlatformStats, PropertyListing, TenantProfile } from "../contracts/genzlease-types";
import { getContractAddress, getStudioUrl } from "../genlayer/client";
import { useWallet } from "../genlayer/wallet";
import { configError, error, success } from "../utils/toast";

export function useGenZLeaseContract(): GenZLease | null {
  const { address } = useWallet();
  const contractAddress = getContractAddress();
  const studioUrl = getStudioUrl();

  return useMemo(() => {
    if (!contractAddress) {
      configError(
        "Setup Required",
        "Contract address not configured. Please set NEXT_PUBLIC_CONTRACT_ADDRESS in your .env file.",
      );
      return null;
    }

    return new GenZLease(contractAddress, address, studioUrl);
  }, [address, contractAddress, studioUrl]);
}

export function usePlatformStats() {
  const contract = useGenZLeaseContract();

  return useQuery<PlatformStats, Error>({
    queryKey: ["genzlease", "platformStats"],
    queryFn: async () => {
      if (!contract) throw new Error("Contract not configured");
      return contract.getPlatformStats();
    },
    enabled: !!contract,
    staleTime: 10_000,
  });
}

export function useListing(listingId: string | null) {
  const contract = useGenZLeaseContract();

  return useQuery<PropertyListing | null, Error>({
    queryKey: ["genzlease", "listing", listingId],
    queryFn: async () => {
      if (!contract || !listingId) return null;
      return contract.getListing(listingId);
    },
    enabled: !!contract && !!listingId,
  });
}

export function useLease(leaseId: string | null) {
  const contract = useGenZLeaseContract();

  return useQuery<LeaseAgreement | null, Error>({
    queryKey: ["genzlease", "lease", leaseId],
    queryFn: async () => {
      if (!contract || !leaseId) return null;
      return contract.getLease(leaseId);
    },
    enabled: !!contract && !!leaseId,
  });
}

export function useTenantProfile(tenantAddress: string | null) {
  const contract = useGenZLeaseContract();

  return useQuery<TenantProfile | null, Error>({
    queryKey: ["genzlease", "tenantProfile", tenantAddress],
    queryFn: async () => {
      if (!contract || !tenantAddress) return null;
      return contract.getTenantProfile(tenantAddress);
    },
    enabled: !!contract && !!tenantAddress,
  });
}

export function useLandlordProfile(landlordAddress: string | null) {
  const contract = useGenZLeaseContract();

  return useQuery<LandlordProfile | null, Error>({
    queryKey: ["genzlease", "landlordProfile", landlordAddress],
    queryFn: async () => {
      if (!contract || !landlordAddress) return null;
      return contract.getLandlordProfile(landlordAddress);
    },
    enabled: !!contract && !!landlordAddress,
  });
}

export function useDisputePrecedents(query: string, k = 5) {
  const contract = useGenZLeaseContract();

  return useQuery<DisputePrecedentMatch[], Error>({
    queryKey: ["genzlease", "precedents", query, k],
    queryFn: async () => {
      if (!contract || !query.trim()) return [];
      return contract.searchDisputePrecedents(query, k);
    },
    enabled: !!contract && !!query.trim(),
  });
}

export function useWithdrawFees() {
  const contract = useGenZLeaseContract();
  const { address } = useWallet();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async () => {
      if (!contract) throw new Error("Contract not configured");
      if (!address) throw new Error("Wallet not connected");
      return contract.withdrawFees();
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ["genzlease", "platformStats"] });
      success("Fees withdrawn", {
        description: "Platform fees have been withdrawn successfully.",
      });
    },
    onError: (err: Error) => {
      error("Failed to withdraw fees", { description: err.message });
    },
  });
}

export function useSetPaused() {
  const contract = useGenZLeaseContract();
  const { address } = useWallet();
  const queryClient = useQueryClient();

  return useMutation({
    mutationFn: async (paused: boolean) => {
      if (!contract) throw new Error("Contract not configured");
      if (!address) throw new Error("Wallet not connected");
      return contract.setPaused(paused);
    },
    onSuccess: (_, paused) => {
      queryClient.invalidateQueries({ queryKey: ["genzlease", "platformStats"] });
      success(paused ? "Protocol paused" : "Protocol resumed");
    },
    onError: (err: Error) => {
      error("Failed to update pause state", { description: err.message });
    },
  });
}
