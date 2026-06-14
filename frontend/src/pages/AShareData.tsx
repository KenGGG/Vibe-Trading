import { useEffect, useState } from "react";
import { Database, RefreshCw, CheckCircle2, AlertTriangle, Activity, Clock, Layers } from "lucide-react";
import { toast } from "sonner";
import { api, type AShareDataStatus } from "@/lib/api";

function StatusPill({ ok, text }: { ok: boolean; text: string }) {
  return (
    <span
      className={[
        "inline-flex items-center gap-1 rounded-full px-2 py-0.5 text-xs font-medium",
        ok
          ? "bg-emerald-500/10 text-emerald-700 dark:text-emerald-300"
          : "bg-amber-500/10 text-amber-700 dark:text-amber-300",
      ].join(" ")}
    >
      {ok ? <CheckCircle2 className="h-3 w-3" /> : <AlertTriangle className="h-3 w-3" />}
      {text}
    </span>
  );
}

function formatTime(value?: string | null): string {
  if (!value) return "未提供";
  return value;
}

export function AShareData() {
  const [status, setStatus] = useState<AShareDataStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [updating, setUpdating] = useState(false);
  const [updateOutput, setUpdateOutput] = useState("");

  const load = async () => {
    try {
      const data = await api.getAShareDataStatus();
      setStatus(data);
    } catch (error) {
      toast.error(`加载 A 股数据状态失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void load();
  }, []);

  const handleUpdate = async () => {
    setUpdating(true);
    try {
      const result = await api.updateAShareData();
      setStatus(result.status);
      setUpdateOutput(result.output);
      toast.success(result.success ? "A 股本地数据库更新完成" : "A 股本地数据库更新失败");
    } catch (error) {
      toast.error(`执行手动更新失败：${error instanceof Error ? error.message : "未知错误"}`);
    } finally {
      setUpdating(false);
    }
  };

  if (loading && !status) {
    return <div className="p-8 text-sm text-muted-foreground">A 股数据状态加载中…</div>;
  }

  if (!status) {
    return <div className="p-8 text-sm text-muted-foreground">暂时无法读取 A 股数据状态。</div>;
  }

  const localDb = status.local_database;
  const network = status.a_stock_data;
  const summary = network.integration_summary;

  return (
    <div className="mx-auto max-w-6xl space-y-6 p-6">
      <div className="space-y-2">
        <div className="flex items-center gap-2 text-xs uppercase tracking-wide text-muted-foreground">
          <Layers className="h-3.5 w-3.5" />
          A 股数据
        </div>
        <h1 className="text-2xl font-semibold tracking-tight">A 股数据源状态</h1>
        <p className="max-w-4xl text-sm text-muted-foreground">
          当前系统已同时接入本地 Dolt 日频数据库与 `a-stock-data` 在线链路。默认策略为：A 股历史 1D 回测优先使用本地数据库；实时、分钟级与在线补齐优先使用 a-stock-data。
        </p>
        <p className="text-xs text-muted-foreground">状态采样时间：{formatTime(status.as_of)}</p>
      </div>

      <div className="grid gap-6 xl:grid-cols-2">
        <section className="rounded-xl border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Database className="h-4 w-4 text-primary" />
                <h2 className="text-base font-semibold">本地 Dolt 日频数据库</h2>
              </div>
              <p className="text-sm text-muted-foreground">
                适合 A 股历史日线回测、长区间批量取数和离线稳定访问。
              </p>
            </div>
            <StatusPill ok={localDb.available} text={localDb.available ? "已接入" : "未就绪"} />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">仓库路径</div>
              <div className="mt-1 break-all font-mono text-xs">{localDb.path}</div>
            </div>
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">最新数据时间</div>
              <div className="mt-1 text-sm font-medium">{formatTime(localDb.latest_trade_date)}</div>
            </div>
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">当前分支</div>
              <div className="mt-1 text-sm font-medium">{localDb.branch || "未提供"}</div>
            </div>
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">优先表</div>
              <div className="mt-1 text-sm font-medium">{localDb.preferred_table || "未识别"}</div>
            </div>
          </div>

          <div className="mt-4 flex flex-wrap items-center gap-2">
            <StatusPill ok={localDb.command_available} text={localDb.command_available ? "dolt 命令可用" : "缺少 dolt 命令"} />
            <StatusPill ok={localDb.repo_ready} text={localDb.repo_ready ? "仓库可访问" : "仓库不可访问"} />
            <StatusPill ok={Boolean(localDb.clean)} text={localDb.clean ? "工作区干净" : "存在未提交变更或状态未知"} />
          </div>

          <div className="mt-4 overflow-x-auto">
            <table className="w-full text-sm">
              <thead>
                <tr className="border-b text-left text-muted-foreground">
                  <th className="py-2 pr-4">表名</th>
                  <th className="py-2 pr-4">最新交易日</th>
                  <th className="py-2">行数</th>
                </tr>
              </thead>
              <tbody>
                {localDb.tables.map((table) => (
                  <tr key={table.name} className="border-b last:border-0">
                    <td className="py-2 pr-4 font-mono text-xs">{table.name}</td>
                    <td className="py-2 pr-4">{formatTime(table.latest_trade_date)}</td>
                    <td className="py-2 tabular-nums">{table.row_count.toLocaleString("zh-CN")}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="mt-4 flex items-center gap-3">
            <button
              type="button"
              onClick={handleUpdate}
              disabled={updating}
              className="inline-flex items-center gap-2 rounded-md bg-primary px-4 py-2 text-sm font-medium text-primary-foreground transition hover:opacity-90 disabled:opacity-60"
            >
              <RefreshCw className={["h-4 w-4", updating ? "animate-spin" : ""].join(" ")} />
              {updating ? "更新中…" : "手动更新本地数据库"}
            </button>
            <span className="text-xs text-muted-foreground">执行命令：`dolt pull`</span>
          </div>

          <div className="mt-4 rounded-lg border bg-muted/20 p-3">
            <div className="mb-1 flex items-center gap-1.5 text-xs font-medium text-muted-foreground">
              <Clock className="h-3 w-3" />
              仓库状态输出
            </div>
            <pre className="max-h-64 overflow-auto whitespace-pre-wrap break-words text-xs text-foreground/80">
              {updateOutput || localDb.message || "暂无输出。"}
            </pre>
          </div>
        </section>

        <section className="rounded-xl border bg-card p-5 shadow-sm">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div className="space-y-1">
              <div className="flex items-center gap-2">
                <Activity className="h-4 w-4 text-primary" />
                <h2 className="text-base font-semibold">a-stock-data 在线链路</h2>
              </div>
              <p className="text-sm text-muted-foreground">
                适合 A 股实时、分钟级和无密钥在线取数；内部优先级为 mootdx、腾讯行情、百度 K 线。
              </p>
            </div>
            <StatusPill ok={network.available} text={network.available ? "已接入" : "未就绪"} />
          </div>

          <div className="grid gap-3 md:grid-cols-2">
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">样本最新数据时间</div>
              <div className="mt-1 text-sm font-medium">{formatTime(network.latest_trade_date)}</div>
            </div>
            <div className="rounded-lg border bg-muted/20 p-3">
              <div className="text-xs text-muted-foreground">推荐场景</div>
              <div className="mt-1 text-sm font-medium">{network.preferred_usage.intraday_or_realtime || "未提供"}</div>
            </div>
          </div>

          <div className="mt-4 space-y-3">
            {network.components.map((component) => (
              <div key={component.name} className="rounded-lg border bg-muted/20 p-3">
                <div className="flex items-center justify-between gap-3">
                  <div className="font-medium">{component.name}</div>
                  <StatusPill ok={component.available} text={component.available ? "可用" : "不可用"} />
                </div>
                <p className="mt-1 text-sm text-muted-foreground">{component.detail}</p>
                {component.latest_trade_date && (
                  <p className="mt-1 text-xs text-muted-foreground">最新日期：{component.latest_trade_date}</p>
                )}
              </div>
            ))}
          </div>

          <div className="mt-4 rounded-lg border bg-muted/20 p-3">
            <div className="mb-2 text-xs font-medium text-muted-foreground">系统当前择优策略</div>
            <ul className="space-y-1 text-sm text-foreground/90">
              <li>历史日线回测：{status.priority.historical_daily}</li>
              <li>实时 / 分钟级：{status.priority.intraday_or_realtime}</li>
              <li>兜底策略：{status.priority.fallback}</li>
            </ul>
          </div>
        </section>
      </div>

      <section className="rounded-xl border bg-card p-5 shadow-sm">
        <div className="mb-4 flex items-start justify-between gap-3">
          <div className="space-y-1">
            <div className="flex items-center gap-2">
              <Layers className="h-4 w-4 text-primary" />
              <h2 className="text-base font-semibold">a-stock-data 七层架构状态</h2>
            </div>
            <p className="text-sm text-muted-foreground">
              保留当前页面原有取数状态的同时，这里按七层架构展示每一层和各 provider 在当前系统中的真实接入情况。
            </p>
          </div>
          <StatusPill ok={summary.integrated_layers > 0} text={`${summary.integrated_layers} / ${summary.total_layers} 层已接入`} />
        </div>

        <div className="grid gap-3 md:grid-cols-4">
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">已接入层数</div>
            <div className="mt-1 text-lg font-semibold">{summary.integrated_layers} / {summary.total_layers}</div>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">可调用层数</div>
            <div className="mt-1 text-lg font-semibold">{summary.callable_layers}</div>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">已验证层数</div>
            <div className="mt-1 text-lg font-semibold">{summary.verified_layers}</div>
          </div>
          <div className="rounded-lg border bg-muted/20 p-3">
            <div className="text-xs text-muted-foreground">当前结论</div>
            <div className="mt-1 text-sm font-medium">{summary.message}</div>
          </div>
        </div>

        <div className="mt-4 space-y-4">
          {network.layers.map((layer) => (
            <div key={layer.key} className="rounded-xl border bg-muted/10 p-4">
              <div className="flex flex-wrap items-start justify-between gap-3">
                <div className="space-y-1">
                  <div className="flex items-center gap-2">
                    <h3 className="text-sm font-semibold">{layer.name}</h3>
                    <StatusPill ok={layer.integrated} text={layer.integrated ? "已接入" : "未接入"} />
                    <StatusPill ok={layer.callable} text={layer.callable ? "可调用" : "不可调用"} />
                    <StatusPill ok={layer.verified} text={layer.verified ? "已验证" : "未验证"} />
                  </div>
                  <p className="text-sm text-muted-foreground">{layer.description}</p>
                  <p className="text-xs text-muted-foreground">
                    能力范围：{layer.capabilities.join(" / ")}
                  </p>
                </div>
              </div>

              <div className="mt-3 grid gap-3 lg:grid-cols-2">
                {layer.providers.map((provider) => (
                  <div key={`${layer.key}-${provider.name}`} className="rounded-lg border bg-background p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <div>
                        <div className="font-medium">{provider.name}</div>
                        <div className="text-xs text-muted-foreground">{provider.role}</div>
                      </div>
                      <div className="flex flex-wrap gap-2">
                        <StatusPill ok={provider.integrated} text={provider.integrated ? "已接线" : "未接线"} />
                        <StatusPill ok={provider.callable} text={provider.callable ? "可调用" : "不可调用"} />
                      </div>
                    </div>
                    <p className="mt-2 text-sm text-muted-foreground">{provider.detail}</p>
                    <p className="mt-1 text-xs text-muted-foreground">
                      验证状态：{provider.verified ? "已验证" : "未验证"}
                      {provider.latest_trade_date ? ` · 最新样本日期：${provider.latest_trade_date}` : ""}
                    </p>
                  </div>
                ))}
              </div>

              <div className="mt-3 rounded-lg border bg-muted/20 p-3 text-sm text-muted-foreground">
                {layer.notes}
              </div>
            </div>
          ))}
        </div>
      </section>
    </div>
  );
}
