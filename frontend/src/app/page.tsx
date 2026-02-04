"use client";

import { useState, useEffect, useCallback } from "react";
import {
  Search,
  Plus,
  Trash2,
  Copy,
  Check,
  AlertCircle,
  ChevronRight,
  Zap,
  Package,
  Tag,
  DollarSign,
  Clipboard,
  ShoppingCart,
  Info
} from "lucide-react";
import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";
import {
  calculateQuote,
  getCatalog,
  getAccountTier,
  getSystemStatus,
  CalcResult,
  LineItem
} from "@/lib/api";

function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

const KNOWN_ACCOUNTS = [
  { id: "25160", name: "Game One", group: "GAME_ONE" },
  { id: "11730", name: "BSN Sports", group: "BSN" },
  { id: "1389", name: "Johnson Lambe (Alli)", group: "ALLI_GROUP" },
  { id: "6812", name: "Bakers (Alli)", group: "ALLI_GROUP" },
  { id: "1336", name: "Sportstop (Alli)", group: "ALLI_GROUP" },
  { id: "10980", name: "League Outfitters", group: "LEAGUE" },
  { id: "0013", name: "Certor Direct (AYF)", group: "DIRECT_AYF" },
];

export default function AvanteCompanion() {
  // Account Context
  const [accountNumber, setAccountNumber] = useState("25160");
  const [accountTier, setAccountTier] = useState<string | null>(null);
  const [accountIntel, setAccountIntel] = useState<{ Freight?: string, Terms?: string, Notes?: string }>({});
  const [tierTrace, setTierTrace] = useState<string[]>([]);

  // SKU Lookup
  const [searchTerm, setSearchTerm] = useState("");
  const [catalogItems, setCatalogItems] = useState<Record<string, any>>({});
  const [selectedSku, setSelectedSku] = useState<string | null>(null);

  // Order Builder
  const [cart, setCart] = useState<Record<string, number>>({});
  const [calcResult, setCalcResult] = useState<CalcResult | null>(null);

  // Context Fields
  const [orderDate, setOrderDate] = useState(new Date().toISOString().split('T')[0]);
  const [orderType, setOrderType] = useState<number>(0); // 0 = Standard
  const [paymentMethod, setPaymentMethod] = useState("CHECK");
  const [shipMethod, setShipMethod] = useState("GROUND");
  const [shipToType, setShipToType] = useState("DOMESTIC_STANDARD");

  // UI State
  const [copiedField, setCopiedField] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);

  // Load account tier when number changes
  useEffect(() => {
    const fetchTier = async () => {
      if (accountNumber.length < 2) return;
      try {
        const data = await getAccountTier(accountNumber);
        setAccountTier(data.tier);
        setTierTrace(data.trace || []);
        setAccountIntel(data.intel || {});
      } catch (e) {
        console.error("Tier fetch error", e);
        setAccountTier("MSRP");
        setAccountIntel({});
      }
    };
    fetchTier();
  }, [accountNumber]);

  // Fetch catalog on search
  useEffect(() => {
    const timer = setTimeout(async () => {
      try {
        const data = await getCatalog(searchTerm, accountNumber);
        setCatalogItems(data);
      } catch (e) {
        console.error("Catalog error", e);
      }
    }, 300);
    return () => clearTimeout(timer);
  }, [searchTerm, accountNumber]);

  // Calculate quote whenever cart or context changes
  useEffect(() => {
    const fetchCalc = async () => {
      if (Object.keys(cart).length === 0) {
        setCalcResult(null);
        return;
      }
      try {
        const res = await calculateQuote({
          account_id: accountNumber,
          items: cart,
          request_date: orderDate,
          order_type: orderType,
          payment_method: paymentMethod,
          ship_method: shipMethod,
          ship_to_type: shipToType
        });
        setCalcResult(res);
        if (res.intel) setAccountIntel(res.intel);
      } catch (e) {
        console.error("Calculation error", e);
      }
    };
    fetchCalc();
  }, [cart, accountNumber, orderDate, orderType, paymentMethod, shipMethod, shipToType]);

  const addToCart = (sku: string, qty: number = 1) => {
    setCart(prev => ({ ...prev, [sku]: (prev[sku] || 0) + qty }));
    setSelectedSku(sku);
  };

  const removeFromCart = (sku: string) => {
    const newCart = { ...cart };
    delete newCart[sku];
    setCart(newCart);
    if (selectedSku === sku) setSelectedSku(null);
  };

  const updateQty = (sku: string, newQty: number) => {
    if (newQty <= 0) {
      removeFromCart(sku);
    } else {
      setCart(prev => ({ ...prev, [sku]: newQty }));
    }
  };

  const clearOrder = () => {
    if (window.confirm("Clear all items from order?")) {
      setCart({});
      setSelectedSku(null);
    }
  };

  const copyToClipboard = (text: string, fieldId: string) => {
    navigator.clipboard.writeText(text);
    setCopiedField(fieldId);
    setTimeout(() => setCopiedField(null), 2000);
  };

  const getTierPrice = (sku: string): number | null => {
    const item = catalogItems[sku];
    if (!item) return null;
    if (item.YourPrice != null) return item.YourPrice;
    if (!accountTier) return null;
    const tierCol = `${accountTier}_Price`;
    return item[tierCol] ?? item.MSRP ?? null;
  };

  const getPriceSource = (sku: string): string => {
    const item = catalogItems[sku];
    if (!item) return "Unknown";
    if (item.RuleApplied) return "Rule";
    if (!accountTier) return "MSRP";
    const tierCol = `${accountTier}_Price`;
    if (item[tierCol] != null) return accountTier;
    return "MSRP";
  };

  // Get the line item from calc result for a SKU
  const getLineItem = (sku: string): LineItem | undefined => {
    return calcResult?.lines.find(l => l.sku === sku);
  };

  return (
    <div className="flex flex-col h-screen bg-[#0a0a0a] text-gray-200 overflow-hidden">
      {/* ═══════════════════════════════════════════════════════════════════════
          ACCOUNT CONTEXT BAR
          ═══════════════════════════════════════════════════════════════════════ */}
      <header className="bg-[#111] border-b border-white/10 px-4 py-2">
        <div className="flex items-center justify-between gap-8">
          <div className="flex items-center gap-6">
            <div className="flex items-center gap-3">
              <div>
                <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Account Number</label>
                <div className="flex items-center gap-2">
                  <input
                    type="text"
                    value={accountNumber}
                    onChange={(e) => setAccountNumber(e.target.value)}
                    className="bg-black border border-white/20 rounded-lg px-2 py-1 text-base font-mono font-bold w-24 focus:outline-none focus:border-blue-500 transition-colors"
                  />
                  <select
                    onChange={(e) => setAccountNumber(e.target.value)}
                    value={KNOWN_ACCOUNTS.find(a => a.id === accountNumber) ? accountNumber : ""}
                    className="bg-white/5 border border-white/10 rounded-lg px-2 py-1.5 text-xs font-semibold text-gray-400 focus:outline-none hover:bg-white/10 cursor-pointer"
                  >
                    <option value="" disabled>Quick Select...</option>
                    {KNOWN_ACCOUNTS.map(acc => (
                      <option key={acc.id} value={acc.id}>{acc.name}</option>
                    ))}
                  </select>
                </div>
              </div>
            </div>

            <div className="h-10 w-px bg-white/10" />

            <div>
              <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Pricing Strategy</label>
              <div className="flex items-center gap-2">
                <span className={cn(
                  "text-lg font-black tracking-tight",
                  accountTier === "GOLD" ? "text-yellow-400" :
                    accountTier === "PLATINUM" ? "text-blue-400" :
                      accountTier === "SILVER" ? "text-gray-300" :
                        accountTier === "BRONZE" ? "text-orange-400" :
                          "text-gray-500"
                )}>
                  {accountTier || "RESOLVING..."}
                </span>
                {accountTier && accountTier !== "MSRP" && (
                  <span className="px-1.5 py-0.5 bg-green-500/20 text-green-400 text-[9px] font-bold rounded uppercase border border-green-500/20">
                    Contract
                  </span>
                )}
              </div>
            </div>

            <div className="h-10 w-px bg-white/10" />

            <div className="h-10 w-px bg-white/10" />

            <div className="flex items-center gap-6">
              <div>
                <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Freight Policy</label>
                <div className={cn(
                  "text-xs font-bold",
                  calcResult?.policy?.freight?.mode === "FFA" ? "text-green-400" : "text-gray-200"
                )}>
                  {calcResult?.policy?.freight?.mode ? (
                    <span>{calcResult.policy.freight.mode} {calcResult.policy.freight.ffa_percent ? `(${calcResult.policy.freight.ffa_percent}%)` : ""}</span>
                  ) : (accountIntel.Freight || "MSRP Standard")}
                </div>
              </div>
              <div>
                <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Payment Terms</label>
                <div className="text-xs font-bold text-gray-200">
                  {calcResult?.policy?.terms?.code || accountIntel.Terms || "Prepaid"}
                  {calcResult?.policy?.terms?.due_date && <span className="ml-1 opacity-50 font-normal">due {calcResult.policy.terms.due_date}</span>}
                </div>
              </div>
            </div>

            <div className="h-10 w-px bg-white/10" />

            <div className="flex items-center gap-4">
              <div>
                <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Request Date</label>
                <input
                  type="date"
                  value={orderDate}
                  onChange={(e) => setOrderDate(e.target.value)}
                  className="bg-black/50 border border-white/10 rounded px-2 py-1 text-[11px] h-8 focus:outline-none focus:border-blue-500 font-mono"
                />
              </div>
              <div>
                <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Order Type</label>
                <select
                  value={orderType}
                  onChange={(e) => setOrderType(parseInt(e.target.value))}
                  className="bg-black/50 border border-white/10 rounded px-2 py-1 text-[11px] h-8 focus:outline-none focus:border-blue-500"
                >
                  <option value={0}>Standard</option>
                  <option value={6}>International</option>
                  <option value={25}>Trade-In</option>
                  <option value={26}>Employee</option>
                </select>
              </div>
              <div>
                <label className="text-[9px] font-bold uppercase tracking-widest text-gray-500 block mb-1">Ship Method</label>
                <select
                  value={shipMethod}
                  onChange={(e) => setShipMethod(e.target.value)}
                  className="bg-black/50 border border-white/10 rounded px-2 py-1 text-[11px] h-8 focus:outline-none focus:border-blue-500"
                >
                  <option value="GROUND">Standard (Ground)</option>
                  <option value="PRIORITY OVERNIGHT">Priority Overnight</option>
                  <option value="FEDEX_2_DAY">FedEx 2Day</option>
                </select>
              </div>
            </div>
          </div>

          <div className="flex items-center gap-4">
            <a
              href="/admin/rules"
              className="px-3 py-1.5 bg-white/5 hover:bg-white/10 border border-white/10 rounded-lg text-xs font-semibold text-gray-400 hover:text-white transition-colors"
            >
              Rules Admin
            </a>
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Subtotal</div>
              <div className="text-xl font-bold">${calcResult?.total.toFixed(2) || "0.00"}</div>
            </div>
            <div className="h-10 w-px bg-white/10" />
            <div className="text-right">
              <div className="text-[10px] uppercase tracking-widest text-gray-500">Final Total</div>
              <div className="text-xl font-bold text-green-400">
                ${(
                  (calcResult?.total || 0) +
                  (calcResult?.policy?.adjustments?.reduce((sum, a) => sum + a.amount, 0) || 0)
                ).toFixed(2)}
              </div>
            </div>
          </div>
        </div>
      </header>


      {/* ═══════════════════════════════════════════════════════════════════════
          MAIN CONTENT: TWO-PANEL LAYOUT
          ═══════════════════════════════════════════════════════════════════════ */}
      <div className="flex-1 flex overflow-hidden">

        {/* ─────────────────────────────────────────────────────────────────────
            LEFT PANEL: SKU LOOKUP
            ───────────────────────────────────────────────────────────────────── */}
        <div className="w-1/2 flex flex-col border-r border-white/10 bg-[#080808]">
          <div className="p-4 border-b border-white/10">
            <div className="relative">
              <Search className="absolute left-4 top-1/2 -translate-y-1/2 text-gray-500" size={20} />
              <input
                type="text"
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
                className="w-full bg-black border border-white/10 rounded-xl pl-12 pr-4 py-3 text-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50"
                placeholder="Search SKU or description..."
                autoFocus
              />
            </div>
          </div>

          <div className="flex-1 overflow-y-auto p-4 space-y-3">
            {Object.entries(catalogItems).map(([sku, data]: [string, any]) => {
              const price = getTierPrice(sku);
              const source = getPriceSource(sku);
              const isInCart = sku in cart;
              const isRule = data.RuleApplied;

              return (
                <div
                  key={sku}
                  onClick={() => addToCart(sku)}
                  className={cn(
                    "p-3 rounded-lg border cursor-pointer transition-all",
                    isInCart
                      ? "bg-blue-500/10 border-blue-500/30"
                      : "bg-[#0f0f0f] border-white/5 hover:border-white/20"
                  )}
                >
                  <div className="flex items-start justify-between gap-4">
                    <div className="flex-1">
                      <div className="flex items-center gap-2 mb-0.5">
                        <span className="text-base font-mono font-bold text-white">{sku}</span>
                        <span className={cn(
                          "px-1 py-0.5 text-[8px] font-bold rounded uppercase",
                          isRule
                            ? "bg-blue-500 text-white"
                            : source === "MSRP"
                              ? "bg-gray-500/20 text-gray-400"
                              : "bg-green-500/20 text-green-400"
                        )}>
                          {isRule ? "Rule" : source}
                        </span>
                        {isInCart && (
                          <span className="px-1 py-0.5 bg-blue-500/20 text-blue-400 text-[8px] font-bold rounded">
                            IN ORDER
                          </span>
                        )}
                      </div>
                      <p className="text-xs text-gray-400 line-clamp-1">{data.Description}</p>
                    </div>

                    <div className="text-right">
                      <div className="text-[9px] uppercase text-gray-500 mb-0.5">Price</div>
                      <div className={cn(
                        "text-xl font-black",
                        isRule ? "text-blue-400" : "text-white"
                      )}>
                        ${price?.toFixed(2) || "N/A"}
                      </div>
                      {data.MSRP && price && price < data.MSRP && (
                        <div className="text-[9px] text-green-500 font-bold">
                          -${(data.MSRP - price).toFixed(2)}
                        </div>
                      )}
                    </div>
                  </div>
                </div>
              );
            })}

            {Object.keys(catalogItems).length === 0 && searchTerm && (
              <div className="text-center py-12 text-gray-500">
                <Package size={48} className="mx-auto mb-4 opacity-30" />
                <p>No products found for "{searchTerm}"</p>
              </div>
            )}
          </div>
        </div>

        {/* ─────────────────────────────────────────────────────────────────────
            RIGHT PANEL: ORDER BUILDER / AVANTE ENTRY
            ───────────────────────────────────────────────────────────────────── */}
        <div className="w-1/2 flex flex-col bg-[#0a0a0a]">
          <div className="px-4 py-3 border-b border-white/10 bg-[#0f0f0f] flex items-center justify-between">
            <h2 className="text-sm font-bold text-white flex items-center gap-2 uppercase tracking-wide">
              <ShoppingCart size={16} className="text-blue-500" />
              Order Builder
            </h2>
            {Object.keys(cart).length > 0 && (
              <button
                onClick={clearOrder}
                className="text-[10px] text-gray-500 hover:text-red-400 transition-colors uppercase font-bold"
              >
                Clear All
              </button>
            )}
          </div>

          <div className="flex-1 overflow-auto">
            {calcResult && calcResult.lines.length > 0 ? (
              <table className="w-full text-left border-collapse">
                <thead className="sticky top-0 bg-[#0f0f0f] border-b border-white/10 z-10">
                  <tr className="text-[10px] uppercase tracking-wider text-gray-500">
                    <th className="px-4 py-2 font-bold">SKU</th>
                    <th className="px-4 py-2 font-bold text-right">Price</th>
                    <th className="px-4 py-2 font-bold text-center w-24">Qty</th>
                    <th className="px-4 py-2 font-bold text-right">Ext</th>
                    <th className="px-4 py-2 w-10"></th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-white/5">
                  {calcResult.lines.map((line) => (
                    <tr key={line.sku} className="group hover:bg-white/[0.02] transition-colors">
                      <td className="px-4 py-2">
                        <div className="flex flex-col">
                          <div className="flex items-center gap-2">
                            <span className="text-sm font-mono font-bold text-white truncate">{line.sku}</span>
                            <span className={cn(
                              "px-1 py-0.5 text-[7px] font-bold rounded uppercase",
                              line.source === "Rule"
                                ? "bg-blue-500 text-white"
                                : line.source === "Contract"
                                  ? "bg-green-500/20 text-green-400"
                                  : "bg-gray-500/20 text-gray-400"
                            )}>
                              {line.source === "Rule" ? "R" : line.source === "Contract" ? "C" : "M"}
                            </span>
                          </div>
                          <span className="text-[10px] text-gray-500 truncate max-w-[150px]">
                            {line.description}
                          </span>
                        </div>
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => copyToClipboard(line.unit_price.toFixed(2), `price-${line.sku}`)}
                          className={cn(
                            "text-base font-black px-2 py-1 rounded-md transition-all flex items-center gap-2 ml-auto",
                            copiedField === `price-${line.sku}`
                              ? "bg-green-500 text-white"
                              : "text-white hover:bg-white/10"
                          )}
                        >
                          ${line.unit_price.toFixed(2)}
                          {copiedField === `price-${line.sku}` ? <Check size={12} /> : <Clipboard size={12} className="opacity-0 group-hover:opacity-100" />}
                        </button>
                      </td>
                      <td className="px-4 py-2 text-center">
                        <input
                          type="number"
                          value={cart[line.sku] || 0}
                          onChange={(e) => updateQty(line.sku, parseInt(e.target.value) || 0)}
                          className="w-16 bg-black border border-white/10 rounded px-2 py-1 text-center font-mono font-bold text-sm"
                          min="1"
                        />
                      </td>
                      <td className="px-4 py-2 text-right font-bold text-blue-400 text-sm">
                        ${line.extended_price.toFixed(2)}
                      </td>
                      <td className="px-4 py-2 text-right">
                        <button
                          onClick={() => removeFromCart(line.sku)}
                          className="p-1.5 text-gray-600 hover:text-red-400 hover:bg-red-500/10 rounded-md transition-colors opacity-0 group-hover:opacity-100"
                        >
                          <Trash2 size={14} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            ) : (
              <div className="flex-1 flex flex-col items-center justify-center text-center py-16">
                <ShoppingCart size={48} className="text-gray-800 mb-4" />
                <h3 className="text-lg font-medium text-gray-400 mb-1">No Items</h3>
                <p className="text-xs text-gray-600 max-w-[200px]">
                  Add items from the catalog to build your order.
                </p>
              </div>
            )}
          </div>

          {/* Order Summary Footer */}
          {calcResult && calcResult.lines.length > 0 && (
            <div className="p-4 bg-[#0f0f0f] border-t border-white/10 space-y-4">
              {/* Policy Alerts */}
              {(calcResult.policy?.holds?.length > 0 || calcResult.policy?.needs_review) && (
                <div className="space-y-2">
                  {calcResult.policy.holds.map(hold => (
                    <div key={hold.code} className="flex items-start gap-2 p-2 bg-red-500/10 border border-red-500/20 rounded text-red-400 text-xs">
                      <AlertCircle size={14} className="mt-0.5" />
                      <div>
                        <span className="font-bold mr-2">{hold.code}</span>
                        {hold.message}
                      </div>
                    </div>
                  ))}
                  {calcResult.policy.needs_review && (
                    <div className="flex items-start gap-2 p-2 bg-yellow-500/10 border border-yellow-500/20 rounded text-yellow-400 text-xs">
                      <Zap size={14} className="mt-0.5" />
                      <div>
                        <span className="font-bold mr-2">REVIEW REQUIRED</span>
                        {calcResult.policy.review_reason}
                      </div>
                    </div>
                  )}
                </div>
              )}

              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <div className="text-xs text-gray-500">{calcResult.lines.length} line items</div>
                  {calcResult.policy?.adjustments?.map(adj => (
                    <div key={adj.code} className="text-xs text-blue-400 font-medium">
                      + {adj.amount.toFixed(2)} {adj.description} ({adj.code})
                    </div>
                  ))}
                </div>
                <div className="text-right">
                  <div className="text-[10px] uppercase text-gray-500">Order Total</div>
                  <div className="text-3xl font-black text-green-400">
                    ${(
                      (calcResult?.total || 0) +
                      (calcResult?.policy?.adjustments?.reduce((sum, a) => sum + a.amount, 0) || 0)
                    ).toFixed(2)}
                  </div>
                </div>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
