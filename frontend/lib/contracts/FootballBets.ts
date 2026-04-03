import type { Bet, LeaderboardEntry, TransactionReceipt } from "./types";
import { GenLayerContractBase, normalizeMapLike } from "./base";

/**
 * FootballBets contract class for interacting with the GenLayer Football Betting contract
 */
class FootballBets extends GenLayerContractBase {
  /**
   * Get all bets from the contract
   */
  async getBets(): Promise<Bet[]> {
    try {
      const bets = await this.read("get_bets", []);
      const normalized = normalizeMapLike<Record<string, Record<string, Record<string, unknown>>>>(bets);

      return Object.entries(normalized).flatMap(([owner, playerBets]) =>
        Object.entries(playerBets || {}).map(([id, betData]) => {
          const data = (betData || {}) as Record<string, unknown>;
          return {
            id,
            owner,
            game_date: String(data.game_date || ""),
            team1: String(data.team1 || ""),
            team2: String(data.team2 || ""),
            predicted_winner: String(data.predicted_winner || ""),
            has_resolved: Boolean(data.has_resolved),
            real_winner: data.real_winner ? String(data.real_winner) : undefined,
            real_score: data.real_score ? String(data.real_score) : undefined,
            resolution_url: data.resolution_url ? String(data.resolution_url) : undefined,
          } as Bet;
        })
      );
    } catch (error) {
      console.error("Error fetching bets:", error);
      throw new Error("Failed to fetch bets from contract");
    }
  }

  async getPlayerPoints(address: string | null): Promise<number> {
    if (!address) {
      return 0;
    }

    try {
      const points = await this.read("get_player_points", [address]);
      return Number(points) || 0;
    } catch (error) {
      console.error("Error fetching player points:", error);
      return 0;
    }
  }

  async getLeaderboard(): Promise<LeaderboardEntry[]> {
    try {
      const points = await this.read("get_points", []);
      const normalized = normalizeMapLike<Record<string, unknown>>(points);

      return Object.entries(normalized)
        .map(([address, playerPoints]) => ({
          address,
          points: Number(playerPoints) || 0,
        }))
        .sort((a, b) => b.points - a.points);
    } catch (error) {
      console.error("Error fetching leaderboard:", error);
      throw new Error("Failed to fetch leaderboard from contract");
    }
  }

  async createBet(
    gameDate: string,
    team1: string,
    team2: string,
    predictedWinner: string
  ): Promise<TransactionReceipt> {
    try {
      const txHash = await this.write("create_bet", [gameDate, team1, team2, predictedWinner]);
      return (await this.waitForAccepted(txHash)) as TransactionReceipt;
    } catch (error) {
      console.error("Error creating bet:", error);
      throw new Error("Failed to create bet");
    }
  }

  async resolveBet(betId: string): Promise<TransactionReceipt> {
    try {
      const txHash = await this.write("resolve_bet", [betId]);
      return (await this.waitForAccepted(txHash)) as TransactionReceipt;
    } catch (error) {
      console.error("Error resolving bet:", error);
      throw new Error("Failed to resolve bet");
    }
  }
}

export default FootballBets;
