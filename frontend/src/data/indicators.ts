export const sectors = [
  "Automobile and Auto Components", "Capital Goods", "Chemicals", "Commodities", "Construction",
  "Construction Materials", "Consumer Discretionary", "Consumer Services", "Energy",
  "Fast Moving Consumer Goods", "Financial Services", "Healthcare", "Industrials",
  "Information Technology", "Media Entertainment & Publication", "Metals & Mining",
  "Oil Gas & Consumable Fuels", "Power", "Realty", "Services", "Telecommunication", "Textiles", "Utilities"
];

export const indicators = [
  {
    id: "live_pe",
    name: "Live P/E Ratio",
    description: "Filters stocks based on their current Price-to-Earnings ratio.",
    examples: [
      "Find IT stocks with a live P/E below 20.",
      "Show me banks where P/E is between 10 and 15."
    ]
  },
  {
    id: "pe_below_sector_median",
    name: "P/E Below Sector Median",
    description: "Finds stocks that are currently cheaper than the median P/E of their specific sector.",
    examples: [
      "Show me top 5 Auto stocks trading below their sector median PE.",
      "List FMCG companies with PE below sector median."
    ]
  },
  {
    id: "revenue_growth_yoy",
    name: "Revenue Growth YoY",
    description: "Filters stocks demonstrating year-over-year revenue growth above a certain percentage.",
    examples: [
      "Find healthcare stocks with revenue growth YoY > 15%.",
      "Show me companies with at least 20% revenue growth."
    ]
  },
  {
    id: "margin_improving",
    name: "Margin Improving",
    description: "Identifies companies whose margins are consistently improving over recent quarters.",
    examples: [
      "Find stocks where margin is improving over 3 quarters.",
      "Show me IT companies with improving margins over 2 quarters."
    ]
  },
  {
    id: "smart_money_inflow",
    name: "Smart Money Inflow",
    description: "Detects stocks where BOTH Foreign Institutional Investors (FII) and Domestic Institutional Investors (DII) are increasing their stake.",
    examples: [
      "Show me stocks with smart money inflow over the last 1 quarter.",
      "Find IT stocks with institutional buying."
    ]
  },
  {
    id: "cfo_positive",
    name: "Cash From Operations Positive",
    description: "Ensures the company is actually generating positive cash from its core business operations.",
    examples: [
      "Find stocks with positive cash flow.",
      "Show me IT stocks with PE < 30 and positive CFO."
    ]
  },
  {
    id: "near_52_week_high",
    name: "Near 52-Week High",
    description: "Finds stocks trading within a specific percentage of their 52-week high, indicating strong momentum.",
    examples: [
      "Show me banking stocks trading within 5% of their 52-week high.",
      "Find energy stocks within 2% of 52-week high."
    ]
  },
  {
    id: "above_200_sma",
    name: "Above 200 SMA",
    description: "Filters stocks whose current price is trading above their 200-day Simple Moving Average, with an optional percentage margin buffer.",
    examples: [
      "Show me FMCG stocks trading above their 200 SMA.",
      "Find stocks trading above their 200 SMA by at least 5% margin."
    ]
  },
  {
    id: "supertrend_bullish",
    name: "Supertrend Bullish",
    description: "Filters based on the technical Supertrend indicator showing a bullish signal for a given period.",
    examples: [
      "Show me stocks where the 14 period supertrend is bullish.",
      "Find FMCG stocks with a bullish supertrend of period 14, where the PE is below the sector median and they have positive cash flow."
    ]
  }
];
