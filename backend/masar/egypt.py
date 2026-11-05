"""Egyptian reference data + identity helpers (national ID, IBAN, phone)."""
from __future__ import annotations

import re
from datetime import date

# code, name_en, name_ar, weight (population x urban-banking skew), region, cities
GOVERNORATES = [
    ("01", "Cairo", "القاهرة", 14.0, "Greater Cairo", ["Nasr City", "Heliopolis", "Maadi", "New Cairo", "Shubra", "Mokattam", "Zamalek"]),
    ("21", "Giza", "الجيزة", 11.0, "Greater Cairo", ["Dokki", "Mohandessin", "6th of October", "Sheikh Zayed", "Haram", "Faisal"]),
    ("14", "Qalyubia", "القليوبية", 5.0, "Greater Cairo", ["Banha", "Shubra El Kheima", "Qalyub", "Obour"]),
    ("02", "Alexandria", "الإسكندرية", 8.0, "Alexandria & Matrouh", ["Smouha", "Sidi Gaber", "Miami", "Agami", "Montaza"]),
    ("13", "Sharqia", "الشرقية", 6.0, "Delta", ["Zagazig", "10th of Ramadan", "Belbeis", "Abu Hammad"]),
    ("12", "Dakahlia", "الدقهلية", 6.0, "Delta", ["Mansoura", "Mit Ghamr", "Talkha", "Dekernes"]),
    ("16", "Gharbia", "الغربية", 4.5, "Delta", ["Tanta", "El Mahalla El Kubra", "Kafr El Zayat", "Zefta"]),
    ("17", "Monufia", "المنوفية", 3.5, "Delta", ["Shebin El Kom", "Sadat City", "Menouf", "Ashmoun"]),
    ("18", "Beheira", "البحيرة", 4.5, "Delta", ["Damanhour", "Kafr El Dawar", "Rashid", "Edku"]),
    ("15", "Kafr El Sheikh", "كفر الشيخ", 2.5, "Delta", ["Kafr El Sheikh", "Desouk", "Baltim"]),
    ("11", "Damietta", "دمياط", 1.5, "Delta", ["Damietta", "New Damietta", "Ras El Bar"]),
    ("19", "Ismailia", "الإسماعيلية", 1.5, "Canal", ["Ismailia", "Fayed", "El Qantara"]),
    ("03", "Port Said", "بورسعيد", 1.2, "Canal", ["Port Said", "Port Fouad"]),
    ("04", "Suez", "السويس", 1.0, "Canal", ["Suez", "Ain Sokhna"]),
    ("22", "Beni Suef", "بني سويف", 2.5, "Upper Egypt", ["Beni Suef", "El Wasta", "Nasser"]),
    ("23", "Fayoum", "الفيوم", 2.5, "Upper Egypt", ["Fayoum", "Ibsheway", "Tamiya"]),
    ("24", "Minya", "المنيا", 4.0, "Upper Egypt", ["Minya", "Mallawi", "Samalut", "Beni Mazar"]),
    ("25", "Assiut", "أسيوط", 3.5, "Upper Egypt", ["Assiut", "Dayrout", "Manfalut", "Abnoub"]),
    ("26", "Sohag", "سوهاج", 3.5, "Upper Egypt", ["Sohag", "Akhmim", "Girga", "Tahta"]),
    ("27", "Qena", "قنا", 2.5, "Upper Egypt", ["Qena", "Nag Hammadi", "Qus"]),
    ("29", "Luxor", "الأقصر", 1.2, "Upper Egypt", ["Luxor", "Esna", "Armant"]),
    ("28", "Aswan", "أسوان", 1.3, "Upper Egypt", ["Aswan", "Kom Ombo", "Edfu"]),
    ("31", "Red Sea", "البحر الأحمر", 0.8, "Frontier", ["Hurghada", "Safaga", "Marsa Alam", "El Gouna"]),
    ("33", "Matrouh", "مطروح", 0.6, "Alexandria & Matrouh", ["Marsa Matrouh", "El Alamein", "Siwa"]),
    ("34", "North Sinai", "شمال سيناء", 0.4, "Frontier", ["Arish", "Bir al-Abd"]),
    ("35", "South Sinai", "جنوب سيناء", 0.4, "Frontier", ["Sharm El Sheikh", "Dahab", "El Tor"]),
    ("32", "New Valley", "الوادي الجديد", 0.3, "Frontier", ["Kharga", "Dakhla"]),
]
GOV_CODES = {g[0] for g in GOVERNORATES}

MALE = [("محمد", "Mohamed"), ("أحمد", "Ahmed"), ("محمود", "Mahmoud"), ("مصطفى", "Mostafa"), ("علي", "Ali"),
        ("عمر", "Omar"), ("خالد", "Khaled"), ("يوسف", "Youssef"), ("إبراهيم", "Ibrahim"), ("حسن", "Hassan"),
        ("حسين", "Hussein"), ("كريم", "Karim"), ("طارق", "Tarek"), ("عمرو", "Amr"), ("هشام", "Hesham"),
        ("شريف", "Sherif"), ("وليد", "Walid"), ("ياسر", "Yasser"), ("سامح", "Sameh"), ("أيمن", "Ayman"),
        ("عادل", "Adel"), ("مينا", "Mina"), ("بيشوي", "Bishoy"), ("جورج", "George"), ("رامي", "Ramy"),
        ("هاني", "Hany"), ("إسلام", "Islam"), ("عبدالرحمن", "Abdelrahman"), ("عبدالله", "Abdallah"), ("سيف", "Seif"),
        ("زياد", "Ziad"), ("مازن", "Mazen"), ("نادر", "Nader"), ("شادي", "Shady"), ("باسم", "Bassem"),
        ("تامر", "Tamer"), ("فادي", "Fady"), ("أشرف", "Ashraf"), ("سعيد", "Said"), ("مروان", "Marwan")]
FEMALE = [("فاطمة", "Fatma"), ("مريم", "Mariam"), ("نور", "Nour"), ("سارة", "Sara"), ("ياسمين", "Yasmin"),
          ("هبة", "Heba"), ("منى", "Mona"), ("دينا", "Dina"), ("رنا", "Rana"), ("آية", "Aya"),
          ("إسراء", "Esraa"), ("شيماء", "Shaimaa"), ("نهى", "Noha"), ("مي", "Mai"), ("ريم", "Reem"),
          ("سلمى", "Salma"), ("هالة", "Hala"), ("سمر", "Samar"), ("أمل", "Amal"), ("رحاب", "Rehab"),
          ("إيمان", "Eman"), ("منة", "Menna"), ("جنى", "Jana"), ("ملك", "Malak"), ("حبيبة", "Habiba"),
          ("ندى", "Nada"), ("لينا", "Lina"), ("مارينا", "Marina"), ("كريستين", "Christine"), ("ماريان", "Marian"),
          ("نيرمين", "Nermeen"), ("داليا", "Dalia"), ("غادة", "Ghada"), ("عبير", "Abeer"), ("سها", "Soha"),
          ("رشا", "Rasha"), ("هند", "Hend"), ("ولاء", "Walaa"), ("أسماء", "Asmaa"), ("إيناس", "Enas")]
FAMILY = [("السيد", "El-Sayed"), ("عبدالعزيز", "Abdelaziz"), ("حسن", "Hassan"), ("إبراهيم", "Ibrahim"),
          ("محمود", "Mahmoud"), ("مصطفى", "Mostafa"), ("عبدالله", "Abdallah"), ("سليمان", "Soliman"),
          ("فرج", "Farag"), ("منصور", "Mansour"), ("الشريف", "El-Sherif"), ("النجار", "El-Naggar"),
          ("الشافعي", "El-Shafei"), ("عثمان", "Osman"), ("رمضان", "Ramadan"), ("شحاتة", "Shehata"),
          ("عبدالحميد", "Abdelhamid"), ("عبدالفتاح", "Abdelfattah"), ("سالم", "Salem"), ("جاد", "Gad"),
          ("بدوي", "Badawy"), ("حجازي", "Hegazy"), ("الخولي", "El-Kholy"), ("زكي", "Zaki"), ("فهمي", "Fahmy"),
          ("مرسي", "Morsy"), ("عيسى", "Eissa"), ("صبري", "Sabry"), ("غالي", "Ghaly"), ("نصر", "Nasr"),
          ("عزت", "Ezzat"), ("حمدي", "Hamdy"), ("توفيق", "Tawfik"), ("البنا", "El-Banna"), ("الجمال", "El-Gamal"),
          ("عامر", "Amer"), ("قاسم", "Kassem"), ("حنا", "Hanna"), ("جرجس", "Girgis"), ("شنودة", "Shenouda")]

# occupation_en, occupation_ar, sector, median monthly income EGP, sigma, floor, weight
OCCUPATIONS = [
    ("Government employee", "موظف حكومي", "Government", 9500, 0.30, 8000, 16),
    ("Teacher", "مدرس", "Government", 9000, 0.30, 8000, 7),
    ("Private-sector employee", "موظف قطاع خاص", "Private", 14000, 0.45, 7000, 18),
    ("Bank employee", "موظف بنك", "Private", 28000, 0.40, 9000, 3),
    ("Software engineer", "مهندس برمجيات", "Private", 42000, 0.55, 12000, 3),
    ("Engineer", "مهندس", "Private", 24000, 0.45, 9000, 5),
    ("Doctor", "طبيب", "Private", 32000, 0.55, 10000, 3),
    ("Pharmacist", "صيدلي", "Private", 17000, 0.40, 8000, 3),
    ("Accountant", "محاسب", "Private", 15000, 0.40, 7500, 4),
    ("Sales representative", "مندوب مبيعات", "Private", 10500, 0.40, 7000, 5),
    ("Business owner", "صاحب عمل", "Self-employed", 38000, 0.85, 8000, 5),
    ("Freelancer", "عمل حر", "Self-employed", 24000, 0.75, 5000, 4),
    ("Technician / craftsman", "فني / حرفي", "Self-employed", 9000, 0.40, 4500, 6),
    ("Driver (ride-hailing)", "سائق", "Self-employed", 8800, 0.35, 4500, 4),
    ("Retired", "متقاعد", "Pension", 6500, 0.45, 1500, 7),
    ("Student", "طالب", "Student", 2200, 0.60, 500, 4),
    ("Homemaker (remittances)", "ربة منزل (تحويلات من الخارج)", "Remittance", 9000, 0.50, 3000, 3),
]

# category -> (label_en, label_ar, merchants, channels, base share of income per tx)
CATEGORIES = {
    "groceries": ("Groceries", "بقالة وسوبر ماركت", ["Carrefour", "Hyper One", "Spinneys", "Metro Market", "Kazyon", "Kheir Zaman", "Fathalla Market", "Seoudi Market", "Gourmet Egypt", "Breadfast"], ["POS", "POS", "E-commerce"], 0.020),
    "dining": ("Dining & delivery", "مطاعم وتوصيل", ["Talabat", "elmenus", "KFC", "McDonald's", "Koshary Abou Tarek", "Mo'men", "Buffalo Burger", "Cook Door", "Gad", "Zooba", "Starbucks", "Costa Coffee"], ["E-commerce", "POS", "POS"], 0.012),
    "transport": ("Transport & fuel", "مواصلات ووقود", ["Uber", "Careem", "inDrive", "Swvl", "Wataniya Petroleum", "ChillOut", "TotalEnergies", "Misr Petroleum"], ["E-commerce", "POS", "Wallet"], 0.010),
    "telecom": ("Mobile & internet", "اتصالات وإنترنت", ["Vodafone Egypt", "Orange Egypt", "e& Egypt", "WE"], ["Fawry", "Wallet", "E-commerce"], 0.012),
    "utilities": ("Bills (Fawry)", "فواتير (فوري)", ["Electricity bill", "Water bill", "Natural gas bill", "WE Home Internet"], ["Fawry"], 0.030),
    "shopping": ("Shopping", "تسوق", ["Noon", "Amazon.eg", "Jumia", "City Stars", "Mall of Egypt", "LC Waikiki", "Defacto", "B.TECH", "2B", "IKEA Egypt"], ["E-commerce", "POS"], 0.035),
    "health": ("Health & pharmacy", "صحة وصيدليات", ["El Ezaby Pharmacy", "Seif Pharmacy", "19011 Pharmacy", "Cleopatra Hospital", "Alfa Lab", "Al Borg Lab", "Vezeeta"], ["POS", "E-commerce"], 0.020),
    "education": ("Education", "تعليم", ["School fees", "University fees", "Udemy", "Coursera", "Training center"], ["Bank transfer", "E-commerce"], 0.150),
    "entertainment": ("Entertainment & subscriptions", "ترفيه واشتراكات", ["Netflix", "Shahid VIP", "Anghami", "Spotify", "Watch It", "VOX Cinemas", "PlayStation Store"], ["E-commerce"], 0.008),
    "travel": ("Travel", "سفر", ["EgyptAir", "Air Cairo", "Booking.com", "Go Bus", "Hotel - North Coast", "Hotel - Hurghada"], ["E-commerce", "POS"], 0.120),
    "cash": ("Cash withdrawal (ATM)", "سحب نقدي", ["ATM withdrawal"], ["ATM"], 0.150),
    "transfers": ("Transfers (InstaPay / wallets)", "تحويلات (إنستاباي / محافظ)", ["InstaPay transfer", "Vodafone Cash top-up", "Bank transfer"], ["InstaPay", "Wallet", "Bank transfer"], 0.080),
    "charity": ("Charity & zakat", "تبرعات وزكاة", ["Egyptian Food Bank", "57357 Hospital", "Magdi Yacoub Foundation", "Resala", "Misr El Kheir"], ["E-commerce", "Fawry"], 0.020),
}
# typical frequency weights of debit categories
CATEGORY_WEIGHTS = {"groceries": 20, "dining": 14, "transport": 13, "telecom": 6, "utilities": 4, "shopping": 9,
                    "health": 5, "education": 1, "entertainment": 4, "travel": 1, "cash": 14, "transfers": 8, "charity": 1}
SUBSCRIPTION_MERCHANTS = {"Netflix", "Shahid VIP", "Anghami", "Spotify", "Watch It"}

# Seasonality windows (approximate Gregorian dates)
RAMADAN_2026 = (date(2026, 2, 18), date(2026, 3, 19))
EID_FITR_2026 = (date(2026, 3, 20), date(2026, 3, 23))
EID_ADHA_2026 = (date(2026, 5, 26), date(2026, 5, 30))
SUMMER = (date(2026, 7, 1), date(2026, 8, 31))
BACK_TO_SCHOOL = (date(2026, 9, 10), date(2026, 10, 10))

# Stock universe. EGX prices are SIMULATED in the demo (no legitimate free EGX feed).
# symbol, name_en, name_ar, market, sector, base_price, annual_vol, sharia_compliant
EGX = [
    ("COMI", "Commercial International Bank", "البنك التجاري الدولي", "EGX", "Banks", 110.0, 0.30, False),
    ("ETEL", "Telecom Egypt", "المصرية للاتصالات", "EGX", "Telecom", 60.0, 0.33, True),
    ("TMGH", "Talaat Moustafa Group", "مجموعة طلعت مصطفى", "EGX", "Real Estate", 75.0, 0.42, True),
    ("SWDY", "Elsewedy Electric", "السويدي إليكتريك", "EGX", "Industrials", 80.0, 0.38, True),
    ("EAST", "Eastern Company", "الشرقية للدخان", "EGX", "Consumer Staples", 35.0, 0.28, False),
    ("HRHO", "EFG Holding", "إي إف جي القابضة", "EGX", "Financial Services", 30.0, 0.40, False),
    ("ABUK", "Abu Qir Fertilizers", "أبوقير للأسمدة", "EGX", "Basic Materials", 55.0, 0.35, True),
    ("FWRY", "Fawry", "فوري", "EGX", "Fintech", 14.0, 0.48, True),
    ("EFIH", "e-finance", "إي فاينانس", "EGX", "Fintech", 25.0, 0.45, True),
    ("ORAS", "Orascom Construction", "أوراسكوم كونستراكشون", "EGX", "Industrials", 400.0, 0.36, True),
    ("JUFO", "Juhayna Food Industries", "جهينة للصناعات الغذائية", "EGX", "Consumer Staples", 30.0, 0.32, True),
    ("PHDC", "Palm Hills Developments", "بالم هيلز للتعمير", "EGX", "Real Estate", 8.0, 0.50, True),
    ("CLHO", "Cleopatra Hospitals", "مستشفى كليوباترا", "EGX", "Healthcare", 12.0, 0.34, True),
    ("ESRS", "Ezz Steel", "حديد عز", "EGX", "Basic Materials", 120.0, 0.46, True),
    ("ADIB", "Abu Dhabi Islamic Bank Egypt", "مصرف أبوظبي الإسلامي مصر", "EGX", "Banks", 40.0, 0.35, True),
]
US = [
    ("AAPL", "Apple", "أبل", "US", "Technology", 230.0, 0.27, True),
    ("MSFT", "Microsoft", "مايكروسوفت", "US", "Technology", 450.0, 0.25, True),
    ("NVDA", "NVIDIA", "إنفيديا", "US", "Technology", 150.0, 0.50, True),
    ("AMZN", "Amazon", "أمازون", "US", "Consumer Discretionary", 200.0, 0.33, True),
    ("GOOGL", "Alphabet", "ألفابت", "US", "Communication", 180.0, 0.30, True),
    ("META", "Meta Platforms", "ميتا", "US", "Communication", 600.0, 0.38, True),
    ("TSLA", "Tesla", "تسلا", "US", "Consumer Discretionary", 300.0, 0.60, True),
    ("JPM", "JPMorgan Chase", "جي بي مورجان", "US", "Banks", 250.0, 0.24, False),
    ("KO", "Coca-Cola", "كوكاكولا", "US", "Consumer Staples", 70.0, 0.16, True),
    ("XOM", "Exxon Mobil", "إكسون موبيل", "US", "Energy", 115.0, 0.25, True),
]
UNIVERSE = EGX + US

# ---------- identity helpers ----------

def national_id_check_digit(first13: str) -> str:
    """Synthetic weighted checksum (the official algorithm is not public)."""
    weights = [2, 7, 6, 5, 4, 3, 2, 7, 6, 5, 4, 3, 2]
    s = sum(int(d) * w for d, w in zip(first13, weights))
    return str((11 - s % 11) % 10)


def make_national_id(birth: date, gov_code: str, male: bool, serial: int) -> str:
    century = "2" if birth.year < 2000 else "3"
    seq3 = f"{serial % 1000:03d}"
    gender_digit = str((serial % 5) * 2 + (1 if male else 0))   # odd = male, even = female
    first13 = f"{century}{birth:%y%m%d}{gov_code}{seq3}{gender_digit}"
    return first13 + national_id_check_digit(first13)


NID_RE = re.compile(r"^[23]\d{13}$")


def validate_national_id(nid: str) -> tuple[bool, str]:
    nid = (nid or "").strip()
    if not NID_RE.match(nid):
        return False, "National ID must be 14 digits starting with 2 or 3"
    century = 1900 if nid[0] == "2" else 2000
    try:
        dob = date(century + int(nid[1:3]), int(nid[3:5]), int(nid[5:7]))
    except ValueError:
        return False, "Invalid birth date inside national ID"
    if dob > date.today():
        return False, "Birth date is in the future"
    if nid[7:9] not in GOV_CODES and nid[7:9] != "88":
        return False, "Unknown governorate code"
    return True, "ok"


def nid_birth_gender(nid: str) -> tuple[date, str]:
    century = 1900 if nid[0] == "2" else 2000
    dob = date(century + int(nid[1:3]), int(nid[3:5]), int(nid[5:7]))
    return dob, ("M" if int(nid[12]) % 2 == 1 else "F")


PHONE_RE = re.compile(r"^(\+20|0020|0)?1[0125]\d{8}$")


def validate_phone(p: str) -> bool:
    return bool(PHONE_RE.match((p or "").replace(" ", "").replace("-", "")))


BANK_CODE = "0077"   # fictional bank code for Masar


def make_iban(branch: int, account_no: int) -> str:
    bban = f"{BANK_CODE}{branch:04d}{account_no:017d}"
    # mod-97: move "EG00" to the end, letters E=14 G=16
    num = int(bban + "141600")
    check = 98 - (num % 97)
    return f"EG{check:02d}{bban}"


def validate_iban(iban: str) -> bool:
    iban = iban.replace(" ", "")
    if not (iban.startswith("EG") and len(iban) == 29 and iban[2:].isdigit()):
        return False
    rearranged = iban[4:] + "1416" + iban[2:4]
    return int(rearranged) % 97 == 1


# ---------- masking (data governance) ----------

def mask_nid(nid: str) -> str:
    return nid[0] + "•" * 10 + nid[-3:] if nid and len(nid) == 14 else "•" * 14


def mask_phone(p: str) -> str:
    return p[:6] + "•••" + p[-3:] if p and len(p) > 9 else "•••"


def mask_email(e: str) -> str:
    if not e or "@" not in e:
        return "•••"
    u, d = e.split("@", 1)
    return u[0] + "•••@" + d


def mask_iban(i: str) -> str:
    return i[:4] + " •••• •••• " + i[-4:] if i else ""
