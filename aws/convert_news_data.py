#!/usr/bin/env python3
"""
Convert Manually Scraped News Data
=================================

Converts manually scraped news articles into the format expected by the SentimentAgent.
"""

import json
import os
from datetime import datetime
from typing import Dict, List, Any

def convert_news_to_sentiment_format(stock_symbol: str, news_articles: List[Dict], 
                                   output_dir: str = "news_data") -> Dict[str, Any]:
    """
    Convert manually scraped news articles to SentimentAgent format
    
    Args:
        stock_symbol: Stock symbol (e.g., 'PLTR')
        news_articles: List of news articles with 'date' and 'title' fields
        output_dir: Directory to save the converted data
        
    Returns:
        Dictionary in SentimentAgent format
    """
    # Create output directory
    os.makedirs(output_dir, exist_ok=True)
    
    # Convert articles to the expected format
    converted_news = []
    for article in news_articles:
        converted_article = {
            "title": article["title"],
            "date": article["date"],
            "source": "Manual Scrape",  # Default source
            "text": article.get("text", ""),  # Add if available
            "url": article.get("url", ""),  # Add if available
            "sentiment": "neutral"  # Default sentiment, will be analyzed by agent
        }
        converted_news.append(converted_article)
    
    # Create the full sentiment agent format
    sentiment_data = {
        "stock_symbol": stock_symbol,
        "search_date": datetime.now().isoformat(),
        "llm_model": "manual_scrape",
        "raw_response": f"Manually scraped news for {stock_symbol} from June-August 2025",
        "parsed_results": {
            stock_symbol: {
                "news": converted_news,
                "press_releases": [],  # Empty for now
                "analyst_actions": [],  # Empty for now
                "market_impact": f"Manual news analysis for {stock_symbol} covering {len(converted_news)} articles from June-August 2025"
            }
        }
    }
    
    # Save to file
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{stock_symbol}_manual_news_{timestamp}.json"
    filepath = os.path.join(output_dir, filename)
    
    with open(filepath, 'w') as f:
        json.dump(sentiment_data, f, indent=2)
    
    print(f"✅ Converted {len(converted_news)} articles for {stock_symbol}")
    print(f"📁 Saved to: {filepath}")
    
    return sentiment_data

def convert_all_news():
    """Convert news data for all stocks"""
    
    # PLTR news data
    pltr_news = [
        {
            "date": "10/06/2025",
            "title": "Fedrigoni and Palantir Partner to Accelerate Operational Transformation with AI"
        },
        {
            "date": "26/06/2025", 
            "title": "Palantir and The Nuclear Company Partner to Launch Platform to Rapidly Scale Nuclear Deployment"
        },
        {
            "date": "30/06/2025",
            "title": "Palantir and Accenture Federal Services Join Forces to Help Federal Government Agencies Reinvent Operations with AI"
        },
        {
            "date": "02/07/2025",
            "title": "BlueForge Alliance and Palantir Launch Warp Speed for Warships to Digitally Transform the U.S. Maritime Industrial Base"
        },
        {
            "date": "14/07/2025",
            "title": "Palantir Announces Date of Second Quarter 2025 Earnings Release and Webcast"
        },
        {
            "date": "21/07/2025",
            "title": "Newly Launched Deloitte and Palantir Strategic Alliance Delivering Tangible Outcomes, Accelerating Transformation for Clients' Modern Enterprise Functions"
        },
        {
            "date": "04/08/2025",
            "title": "Palantir Reports Q2 2025 U.S. Comm Revenue Growth of 93% Y/Y and Revenue Growth of 48% Y/Y; Guides Q3 Revenue to 50% Y/Y; Raises FY 2025 Revenue Guidance to 45% Y/Y and U.S. Comm Revenue Guidance to 85% Y/Y, Crushing Consensus Expectations"
        },
        {
            "date": "12/08/2025",
            "title": "Palantir and SOMPO Expand Partnership in Multi-Year Agreement"
        }
    ]
    
    # GOOGL (Alphabet) news data
    googl_news = [
        {
            "date": "09/07/2025",
            "title": "Alphabet Announces Date of Second Quarter 2025 Financial Results Conference Call"
        },
        {
            "date": "23/07/2025",
            "title": "Alphabet Announces Second Quarter 2025 Results"
        },
        {
            "date": "12/08/2025",
            "title": "Alphabet to Present at the Goldman Sachs 2025 Communacopia + Technology Conference"
        }
    ]
    
    # UNH (UnitedHealth Group) news data
    unh_news = [
        {
            "date": "04/06/2025",
            "title": "UNITEDHEALTH GROUP ANNOUNCES EARNINGS RELEASE DATE"
        },
        {
            "date": "04/06/2025",
            "title": "UnitedHealth Group Updates on Annual Shareholder Meeting, Board Actions"
        },
        {
            "date": "23/06/2025",
            "title": "UnitedHealth Group Recommends Shareholders Reject \"Mini-Tender\" Offer by Tutanota"
        },
        {
            "date": "25/07/2025",
            "title": "EARNINGS TELECONFERENCE MOVES TO EARLIER TIME ON JULY 29"
        },
        {
            "date": "29/07/2025",
            "title": "UnitedHealth Group Re-Establishes Full Year Outlook and Reports Second Quarter 2025 Results"
        },
        {
            "date": "31/07/2025",
            "title": "UnitedHealth Group Announces Changes to Leadership Team"
        },
        {
            "date": "13/08/2025",
            "title": "UnitedHealth Group Board Authorizes Payment of Quarterly Dividend"
        }
    ]
    
    # JPM (JPMorgan Chase) news data
    jpm_news = [
        {
            "date": "13/06/2025",
            "title": "JPMorganChase Declares Preferred Stock Dividends"
        },
        {
            "date": "16/06/2025",
            "title": "JPMorganChase to Host Second-Quarter 2025 Earnings Call"
        },
        {
            "date": "01/07/2025",
            "title": "JPMorganChase Plans Dividend Increase and Has Authorized a New Common Share Repurchase Program"
        },
        {
            "date": "01/07/2025",
            "title": "JPMorganChase Announces 2025 Dodd-Frank Act Stress Test Results"
        },
        {
            "date": "15/07/2025",
            "title": "JPMorganChase Declares Preferred Stock Dividends"
        },
        {
            "date": "12/08/2025",
            "title": "JPMorganChase to Present at the Barclays Global Financial Services Conference"
        },
        {
            "date": "15/08/2025",
            "title": "JPMorganChase Declares Preferred Stock Dividends"
        }
    ]
    
    # NVDA (NVIDIA) news data
    nvda_news = [
        {
            "date": "10/06/2025",
            "title": "NVIDIA Powers Europe's Fastest Supercomputer"
        },
        {
            "date": "11/06/2025",
            "title": "NVIDIA Stockholder Meeting Set for June 25; Individuals Can Participate Online"
        },
        {
            "date": "11/06/2025",
            "title": "NVIDIA Partners With Novo Nordisk and DCAI to Advance Drug Discovery"
        },
        {
            "date": "11/06/2025",
            "title": "NVIDIA Builds World's First Industrial AI Cloud to Advance European Manufacturing"
        },
        {
            "date": "11/06/2025",
            "title": "Siemens and NVIDIA Expand Partnership to Accelerate AI Capabilities in Manufacturing"
        },
        {
            "date": "11/06/2025",
            "title": "NVIDIA DGX Cloud Lepton Connects Europe's Developers to Global NVIDIA Compute Ecosystem"
        },
        {
            "date": "11/06/2025",
            "title": "NVIDIA Partners With Europe Model Builders and Cloud Providers to Accelerate Region's Leap Into AI"
        },
        {
            "date": "11/06/2025",
            "title": "Europe Builds AI Infrastructure With NVIDIA to Fuel Region's Next Industrial Transformation"
        },
        {
            "date": "30/07/2025",
            "title": "NVIDIA Sets Conference Call for Second-Quarter Financial Results"
        },
        {
            "date": "11/08/2025",
            "title": "NVIDIA Opens Portals to World of Robotics With New Omniverse Libraries, Cosmos Physical AI Models and AI Computing Infrastructure"
        },
        {
            "date": "11/08/2025",
            "title": "NVIDIA RTX PRO Servers With Blackwell Coming to World's Most Popular Enterprise Systems"
        },
        {
            "date": "18/08/2025",
            "title": "NVIDIA Blackwell Architecture Comes to GeForce NOW"
        },
        {
            "date": "22/08/2025",
            "title": "NVIDIA Introduces Spectrum-XGS Ethernet to Connect Distributed Data Centers Into Giga-Scale AI Super-Factories"
        },
        {
            "date": "25/08/2025",
            "title": "NVIDIA Blackwell-Powered Jetson Thor Now Available, Accelerating the Age of General Robotics"
        },
        {
            "date": "26/08/2025",
            "title": "Industry Leaders Transform Enterprise Data Centers for the AI Era With NVIDIA RTX PRO Servers"
        },
        {
            "date": "27/08/2025",
            "title": "NVIDIA Announces Financial Results for Second Quarter Fiscal 2026"
        },
        {
            "date": "28/08/2025",
            "title": "NVIDIA Announces Upcoming Event for Financial Community"
        }
    ]
    
    # ABBV (AbbVie) news data
    abbv_news = [
        {
            "date": "03/06/2025",
            "title": "AbbVie to Present at the Goldman Sachs 46th Annual Global Healthcare Conference"
        },
        {
            "date": "03/06/2025",
            "title": "AbbVie Invites People Living with Migraine to Enter the Second Annual AbbVie Migraine Career Catalyst Award™ Contest to Support Their Professional Goals"
        },
        {
            "date": "11/06/2025",
            "title": "U.S. FDA Approves Expanded Indication for AbbVie's MAVYRET® (Glecaprevir/Pibrentasvir) as First and Only Treatment for People with Acute Hepatitis C Virus"
        },
        {
            "date": "16/06/2025",
            "title": "AbbVie Provides Update on VERONA Trial for Newly Diagnosed Higher-Risk Myelodysplastic Syndromes"
        },
        {
            "date": "18/06/2025",
            "title": "AbbVie Announces New Data Demonstrating Atogepant (QULIPTA® / AQUIPTA®) Achieves Superiority Across All Endpoints in Phase 3 Head-to-Head Study Compared to Topiramate for Migraine Prevention"
        },
        {
            "date": "20/06/2025",
            "title": "AbbVie Declares Quarterly Dividend"
        },
        {
            "date": "30/06/2025",
            "title": "AbbVie to Host Second-Quarter 2025 Earnings Conference Call"
        },
        {
            "date": "30/06/2025",
            "title": "U.S. Food and Drug Administration Accepts for Review Allergan Aesthetics Premarket Approval Application for SKINVIVE by JUVÉDERM® for the Improvement of Neck Appearance"
        },
        {
            "date": "30/06/2025",
            "title": "AbbVie to Acquire Capstan Therapeutics, Further Strengthening Commitment to Transforming Patient Care in Immunology"
        },
        {
            "date": "10/07/2025",
            "title": "AbbVie and Ichnos Glenmark Innovation (IGI) Announce Exclusive Global Licensing Agreement for ISB 2001, a First-in-Class CD38×BCMA×CD3 Trispecific Antibody"
        },
        {
            "date": "22/07/2025",
            "title": "BOTOX® Cosmetic (onabotulinumtoxinA) Selects This Year's Entrepreneurs for The Confidence Project"
        },
        {
            "date": "29/07/2025",
            "title": "AbbVie Submits for U.S. FDA Approval of Combination Treatment of VENCLEXTA® (venetoclax) and Acalabrutinib for Previously Untreated Patients with Chronic Lymphocytic Leukemia (CLL)"
        },
        {
            "date": "30/07/2025",
            "title": "AbbVie Announces Positive Topline Results from Phase 3 UP-AA Trial Evaluating Upadacitinib (RINVOQ®) for Alopecia Areata"
        },
        {
            "date": "31/07/2025",
            "title": "AbbVie Reports Second-Quarter 2025 Financial Results"
        },
        {
            "date": "05/08/2025",
            "title": "Allergan Aesthetics Unveils the New Faces of Natrelle® and Real Stories of Empowerment and Transparency"
        },
        {
            "date": "06/08/2025",
            "title": "Get Ready, JUVÉDERM® Day is Calling!"
        },
        {
            "date": "12/08/2025",
            "title": "AbbVie Announces $195 Million Investment to Expand Active Pharmaceutical Ingredient Manufacturing in the U.S."
        },
        {
            "date": "19/08/2025",
            "title": "SkinMedica® Unveils Its Newest Hydration Hero"
        },
        {
            "date": "19/08/2025",
            "title": "AbbVie Completes Acquisition of Capstan Therapeutics"
        },
        {
            "date": "21/08/2025",
            "title": "AbbVie Announces Positive Topline Results from Second Phase 3 UP-AA Trial Evaluating Upadacitinib (RINVOQ®) for Alopecia Areata"
        },
        {
            "date": "25/08/2025",
            "title": "AbbVie to Acquire Gilgamesh Pharmaceuticals' Bretisilocin, a Novel, Investigational Therapy for Major Depressive Disorder, Expanding Psychiatry Pipeline"
        }
    ]
    
    # TMO (Thermo Fisher Scientific) news data
    tmo_news = [
        {
            "date": "02/06/2025",
            "title": "Thermo Fisher Scientific Unveils Next-generation Mass Spectrometers at ASMS 2025 to Revolutionize Biopharma Applications and Omics Research"
        },
        {
            "date": "02/06/2025",
            "title": "Thermo Fisher Scientific Launches Cutting-edge Solutions for Omics, Biopharma and Environmental Workflows at ASMS 2025"
        },
        {
            "date": "10/06/2025",
            "title": "Thermo Fisher Scientific Showcases Flexible Solutions Built for Innovation, Speed and Scale at the 2025 BIO International Convention"
        },
        {
            "date": "12/06/2025",
            "title": "Regeneron Genetics Center Selects Olink® Explore HT for Landmark Proteomics Study of 200,000 Patient Samples"
        },
        {
            "date": "16/06/2025",
            "title": "Tufts Center Study Shows Significant Time Savings in Delivering Therapies to Patients with Thermo Fisher Scientific's Accelerator™ Drug Development 360° CDMO and CRO Solutions"
        },
        {
            "date": "23/06/2025",
            "title": "Thermo Fisher Scientific Awarded $94.5 Million U.S. Government Contract to Supply the Navy with Advanced Radiation Detection Systems"
        },
        {
            "date": "01/07/2025",
            "title": "Thermo Fisher Scientific to Hold Earnings Conference Call on Wednesday, July 23, 2025"
        },
        {
            "date": "03/07/2025",
            "title": "Thermo Fisher's NGS Assay Receives FDA Approval as a Companion Diagnostic for ZEGFROVY and for Tumor Profiling"
        },
        {
            "date": "10/07/2025",
            "title": "Thermo Fisher Scientific Declares Quarterly Dividend"
        },
        {
            "date": "14/07/2025",
            "title": "Thermo Fisher Scientific Introduces the Oncomine Comprehensive Assay Plus on the Ion Torrent Genexus System to Help Advance the Future of Precision Medicine"
        },
        {
            "date": "16/07/2025",
            "title": "Thermo Fisher Scientific and Sanofi Expand Strategic Partnership to Enable Additional U.S. Drug Product Manufacturing"
        },
        {
            "date": "16/07/2025",
            "title": "Thermo Fisher Scientific, South African Medical Research Council and Department of Science Innovation and Technology Announce New Training Facility to Develop Next Generation of South African Scientists"
        },
        {
            "date": "23/07/2025",
            "title": "Thermo Fisher Scientific Reports Second Quarter 2025 Results"
        },
        {
            "date": "23/07/2025",
            "title": "Thermo Fisher Scientific's Chief Financial Officer, Stephen Williamson, to Retire in Early 2026"
        },
        {
            "date": "24/07/2025",
            "title": "Thermo Fisher Scientific Increases Accessibility to Research With the Launches of Scios 3 and Talos 12 Electron Microscopes at M&M 2025 Conference"
        },
        {
            "date": "28/07/2025",
            "title": "Thermo Fisher Scientific Showcases Diagnostics Solutions Designed to Meet Evolving Global Healthcare Demands at ADLM 2025"
        },
        {
            "date": "11/08/2025",
            "title": "Thermo Fisher Receives FDA Approval for NGS-Based Companion Diagnostic for New Non-Small Cell Lung Cancer Treatment"
        },
        {
            "date": "21/08/2025",
            "title": "Thermo Fisher Scientific Opens Manufacturing Center of Excellence Site in North Carolina"
        },
        {
            "date": "28/08/2025",
            "title": "Thermo Fisher Scientific Secures R&D 100 Awards for Innovations Accelerating the Discovery and Development of Therapies"
        },
        {
            "date": "28/08/2025",
            "title": "Thermo Fisher Scientific to Participate in J.P. Morgan CEO Call Series on September 5, 2025"
        }
    ]
    
    # BAC (Bank of America) news data
    bac_news = [
        {
            "date": "11/06/2025",
            "title": "Bank of America Announces Redemption of $3,000,000,000 1.319% Fixed/Floating Rate Senior Notes, Due June 2026"
        },
        {
            "date": "11/06/2025",
            "title": "BofA Clients Embrace New $10 Million Limit in U.S. Real-Time Payments"
        },
        {
            "date": "11/06/2025",
            "title": "Bank of America Declares Preferred Stock Dividends Payable in July and August 2025"
        },
        {
            "date": "01/07/2025",
            "title": "Bank of America Comments on Stress Test Results; Plans to Increase Quarterly Dividend 8% to $0.28 Per Share"
        },
        {
            "date": "07/07/2025",
            "title": "BofA Directs Additional $1 Million to Los Angeles Nonprofits for Evolving Fire Recovery Needs"
        },
        {
            "date": "08/07/2025",
            "title": "BofA Names Julie Schmelzle President of Southwest Florida"
        },
        {
            "date": "09/07/2025",
            "title": "Bank of America to Report Second Quarter 2025 Financial Results and Host Investor Conference Call on July 16"
        },
        {
            "date": "10/07/2025",
            "title": "Bank of America, N.A. Announces Redemptions of $2,000,000,000 5.650% Senior Bank Notes and $400,000,000 Floating Rate Senior Bank Notes, Due August 2025"
        },
        {
            "date": "11/07/2025",
            "title": "BofA Recognized by Celent for Delivering Innovative Digital Experiences for Clients"
        },
        {
            "date": "14/07/2025",
            "title": "Bank of America Announces Redemption of $2,000,000,000 4.827% Fixed/Floating Rate Senior Notes, Due July 2026"
        },
        {
            "date": "16/07/2025",
            "title": "Bank of America Reports Second Quarter 2025 Financial Results"
        },
        {
            "date": "18/07/2025",
            "title": "Bank of America Declares Preferred Stock Dividends Payable in August and September 2025"
        },
        {
            "date": "23/07/2025",
            "title": "Bank of America Increases Common Stock Dividend 8% to $0.28 Per Share, Authorizes $40 Billion Stock Repurchase Program"
        },
        {
            "date": "30/07/2025",
            "title": "Confronted With Higher Living Costs, 72% of Young Adults Take Action to Improve Their Financial Health, Finds BofA Better Money Habits Study"
        },
        {
            "date": "30/07/2025",
            "title": "Ante el aumento del costo de la vida, el 72% de los adultos jóvenes toma medidas para mejorar su salud financiera, según un estudio de Mejores Hábitos Financieros de BofA"
        },
        {
            "date": "06/08/2025",
            "title": "BofA Names Christine Williams President of Myrtle Beach"
        },
        {
            "date": "20/08/2025",
            "title": "A Decade of AI Innovation: BofA's Virtual Assistant Erica Surpasses 3 Billion Client Interactions"
        },
        {
            "date": "20/08/2025",
            "title": "Alaska Airlines and Bank of America Present a New Premium Credit Card Designed for Global Travelers, the Atmos™ Rewards Summit Visa Infinite® Card"
        },
        {
            "date": "29/08/2025",
            "title": "Bank of America Chief Financial Officer to Participate in the Barclays Global Financial Services Conference on September 8"
        }
    ]
    
    # WFC (Wells Fargo) news data
    wfc_news = [
        {
            "date": "03/06/2025",
            "title": "Wells Fargo to Present at the Morgan Stanley U.S. Financials Conference"
        },
        {
            "date": "03/06/2025",
            "title": "Wells Fargo Confirms that the Federal Reserve Has Removed the Limits on Growth in Total Assets Imposed"
        },
        {
            "date": "01/07/2025",
            "title": "Wells Fargo Expects SCB to Decrease to 2.5% from 3.8% and Intends to Raise Dividend by 12.5% to $0.4"
        },
        {
            "date": "08/07/2025",
            "title": "Wells Fargo to Announce Second Quarter 2025 Earnings on July 15, 2025"
        },
        {
            "date": "09/07/2025",
            "title": "Wells Fargo Donates $1 Million Toward Flood Relief Efforts in Texas"
        },
        {
            "date": "10/07/2025",
            "title": "Wells Fargo Names Tim Ruby to Lead Healthcare, Higher Education and Not-for-Profit Banking Nationwide"
        },
        {
            "date": "15/07/2025",
            "title": "Wells Fargo Reports Second Quarter 2025 Financial Results"
        },
        {
            "date": "16/07/2025",
            "title": "Wells Fargo Expands Commercial Banking Healthcare Team by More Than 30%, Increasing Specialized Coverage"
        },
        {
            "date": "29/07/2025",
            "title": "Wells Fargo & Company Increases Common Stock Dividend"
        },
        {
            "date": "31/07/2025",
            "title": "Wells Fargo Board of Directors Announces Intention to Name CEO, Charlie Scharf, Chairman"
        },
        {
            "date": "04/08/2025",
            "title": "Wells Fargo Commercial Banking Announces Collaboration with the National Center for the Middle Market"
        },
        {
            "date": "05/08/2025",
            "title": "Wells Fargo announces expansion of strategic relationship with Google Cloud"
        },
        {
            "date": "14/08/2025",
            "title": "How independent financial advisors can drive smart, sustainable growth"
        },
        {
            "date": "15/08/2025",
            "title": "Wells Fargo & Company Declares Cash Dividends on Preferred Stock"
        },
        {
            "date": "15/08/2025",
            "title": "Alternative investments now available in unified managed accounts at Wells Fargo"
        }
    ]
    
    # XOM (ExxonMobil) news data
    xom_news = [
        {
            "date": "01/08/2025",
            "title": "ExxonMobil announces second-quarter 2025 results"
        },
        {
            "date": "08/08/2025",
            "title": "ExxonMobil Guyana begins production at fourth offshore Guyana project"
        }
    ]
    
    # CVX (Chevron) news data
    cvx_news = [
        {
            "date": "17/06/2025",
            "title": "Chevron enters domestic lithium sector to support U.S. energy security"
        },
        {
            "date": "17/06/2025",
            "title": "Chevron and Halliburton enable intelligent hydraulic fracturing"
        },
        {
            "date": "29/07/2025",
            "title": "John B. Hess joins Chevron's board of directors"
        },
        {
            "date": "01/08/2025",
            "title": "Chevron reports second quarter 2025 results"
        },
        {
            "date": "06/08/2025",
            "title": "Explainer: what is the permian basin?"
        },
        {
            "date": "14/08/2025",
            "title": "Built on legacy, driven by discipline: Chevron's permian advantage explained"
        },
        {
            "date": "18/08/2025",
            "title": "Greeley stampede is riding high, with Chevron's support"
        },
        {
            "date": "19/08/2025",
            "title": "Leaning into Argentina's shale growth opportunities"
        }
    ]
    
    # COP (ConocoPhillips) news data
    cop_news = [
        {
            "date": "26/06/2025",
            "title": "ConocoPhillips to Hold Second-Quarter Earnings Conference Call on Thursday, Aug. 7"
        },
        {
            "date": "01/07/2025",
            "title": "ConocoPhillips appoints Kathleen McGinty to its board of directors"
        },
        {
            "date": "18/07/2025",
            "title": "ConocoPhillips Makes Application to Cease to Be a Reporting Issuer in Canada"
        },
        {
            "date": "04/08/2025",
            "title": "Coastal Bend LNG selects ConocoPhillips' Optimized Cascade® Process technology"
        },
        {
            "date": "07/08/2025",
            "title": "ConocoPhillips announces second-quarter 2025 results and quarterly dividend"
        },
        {
            "date": "21/08/2025",
            "title": "ConocoPhillips further expands LNG business with additional Gulf Coast offtake agreement"
        }
    ]
    
    print("🔄 Converting all news data...")
    print("=" * 50)
    
    # Convert PLTR news
    print("\n📈 Converting PLTR news...")
    pltr_data = convert_news_to_sentiment_format("PLTR", pltr_news)
    
    # Convert GOOGL news
    print("\n📈 Converting GOOGL news...")
    googl_data = convert_news_to_sentiment_format("GOOGL", googl_news)
    
    # Convert UNH news
    print("\n📈 Converting UNH news...")
    unh_data = convert_news_to_sentiment_format("UNH", unh_news)
    
    # Convert JPM news
    print("\n📈 Converting JPM news...")
    jpm_data = convert_news_to_sentiment_format("JPM", jpm_news)
    
    # Convert NVDA news
    print("\n📈 Converting NVDA news...")
    nvda_data = convert_news_to_sentiment_format("NVDA", nvda_news)
    
    # Convert ABBV news
    print("\n📈 Converting ABBV news...")
    abbv_data = convert_news_to_sentiment_format("ABBV", abbv_news)
    
    # Convert TMO news
    print("\n�� Converting TMO news...")
    tmo_data = convert_news_to_sentiment_format("TMO", tmo_news)
    
    # Convert BAC news
    print("\n📈 Converting BAC news...")
    bac_data = convert_news_to_sentiment_format("BAC", bac_news)
    
    # Convert WFC news
    print("\n📈 Converting WFC news...")
    wfc_data = convert_news_to_sentiment_format("WFC", wfc_news)
    
    # Convert XOM news
    print("\n📈 Converting XOM news...")
    xom_data = convert_news_to_sentiment_format("XOM", xom_news)
    
    # Convert CVX news
    print("\n📈 Converting CVX news...")
    cvx_data = convert_news_to_sentiment_format("CVX", cvx_news)
    
    # Convert COP news
    print("\n📈 Converting COP news...")
    cop_data = convert_news_to_sentiment_format("COP", cop_news)
    
    print(f"\n📊 Total Conversion Summary:")
    print(f"   PLTR: {len(pltr_data['parsed_results']['PLTR']['news'])} articles")
    print(f"   GOOGL: {len(googl_data['parsed_results']['GOOGL']['news'])} articles")
    print(f"   UNH: {len(unh_data['parsed_results']['UNH']['news'])} articles")
    print(f"   JPM: {len(jpm_data['parsed_results']['JPM']['news'])} articles")
    print(f"   NVDA: {len(nvda_data['parsed_results']['NVDA']['news'])} articles")
    print(f"   ABBV: {len(abbv_data['parsed_results']['ABBV']['news'])} articles")
    print(f"   TMO: {len(tmo_data['parsed_results']['TMO']['news'])} articles")
    print(f"   BAC: {len(bac_data['parsed_results']['BAC']['news'])} articles")
    print(f"   WFC: {len(wfc_data['parsed_results']['WFC']['news'])} articles")
    print(f"   XOM: {len(xom_data['parsed_results']['XOM']['news'])} articles")
    print(f"   CVX: {len(cvx_data['parsed_results']['CVX']['news'])} articles")
    print(f"   COP: {len(cop_data['parsed_results']['COP']['news'])} articles")
    total_articles = (len(pltr_data['parsed_results']['PLTR']['news']) + 
                     len(googl_data['parsed_results']['GOOGL']['news']) + 
                     len(unh_data['parsed_results']['UNH']['news']) +
                     len(jpm_data['parsed_results']['JPM']['news']) +
                     len(nvda_data['parsed_results']['NVDA']['news']) +
                     len(abbv_data['parsed_results']['ABBV']['news']) +
                     len(tmo_data['parsed_results']['TMO']['news']) +
                     len(bac_data['parsed_results']['BAC']['news']) +
                     len(wfc_data['parsed_results']['WFC']['news']) +
                     len(xom_data['parsed_results']['XOM']['news']) +
                     len(cvx_data['parsed_results']['CVX']['news']) +
                     len(cop_data['parsed_results']['COP']['news']))
    print(f"   Total: {total_articles} articles")
    
    return pltr_data, googl_data, unh_data, jpm_data, nvda_data, abbv_data, tmo_data, bac_data, wfc_data, xom_data, cvx_data, cop_data

if __name__ == "__main__":
    # Convert all news
    convert_all_news()
    
    print("\n🎉 Conversion complete!")
    print("📝 Next steps:")
    print("   1. Add more stock news data using the same format")
    print("   2. Run batch_stock_scrape_backtest.py")
    print("   3. Run process_all_stocks.py")
