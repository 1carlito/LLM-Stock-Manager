import re
from typing import Dict, List, Tuple
from dataclasses import dataclass
from enum import Enum
import os

class Sector(Enum):
    AI_TECH = "AI/TECH"
    HEALTHCARE = "HEALTHCARE" 
    ENERGY = "ENERGY"

@dataclass
class EarningsReport:
    date: str
    revenue: float
    revenue_growth: float
    operating_profit: float
    operating_margin: float
    eps: float
    price_before: float
    price_after: float
    
    @property
    def price_change_pct(self) -> float:
        return ((self.price_after - self.price_before) / self.price_before) * 100

class Company:
    def __init__(self, ticker: str, name: str, sector: Sector):
        self.ticker = ticker
        self.name = name
        self.sector = sector
        self.earnings_history: List[EarningsReport] = []
        
    def add_earnings_report(self, report: EarningsReport):
        self.earnings_history.append(report)
        
    def get_avg_reaction(self) -> float:
        if not self.earnings_history:
            return 0.0
        reactions = [report.price_change_pct for report in self.earnings_history]
        return sum(reactions) / len(reactions)
    
    def get_latest_metrics(self) -> Dict:
        """Get the latest earnings metrics for LLM predictions"""
        if not self.earnings_history:
            return {}
        
        latest = self.earnings_history[-1]
        return {
            'revenue': latest.revenue,
            'revenue_growth': latest.revenue_growth,
            'operating_profit': latest.operating_profit,
            'operating_margin': latest.operating_margin,
            'eps': latest.eps,
            'price_before': latest.price_before,
            'price_after': latest.price_after,
            'price_change_pct': latest.price_change_pct
        }
    
    def get_historical_summary(self) -> str:
        """Get a summary of historical performance for LLM context"""
        if not self.earnings_history:
            return "No historical data available."
        
        total_quarters = len(self.earnings_history)
        positive_reactions = sum(1 for r in self.earnings_history if r.price_change_pct > 0)
        avg_revenue_growth = sum(r.revenue_growth for r in self.earnings_history) / total_quarters
        avg_margin = sum(r.operating_margin for r in self.earnings_history) / total_quarters
        
        return f"Historical Performance: {total_quarters} quarters analyzed. " \
               f"Positive reactions: {positive_reactions}/{total_quarters} ({positive_reactions/total_quarters*100:.1f}%). " \
               f"Average revenue growth: {avg_revenue_growth:.1f}%. " \
               f"Average operating margin: {avg_margin:.1f}%."

def parse_number(text: str) -> float:
    """Extract number from text containing currency symbols and units"""
    # Remove currency symbols and units
    text = text.replace('$', '').replace('B', '').replace('M', '')
    # Extract number using regex
    match = re.search(r'[-+]?\d*\.?\d+', text)
    if match:
        return float(match.group())
    return 0.0

def parse_percentage(text: str) -> float:
    """Extract percentage from text"""
    match = re.search(r'[-+]?\d*\.?\d+', text)
    if match:
        return float(match.group())
    return 0.0

def parse_earnings_data(filename: str) -> Dict[str, Company]:
    companies = {}
    current_company = None
    current_quarter = {}
    
    with open(filename, 'r') as f:
        lines = f.readlines()
        
    for line in lines:
        line = line.strip()
        if not line:
            continue
            
        # New company section
        if "PALANTIR (PLTR)" in line:
            current_company = Company("PLTR", "Palantir", Sector.AI_TECH)
            companies["PLTR"] = current_company
            current_quarter = {}
        elif "NOVO NORDISK (NVO)" in line:
            current_company = Company("NVO", "Novo Nordisk", Sector.HEALTHCARE)
            companies["NVO"] = current_company
            current_quarter = {}
        elif "BP" in line and len(line) < 5:  # Just "BP" alone
            current_company = Company("BP", "BP", Sector.ENERGY)
            companies["BP"] = current_company
            current_quarter = {}
        elif "MICROSOFT (MSFT)" in line:
            current_company = Company("MSFT", "Microsoft", Sector.AI_TECH)
            companies["MSFT"] = current_company
            current_quarter = {}
            
        # Quarter marker
        elif line.startswith("Q") and ":" in line:
            if current_quarter:  # Save previous quarter if exists
                try:
                    report = EarningsReport(
                        date=current_quarter.get('date', ''),
                        revenue=current_quarter.get('revenue', 0.0),
                        revenue_growth=current_quarter.get('revenue_growth', 0.0),
                        operating_profit=current_quarter.get('operating_profit', 0.0),
                        operating_margin=current_quarter.get('operating_margin', 0.0),
                        eps=current_quarter.get('eps', 0.0),
                        price_before=current_quarter.get('price_before', 0.0),
                        price_after=current_quarter.get('price_after', 0.0)
                    )
                    current_company.add_earnings_report(report)
                except Exception as e:
                    print(f"Error processing quarter: {e}")
            current_quarter = {'date': line.split(':')[0].strip()}
            
        # Parse metrics
        elif current_quarter is not None:
            if "Revenue:" in line:
                current_quarter['revenue'] = parse_number(line.split(':')[1])
                if "YoY" in line:
                    current_quarter['revenue_growth'] = parse_percentage(line.split('(')[1])
            elif "Operating profit:" in line:
                current_quarter['operating_profit'] = parse_number(line.split(':')[1])
            elif "margin:" in line:
                current_quarter['operating_margin'] = parse_percentage(line)
            elif "EPS:" in line:
                current_quarter['eps'] = parse_number(line.split(':')[1])
            elif "Stock price before earnings:" in line:
                current_quarter['price_before'] = parse_number(line.split(':')[1])
            elif "Stock price after earnings:" in line:
                current_quarter['price_after'] = parse_number(line.split(':')[1])
                
    # Add final quarter if exists
    if current_quarter and current_company:
        try:
            report = EarningsReport(
                date=current_quarter.get('date', ''),
                revenue=current_quarter.get('revenue', 0.0),
                revenue_growth=current_quarter.get('revenue_growth', 0.0),
                operating_profit=current_quarter.get('operating_profit', 0.0),
                operating_margin=current_quarter.get('operating_margin', 0.0),
                eps=current_quarter.get('eps', 0.0),
                price_before=current_quarter.get('price_before', 0.0),
                price_after=current_quarter.get('price_after', 0.0)
            )
            current_company.add_earnings_report(report)
        except Exception as e:
            print(f"Error processing final quarter: {e}")
            
    return companies

def display_company_data(companies: Dict[str, Company]):
    """Display parsed company data for verification"""
    print("Parsed Company Data:")
    print("=" * 50)
    
    for ticker, company in companies.items():
        print(f"\n{company.name} ({ticker}) - {company.sector.value}")
        print(f"Number of earnings reports: {len(company.earnings_history)}")
        
        if company.earnings_history:
            latest = company.get_latest_metrics()
            print(f"Latest quarter: {company.earnings_history[-1].date}")
            print(f"Latest revenue: ${latest['revenue']:.2f}B")
            print(f"Latest revenue growth: {latest['revenue_growth']:.1f}%")
            print(f"Latest EPS: ${latest['eps']:.2f}")
            print(f"Latest stock reaction: {latest['price_change_pct']:.1f}%")
            
            print(f"\nHistorical Summary:")
            print(company.get_historical_summary())
        print("-" * 30)

def main():
    """Main function to parse and display earnings data"""
    print("Stock Agent Evaluation - Data Parser")
    print("=" * 40)
    
    # Load historical data
    companies = parse_earnings_data('earnings_data.txt')
    
    # Display parsed data
    display_company_data(companies)
    
    print(f"\nTotal companies loaded: {len(companies)}")
    print("\nData parsing complete. Use this data with LLM predictors.")

if __name__ == "__main__":
    main() 