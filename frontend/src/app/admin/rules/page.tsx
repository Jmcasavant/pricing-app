"use client";

import { useState, useEffect, useCallback } from "react";
import {
    getRules,
    getRuleStats,
    createRule,
    updateRule,
    deleteRule,
    testRule,
    Rule,
    RuleCreate,
    RuleStats,
    RuleTestResult,
} from "@/lib/rules-api";
import {
    Plus,
    Search,
    Trash2,
    Edit2,
    Check,
    X,
    AlertTriangle,
    CheckCircle,
    RefreshCw,
    Filter,
    TestTube,
    ChevronLeft,
} from "lucide-react";
import Link from "next/link";

const ACTION_TYPES = [
    { value: "override_unit_price", label: "Override Price" },
    { value: "discount_amount", label: "Discount Amount" },
    { value: "discount_percent", label: "Discount %" },
    { value: "price_floor", label: "Price Floor" },
];

const KNOWN_GROUPS = [
    "GAME_ONE",
    "BSN",
    "ALLI_GROUP",
    "LEAGUE",
    "BADGER_GROUP",
];

export default function RulesAdminPage() {
    // State
    const [rules, setRules] = useState<Rule[]>([]);
    const [stats, setStats] = useState<RuleStats | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [search, setSearch] = useState("");
    const [filterGroup, setFilterGroup] = useState<string>("");
    const [showInactive, setShowInactive] = useState(true);

    // Edit state
    const [editingRule, setEditingRule] = useState<Rule | null>(null);
    const [isCreating, setIsCreating] = useState(false);

    // Test state
    const [testAccountId, setTestAccountId] = useState("");
    const [testSku, setTestSku] = useState("");
    const [testResult, setTestResult] = useState<RuleTestResult | null>(null);
    const [testLoading, setTestLoading] = useState(false);

    // Load rules
    const loadRules = useCallback(async () => {
        try {
            setLoading(true);
            const [rulesData, statsData] = await Promise.all([
                getRules(showInactive),
                getRuleStats(),
            ]);
            setRules(rulesData);
            setStats(statsData);
            setError(null);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to load rules");
        } finally {
            setLoading(false);
        }
    }, [showInactive]);

    useEffect(() => {
        loadRules();
    }, [loadRules]);

    // Filter rules
    const filteredRules = rules.filter((rule) => {
        const matchesSearch =
            !search ||
            rule.name.toLowerCase().includes(search.toLowerCase()) ||
            rule.rule_id.toLowerCase().includes(search.toLowerCase()) ||
            rule.sku?.toLowerCase().includes(search.toLowerCase()) ||
            rule.sku_prefix?.toLowerCase().includes(search.toLowerCase());

        const matchesGroup =
            !filterGroup ||
            rule.account_group === filterGroup ||
            rule.account === filterGroup;

        return matchesSearch && matchesGroup;
    });

    // Handlers
    const handleSaveRule = async (rule: Rule | RuleCreate) => {
        try {
            if ("rule_id" in rule && rule.rule_id && !isCreating) {
                await updateRule(rule.rule_id, rule);
            } else {
                await createRule(rule as RuleCreate);
            }
            setEditingRule(null);
            setIsCreating(false);
            loadRules();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to save");
        }
    };

    const handleDeleteRule = async (ruleId: string) => {
        if (!confirm(`Delete rule "${ruleId}"?`)) return;
        try {
            await deleteRule(ruleId);
            loadRules();
        } catch (e) {
            setError(e instanceof Error ? e.message : "Failed to delete");
        }
    };

    const handleTest = async () => {
        if (!testAccountId || !testSku) return;
        try {
            setTestLoading(true);
            const result = await testRule(testAccountId, testSku);
            setTestResult(result);
        } catch (e) {
            setError(e instanceof Error ? e.message : "Test failed");
        } finally {
            setTestLoading(false);
        }
    };

    const startCreate = () => {
        setIsCreating(true);
        setEditingRule({
            rule_id: "",
            name: "",
            active: true,
            priority: 50,
            account: null,
            account_group: null,
            sku: null,
            sku_prefix: null,
            brand: null,
            min_qty: null,
            max_qty: null,
            start_date: "2026-01-01",
            end_date: "2026-04-30",
            channel: "all",
            action_type: "override_unit_price",
            action_value: "",
            notes: null,
        });
    };

    return (
        <div className="min-h-screen bg-black text-white selection:bg-blue-500/30">
            {/* Header */}
            <header className="bg-[#0f0f0f] border-b border-white/10 px-4 py-2">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <Link
                            href="/"
                            className="flex items-center gap-2 text-gray-500 hover:text-white transition-colors"
                        >
                            <ChevronLeft size={18} />
                            <span className="text-xs font-bold uppercase tracking-wider">Back</span>
                        </Link>
                        <h1 className="text-2xl font-black tracking-tighter bg-gradient-to-r from-blue-400 via-indigo-300 to-blue-500 bg-clip-text text-transparent">
                            Rules Admin
                        </h1>
                    </div>
                    <div className="flex items-center gap-3">
                        {stats && (
                            <div className="flex gap-4 text-[10px] uppercase font-black tracking-[0.2em]">
                                <span className="flex items-center gap-1.5 min-w-[70px]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.6)]" />
                                    <span className="text-white">{stats.active}</span>
                                    <span className="text-gray-500">Active</span>
                                </span>
                                <span className="flex items-center gap-1.5 min-w-[70px]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-amber-500 shadow-[0_0_8px_rgba(245,158,11,0.4)]" />
                                    <span className="text-white">{stats.expired}</span>
                                    <span className="text-gray-500">Expired</span>
                                </span>
                                <span className="flex items-center gap-1.5 min-w-[60px]">
                                    <span className="w-1.5 h-1.5 rounded-full bg-gray-600" />
                                    <span className="text-white">{stats.total}</span>
                                    <span className="text-gray-500">Total</span>
                                </span>
                            </div>
                        )}
                        <div className="h-6 w-px bg-white/10 mx-2" />
                        <button
                            onClick={loadRules}
                            className="p-1.5 text-gray-500 hover:text-white transition-colors"
                            title="Refresh"
                        >
                            <RefreshCw size={16} className={loading ? "animate-spin" : ""} />
                        </button>
                        <button
                            onClick={startCreate}
                            className="flex items-center gap-2 px-3 py-1.5 bg-blue-600 hover:bg-blue-500 rounded-lg transition-all font-bold text-xs shadow-lg shadow-blue-500/20"
                        >
                            <Plus size={14} />
                            Add Rule
                        </button>
                    </div>
                </div>
            </header>

            <div className="flex">
                {/* Main content */}
                {/* Main content */}
                <main className="flex-1 p-4">
                    {/* Error banner */}
                    {error && (
                        <div className="mb-4 p-3 bg-red-900/20 border border-red-500/30 rounded-lg flex items-center gap-2 text-red-400 text-xs font-bold">
                            <AlertTriangle size={16} />
                            {error}
                            <button onClick={() => setError(null)} className="ml-auto">
                                <X size={14} />
                            </button>
                        </div>
                    )}

                    {/* Search and filters */}
                    <div className="mb-4 flex gap-2">
                        <div className="relative flex-1">
                            <Search
                                size={16}
                                className="absolute left-3 top-1/2 -translate-y-1/2 text-gray-500"
                            />
                            <input
                                type="text"
                                value={search}
                                onChange={(e) => setSearch(e.target.value)}
                                placeholder="Search rules..."
                                className="w-full pl-10 pr-4 py-1.5 bg-[#111] border border-white/10 rounded-lg text-sm text-white placeholder-gray-600 focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>
                        <select
                            value={filterGroup}
                            onChange={(e) => setFilterGroup(e.target.value)}
                            className="px-3 py-1.5 bg-[#111] border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
                        >
                            <option value="">All Groups</option>
                            {KNOWN_GROUPS.map((g) => (
                                <option key={g} value={g}>
                                    {g}
                                </option>
                            ))}
                        </select>
                        <label className="flex items-center gap-2 px-3 py-1.5 bg-[#111] border border-white/10 rounded-lg cursor-pointer hover:bg-white/5 transition-colors">
                            <input
                                type="checkbox"
                                checked={showInactive}
                                onChange={(e) => setShowInactive(e.target.checked)}
                                className="rounded bg-black border-white/20 text-blue-500 focus:ring-0 focus:ring-offset-0"
                            />
                            <span className="text-[10px] uppercase font-bold tracking-wider text-gray-500">Show Inactive</span>
                        </label>
                    </div>

                    {/* Rules table */}
                    <div className="bg-[#0f0f0f] border border-white/10 rounded-xl overflow-hidden shadow-2xl">
                        <table className="w-full text-left border-collapse">
                            <thead>
                                <tr className="bg-white/[0.03] border-b border-white/10 text-[9px] uppercase font-black tracking-[0.2em] text-gray-500">
                                    <th className="px-3 py-1.5 w-10">Act</th>
                                    <th className="px-3 py-1.5 w-14 text-center">Pri</th>
                                    <th className="px-3 py-1.5">Rule ID</th>
                                    <th className="px-3 py-1.5">Name</th>
                                    <th className="px-3 py-1.5">Match Conditions</th>
                                    <th className="px-3 py-1.5">Action</th>
                                    <th className="px-3 py-1.5">Validity</th>
                                    <th className="px-3 py-1.5 w-20 text-right">Actions</th>
                                </tr>
                            </thead>
                            <tbody className="divide-y divide-white/5">
                                {loading && !rules.length ? (
                                    <tr>
                                        <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                                            Loading rules...
                                        </td>
                                    </tr>
                                ) : filteredRules.length === 0 ? (
                                    <tr>
                                        <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                                            No rules found
                                        </td>
                                    </tr>
                                ) : (
                                    filteredRules.map((rule) => (
                                        <tr
                                            key={rule.rule_id}
                                            className={`group hover:bg-white/[0.02] transition-colors ${!rule.active ? "opacity-40 grayscale" : ""
                                                }`}
                                        >
                                            <td className="px-3 py-2">
                                                {rule.active ? (
                                                    <div className="w-2 h-2 rounded-full bg-green-500 shadow-[0_0_8px_rgba(34,197,94,0.5)]" />
                                                ) : (
                                                    <div className="w-2 h-2 rounded-full bg-gray-600" />
                                                )}
                                            </td>
                                            <td className="px-3 py-2 text-center">
                                                <span className={`text-[10px] font-mono font-black px-1.5 py-0.5 rounded ${rule.priority < 50
                                                    ? "bg-blue-500 text-white"
                                                    : "bg-white/5 text-gray-500"
                                                    }`}>
                                                    {rule.priority}
                                                </span>
                                            </td>
                                            <td className="px-3 py-2">
                                                <span className="font-mono text-xs font-bold text-blue-400">
                                                    {rule.rule_id}
                                                </span>
                                            </td>
                                            <td className="px-3 py-2 text-xs font-bold text-white tracking-tight">{rule.name}</td>
                                            <td className="px-3 py-2">
                                                <div className="flex flex-wrap gap-1.5">
                                                    {rule.account_group && (
                                                        <span className="px-1.5 py-0.5 bg-indigo-500/10 text-indigo-300 rounded text-[9px] font-black uppercase tracking-tight border border-indigo-500/30">
                                                            {rule.account_group}
                                                        </span>
                                                    )}
                                                    {rule.account && (
                                                        <span className="px-1.5 py-0.5 bg-blue-500/10 text-blue-300 rounded text-[9px] font-black uppercase tracking-tight border border-blue-500/30">
                                                            {rule.account}
                                                        </span>
                                                    )}
                                                    {rule.sku && (
                                                        <span className="px-1.5 py-0.5 bg-amber-500/10 text-amber-500 rounded text-[9px] font-black uppercase tracking-tight border border-amber-500/30">{rule.sku}</span>
                                                    )}
                                                    {rule.sku_prefix && (
                                                        <span className="px-1.5 py-0.5 bg-amber-500/10 text-amber-500 rounded text-[9px] font-black uppercase tracking-tight border border-amber-500/30">{rule.sku_prefix}*</span>
                                                    )}
                                                </div>
                                            </td>
                                            <td className="px-3 py-2">
                                                <span className="text-sm font-black text-[#22c55e] tracking-tight">
                                                    {rule.action_type === "override_unit_price" && `$${rule.action_value}`}
                                                    {rule.action_type === "discount_amount" && `-$${rule.action_value}`}
                                                    {rule.action_type === "discount_percent" && `-${rule.action_value}%`}
                                                    {rule.action_type === "price_floor" && `≥$${rule.action_value}`}
                                                </span>
                                            </td>
                                            <td className="px-3 py-2 text-[10px] font-mono text-gray-400 font-bold uppercase tracking-tighter">
                                                {(rule.start_date || 'N/A').split('-').slice(1).join('/')} - {(rule.end_date || 'N/A').split('-').slice(1).join('/')}
                                            </td>
                                            <td className="px-3 py-2 text-right">
                                                <div className="flex justify-end gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
                                                    <button
                                                        onClick={() => setEditingRule(rule)}
                                                        className="p-1 text-gray-500 hover:text-white transition-colors"
                                                        title="Edit"
                                                    >
                                                        <Edit2 size={14} />
                                                    </button>
                                                    <button
                                                        onClick={() => handleDeleteRule(rule.rule_id)}
                                                        className="p-1 text-gray-500 hover:text-red-400 transition-colors"
                                                        title="Delete"
                                                    >
                                                        <Trash2 size={14} />
                                                    </button>
                                                </div>
                                            </td>
                                        </tr>
                                    ))
                                )}
                            </tbody>
                        </table>
                    </div>
                </main>

                {/* Right sidebar - Rule Tester */}
                <aside className="w-72 bg-[#0f0f0f] border-l border-white/10 p-4">
                    <h2 className="flex items-center gap-2 text-xs font-black uppercase tracking-widest text-gray-500 mb-6">
                        <TestTube size={14} className="text-blue-500" />
                        Rule Tester
                    </h2>
                    <div className="space-y-4">
                        <div>
                            <label className="block text-[9px] uppercase font-black tracking-[0.2em] text-gray-600 mb-2">Account ID</label>
                            <input
                                type="text"
                                value={testAccountId}
                                onChange={(e) => setTestAccountId(e.target.value)}
                                placeholder="e.g. 25160"
                                className="w-full px-3 py-2 bg-white/[0.03] border border-white/5 rounded-lg text-sm text-white placeholder-gray-800 focus:outline-none focus:border-blue-500/50 transition-all font-mono"
                            />
                        </div>
                        <div>
                            <label className="block text-[9px] uppercase font-black tracking-[0.2em] text-gray-600 mb-2">SKU / Model</label>
                            <input
                                type="text"
                                value={testSku}
                                onChange={(e) => setTestSku(e.target.value)}
                                placeholder="e.g. 20750"
                                className="w-full px-3 py-2 bg-white/[0.03] border border-white/5 rounded-lg text-sm text-white placeholder-gray-800 focus:outline-none focus:border-blue-500/50 transition-all font-mono"
                            />
                        </div>
                        <button
                            onClick={handleTest}
                            disabled={testLoading || !testAccountId || !testSku}
                            className="w-full py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 disabled:text-gray-700 rounded-lg font-bold text-xs uppercase tracking-widest transition-all shadow-lg shadow-blue-500/10"
                        >
                            {testLoading ? "Testing..." : "Run Test"}
                        </button>

                        {testResult && (
                            <div className="mt-6 p-4 bg-black border border-white/5 rounded-xl space-y-4">
                                <div className="flex justify-between items-center">
                                    <span className="text-[10px] uppercase font-bold text-gray-600">Base</span>
                                    <span className="font-mono text-sm">${testResult.base_price?.toFixed(2) || 'N/A'}</span>
                                </div>
                                <div className="flex justify-between items-end border-t border-white/5 pt-3">
                                    <span className="text-[10px] uppercase font-bold text-gray-600 mb-1">Final Price</span>
                                    <span className="font-black text-2xl text-green-400 tracking-tight leading-none">
                                        ${testResult.final_price?.toFixed(2) || 'N/A'}
                                    </span>
                                </div>
                                <div className="flex justify-between items-center">
                                    <span className="text-[10px] uppercase font-bold text-gray-600">Source</span>
                                    <span
                                        className={`px-2 py-0.5 rounded text-[10px] font-black uppercase tracking-tight ${testResult.source === "Rule"
                                            ? "bg-blue-500 text-white shadow-lg shadow-blue-500/20"
                                            : "bg-white/10 text-gray-400"
                                            }`}
                                    >
                                        {testResult.source}
                                    </span>
                                </div>

                                {testResult.matched_rules.length > 0 && (
                                    <div className="pt-4 border-t border-white/5">
                                        <p className="text-[9px] uppercase font-black tracking-widest text-gray-600 mb-2">Matched Rules:</p>
                                        <ul className="space-y-2">
                                            {testResult.matched_rules.map((r, i) => (
                                                <li key={i} className="p-2 bg-white/[0.03] border border-white/5 rounded-lg">
                                                    <div className="font-mono text-[10px] font-bold text-blue-400 leading-none mb-1">{r.rule_id}</div>
                                                    <div className="text-[10px] text-gray-500 leading-tight">{r.name}</div>
                                                </li>
                                            ))}
                                        </ul>
                                    </div>
                                )}
                            </div>
                        )}
                    </div>
                </aside>
            </div>

            {/* Edit Modal */}
            {editingRule && (
                <RuleEditModal
                    rule={editingRule}
                    isNew={isCreating}
                    onSave={handleSaveRule}
                    onCancel={() => {
                        setEditingRule(null);
                        setIsCreating(false);
                    }}
                />
            )}
        </div>
    );
}

// Rule Edit Modal Component
function RuleEditModal({
    rule,
    isNew,
    onSave,
    onCancel,
}: {
    rule: Rule;
    isNew: boolean;
    onSave: (rule: Rule | RuleCreate) => void;
    onCancel: () => void;
}) {
    const [formData, setFormData] = useState<Rule>({ ...rule });
    const [saving, setSaving] = useState(false);

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault();
        setSaving(true);
        try {
            await onSave(formData);
        } finally {
            setSaving(false);
        }
    };

    const updateField = (field: keyof Rule, value: any) => {
        setFormData((prev) => ({ ...prev, [field]: value }));
    };

    return (
        <div className="fixed inset-0 bg-black/80 flex items-center justify-center z-50 backdrop-blur-sm p-4">
            <div className="bg-[#0f0f0f] border border-white/10 rounded-2xl w-full max-w-2xl max-h-[95vh] overflow-y-auto shadow-2xl">
                <div className="flex items-center justify-between px-6 py-4 border-b border-white/10">
                    <h2 className="text-lg font-black tracking-tight text-white uppercase italic">
                        {isNew ? "Create Rule" : `Edit: ${rule.rule_id}`}
                    </h2>
                    <button onClick={onCancel} className="text-gray-500 hover:text-white transition-colors">
                        <X size={20} />
                    </button>
                </div>

                <form onSubmit={handleSubmit} className="p-6 space-y-6">
                    {/* Name */}
                    <div>
                        <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">
                            Rule Name <span className="text-red-500">*</span>
                        </label>
                        <input
                            type="text"
                            value={formData.name}
                            onChange={(e) => updateField("name", e.target.value)}
                            required
                            placeholder="e.g. ALLI: F7 Varsity $270"
                            className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                        />
                    </div>

                    {/* Row: Active, Priority */}
                    <div className="grid grid-cols-2 gap-6 p-4 bg-white/[0.02] border border-white/5 rounded-xl">
                        <div className="flex h-full items-center gap-3">
                            <input
                                type="checkbox"
                                id="active"
                                checked={formData.active}
                                onChange={(e) => updateField("active", e.target.checked)}
                                className="w-4 h-4 rounded bg-black border-white/20 text-blue-500 focus:ring-0 focus:ring-offset-0"
                            />
                            <label htmlFor="active" className="text-sm font-bold text-gray-200 uppercase tracking-wide">
                                Rule Active
                            </label>
                        </div>
                        <div>
                            <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5 flex items-center gap-1.5">
                                Priority Level
                                <div className="group relative cursor-help">
                                    <AlertTriangle size={12} className="text-amber-500" />
                                    <div className="absolute bottom-full left-1/2 -translate-x-1/2 mb-2 w-48 bg-black border border-white/10 p-3 rounded-lg text-[10px] text-gray-400 hidden group-hover:block z-50 shadow-2xl leading-relaxed">
                                        <span className="text-white font-bold block mb-1">Execution Order:</span>
                                        1 = Top Priority (Executes First)<br />
                                        50 = Standard<br />
                                        100 = Final Priority (Executes Last)
                                    </div>
                                </div>
                            </label>
                            <input
                                type="number"
                                value={formData.priority}
                                onChange={(e) => updateField("priority", parseInt(e.target.value))}
                                className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors font-mono"
                            />
                        </div>
                    </div>

                    {/* Matching Section */}
                    <div className="p-4 bg-white/[0.02] border border-white/5 rounded-xl space-y-4">
                        <h3 className="text-[10px] uppercase font-black tracking-[0.2em] text-blue-500">Target Match Conditions</h3>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">Group</label>
                                <select
                                    value={formData.account_group || ""}
                                    onChange={(e) => updateField("account_group", e.target.value || null)}
                                    className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors cursor-pointer"
                                >
                                    <option value="">None (Universal)</option>
                                    {KNOWN_GROUPS.map((g) => (
                                        <option key={g} value={g}>
                                            {g}
                                        </option>
                                    ))}
                                </select>
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">Account ID</label>
                                <input
                                    type="text"
                                    value={formData.account || ""}
                                    onChange={(e) => updateField("account", e.target.value || null)}
                                    placeholder="Acct #"
                                    className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>
                        </div>
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">Specific SKU</label>
                                <input
                                    type="text"
                                    value={formData.sku || ""}
                                    onChange={(e) => updateField("sku", e.target.value || null)}
                                    placeholder="Full SKU"
                                    className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white font-mono focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>
                            <div>
                                <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">SKU Prefix</label>
                                <input
                                    type="text"
                                    value={formData.sku_prefix || ""}
                                    onChange={(e) => updateField("sku_prefix", e.target.value || null)}
                                    placeholder="Start with..."
                                    className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white font-mono focus:outline-none focus:border-blue-500 transition-colors"
                                />
                            </div>
                        </div>
                    </div>

                    {/* Action Section */}
                    <div className="grid grid-cols-2 gap-4 border-t border-white/5 pt-6">
                        <div>
                            <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">
                                Action Type <span className="text-red-500">*</span>
                            </label>
                            <select
                                value={formData.action_type}
                                onChange={(e) => updateField("action_type", e.target.value)}
                                required
                                className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                            >
                                {ACTION_TYPES.map((t) => (
                                    <option key={t.value} value={t.value}>
                                        {t.label}
                                    </option>
                                ))}
                            </select>
                        </div>
                        <div>
                            <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">
                                Pricing Value <span className="text-red-500">*</span>
                            </label>
                            <input
                                type="text"
                                value={formData.action_value}
                                onChange={(e) => updateField("action_value", e.target.value)}
                                required
                                placeholder="e.g. 270"
                                className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors font-mono font-bold"
                            />
                        </div>
                    </div>

                    {/* Dates */}
                    <div className="grid grid-cols-2 gap-4">
                        <div>
                            <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">Validity Start</label>
                            <input
                                type="date"
                                value={formData.start_date || ""}
                                onChange={(e) => updateField("start_date", e.target.value || null)}
                                className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>
                        <div>
                            <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">Validity End</label>
                            <input
                                type="date"
                                value={formData.end_date || ""}
                                onChange={(e) => updateField("end_date", e.target.value || null)}
                                className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors"
                            />
                        </div>
                    </div>

                    {/* Notes */}
                    <div>
                        <label className="block text-[10px] uppercase font-black tracking-widest text-gray-500 mb-1.5">Internal Notes</label>
                        <textarea
                            value={formData.notes || ""}
                            onChange={(e) => updateField("notes", e.target.value || null)}
                            rows={2}
                            placeholder="Reason for rule..."
                            className="w-full px-3 py-2 bg-black border border-white/10 rounded-lg text-sm text-white focus:outline-none focus:border-blue-500 transition-colors resize-none"
                        />
                    </div>

                    {/* Actions */}
                    <div className="flex justify-end gap-3 pt-6 border-t border-white/10">
                        <button
                            type="button"
                            onClick={onCancel}
                            className="px-4 py-2 text-xs font-bold uppercase tracking-widest text-gray-500 hover:text-white transition-colors"
                        >
                            Cancel
                        </button>
                        <button
                            type="submit"
                            disabled={saving}
                            className="flex items-center gap-2 px-6 py-2 bg-blue-600 hover:bg-blue-500 disabled:bg-white/5 rounded-lg font-bold text-xs uppercase tracking-widest transition-all shadow-lg shadow-blue-500/20"
                        >
                            {saving ? (
                                <RefreshCw size={14} className="animate-spin" />
                            ) : (
                                <Check size={14} />
                            )}
                            {isNew ? "Create Rule" : "Save Changes"}
                        </button>
                    </div>
                </form>
            </div>
        </div>
    );
}
