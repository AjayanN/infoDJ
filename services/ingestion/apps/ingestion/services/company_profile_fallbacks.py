"""Reviewed normalization fallbacks for profile facts disclosed in company filings.

These values fill only fields that the generic SEC parser could not normalize. They
are persisted against the latest extracted 10-K source and must be reviewed when
the company universe or annual filings change.
"""

PROFILE_FALLBACKS: dict[str, dict[str, list[str] | str]] = {
    "amazon": {"subsidiaries": ["Whole Foods Market", "Audible", "Twitch", "Zappos", "Zoox"]},
    "american-tower": {
        "subsidiaries": ["CoreSite"],
        "segments": ["U.S. and Canada", "Asia-Pacific", "Africa", "Europe", "Latin America", "Data Centers"],
        "revenue_sources": ["Property revenue", "Services revenue"],
        "competitors": ["Other independent tower operators", "Wireless carriers operating their own sites", "Alternative communications infrastructure providers"],
    },
    "apple": {"subsidiaries": ["Beats Electronics", "Shazam"]},
    "caterpillar": {
        "segments": ["Construction Industries", "Resource Industries", "Energy & Transportation", "Financial Products"],
        "customer_groups": ["Independent dealers", "Construction customers", "Mining customers", "Energy and transportation customers", "Government customers"],
        "revenue_sources": ["Machinery and engine sales", "Parts and service revenue", "Financing revenue"],
    },
    "exxonmobil": {
        "segments": ["Upstream", "Energy Products", "Chemical Products", "Specialty Products"],
        "customer_groups": ["Industrial customers", "Fuel and lubricant distributors", "Chemical manufacturers", "Wholesale and retail channels"],
        "revenue_sources": ["Crude oil and natural gas sales", "Fuel and lubricant sales", "Chemical product sales", "Specialty product sales"],
    },
    "ford-motor-company": {
        "business_model": "Ford designs, manufactures, markets and services vehicles while earning additional revenue from commercial services and vehicle financing.",
        "brands": ["Ford", "Lincoln"],
        "segments": ["Ford Blue", "Ford Model e", "Ford Pro", "Ford Credit"],
        "customer_groups": ["Retail vehicle buyers", "Commercial and fleet customers", "Dealers", "Vehicle financing customers"],
        "revenue_sources": ["Vehicle sales", "Parts and service revenue", "Commercial software and services", "Financing and leasing income"],
        "competitors": ["Global automotive manufacturers", "Electric vehicle manufacturers", "Commercial vehicle providers", "Vehicle finance providers"],
    },
    "freeport-mcmoran": {
        "brands": ["Freeport-McMoRan"],
        "products": ["Copper", "Gold", "Molybdenum"],
        "customer_groups": ["Copper smelters", "Refiners", "Industrial metals customers"],
        "revenue_sources": ["Copper sales", "Gold sales", "Molybdenum sales"],
        "competitors": ["Global copper producers", "Diversified mining companies"],
    },
    "general-electric": {
        "brands": ["GE Aerospace"],
        "customer_groups": ["Commercial airlines", "Aircraft lessors", "Aerospace manufacturers", "Government and defense customers"],
        "revenue_sources": ["Commercial engine sales", "Defense engine sales", "Services and spare parts revenue"],
    },
    "jpmorgan-chase": {
        "revenue_sources": ["Net interest income", "Investment banking fees", "Asset and wealth management fees", "Card income", "Markets and transaction fees"],
    },
    "microsoft": {
        "subsidiaries": ["LinkedIn", "GitHub", "Activision Blizzard", "Nuance Communications"],
        "brands": ["Microsoft", "Windows", "Azure", "Microsoft 365", "Xbox", "LinkedIn", "GitHub"],
        "segments": ["Productivity and Business Processes", "Intelligent Cloud", "More Personal Computing"],
        "products": ["Microsoft 365", "Azure", "Windows", "Dynamics 365", "Xbox", "LinkedIn", "GitHub", "Copilot"],
        "customer_groups": ["Consumers", "Small and medium businesses", "Large enterprises", "Public-sector organizations", "Developers and IT professionals"],
        "competitors": ["Cloud infrastructure providers", "Business software providers", "Operating-system and device companies", "Gaming platforms", "Artificial intelligence platforms"],
    },
    "newmont": {
        "subsidiaries": ["Newcrest Mining"],
        "brands": ["Newmont"],
        "customer_groups": ["Smelters", "Refiners", "Bullion banks", "Industrial metals customers"],
        "competitors": ["Global gold producers", "Diversified mining companies"],
    },
    "nextera-energy": {
        "brands": ["Florida Power & Light", "NextEra Energy Resources"],
        "segments": ["Florida Power & Light", "NextEra Energy Resources"],
        "products": ["Electricity", "Renewable generation", "Battery storage", "Natural gas infrastructure"],
        "competitors": ["Regulated electric utilities", "Independent power producers", "Renewable-energy developers"],
    },
    "pfizer": {
        "brands": ["Pfizer", "Comirnaty", "Paxlovid", "Prevnar", "Ibrance"],
        "segments": ["Biopharmaceutical products"],
        "customer_groups": ["Wholesalers", "Retail pharmacies", "Hospitals and clinics", "Governments and public-health agencies"],
        "revenue_sources": ["Biopharmaceutical product sales", "Alliance revenue", "Licensing and royalty revenue"],
        "competitors": ["Global pharmaceutical companies", "Biotechnology companies", "Generic and biosimilar manufacturers"],
    },
    "prologis": {
        "subsidiaries": ["Prologis operating partnerships"],
        "brands": ["Prologis"],
        "segments": ["Real Estate Operations", "Strategic Capital"],
        "customer_groups": ["Logistics operators", "Retailers", "Manufacturers", "E-commerce companies"],
        "revenue_sources": ["Rental income", "Strategic capital fees", "Development and disposition gains"],
        "leadership": ["Chief Executive Officer and executive leadership team disclosed in annual filings"],
        "competitors": ["Industrial real-estate investment trusts", "Private logistics-property owners", "Commercial property developers"],
    },
    "tesla": {
        "segments": ["Automotive", "Energy Generation and Storage"],
        "customer_groups": ["Retail vehicle buyers", "Commercial fleet customers", "Energy generation and storage customers", "Charging customers"],
    },
    "unitedhealth-group": {
        "subsidiaries": ["UnitedHealthcare", "Optum"],
        "brands": ["UnitedHealthcare", "Optum Health", "Optum Insight", "Optum Rx"],
        "segments": ["UnitedHealthcare", "Optum Health", "Optum Insight", "Optum Rx"],
        "customer_groups": ["Individuals and families", "Employers", "Government health programs", "Health care providers", "Life sciences companies"],
        "competitors": ["Health insurers", "Pharmacy benefit managers", "Health care service providers", "Health technology companies"],
    },
    "visa": {
        "brands": ["Visa", "Visa Direct", "Cybersource", "Verifi"],
        "segments": ["Payment Services"],
        "customer_groups": ["Financial institutions", "Merchants", "Fintech companies", "Governments", "Consumers and businesses"],
        "competitors": ["Global card networks", "Domestic payment networks", "Account-to-account payment systems", "Digital wallets and fintech platforms"],
    },
    "walmart": {
        "brands": ["Walmart", "Sam's Club", "Flipkart", "PhonePe"],
        "segments": ["Walmart U.S.", "Walmart International", "Sam's Club"],
        "customer_groups": ["Retail consumers", "Sam's Club members", "Marketplace sellers", "Advertising customers", "Business customers"],
    },
}
