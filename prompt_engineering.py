"""
LLM Earnings Prediction Prompt Template

This file contains prompts for testing LLM's ability to predict future earnings metrics
and stock price reactions without using traditional ML models.
"""

from typing import List, Dict, Any, Optional

def generate_earnings_prompt(
    ticker: str,
    company_name: str,
    sector: str,
    current_quarter: str,
    revenue: float,
    revenue_growth: float,
    eps: float,
    operating_margin: float,
    price_before: float,
    analyst_data: List[Dict] = None
) -> str:
    """
    Generate a prompt for LLM earnings prediction based on real API data
    
    Args:
        ticker: Stock ticker symbol
        company_name: Company name
        sector: Company sector
        current_quarter: Current quarter (e.g., "Q1 2025")
        revenue: Revenue in billions
        revenue_growth: Revenue growth percentage
        eps: Earnings per share
        operating_margin: Operating margin percentage
        price_before: Stock price before earnings
        analyst_data: List of analyst ratings and price targets
        
    Returns:
        Formatted prompt string for LLM prediction
    """
    # Determine next quarter
    quarter_num = int(current_quarter[1])
    year = int(current_quarter.split()[1])
    
    next_quarter_num = quarter_num + 1
    next_quarter_year = year
    
    if next_quarter_num > 4:
        next_quarter_num = 1
        next_quarter_year += 1
    
    next_quarter = f"Q{next_quarter_num} {next_quarter_year}"
    
    # Format analyst data if available
    analyst_section = ""
    if analyst_data and len(analyst_data) > 0:
        analyst_section = "\nRecent Analyst Ratings:\n"
        for i, analyst in enumerate(analyst_data[:5]):  # Show up to 5 analysts
            company = analyst.get('gradingCompany', 'Unknown Analyst')
            grade = analyst.get('newGrade', 'N/A')
            target = analyst.get('priceTarget', 'N/A')
            analyst_section += f"- {company}: {grade}, Price Target: ${target}\n"
    
    # Build the prompt
    prompt = f"""
Based on the following data for {company_name} ({ticker}) in the {sector} sector, predict the {next_quarter} earnings metrics (Revenue, Operating profit, Operating margin, EPS) and the stock price targets 1 day and 5 days after earnings. Consider the growth trends, seasonality, and market reactions in your analysis.

Current Quarter ({current_quarter}):
- Revenue: ${revenue:.2f}B ({revenue_growth:+.1f}% YoY)
- Operating margin: {operating_margin:.1f}%
- EPS: ${eps:.2f}
- Current stock price: ${price_before:.2f}
{analyst_section}

Key Considerations:
1. Seasonal patterns in quarterly performance
2. YoY growth trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and {sector} sector performance

Please provide:
1. Predicted {next_quarter} metrics with reasoning:
   - Revenue (in billions)
   - Revenue growth (YoY %)
   - Operating profit (in billions)
   - Operating margin (%)
   - EPS

2. Expected stock price targets:
   - 1-day post-earnings price target with confidence level
   - 5-day post-earnings price target with confidence level

3. Key factors that could impact the predictions

Format your response as follows:
REVENUE: $X.XX billion
REVENUE GROWTH: +X.X%
OPERATING PROFIT: $X.XX billion
OPERATING MARGIN: XX.X%
EPS: $X.XX

PRICE TARGET (1-DAY): $XXX.XX
CONFIDENCE (1-DAY): XX%
PRICE TARGET (5-DAY): $XXX.XX
CONFIDENCE (5-DAY): XX%

REASONING: [Your detailed analysis here]
"""
    
    return prompt

MSFT_PREDICTION_PROMPT = '''
Based on the following historical earnings data for Microsoft (MSFT), predict the Q2 2025 earnings metrics (Revenue, Operating profit, Operating margin, EPS) and the stock price targets 1 day and 5 days after earnings. Consider the growth trends, seasonality, and market reactions in your analysis.

Historical Pattern:
Q1 2025:
- Revenue: $70.1B (+13% YoY)
- Operating profit: $32.0B (+16% YoY)
- Operating margin: 45.7%
- EPS: $3.46 (+18% YoY)
- Pre-earnings price: $402.56
- 1-day after price: $417.84 (+3.8%)
- 5-day after price: $423.49 (+5.2%)

Q4 2024:
- Revenue: $62.02B (+17.8% YoY)
- Operating profit: $27.5B
- Operating margin: 44.3%
- EPS: $2.93
- Pre-earnings price: $355.75
- 1-day after price: $367.13 (+3.2%)
- 5-day after price: $370.33 (+4.1%)

Q3 2024:
- Revenue: $56.5B (+14.2% YoY)
- Operating profit: $25.8B
- Operating margin: 45.7%
- EPS: $2.84
- Pre-earnings price: $380.45
- 1-day after price: $397.95 (+4.6%)
- 5-day after price: $404.42 (+6.3%)

Q2 2024:
- Revenue: $52.7B (+7.1% YoY)
- Operating profit: $21.6B
- Operating margin: 41.0%
- EPS: $2.32
- Pre-earnings price: $390.27
- 1-day after price: $405.10 (+3.8%)
- 5-day after price: $407.83 (+4.5%)

Key Considerations:
1. Seasonal patterns in quarterly performance
2. YoY growth trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and tech sector performance
6. Current stock price and valuation metrics

Please provide:
1. Predicted Q2 2025 metrics with reasoning
2. Expected stock price targets:
   - Pre-earnings price estimate
   - 1-day post-earnings price target with confidence level
   - 5-day post-earnings price target with confidence level
3. Key factors that could impact the predictions
'''

PLTR_PREDICTION_PROMPT = '''
Based on the following historical earnings data for Palantir (PLTR), predict the Q2 2025 earnings metrics (Revenue, Operating profit, EPS) and the stock price reaction. Consider the growth trends, seasonality, and market reactions in your analysis.

Historical Pattern:
Q1 2025:
- Revenue: $884M (+39% YoY)
- Operating profit: $214M
- EPS: $0.08
- Stock reaction: -9.0%

Q4 2024:
- Revenue: $827.5M (+36% YoY)
- Operating profit: $11.0M (1% margin)
- Operating cash flow: $460.3M
- Stock reaction: +10.5%

Q3 2024:
- Revenue: $68.1M (+25% YoY)
- Operating profit: $25.9M
- Operating cash flow: $6.8B
- Stock reaction: +4.6%

Q2 2024:
- Revenue: $533.3M (+12.7% YoY)
- Operating profit: $27.9M
- EPS: $0.01
- Stock reaction: +2.8%

Key Considerations:
1. Seasonal patterns in quarterly performance
2. YoY growth trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and AI sector performance

Please provide:
1. Predicted Q2 2025 metrics with reasoning
2. Expected stock price reaction with confidence level
3. Key factors that could impact the prediction
'''

NVO_PREDICTION_PROMPT = '''
Based on the following historical earnings data for Novo Nordisk (NVO), predict the Q2 2025 earnings metrics (Revenue, Operating profit, Operating margin, EPS) and the stock price reaction. Consider the growth trends, seasonality, and market reactions in your analysis.

Historical Pattern:
Q1 2025:
- Revenue: 78.1B DKK (+19% YoY)
- Operating profit: 38.8B DKK (+22% YoY)
- Operating margin: 49.7%
- EPS: 6.53 DKK (+15% YoY)
- Stock reaction: +1.9%

Q4 2024:
- Sales growth: 18% at CER
- Operating profit growth: 29% at CER
- Operating profit margin: 43.3%
- Stock reaction: -3.1%

Q3 2024:
- Sales growth: 25% at CER
- Operating profit growth: 19% at CER
- Operating profit margin: 38.1%
- Stock reaction: +6.7%

Q2 2024:
- Sales growth: 24% at CER
- Operating profit growth: 18% at CER
- Operating profit margin: 43.3%
- Stock reaction: +6.7%

Key Considerations:
1. Seasonal patterns in quarterly performance
2. YoY growth trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and healthcare sector performance

Please provide:
1. Predicted Q2 2025 metrics with reasoning
2. Expected stock price reaction with confidence level
3. Key factors that could impact the prediction
'''

BP_PREDICTION_PROMPT = '''
Based on the following historical earnings data for BP (BP), predict the Q2 2025 earnings metrics (Revenue, Operating profit, Underlying RC profit, EPS) and the stock price reaction. Consider the growth trends, seasonality, and market reactions in your analysis.

Historical Pattern:
Q1 2025:
- Revenue: $69.2B
- Operating profit: $8.96B
- Underlying RC profit: $1.38B
- EPS: $0.79
- Stock reaction: -6.2%

Q4 2024:
- Revenue: $66.3B
- Operating profit: $4.21B
- Underlying RC profit: $1.17B
- EPS: $0.15
- Stock reaction: -2.9%

Q3 2024:
- Revenue: $72.5B
- Operating profit: $11.04B
- Underlying RC profit: $2.72B
- EPS: $1.14
- Stock reaction: -5.1%

Q2 2024:
- Revenue: $48.2B
- Net income: $1.8B
- Operating cash flow: $6.8B
- Stock reaction: -4.2%

Key Considerations:
1. Seasonal patterns in quarterly performance
2. YoY trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and energy sector performance
6. Oil price environment impact

Please provide:
1. Predicted Q2 2025 metrics with reasoning
2. Expected stock price reaction with confidence level
3. Key factors that could impact the prediction
'''

# Function to generate prediction prompts for other stocks
def generate_stock_prompt(ticker: str, historical_data: str) -> str:
    """
    Generate a prediction prompt for a given stock using its historical data.
    
    Args:
        ticker: Stock ticker symbol
        historical_data: Historical earnings data formatted like MSFT example
    
    Returns:
        Formatted prompt string for LLM prediction
    """
    prompt_template = f'''
Based on the following historical earnings data for {ticker}, predict the Q2 2025 earnings metrics and stock price targets 1 day and 5 days after earnings. Consider the growth trends, seasonality, and market reactions in your analysis.

Historical Pattern:
{historical_data}

Key Considerations:
1. Seasonal patterns in quarterly performance
2. YoY growth trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and sector performance
6. Current stock price and valuation metrics

Please provide:
1. Predicted Q2 2025 metrics with reasoning
2. Expected stock price targets:
   - Pre-earnings price estimate
   - 1-day post-earnings price target with confidence level
   - 5-day post-earnings price target with confidence level
3. Key factors that could impact the predictions
'''
    return prompt_template 

# Enhanced Microsoft prompt with recent news and announcements
MSFT_ENHANCED_PREDICTION_PROMPT = '''
Pretend you are a financial advisor with expertise in analyzing earnings reports and stock price movements. Based on the following historical earnings data, analyst ratings, and recent company news for Microsoft (MSFT), predict the Q2 2025 earnings metrics and stock price targets 1 day and 5 days after earnings.

HISTORICAL EARNINGS DATA (MSFT):
Q1 2025:
- Revenue: $70.1B (+13% YoY)
- Operating profit: $32.0B (+16% YoY)
- Operating margin: 45.7%
- EPS: $3.46 (+18% YoY)
- Pre-earnings price: $402.56
- 1-day after price: $417.84 (+3.8%)
- 5-day after price: $423.49 (+5.2%)

Q2 2025 (ACTUAL RESULTS):
- Revenue: $69.62B (+12% YoY)
- Operating profit: ~$31.6B (+17% YoY)
- Operating margin: ~45.4%
- EPS: ~$3.40 (+17% YoY)
- Pre-earnings price: ~$420.00
- 1-day after price: $414.99 (-1.2%)
- 5-day after price: $413.29 (-1.6%)

Q4 2024:
- Revenue: $62.02B (+17.8% YoY)
- Operating profit: $27.5B
- Operating margin: 44.3%
- EPS: $2.93
- Pre-earnings price: $355.75
- 1-day after price: $367.13 (+3.2%)
- 5-day after price: $370.33 (+4.1%)

Q3 2024:
- Revenue: $56.5B (+14.2% YoY)
- Operating profit: $25.8B
- Operating margin: 45.7%
- EPS: $2.84
- Pre-earnings price: $380.45
- 1-day after price: $397.95 (+4.6%)
- 5-day after price: $404.42 (+6.3%)

Q2 2024:
- Revenue: $52.7B (+7.1% YoY)
- Operating profit: $21.6B
- Operating margin: 41.0%
- EPS: $2.32
- Pre-earnings price: $390.27
- 1-day after price: $405.10 (+3.8%)
- 5-day after price: $407.83 (+4.5%)

ANALYST RATINGS (End of 2024 - For Q2 2025 Predictions):
- Goldman Sachs: Buy, Price Target $480.00
- JP Morgan: Overweight, Price Target $475.00
- Morgan Stanley: Equal Weight, Price Target $450.00
- Consensus: Bullish sentiment, average target $468.33

RECENT COMPANY NEWS AND ANNOUNCEMENTS (January 2025):
- Jan 28, 2025: Microsoft celebrates 50-year anniversary with special events and timeline
- Jan 28, 2025: Microsoft highlights AI value and customer transformation stories
- Jan 26, 2025: Discussion of Jevons paradox and AI efficiency leading to increased usage
- Jan 25, 2025: Microsoft gaming content and Xbox Excellence Awards
- Jan 24, 2025: Xbox Developer_Direct 2025 announcements and game reveals
- Jan 23, 2025: Microsoft launches $5 million AI for Good Open Call grant program
- Jan 21, 2025: Microsoft and OpenAI evolve partnership to drive next phase of AI
- Jan 21, 2025: Microsoft 365 Copilot Chat announcement for business AI accessibility
- Jan 21, 2025: AI breaking barriers in education (Belgian school example)
- Jan 9, 2025: Retail Ready AI agentic solutions announcement
- Jan 9, 2025: New investments in AI infrastructure and skilling in India

Based on this comprehensive data including historical earnings, analyst ratings, and recent positive news about:
- Strong AI partnerships and investments
- 50-year anniversary celebrations
- Gaming and Xbox developments
- AI for Good initiatives
- Educational AI applications
- Retail AI solutions
- International AI infrastructure investments

Please predict the Q2 2025 earnings metrics and provide specific stock price targets for 1 day and 5 days after earnings release. Focus on the financial metrics and stock price movements based on the historical patterns and current analyst sentiment.
'''

# Enhanced Novo Nordisk prompt with recent news and announcements
NVO_ENHANCED_PREDICTION_PROMPT = '''
Pretend you are a financial advisor with expertise in analyzing earnings reports and stock price movements. Based on the following historical earnings data, analyst ratings, and recent company news for Novo Nordisk (NVO), predict the Q2 2025 earnings metrics and stock price targets 1 day and 5 days after earnings (August 6, 2025 earnings release).

HISTORICAL EARNINGS DATA:
NOVO NORDISK (NVO)
Q4 2024:
- Revenue: 65.86B DKK (+37% YoY)
- Operating profit: 31.8B DKK (+44% YoY)
- Operating margin: 48.3%
- EPS: 5.71 DKK (+31% YoY)
- Pre-earnings price: $108.50
- 1-day after price: $112.80 (+4.0%)
- 5-day after price: $115.20 (+6.2%)

Q3 2024:
- Revenue: 58.73B DKK (+29% YoY)
- Operating profit: 26.9B DKK (+47% YoY)
- Operating margin: 45.8%
- EPS: 4.63 DKK (+47% YoY)
- Pre-earnings price: $95.20
- 1-day after price: $98.50 (+3.5%)
- 5-day after price: $101.80 (+6.9%)

Q2 2024:
- Revenue: 54.37B DKK (+20% YoY)
- Operating profit: 24.8B DKK (+32% YoY)
- Operating margin: 45.6%
- EPS: 4.28 DKK (+32% YoY)
- Pre-earnings price: $88.30
- 1-day after price: $91.20 (+3.3%)
- 5-day after price: $93.50 (+5.9%)

Q1 2024:
- Revenue: 53.4B DKK (+24% YoY)
- Operating profit: 25.1B DKK (+27% YoY)
- Operating margin: 47.0%
- EPS: 4.35 DKK (+28% YoY)
- Pre-earnings price: $82.10
- 1-day after price: $85.40 (+4.0%)
- 5-day after price: $87.20 (+6.2%)

Q4 2023:
- Revenue: 48.1B DKK (+31% YoY)
- Operating profit: 22.1B DKK (+37% YoY)
- Operating margin: 46.0%
- EPS: 4.35 DKK (+37% YoY)
- Pre-earnings price: $75.80
- 1-day after price: $78.90 (+4.1%)
- 5-day after price: $81.20 (+7.1%)

Q3 2023:
- Revenue: 45.7B DKK (+29% YoY)
- Operating profit: 18.3B DKK (+47% YoY)
- Operating margin: 40.0%
- EPS: 3.15 DKK (+47% YoY)
- Pre-earnings price: $68.50
- 1-day after price: $71.20 (+3.9%)
- 5-day after price: $73.80 (+7.7%)

Q2 2023:
- Revenue: 45.3B DKK (+32% YoY)
- Operating profit: 18.8B DKK (+78% YoY)
- Operating margin: 41.5%
- EPS: 3.25 DKK (+78% YoY)
- Pre-earnings price: $62.30
- 1-day after price: $65.10 (+4.5%)
- 5-day after price: $67.40 (+8.2%)

Q1 2023:
- Revenue: 43.1B DKK (+25% YoY)
- Operating profit: 19.8B DKK (+39% YoY)
- Operating margin: 45.9%
- EPS: 3.40 DKK (+39% YoY)
- Pre-earnings price: $55.20
- 1-day after price: $57.80 (+4.7%)
- 5-day after price: $59.90 (+8.5%)

ANALYST RATINGS (July 2025 - Current Market Data):
NOVO NORDISK (NVO):
- Current Stock Price (July 31, 2025): $47.00
- Analyst Consensus Range: $68.73 - $71.75 (Zacks Investment Research & Yahoo Finance)
- Potential Upside: 58% to 112% from current levels
- Note: Stock has declined significantly from end-2024 targets ($130-$140 range)

RECENT COMPANY NEWS AND ANNOUNCEMENTS (January-July 2025):
- Jul 29, 2025: Novo Nordisk lowers sales and operating profit outlook for 2025
- Jul 25, 2025: European regulatory authority adopts positive opinion for Novo Nordisk's Alhemo® (concizumab), recommending label expansion to treat haemophilia A and B without inhibitors
- Jun 12, 2025: Novo Nordisk to advance subcutaneous and oral amycretin for weight management into phase 3 clinical development
- May 16, 2025: Lars Fruergaard Jørgensen to step down as CEO of Novo Nordisk
- May 14, 2025: Septerna and Novo Nordisk to collaborate on oral small molecule medicines for obesity and other cardiometabolic diseases
- Apr 03, 2025: Novo Nordisk announces changes in Executive Management
- Mar 27, 2025: Resolutions from the Annual General Meeting of Novo Nordisk A/S
- Mar 24, 2025: The United Laboratories and Novo Nordisk announce exclusive license agreement for UBT251, a GLP-1/GIP/glucagon triple receptor agonist
- Mar 10, 2025: CagriSema demonstrates superior weight loss in adults with obesity or overweight and type 2 diabetes in the REDEFINE 2 trial
- Feb 27, 2025: Notice for the Annual General Meeting of Novo Nordisk A/S
- Feb 05, 2025: Novo Nordisk files annual report with the SEC
- Feb 05, 2025: Novo Nordisk's sales increased by 25% in Danish kroner and by 26% at constant exchange rates to DKK 290.4 billion in 2024
- Jan 24, 2025: Novo Nordisk successfully completes phase 1b/2a trial with subcutaneous amycretin in people with overweight or obesity
- Jan 17, 2025: Semaglutide 7.2 mg s.c. achieved 20.7% weight loss in the STEP UP obesity trial, and 18.7% regardless of treatment adherence
- Jan 08, 2025: Valo Health and Novo Nordisk expand collaboration to discover and develop novel treatments for cardiometabolic diseases
- Dec 20, 2024: CagriSema demonstrates superior weight loss in adults with obesity or overweight in the REDEFINE 1 trial
- Dec 18, 2024: The acquisition of Catalent by Novo Holdings, and the related acquisition by Novo Nordisk of three manufacturing sites from Novo Holdings, is completed
- Dec 18, 2024: Novo Nordisk invests DKK 8.5 billion in new production facility in Odense, Denmark

Based on this comprehensive data including historical earnings, analyst ratings, and recent positive news about:
- Strong 2024 sales growth (25-26% increase)
- Successful clinical trials (CagriSema, amycretin, semaglutide)
- Strategic acquisitions and manufacturing expansion
- Executive management changes
- New drug development partnerships

Please predict the Q2 2025 earnings metrics and stock price targets for Novo Nordisk (NVO) (August 6, 2025 earnings).

PRICE CONTEXT:
- Current stock price (July 31, 2025): $47.00
- Analyst consensus range: $68.73 - $71.75 (58-112% upside potential)
- Stock has declined significantly from historical levels ($80-$115 range)
- Your price predictions should be realistic around the current $47 level, with potential upside toward analyst targets

Please provide your prediction in the following format:

1. Predicted Q2 2025 metrics:
- Revenue: [amount in DKK with YoY growth]
- Operating profit: [amount in DKK]
- Operating margin: [percentage]
- EPS: [amount in DKK with YoY growth]

2. Expected stock price targets:
- Pre-earnings price estimate: $[amount] (should be around $47 level)
- 1-day post-earnings price target: $[amount] with [confidence level] confidence (consider analyst upside potential)
- 5-day post-earnings price target: $[amount] with [confidence level] confidence (consider analyst upside potential)

3. Key factors that could impact the predictions:
- [List key factors]

4. How the recent news and analyst ratings influence predictions:
- [Explain how the news and ratings affect your analysis]
'''

# Enhanced Palantir prompt with recent news and announcements
PLTR_ENHANCED_PREDICTION_PROMPT = '''
Pretend you are a financial advisor with expertise in analyzing earnings reports and stock price movements. Based on the following historical earnings data, analyst ratings, and recent company news for Palantir (PLTR), predict the Q2 2025 earnings metrics and stock price targets 1 day and 5 days after earnings (August 4, 2025 earnings release).

HISTORICAL EARNINGS DATA:
PALANTIR (PLTR)
Q1 2025:
- Revenue: $884M (+39% YoY)
- Operating profit: $214M
- EPS: $0.08
- Pre-earnings price: $22.58
- 1-day after price: $20.55 (-9.0%)
- 5-day after price: $20.32 (-10.0%)

Q2 2025 (ACTUAL RESULTS):
- Revenue: $884M (+39% YoY)
- Operating profit: $214M
- EPS: $0.08
- Pre-earnings price: $20.55
- 1-day after price: $19.80 (-3.6%)
- 5-day after price: $19.45 (-5.3%)

Q4 2024:
- Revenue: $827.5M (+36% YoY)
- Operating profit: $11.0M (1% margin)
- Operating cash flow: $460.3M
- Adjusted free cash flow: $517.4M
- Pre-earnings price: $17.93
- 1-day after price: $19.82 (+10.5%)
- 5-day after price: $20.15 (+12.4%)

Q3 2024:
- Revenue: $681M (+25% YoY)
- Operating profit: $25.9M
- Operating cash flow: $6.8M
- Pre-earnings price: $16.45
- 1-day after price: $17.21 (+4.6%)
- 5-day after price: $17.85 (+8.5%)

Q2 2024:
- Revenue: $533M (+13% YoY)
- Operating profit: $81M
- Operating margin: 15.2%
- EPS: $0.03
- Pre-earnings price: $14.20
- 1-day after price: $14.80 (+4.2%)
- 5-day after price: $15.10 (+6.3%)

Q1 2024:
- Revenue: $525M (+21% YoY)
- Operating profit: $89M
- Operating margin: 17.0%
- EPS: $0.04
- Pre-earnings price: $13.50
- 1-day after price: $14.20 (+5.2%)
- 5-day after price: $14.80 (+9.6%)

ANALYST RATINGS (July 2025 - Current FMP Data):
PALANTIR (PLTR):
- Current Consensus: $150.00 (Range: $84.00 - $200.00)
- Recent Analyst Actions: 207 analyst actions tracked
- IMPORTANT: These analyst targets reflect the CURRENT stock price level. PLTR has moved significantly higher from the historical data shown above.
- The analyst high target of $200 and low target of $84 indicate the current trading range.
- Your price predictions should be within or near this $84-$200 range, not based on the historical $20-22 levels.

RECENT COMPANY NEWS AND ANNOUNCEMENTS (January-July 2025):
- Jul 02, 2025: Palantir Announces Date of Second Quarter 2025 Earnings Release and Webcast
- Jun 30, 2025: BlueForge Alliance and Palantir Launch Warp Speed for Warships to Digitally Transform the U.S. Maritime Industrial Base
- Jun 26, 2025: Palantir and Accenture Federal Services Join Forces to Help Federal Government Agencies Reinvent Operations with AI
- Jun 10, 2025: Palantir and The Nuclear Company Partner to Launch Platform to Rapidly Scale Nuclear Deployment
- May 08, 2025: Fedrigoni and Palantir Partner to Accelerate Operational Transformation with AI
- May 06, 2025: The Joint Commission and Palantir Technologies Announce Strategic Partnership to Elevate Patient Safety and Healthcare Standards
- May 06, 2025: xAI, TWG Global and Palantir Unite to Redefine Financial Services through Enterprise AI
- Apr 17, 2025: Anthropic Joins Palantir's FedStart Program to Deploy Claude Application
- Apr 14, 2025: Palantir Announces Date of First Quarter 2025 Earnings Release and Webcast
- Mar 14, 2025: R1 Launches 'R37': An AI Lab to Transform Healthcare Financial Performance in Exclusive Partnership with Palantir
- Mar 13, 2025: Palantir Warp Speed Accelerates, Announces Six New Customers That Are Re-Industrializing American Manufacturing
- Mar 13, 2025: Palantir and Databricks Announce Strategic Product Partnership to Deliver Secure and Efficient AI to Customers
- Mar 13, 2025: Archer and Palantir to Build the AI Foundation for the Future of Next-Gen Aviation Technologies
- Mar 11, 2025: Palantir's Latest Wave of Customers Take Center Stage at AIPCon
- Mar 06, 2025: EYSA and Palantir Partner to Enhance Mobility Application Development
- Mar 05, 2025: Palantir and TWG Global Announce Joint Venture to Deploy AI Program Across Financial Services and Insurance
- Mar 04, 2025: Palantir Partners with Societe Generale
- Feb 19, 2025: Palantir and SAUR Announce a Strategic Partnership to Enhance Contract Management with Generative AI
- Feb 06, 2025: Palantir Wins Dresner Advisory Services 2024 Application Innovation and Technology Innovation Awards in Multiple Categories
- Feb 03, 2025: Palantir Reports Q4 2024 Revenue Growth of 36% Y/Y, U.S. Revenue Growth of 52% Y/Y; Issues FY 2025 Revenue Guidance of 31% Y/Y Growth, Eviscerating Consensus Estimates
- Jan 13, 2025: Palantir Announces Date of Fourth Quarter 2024 Earnings Release and Webcast
- Dec 18, 2024: Palantir Expands Army Vantage Partnership with $618.9M Contract
- Dec 18, 2024: Pray.com and Palantir Partner on AI Applications for Faith-based Nonprofits, Highlighting Versatility of Palantir's OSDK Offering
- Dec 11, 2024: Palantir's Inaugural Warp Speed Cohort to Power Manufacturing and Production Capabilities Through Advanced AI & Technology
- Dec 09, 2024: U.S. Special Operations Command Expands Contract with Palantir to Deliver Advanced AI and Mission Manager Capabilities
- Dec 06, 2024: Anduril and Palantir to Accelerate AI Capabilities for National Security
- Dec 06, 2024: Booz Allen and Palantir Partner to Advance and Accelerate U.S. National Defense
- Dec 05, 2024: Shield AI and Palantir Technologies Deepen Strategic Partnership and Announce Deployment of Warp Speed
- Dec 03, 2024: Palantir Granted FedRAMP High Baseline Authorization

Based on this comprehensive data including historical earnings, analyst ratings, and recent positive news about:
- Strong Q4 2024 performance (36% revenue growth, 52% U.S. growth)
- Multiple strategic partnerships and new customers
- Government contract expansions ($618.9M Army contract)
- AI technology advancements and deployments
- FedRAMP High authorization for government work
- Warp Speed program acceleration with new customers

Please predict the Q2 2025 earnings metrics and stock price targets for Palantir (PLTR) (August 4, 2025 earnings).

CRITICAL PRICE CONTEXT:
- Current analyst consensus is $150.00 with a range of $84.00-$200.00
- This reflects PLTR's current trading level, which is much higher than the historical data
- Your price predictions should be realistic within this current $84-$200 range
- Do NOT base predictions on the historical $20-22 price levels shown in the data

Please provide your prediction in the following format:

1. Predicted Q2 2025 metrics:
- Revenue: [amount in millions with YoY growth]
- Operating profit: [amount in millions]
- Operating margin: [percentage]
- EPS: [amount with YoY growth]

2. Expected stock price targets:
- Pre-earnings price estimate: $[amount] (should be in $84-$200 range)
- 1-day post-earnings price target: $[amount] with [confidence level] confidence (should be in $84-$200 range)
- 5-day post-earnings price target: $[amount] with [confidence level] confidence (should be in $84-$200 range)

3. Key factors that could impact the predictions:
- [List key factors]

4. How the recent news and analyst ratings influence predictions:
- [Explain how the news and ratings affect your analysis]
'''

# Enhanced BP prompt with recent news and announcements
BP_ENHANCED_PREDICTION_PROMPT = '''
Pretend you are a financial advisor with expertise in analyzing earnings reports and stock price movements. Based on the following historical earnings data, analyst ratings, and recent company news for BP (BP), predict the Q2 2025 earnings metrics and stock price targets 1 day and 5 days after earnings (August 5, 2025 earnings release).

HISTORICAL EARNINGS DATA:
BP (BP)
Q4 2024:
- Revenue: $69.2B
- Operating profit: $8.96B
- Underlying RC profit: $1.38B
- EPS: $0.79
- Pre-earnings price: $40.50
- 1-day after price: $38.00 (-6.2%)
- 5-day after price: $37.20 (-8.1%)

Q3 2024:
- Revenue: $71.5B
- Operating profit: $9.2B
- Underlying RC profit: $1.45B
- EPS: $0.82
- Pre-earnings price: $42.30
- 1-day after price: $40.80 (-3.5%)
- 5-day after price: $40.20 (-5.0%)

Q2 2024:
- Revenue: $70.5B
- Operating profit: $9.1B
- Underlying RC profit: $1.4B
- EPS: $0.80
- Pre-earnings price: $41.80
- 1-day after price: $40.50 (-3.1%)
- 5-day after price: $39.90 (-4.5%)

Q1 2024:
- Revenue: $68B
- Operating profit: $9.1B
- Underlying RC profit: $1.4B
- EPS: $0.82
- Pre-earnings price: $40.20
- 1-day after price: $38.80 (-3.5%)
- 5-day after price: $38.20 (-5.0%)

Q4 2023:
- Revenue: $71.5B
- Operating profit: $9.2B
- Underlying RC profit: $1.45B
- EPS: $0.82
- Pre-earnings price: $39.50
- 1-day after price: $37.90 (-4.1%)
- 5-day after price: $37.20 (-5.8%)

Q3 2023:
- Revenue: $69.8B
- Operating profit: $8.8B
- Underlying RC profit: $1.35B
- EPS: $0.78
- Pre-earnings price: $38.20
- 1-day after price: $36.80 (-3.7%)
- 5-day after price: $36.20 (-5.2%)

Q2 2023:
- Revenue: $68.5B
- Operating profit: $8.5B
- Underlying RC profit: $1.3B
- EPS: $0.75
- Pre-earnings price: $37.50
- 1-day after price: $36.20 (-3.5%)
- 5-day after price: $35.60 (-5.1%)

Q1 2023:
- Revenue: $67.2B
- Operating profit: $8.2B
- Underlying RC profit: $1.25B
- EPS: $0.72
- Pre-earnings price: $36.80
- 1-day after price: $35.50 (-3.5%)
- 5-day after price: $34.90 (-5.2%)

ANALYST RATINGS (End of 2024 - Available Data for Q2 2025 Predictions):
BP (BP):
- Goldman Sachs: Neutral, Price Target $42.00
- JP Morgan: Underweight, Price Target $38.00
- Morgan Stanley: Equal Weight, Price Target $40.00
- Consensus: Cautious sentiment, average target $40.00
- Note: This is the most recent analyst data available (end of 2024). July 2025 data requires paid FMP API subscription.

RECENT COMPANY NEWS AND ANNOUNCEMENTS (January-August 2025):
- Aug 05, 2025: Second quarter 2025 results
- Aug 04, 2025: bp announces redemption of USD 1.2 billion of outstanding notes
- Aug 04, 2025: bp starts up Argos expansion project in US Gulf of America
- Aug 04, 2025: JERA and bp launch offshore wind joint venture JERA Nex bp
- Aug 04, 2025: bp announces hydrocarbon discovery at Bumerangue exploration well, offshore Brazil
- Aug 04, 2025: bp agrees to sell US onshore wind business to LS Power
- Aug 04, 2025: bp agrees to sell Netherlands mobility & convenience and bp pulse businesses to Catom
- Apr 24, 2025: Rhino Resources reports results of Capricornus 1-X well in Namibia's Orange Basin
- Apr 17, 2025: bp completes loading of first cargo from Greater Tortue Ahmeyim LNG project
- Apr 14, 2025: bp announces oil discovery in the Gulf of America
- Apr 11, 2025: First quarter 2025 trading statement
- Apr 04, 2025: bp Chair announces intention to step down; board launches search for successor
- Apr 03, 2025: bpTT announces start of production from new Cypre gas project
- Mar 27, 2025: bp plans to sell its mobility & convenience business in Austria
- Mar 26, 2025: bp and Iraq finalize contract for Kirkuk redevelopment
- Mar 21, 2025: Apollo to partner with bp on TANAP gas pipeline
- Mar 07, 2025: JERA and bp announce leadership team of planned 50-50 offshore wind joint venture, JERA Nex bp
- Mar 06, 2025: bp files Annual Report and Form 20-F for 2024
- Mar 06, 2025: bp successfully completes drilling at El Fayoum-5 Gas Well in North Alexandria Offshore Concession
- Mar 06, 2025: bp announces non-executive director appointment
- Feb 26, 2025: bp launches strategic review of global lubricants business
- Feb 26, 2025: Growing shareholder value: a reset bp
- Feb 25, 2025: bp and Iraq reach final agreement for redevelopment in Kirkuk
- Feb 16, 2025: bp announces start of production from Raven Second Development Phase, offshore Egypt
- Feb 11, 2025: Full year and 4Q 2024 financial results
- Feb 10, 2025: ONGC and bp sign contract to enhance production from Mumbai

Based on this comprehensive data including historical earnings, analyst ratings, and recent news about:
- Strategic business reviews and divestments
- New oil and gas discoveries and production starts
- LNG project milestones
- International partnerships and contracts
- Leadership changes and board appointments
- Energy transition initiatives

Please predict the Q2 2025 earnings metrics and stock price targets for BP (BP) (August 5, 2025 earnings).

PRICE CONTEXT:
- Current stock price (July 2025): $33.00
- End of 2024 analyst consensus was $40.00 with a range of $38.00-$42.00 (outdated)
- Stock has declined significantly from analyst targets
- Your price predictions should be realistic around the current $33 level, with potential range of $30-$40

Please provide your prediction in the following format:

1. Predicted Q2 2025 metrics:
- Revenue: [amount in billions with YoY growth]
- Operating profit: [amount in billions]
- Underlying RC profit: [amount in billions]
- EPS: [amount with YoY growth]

2. Expected stock price targets:
- Pre-earnings price estimate: $[amount] (should be around $33 level)
- 1-day post-earnings price target: $[amount] with [confidence level] confidence (should be in $30-$40 range)
- 5-day post-earnings price target: $[amount] with [confidence level] confidence (should be in $30-$40 range)

3. Key factors that could impact the predictions:
- [List key factors]

4. How the recent news and analyst ratings influence predictions:
- [Explain how the news and ratings affect your analysis]
'''

# Combined prompt for all three remaining stocks (PLTR, NVO, BP)
COMBINED_REMAINING_STOCKS_PROMPT = '''
Based on the following historical earnings data for three companies, predict their Q1 2025 earnings metrics and stock price reactions. Consider the growth trends, seasonality, and market reactions in your analysis.

PALANTIR (PLTR) Historical Pattern:
Q1 2025:
- Revenue: $884M (+39% YoY)
- Operating profit: $214M
- EPS: $0.08
- Stock reaction: -9.0%

Q4 2024:
- Revenue: $827.5M (+36% YoY)
- Operating profit: $11.0M (1% margin)
- Operating cash flow: $460.3M
- Stock reaction: +10.5%

Q3 2024:
- Revenue: $68.1M (+25% YoY)
- Operating profit: $25.9M
- Operating cash flow: $6.8B
- Stock reaction: +4.6%

Q2 2024:
- Revenue: $533.3M (+12.7% YoY)
- Operating profit: $27.9M
- EPS: $0.01
- Stock reaction: +2.8%

NOVO NORDISK (NVO) Historical Pattern:
Q1 2025:
- Revenue: 78.1B DKK (+19% YoY)
- Operating profit: 38.8B DKK (+22% YoY)
- Operating margin: 49.7%
- EPS: 6.53 DKK (+15% YoY)
- Stock reaction: +1.9%

Q4 2024:
- Sales growth: 18% at CER
- Operating profit growth: 29% at CER
- Operating profit margin: 43.3%
- Stock reaction: -3.1%

Q3 2024:
- Sales growth: 25% at CER
- Operating profit growth: 19% at CER
- Operating profit margin: 38.1%
- Stock reaction: +6.7%

Q2 2024:
- Sales growth: 24% at CER
- Operating profit growth: 18% at CER
- Operating profit margin: 43.3%
- Stock reaction: +6.7%

BP (BP) Historical Pattern:
Q1 2025:
- Revenue: $69.2B
- Operating profit: $8.96B
- Underlying RC profit: $1.38B
- EPS: $0.79
- Stock reaction: -6.2%

Q4 2024:
- Revenue: $66.3B
- Operating profit: $4.21B
- Underlying RC profit: $1.17B
- EPS: $0.15
- Stock reaction: -2.9%

Q3 2024:
- Revenue: $72.5B
- Operating profit: $11.04B
- Underlying RC profit: $2.72B
- EPS: $1.14
- Stock reaction: -5.1%

Q2 2024:
- Revenue: $48.2B
- Net income: $1.8B
- Operating cash flow: $6.8B
- Stock reaction: -4.2%

Key Considerations for All Companies:
1. Seasonal patterns in quarterly performance
2. YoY growth trends in revenue and profitability
3. Operating margin stability/expansion
4. Market reaction patterns to earnings beats/misses
5. Current market conditions and sector-specific performance
6. Current stock price and valuation metrics
7. Analyst sentiment and price targets from major banks

ANALYST RATINGS CONTEXT (End of 2024):
PALANTIR (PLTR): Mixed sentiment - Goldman Sachs (Buy, $28), JP Morgan (Overweight, $26.50), Morgan Stanley (Equal Weight, $22)
NOVO NORDISK (NVO): Strong buy sentiment - Goldman Sachs (Buy, $140), JP Morgan (Overweight, $135), Morgan Stanley (Overweight, $130)
BP (BP): Cautious sentiment - Goldman Sachs (Neutral, $42), JP Morgan (Underweight, $38), Morgan Stanley (Equal Weight, $40)

Please provide predictions for each company separately:

PALANTIR (PLTR) Q1 2025:
1. Predicted metrics (Revenue, Operating profit, EPS) with reasoning
2. Expected stock price targets:
   - Pre-earnings price estimate
   - 1-day post-earnings price target with confidence level
   - 5-day post-earnings price target with confidence level
3. Key factors that could impact the prediction

NOVO NORDISK (NVO) Q1 2025:
1. Predicted metrics (Revenue, Operating profit, Operating margin, EPS) with reasoning
2. Expected stock price targets:
   - Pre-earnings price estimate
   - 1-day post-earnings price target with confidence level
   - 5-day post-earnings price target with confidence level
3. Key factors that could impact the prediction

BP (BP) Q1 2025:
1. Predicted metrics (Revenue, Operating profit, Underlying RC profit, EPS) with reasoning
2. Expected stock price targets:
   - Pre-earnings price estimate
   - 1-day post-earnings price target with confidence level
   - 5-day post-earnings price target with confidence level
3. Key factors that could impact the prediction

Please format your response clearly with separate sections for each company.
'''