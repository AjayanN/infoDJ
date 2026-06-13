"""Reviewed normalization fallbacks for profile facts disclosed in company filings.

These values replace fields whose generic SEC extraction is not sufficiently
reliable for publication. They are persisted against the latest extracted 10-K
source and must be reviewed when the company universe or annual filings change.
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
        "brands": ["Caterpillar", "Cat"],
        "segments": ["Construction Industries", "Resource Industries", "Energy & Transportation", "Financial Products"],
        "products": ["Construction equipment", "Mining equipment", "Diesel and natural gas engines", "Industrial gas turbines", "Locomotives", "Financial services"],
        "customer_groups": ["Independent dealers", "Construction customers", "Mining customers", "Energy and transportation customers", "Government customers"],
        "revenue_sources": ["Machinery and engine sales", "Parts and service revenue", "Financing revenue"],
        "competitors": ["Deere & Company", "Komatsu", "Hitachi Construction Machinery", "Liebherr", "Sandvik", "Volvo Construction Equipment"],
        "strategic_priorities": ["Expand services revenue", "Invest in autonomous and connected equipment", "Support energy-transition customers", "Improve operational efficiency"],
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


# Generic filing parsers are useful for discovery, but these three user-facing
# fields require reviewed terminology. Keeping the core set complete also stops
# filing headers, table labels, and isolated capitalized words from being
# published as a business model, brand, or product.
PROFILE_CORE_FALLBACKS: dict[str, dict[str, list[str] | str]] = {
    "amazon": {
        "business_model": "Amazon operates online and physical retail businesses, third-party seller services, subscription offerings, advertising, and cloud infrastructure services through AWS.",
        "brands": ["Amazon", "Amazon Web Services", "Prime", "Whole Foods Market", "Audible", "Twitch"],
        "products": ["Online retail", "Third-party seller services", "AWS cloud services", "Prime subscriptions", "Digital advertising", "Devices and digital content"],
    },
    "american-tower": {
        "business_model": "American Tower leases communications sites and related infrastructure to wireless carriers and other network operators, and also operates data-center facilities through CoreSite.",
        "brands": ["American Tower", "CoreSite"],
        "products": ["Tower and communications-site leasing", "Colocation and data-center services", "Site development services"],
    },
    "apple": {
        "business_model": "Apple designs and sells devices and related accessories while earning recurring revenue from digital content, cloud, payment, warranty, advertising, and other services tied to its installed device base.",
        "brands": ["Apple", "iPhone", "Mac", "iPad", "Apple Watch", "AirPods", "Apple TV", "Apple Music"],
        "products": ["iPhone", "Mac", "iPad", "Wearables and accessories", "Digital content and cloud services", "Payment and warranty services"],
    },
    "caterpillar": {
        "business_model": "Caterpillar sells construction and mining equipment, engines, turbines, locomotives, parts, and services through an independent dealer network, with additional revenue from equipment financing and leasing.",
        "brands": ["Caterpillar", "Cat"],
        "products": ["Construction equipment", "Mining equipment", "Diesel and natural gas engines", "Industrial gas turbines", "Locomotives", "Financial services"],
    },
    "disney": {
        "business_model": "Disney creates and distributes entertainment through television networks, streaming services, film and television studios, sports media, theme parks, resorts, consumer products, and licensing.",
        "brands": ["Disney", "ABC", "ESPN", "Pixar", "Marvel", "Lucasfilm", "National Geographic", "Disney+", "Hulu"],
        "products": ["Film and television content", "Linear television networks", "Streaming services", "Sports media", "Theme parks and resorts", "Consumer products and licensing"],
    },
    "exxonmobil": {
        "business_model": "ExxonMobil explores for and produces oil and natural gas, manufactures and sells fuels, lubricants, chemicals, and specialty products, and develops lower-emission and carbon-management businesses.",
        "brands": ["Exxon", "Mobil", "Esso", "ExxonMobil"],
        "products": ["Crude oil", "Natural gas", "Fuels", "Lubricants", "Chemical products", "Specialty products"],
    },
    "ford-motor-company": {
        "business_model": "Ford designs, manufactures, markets, and services vehicles while earning additional revenue from commercial software and services, parts, vehicle financing, and leasing.",
        "brands": ["Ford", "Lincoln"],
        "products": ["Passenger vehicles", "Trucks and vans", "Electric vehicles", "Parts and services", "Commercial software and services", "Vehicle financing and leasing"],
    },
    "freeport-mcmoran": {
        "business_model": "Freeport-McMoRan develops and operates large mining assets and earns revenue primarily from the production and sale of copper, gold, and molybdenum.",
        "brands": ["Freeport-McMoRan"],
        "products": ["Copper", "Gold", "Molybdenum"],
    },
    "general-electric": {
        "business_model": "GE Aerospace designs and manufactures commercial and defense aircraft engines and systems, with a large installed base that generates long-term services and spare-parts revenue.",
        "brands": ["GE Aerospace"],
        "products": ["Commercial aircraft engines", "Defense aircraft engines", "Integrated engine systems", "Maintenance and spare-parts services"],
    },
    "jpmorgan-chase": {
        "business_model": "JPMorgan Chase provides consumer and commercial banking, payments, investment banking, markets, securities services, and asset and wealth management, earning interest income and service fees.",
        "brands": ["JPMorgan Chase", "Chase", "J.P. Morgan"],
        "products": ["Consumer banking", "Commercial banking", "Credit cards and payments", "Investment banking and markets", "Asset management", "Wealth management"],
    },
    "microsoft": {
        "business_model": "Microsoft develops and licenses software, sells cloud infrastructure and business applications, operates professional and advertising platforms, and provides gaming content, consoles, and subscriptions.",
        "brands": ["Microsoft", "Windows", "Azure", "Microsoft 365", "Dynamics 365", "Xbox", "LinkedIn", "GitHub"],
        "products": ["Microsoft 365", "Azure", "Windows", "Dynamics 365", "LinkedIn", "GitHub", "Xbox products and services", "Copilot"],
    },
    "netflix": {
        "business_model": "Netflix distributes film, series, games, and live programming through paid streaming memberships, with plans funded by subscription fees and, for advertising-supported tiers, advertising revenue.",
        "brands": ["Netflix"],
        "products": ["Subscription video streaming", "Advertising-supported streaming", "Games", "Live programming"],
    },
    "newmont": {
        "business_model": "Newmont develops and operates mines and earns revenue primarily from the production and sale of gold, with additional copper, silver, lead, and zinc output.",
        "brands": ["Newmont"],
        "products": ["Gold", "Copper", "Silver", "Lead", "Zinc"],
    },
    "nextera-energy": {
        "business_model": "NextEra Energy combines a regulated electric utility serving Florida with a competitive energy business that develops and operates wind, solar, battery-storage, natural-gas, and transmission assets.",
        "brands": ["NextEra Energy", "Florida Power & Light", "NextEra Energy Resources"],
        "products": ["Regulated electricity", "Wind generation", "Solar generation", "Battery storage", "Natural-gas generation and infrastructure", "Transmission services"],
    },
    "pfizer": {
        "business_model": "Pfizer discovers, develops, manufactures, and commercializes biopharmaceutical medicines and vaccines, earning product sales plus alliance, licensing, and royalty revenue.",
        "brands": ["Pfizer", "Comirnaty", "Paxlovid", "Prevnar", "Ibrance"],
        "products": ["Vaccines", "Oncology medicines", "Internal medicine therapies", "Hospital medicines", "Rare-disease therapies"],
    },
    "prologis": {
        "business_model": "Prologis owns, develops, and leases logistics real estate and earns rental income, development gains, and fees from strategic-capital ventures managed with institutional partners.",
        "brands": ["Prologis"],
        "products": ["Logistics property leasing", "Property development", "Strategic capital management", "Customer energy and mobility services"],
    },
    "tesla": {
        "business_model": "Tesla designs, manufactures, sells, and services electric vehicles and energy-generation and storage systems, supported by charging, software, connectivity, insurance, and regulatory-credit revenue.",
        "brands": ["Tesla", "Model S", "Model 3", "Model X", "Model Y", "Cybertruck", "Powerwall", "Megapack"],
        "products": ["Electric vehicles", "Energy storage systems", "Solar energy systems", "Charging services", "Vehicle software and connectivity", "Insurance and after-sales services"],
    },
    "unitedhealth-group": {
        "business_model": "UnitedHealth Group combines health-benefit plans through UnitedHealthcare with care delivery, pharmacy services, data, technology, and advisory services through Optum.",
        "brands": ["UnitedHealthcare", "Optum Health", "Optum Insight", "Optum Rx"],
        "products": ["Health benefit plans", "Care delivery", "Pharmacy benefit services", "Health technology and analytics", "Advisory and payment services"],
    },
    "visa": {
        "business_model": "Visa operates a global payments network and earns service, data-processing, international-transaction, and value-added-service revenue from financial institutions, merchants, and other payment participants.",
        "brands": ["Visa", "Visa Direct", "Cybersource", "Verifi"],
        "products": ["Payment network processing", "Credit, debit, and prepaid credentials", "Cross-border payment services", "Visa Direct", "Fraud, risk, and acceptance services"],
    },
    "walmart": {
        "business_model": "Walmart sells merchandise and services through stores, clubs, and digital marketplaces, with additional revenue from memberships, advertising, marketplace services, and financial and fulfillment offerings.",
        "brands": ["Walmart", "Sam's Club", "Flipkart", "PhonePe"],
        "products": ["Retail merchandise", "Grocery", "E-commerce marketplace services", "Membership programs", "Advertising services", "Fulfillment and financial services"],
    },
}

for company_slug, core_values in PROFILE_CORE_FALLBACKS.items():
    PROFILE_FALLBACKS.setdefault(company_slug, {}).update(core_values)


BUSINESS_MODEL_FALLBACKS: dict[str, dict[str, list[str]]] = {
    "caterpillar": {
        "PAYER": ["Construction customers", "Mining customers", "Energy and transportation customers", "Government customers"],
        "USER": ["Equipment operators", "Fleet owners", "Independent dealers"],
        "OFFERING": ["Construction equipment", "Mining equipment", "Engines and turbines", "Locomotives", "Parts and services", "Equipment financing"],
        "REVENUE": ["Equipment sales", "Parts and service revenue", "Financing and leasing income"],
        "CHANNEL": ["Independent dealer network", "Direct enterprise relationships", "Digital fleet and service platforms"],
        "GEOGRAPHY": ["North America", "Latin America", "Europe, Africa and Middle East", "Asia-Pacific"],
        "PARTNER": ["Independent Cat dealers", "Suppliers", "Technology partners"],
        "COST": ["Manufacturing", "Materials and components", "Research and development", "Dealer and service support", "Financing costs"],
        "ASSET": ["Cat brand", "Independent dealer network", "Manufacturing footprint", "Installed equipment base", "Engineering and product technology"],
    },
}


SECTOR_BUSINESS_MODEL_FALLBACKS: dict[str, dict[str, list[str]]] = {
    "Information Technology": {
        "CHANNEL": ["Direct enterprise sales", "Digital distribution", "Channel partners"],
        "PARTNER": ["Developers", "Cloud and hardware partners", "Resellers"],
        "COST": ["Research and development", "Data centers and infrastructure", "Sales and marketing"],
        "ASSET": ["Software and intellectual property", "Installed customer base", "Technology infrastructure"],
    },
    "Financials": {
        "CHANNEL": ["Digital platforms", "Financial-institution relationships", "Direct sales"],
        "PARTNER": ["Financial institutions", "Merchants", "Technology providers"],
        "COST": ["Funding and credit costs", "Technology and operations", "Compliance and risk management"],
        "ASSET": ["Network and licenses", "Customer relationships", "Risk and transaction data"],
    },
    "Health Care": {
        "CHANNEL": ["Wholesalers and pharmacies", "Health-plan and provider relationships", "Direct institutional sales"],
        "PARTNER": ["Health care providers", "Distributors", "Research and technology partners"],
        "COST": ["Medical or product costs", "Research and development", "Sales, administration and compliance"],
        "ASSET": ["Clinical and health data", "Product portfolio", "Provider and distribution relationships"],
    },
    "Consumer Discretionary": {
        "CHANNEL": ["Direct sales", "Retail and dealer channels", "Digital commerce"],
        "PARTNER": ["Suppliers", "Distribution partners", "Technology and service partners"],
        "COST": ["Products and manufacturing", "Distribution and fulfillment", "Marketing and technology"],
        "ASSET": ["Brands", "Distribution network", "Customer base", "Operating technology"],
    },
    "Consumer Staples": {
        "CHANNEL": ["Stores and clubs", "Digital commerce", "Marketplace and delivery channels"],
        "PARTNER": ["Suppliers", "Marketplace sellers", "Logistics and delivery partners"],
        "COST": ["Merchandise", "Store and fulfillment operations", "Labor and logistics"],
        "ASSET": ["Store and fulfillment network", "Brands", "Membership and customer relationships"],
    },
    "Energy": {
        "CHANNEL": ["Wholesale commodity markets", "Branded and distributor channels", "Direct industrial sales"],
        "PARTNER": ["Resource and infrastructure partners", "Suppliers", "Distributors"],
        "COST": ["Exploration and production", "Refining and manufacturing", "Transportation and compliance"],
        "ASSET": ["Reserves and production assets", "Refineries and plants", "Distribution infrastructure"],
    },
    "Utilities": {
        "CHANNEL": ["Regulated utility service", "Wholesale power markets", "Long-term energy contracts"],
        "PARTNER": ["Grid operators", "Equipment suppliers", "Project and financing partners"],
        "COST": ["Generation and purchased power", "Grid infrastructure", "Operations and regulatory compliance"],
        "ASSET": ["Generation fleet", "Transmission and distribution network", "Development pipeline"],
    },
    "Industrials": {
        "CHANNEL": ["Dealer and distributor networks", "Direct enterprise sales", "Aftermarket service channels"],
        "PARTNER": ["Dealers and distributors", "Suppliers", "Technology partners"],
        "COST": ["Manufacturing", "Materials and components", "Research and development", "Service support"],
        "ASSET": ["Brands", "Manufacturing footprint", "Installed equipment base", "Engineering capabilities"],
    },
    "Communication Services": {
        "CHANNEL": ["Direct-to-consumer platforms", "Distribution partners", "Advertising sales channels"],
        "PARTNER": ["Content and production partners", "Distribution platforms", "Advertisers"],
        "COST": ["Content and production", "Technology and distribution", "Marketing and customer acquisition"],
        "ASSET": ["Brands and intellectual property", "Content library", "Audience and subscriber relationships", "Distribution platforms"],
    },
    "Real Estate": {
        "CHANNEL": ["Direct leasing", "Property-development relationships", "Strategic capital partnerships"],
        "PARTNER": ["Tenants", "Capital partners", "Developers and contractors"],
        "COST": ["Property operations", "Development and maintenance", "Interest and capital costs"],
        "ASSET": ["Property portfolio", "Land and development pipeline", "Tenant relationships"],
    },
    "Materials": {
        "CHANNEL": ["Long-term customer contracts", "Commodity markets", "Direct industrial sales"],
        "PARTNER": ["Smelters and refiners", "Equipment and logistics suppliers", "Host governments and communities"],
        "COST": ["Mining and processing", "Energy and materials", "Transportation and site development"],
        "ASSET": ["Mineral reserves", "Mines and processing facilities", "Operating permits and technical expertise"],
    },
}
