export const ASSET_COLORS: Record<string, string> = {
  TQQQ: "#1d4ed8",
  SOXL: "#0ea5e9",
  GLD: "#f59e0b",
  SVXY: "#8b5cf6",
  CASH: "#94a3b8",
};

export function targetWeightList(s: {
  target_weight_tqqq: number;
  target_weight_soxl: number;
  target_weight_gld: number;
  target_weight_svxy: number;
  target_weight_cash: number;
}) {
  return [
    { label: "TQQQ", value: s.target_weight_tqqq, color: ASSET_COLORS.TQQQ },
    { label: "SOXL", value: s.target_weight_soxl, color: ASSET_COLORS.SOXL },
    { label: "GLD", value: s.target_weight_gld, color: ASSET_COLORS.GLD },
    { label: "SVXY", value: s.target_weight_svxy, color: ASSET_COLORS.SVXY },
    { label: "CASH", value: s.target_weight_cash, color: ASSET_COLORS.CASH },
  ];
}
