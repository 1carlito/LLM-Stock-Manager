# OpenBB Sector Information Structure

## Overview

OpenBB returns sector information, but the **structure depends on the data provider** used. Most providers return a **two-level hierarchy**: **Sector** (main) and **Industry** (subsector).

---

## Current Implementation

### Standard Fields (Most Providers)

```python
overview = provider.get_company_overview("AAPL")

# Main Sector (broad classification)
sector = overview.get('Sector', '')  # e.g., "Technology"

# Industry/Subsector (more specific classification)
industry = overview.get('Industry', '')  # e.g., "Consumer Electronics"
```

**Structure:**
- **Sector** = Main/Broad sector classification
- **Industry** = More specific subsector/industry classification

### Example Values

```python
# Apple (AAPL)
{
    'Sector': 'Technology',
    'Industry': 'Consumer Electronics'
}

# JPMorgan (JPM)
{
    'Sector': 'Financial Services',
    'Industry': 'Banks - Diversified'
}

# Tesla (TSLA)
{
    'Sector': 'Consumer Cyclical',
    'Industry': 'Auto Manufacturers'
}
```

---

## Extended Fields (Provider-Dependent)

Some providers may return additional classification fields:

### GICS Classification (Global Industry Classification Standard)

```python
overview = provider.get_company_overview("AAPL")

# GICS fields (if available)
gics_sector = overview.get('GICS_Sector', '')        # e.g., "Information Technology"
gics_industry = overview.get('GICS_Industry', '')    # e.g., "Technology Hardware, Storage & Peripherals"
gics_sub_industry = overview.get('GICS_SubIndustry', '')  # e.g., "Technology Hardware, Storage & Peripherals"
```

**GICS Hierarchy:**
1. **Sector** (11 sectors)
2. **Industry Group** (24 groups)
3. **Industry** (69 industries)
4. **Sub-Industry** (158 sub-industries)

### ICB Classification (Industry Classification Benchmark)

```python
overview = provider.get_company_overview("AAPL")

# ICB fields (if available)
icb_sector = overview.get('ICB_Sector', '')        # e.g., "Technology"
icb_subsector = overview.get('ICB_Subsector', '')  # e.g., "Technology Hardware & Equipment"
```

**ICB Hierarchy:**
1. **Industry** (10 industries)
2. **Supersector** (19 supersectors)
3. **Sector** (41 sectors)
4. **Subsector** (114 subsectors)

---

## Provider-Specific Behavior

### Yahoo Finance (Default, Free)
- ✅ Returns: `Sector` and `Industry`
- ❌ Does NOT return: GICS or ICB fields
- **Structure**: 2-level (Sector → Industry)

### Alpha Vantage
- ✅ Returns: `Sector` and `Industry` (from company overview)
- ❌ Does NOT return: GICS or ICB fields
- **Structure**: 2-level (Sector → Industry)

### Polygon.io
- ✅ Returns: `Sector` and `Industry`
- ✅ May return: GICS fields (if available)
- **Structure**: 2-level or 3-level (depending on data)

### Intrinio
- ✅ Returns: `Sector` and `Industry`
- ✅ May return: GICS fields
- **Structure**: 2-level or 3-level (depending on data)

---

## Code Implementation

### Current Extraction

```python
# From openbb_provider.py
overview['Sector'] = row.get('sector', '')      # Main sector
overview['Industry'] = row.get('industry', '')  # Industry/Subsector

# Extended fields (if available)
overview['GICS_Sector'] = row.get('gics_sector', row.get('gicsSector', ''))
overview['GICS_Industry'] = row.get('gics_industry', row.get('gicsIndustry', ''))
overview['GICS_SubIndustry'] = row.get('gics_sub_industry', row.get('gicsSubIndustry', ''))
overview['ICB_Sector'] = row.get('icb_sector', row.get('icbSector', ''))
overview['ICB_Subsector'] = row.get('icb_subsector', row.get('icbSubsector', ''))
```

### Usage

```python
from aws.open_source.plugins.data_providers import OpenBBProvider

provider = OpenBBProvider()
overview = provider.get_company_overview("AAPL")

# Standard fields (always available)
main_sector = overview.get('Sector', '')      # "Technology"
subsector = overview.get('Industry', '')      # "Consumer Electronics"

# Extended fields (provider-dependent, may be empty)
gics_sector = overview.get('GICS_Sector', '')
gics_industry = overview.get('GICS_Industry', '')
gics_sub_industry = overview.get('GICS_SubIndustry', '')
icb_sector = overview.get('ICB_Sector', '')
icb_subsector = overview.get('ICB_Subsector', '')
```

---

## Answer to Your Question

**Q: Is it one sector or main sector and subsector?**

**A: It's a two-level structure:**
- **Main Sector** (`Sector` field) - Broad classification
- **Subsector/Industry** (`Industry` field) - More specific classification

**Example:**
- **Sector**: "Technology" (main)
- **Industry**: "Consumer Electronics" (subsector)

**Additional fields may be available** depending on the provider:
- GICS classification (4-level hierarchy)
- ICB classification (4-level hierarchy)

But the **standard fields** (`Sector` and `Industry`) are available from most providers and provide a **2-level hierarchy**.

---

## Recommendations

### For Reasoning Agent

Use the **2-level structure** (Sector + Industry) for most use cases:

```python
decision = reasoning_agent.make_decision(
    symbol="AAPL",
    company_data={
        'Sector': 'Technology',           # Main sector
        'Industry': 'Consumer Electronics'  # Subsector
    }
)
```

### For Portfolio Analysis

Group by **main sector** for diversification:

```python
# Group decisions by main sector
sector_groups = {}
for decision in decisions:
    sector = decision.get('sector', 'Unknown')
    if sector not in sector_groups:
        sector_groups[sector] = []
    sector_groups[sector].append(decision)
```

### For Detailed Analysis

Use **industry** (subsector) for more granular grouping:

```python
# Group by industry for detailed analysis
industry_groups = {}
for decision in decisions:
    industry = decision.get('industry', 'Unknown')
    if industry not in industry_groups:
        industry_groups[industry] = []
    industry_groups[industry].append(decision)
```

---

## Summary

✅ **Standard Structure**: 2-level (Sector → Industry)
- `Sector` = Main/Broad classification
- `Industry` = Subsector/Specific classification

✅ **Extended Fields**: May be available (GICS, ICB) depending on provider

✅ **Most Providers**: Return Sector + Industry (2-level hierarchy)

**Recommendation**: Use `Sector` (main) and `Industry` (subsector) for your Reasoning Agent integration.

