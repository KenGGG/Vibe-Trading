import { useTranslation } from "react-i18next";
﻿import { Bot, TrendingUp, Globe, Sparkles, Users, UserCircle2, NotebookPen, Landmark } from "lucide-react";

interface Example {
  title: string;
  desc: string;
  prompt: string;
}

interface Category {
  label: string;
  icon: React.ReactNode;
  color: string;
  examples: Example[];
}

const CATEGORIES: Category[] = [
  {
    label: "多市场回测",
    icon: <TrendingUp className="h-4 w-4" />,
    color: "text-red-400 border-red-500/30 hover:border-red-500/60 hover:bg-red-500/5",
    examples: [
      {
        title: "跨市场组合",
        desc: "A股 + 加密货币 + 美股，风险平价优化器",
        prompt: "回测 000001.SZ、BTC-USDT 和 AAPL 在 2024 全年的风险平价组合，并与等权基准比较",
      },
      {
        title: "BTC 5分钟 MACD 策略",
        desc: "基于 OKX 实时数据的分钟级加密货币回测",
        prompt: "回测 BTC-USDT 5 分钟 MACD 策略，参数 fast=12 slow=26 signal=9，区间为最近 30 天",
      },
      {
        title: "美股科技最大分散化",
        desc: "通过 yfinance 对 FAANG+ 进行组合优化",
        prompt: "用最大分散化投资组合优化器回测 AAPL、MSFT、GOOGL、AMZN、NVDA 在 2024 全年的表现",
      },
    ],
  },
  {
    label: "研究与分析",
    icon: <Sparkles className="h-4 w-4" />,
    color: "text-amber-400 border-amber-500/30 hover:border-amber-500/60 hover:bg-amber-500/5",
    examples: [
      {
        title: "多因子 Alpha 模型",
        desc: "对 300 只股票进行 IC 加权因子合成",
        prompt: "基于沪深 300 成分股，使用动量、反转、波动率和换手率构建 IC 加权的多因子 alpha 模型，并回测 2023-2024 年表现",
      },
      {
        title: "期权希腊值分析",
        desc: "Black-Scholes 定价与 Delta/Gamma/Theta/Vega 分析",
        prompt: "使用 Black-Scholes 计算期权希腊值：spot=100、strike=105、risk-free rate=3%、vol=25%、expiry=90 days，分析 Delta/Gamma/Theta/Vega",
      },
    ],
  },
  {
    label: "群体智能团队",
    icon: <Users className="h-4 w-4" />,
    color: "text-violet-400 border-violet-500/30 hover:border-violet-500/60 hover:bg-violet-500/5",
    examples: [
      {
        title: "投资委员会评审",
        desc: "多智能体辩论：多头 vs 空头，风险审查，投资经理决策",
        prompt: "[Swarm Team Mode] 使用 investment_committee 预设，在当前市场条件下评估 NVDA 应该做多还是做空",
      },
      {
        title: "量化策略工作台",
        desc: "筛选 → 因子研究 → 回测 → 风险审计流水线",
        prompt: "[Swarm Team Mode] 使用 quant_strategy_desk 预设，寻找并回测沪深 300 成分股中最优的动量策略",
      },
    ],
  },
  {
    label: "文档与网络研究",
    icon: <Globe className="h-4 w-4" />,
    color: "text-blue-400 border-blue-500/30 hover:border-blue-500/60 hover:bg-blue-500/5",
    examples: [
      {
        title: "分析财报 PDF",
        desc: "上传 PDF 并就财务数据提问",
        prompt: "总结已上传财报中的关键财务指标、风险点和未来展望",
      },
      {
        title: "网络研究：宏观展望",
        desc: "读取实时网页来源进行宏观分析",
        prompt: "阅读最新的美联储会议纪要，并总结其对股票和加密货币市场的关键影响",
      },
    ],
  },
  {
    label: "交易日志",
    icon: <NotebookPen className="h-4 w-4" />,
    color: "text-orange-400 border-orange-500/30 hover:border-orange-500/60 hover:bg-orange-500/5",
    examples: [
      {
        title: "分析券商导出数据",
        desc: "解析同花顺/东财/富途/通用 CSV —— 持仓天数、胜率、盈亏比、小时分布",
        prompt: "分析我刚上传的交易日志，输出完整画像，包括持仓统计、胜率、主要交易标的和小时分布",
      },
      {
        title: "诊断行为偏差",
        desc: "处置效应、过度交易、追涨动量、锚定效应 —— 严重程度 + 数值证据",
        prompt: "对我的交易日志运行 4 项行为诊断（处置效应、过度交易、追涨、锚定），并告诉我哪种偏差对盈亏伤害最大",
      },
    ],
  },
  {
    label: "交易连接器",
    icon: <Landmark className="h-4 w-4" />,
    color: "text-cyan-400 border-cyan-500/30 hover:border-cyan-500/60 hover:bg-cyan-500/5",
    examples: [
      {
        title: "检查已选连接器",
        desc: "列出连接器配置并验证当前选择",
        prompt: "List my trading connector profiles, show which one is selected, then check that selected connector. If it is not ready, tell me exactly what setup step is missing. Do not place or modify orders.",
      },
      {
        title: "分析连接器投资组合",
        desc: "从已选连接器读取账户摘要与持仓",
        prompt: "Use the selected trading connector profile to summarize my account, positions, concentration, cash, and portfolio risk. Do not place or modify orders.",
      },
      {
        title: "报价与趋势",
        desc: "通过已选连接器获取报价及近 30 日日线",
        prompt: "Use the selected trading connector to fetch an AAPL quote and 30 daily bars, then summarize the current quote versus the recent trend. Keep it read-only.",
      },
    ],
  },
  {
    label: "影子账户",
    icon: <UserCircle2 className="h-4 w-4" />,
    color: "text-emerald-400 border-emerald-500/30 hover:border-emerald-500/60 hover:bg-emerald-500/5",
    examples: [
      {
        title: "从日志训练影子账户",
        desc: "从券商 CSV 提取策略规则并持久化影子账户配置",
        prompt: "根据我刚上传的交易日志训练影子账户，展示提取出的规则，并确认这些规则是否符合我的交易行为",
      },
      {
        title: "我少赚了多少？",
        desc: "回测影子策略并对比实际盈亏差异",
        prompt: "在美股市场对最近 90 天运行影子账户回测，并拆解我的实际盈亏与影子账户偏离的原因（违规、提前离场、错过信号）",
      },
      {
        title: "生成影子报告",
        desc: "8 个章节的 HTML/PDF —— 净值曲线、分市场夏普、归因瀑布图",
        prompt: "生成影子账户报告并给我链接，重点先说明我与影子账户之间的收益差异",
      },
    ],
  },
];

const CAPABILITY_CHIPS = [
  "金融技能库",
  "群体智能团队",
  "自动发现工具",
  "3 大市场：A股 · 加密货币 · 港美股",
  "交易连接器配置",
  "分钟级到日线级时间框架",
  "4 种投资组合优化器",
  "15+ 风险指标",
  "期权与衍生品",
  "PDF 与网络研究",
  "因子分析与机器学习",
  "交易日志分析器",
  "影子账户回测",
  "持久化记忆",
  "会话搜索",
];

interface Props {
  onExample: (s: string) => void;
}

export function WelcomeScreen({ onExample }: Props) {
  const { t } = useTranslation();
  return (
    <div className="flex flex-col items-center justify-center min-h-[60vh] space-y-8 text-center">
      {/* Header */}
      <div className="space-y-3">
        <div className="h-16 w-16 mx-auto rounded-2xl bg-gradient-to-br from-primary/80 to-info/80 flex items-center justify-center shadow-lg">
          <Bot className="h-8 w-8 text-white" />
        </div>
        <div>
          <h2 className="text-2xl font-bold tracking-tight">{t('welcome.title')}</h2>
          <p className="text-xs text-muted-foreground mt-1 max-w-sm mx-auto leading-relaxed">
            与你的专业金融智能体团队一起进行 Vibe Trading
          </p>
          <p className="text-sm text-muted-foreground mt-2 max-w-md leading-relaxed mx-auto">
            描述一个交易策略即可开始。
          </p>
        </div>
      </div>

      {/* Capability chips */}
      <div className="flex flex-wrap justify-center gap-2 max-w-lg">
        {CAPABILITY_CHIPS.map((chip) => (
          <span
            key={chip}
            className="px-2.5 py-1 text-xs rounded-full border border-border/60 text-muted-foreground bg-muted/30"
          >
            {chip}
          </span>
        ))}
      </div>

      {/* Example categories grid */}
      <div className="w-full max-w-2xl text-left space-y-4">
        <p className="text-xs text-muted-foreground px-1">{t('welcome.tryExample')}</p>
        <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
          {CATEGORIES.map((cat) => (
            <div key={cat.label} className="space-y-2">
              <div className={`flex items-center gap-1.5 text-xs font-medium px-1 ${cat.color.split(" ").filter(c => c.startsWith("text-")).join(" ")}`}>
                {cat.icon}
                <span>{cat.label}</span>
              </div>
              <div className="space-y-1.5">
                {cat.examples.map((ex) => (
                  <button
                    key={ex.title}
                    onClick={() => onExample(ex.prompt)}
                    className={`block w-full text-left px-3 py-2.5 rounded-xl border transition-colors ${cat.color}`}
                  >
                    <span className="text-sm font-medium text-foreground leading-snug">
                      {ex.title}
                    </span>
                    <span className="block text-xs text-muted-foreground mt-0.5 leading-snug">
                      {ex.desc}
                    </span>
                  </button>
                ))}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
}
