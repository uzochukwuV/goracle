import { createClient } from "genlayer-js";
import { studionet } from "genlayer-js/chains";
import type { CalldataEncodable, Hash } from "genlayer-js/types";

export interface BaseTransactionReceipt {
  status: string;
  hash: string;
  blockNumber?: number;
  [key: string]: unknown;
}

export type PrimitiveMapLike = Map<unknown, unknown> | Record<string, unknown>;

export function normalizeMapLike<T = unknown>(value: unknown): T {
  if (value instanceof Map) {
    const out: Record<string, unknown> = {};
    for (const [key, nested] of value.entries()) {
      out[String(key)] = normalizeMapLike(nested);
    }
    return out as T;
  }

  if (Array.isArray(value)) {
    return value.map((item) => normalizeMapLike(item)) as T;
  }

  if (value && typeof value === "object") {
    const out: Record<string, unknown> = {};
    for (const [key, nested] of Object.entries(value as Record<string, unknown>)) {
      out[key] = normalizeMapLike(nested);
    }
    return out as T;
  }

  return value as T;
}

export class GenLayerContractBase {
  protected contractAddress: `0x${string}`;
  protected endpoint?: string;
  protected account?: `0x${string}`;
  protected client: ReturnType<typeof createClient>;

  constructor(contractAddress: string, account?: string | null, endpoint?: string) {
    this.contractAddress = contractAddress as `0x${string}`;
    this.endpoint = endpoint;
    this.account = account ? (account as `0x${string}`) : undefined;
    this.client = this.createClient();
  }

  private createClient(): ReturnType<typeof createClient> {
    const config: {
      chain: typeof studionet;
      account?: `0x${string}`;
      endpoint?: string;
    } = {
      chain: studionet,
    };

    if (this.account) {
      config.account = this.account;
    }

    if (this.endpoint) {
      config.endpoint = this.endpoint;
    }

    return createClient(config);
  }

  updateAccount(account: string | null): void {
    this.account = account ? (account as `0x${string}`) : undefined;
    this.client = this.createClient();
  }

  protected async read(functionName: string, args: CalldataEncodable[] = []): Promise<unknown> {
    return this.client.readContract({
      address: this.contractAddress,
      functionName,
      args,
    });
  }

  protected async write(
    functionName: string,
    args: CalldataEncodable[] = [],
    value: bigint = BigInt(0)
  ): Promise<Hash> {
    return this.client.writeContract({
      address: this.contractAddress,
      functionName,
      args,
      value,
    }) as Promise<Hash>;
  }

  async waitForAccepted(hash: Hash): Promise<BaseTransactionReceipt> {
    const receipt = await this.client.waitForTransactionReceipt({
      hash,
      status: "ACCEPTED" as any,
      retries: 24,
      interval: 5000,
    });

    return receipt as BaseTransactionReceipt;
  }

  async getTransaction(hash: Hash): Promise<unknown> {
    return this.client.getTransaction({ hash });
  }

  async getTransactionReceipt(hash: Hash): Promise<unknown> {
    return this.client.getTransactionReceipt({ hash });
  }
}
