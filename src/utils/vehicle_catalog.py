from datetime import datetime


VEHICLE_BRAND_MODELS = {
    "Alfa Romeo": ["159", "Brera", "Giulia", "Giulietta", "Mito", "Stelvio", "Tonale"],
    "Audi": ["A3", "A4", "A5", "A6", "A7", "A8", "Q2", "Q3", "Q5", "Q7", "Q8", "TT"],
    "BMW": ["1 Serisi", "2 Serisi", "3 Serisi", "4 Serisi", "5 Serisi", "7 Serisi", "X1", "X3", "X5", "i3", "iX1"],
    "Chevrolet": ["Aveo", "Captiva", "Cruze", "Kalos", "Lacetti", "Spark"],
    "Citroen": ["Berlingo", "C-Elysee", "C3", "C4", "C4 X", "C5 Aircross", "Jumpy"],
    "Cupra": ["Ateca", "Born", "Formentor", "Leon"],
    "Dacia": ["Duster", "Jogger", "Lodgy", "Logan", "Sandero", "Spring"],
    "Fiat": ["500", "500L", "Albea", "Doblo", "Egea", "Fiorino", "Linea", "Panda", "Punto", "Scudo"],
    "Ford": ["B-Max", "C-Max", "Connect", "Courier", "EcoSport", "Fiesta", "Focus", "Fusion", "Kuga", "Mondeo", "Puma", "Ranger", "Tourneo Courier", "Tourneo Custom"],
    "Honda": ["Accord", "Civic", "CR-V", "City", "HR-V", "Jazz"],
    "Hyundai": ["Accent", "Bayon", "Elantra", "Getz", "i10", "i20", "i30", "Kona", "Santa Fe", "Tucson"],
    "Isuzu": ["D-Max"],
    "Jaguar": ["E-Pace", "F-Pace", "XE", "XF"],
    "Jeep": ["Compass", "Renegade", "Wrangler"],
    "Kia": ["Bongo", "Carens", "Ceed", "Cerato", "Niro", "Picanto", "Rio", "Sorento", "Sportage", "Stonic"],
    "Land Rover": ["Defender", "Discovery", "Discovery Sport", "Range Rover Evoque", "Range Rover Sport", "Velar"],
    "Lexus": ["CT", "ES", "IS", "NX", "RX", "UX"],
    "Mazda": ["2", "3", "6", "CX-3", "CX-5", "MX-5"],
    "Mercedes-Benz": ["A Serisi", "B Serisi", "C Serisi", "CLA", "CLS", "E Serisi", "GLA", "GLB", "GLC", "GLE", "Sprinter", "Vito"],
    "Mini": ["Clubman", "Cooper", "Countryman"],
    "Mitsubishi": ["ASX", "Colt", "L200", "Lancer", "Outlander", "Space Star"],
    "Nissan": ["Juke", "Micra", "Navara", "Note", "Qashqai", "X-Trail"],
    "Opel": ["Astra", "Combo", "Corsa", "Crossland", "Grandland", "Insignia", "Mokka", "Vivaro", "Zafira"],
    "Peugeot": ["2008", "208", "3008", "301", "308", "408", "5008", "Bipper", "Boxer", "Partner", "Rifter"],
    "Porsche": ["911", "Cayenne", "Macan", "Panamera", "Taycan"],
    "Renault": ["Captur", "Clio", "Express", "Fluence", "Kadjar", "Kangoo", "Latitude", "Laguna", "Megane", "Scenic", "Symbol", "Taliant", "Trafic"],
    "Seat": ["Arona", "Ateca", "Ibiza", "Leon", "Toledo"],
    "Skoda": ["Fabia", "Kamiq", "Karoq", "Kodiaq", "Octavia", "Rapid", "Scala", "Superb"],
    "Suzuki": ["Baleno", "Jimny", "S-Cross", "Swift", "Vitara"],
    "Tesla": ["Model 3", "Model S", "Model X", "Model Y"],
    "Toyota": ["Auris", "Avensis", "C-HR", "Corolla", "Corolla Cross", "Hilux", "Land Cruiser", "RAV4", "Yaris", "Yaris Cross"],
    "Volkswagen": ["Amarok", "Arteon", "Caddy", "Caravelle", "Golf", "Jetta", "Passat", "Polo", "T-Cross", "T-Roc", "Tiguan", "Touareg", "Transporter"],
    "Volvo": ["S60", "S90", "V40", "V60", "XC40", "XC60", "XC90"],
}


def get_vehicle_brands():
    return sorted(VEHICLE_BRAND_MODELS.keys())


def get_models_for_brand(brand):
    normalized = (brand or "").strip().lower()
    for key, models in VEHICLE_BRAND_MODELS.items():
        if key.lower() == normalized:
            return models
    return []


def get_vehicle_years(start_year=1980):
    current_year = datetime.now().year + 1
    return [str(year) for year in range(current_year, start_year - 1, -1)]
