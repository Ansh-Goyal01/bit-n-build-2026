"""Registry of the central and Uttar Pradesh state welfare schemes in the corpus.

The slug is the scheme's identifier on myscheme.gov.in and doubles as the
stable scheme_id everywhere in Adhikaar (corpus, index, rules, eval labels).
"""

from pydantic import BaseModel


class SchemeSource(BaseModel):
    slug: str
    short_name: str
    name: str
    category: str


SCHEME_SOURCES: list[SchemeSource] = [
    SchemeSource(
        slug="pm-kisan",
        short_name="PM-KISAN",
        name="Pradhan Mantri Kisan Samman Nidhi",
        category="farmers",
    ),
    SchemeSource(
        slug="pmfby",
        short_name="PMFBY",
        name="Pradhan Mantri Fasal Bima Yojana",
        category="farmers",
    ),
    SchemeSource(
        slug="pmay-g",
        short_name="PMAY-G",
        name="Pradhan Mantri Awaas Yojana - Gramin",
        category="housing",
    ),
    SchemeSource(
        slug="nsap-ignoaps",
        short_name="IGNOAPS",
        name="Indira Gandhi National Old Age Pension Scheme",
        category="pension",
    ),
    SchemeSource(
        slug="ignwps",
        short_name="IGNWPS",
        name="Indira Gandhi National Widow Pension Scheme",
        category="pension",
    ),
    SchemeSource(
        slug="igndps",
        short_name="IGNDPS",
        name="Indira Gandhi National Disability Pension Scheme",
        category="pension",
    ),
    SchemeSource(
        slug="pmsby",
        short_name="PMSBY",
        name="Pradhan Mantri Suraksha Bima Yojana",
        category="insurance",
    ),
    SchemeSource(
        slug="pmjjby",
        short_name="PMJJBY",
        name="Pradhan Mantri Jeevan Jyoti Bima Yojana",
        category="insurance",
    ),
    SchemeSource(
        slug="apy",
        short_name="APY",
        name="Atal Pension Yojana",
        category="pension",
    ),
    SchemeSource(
        slug="ab-pmjay",
        short_name="PM-JAY",
        name="Ayushman Bharat Pradhan Mantri Jan Arogya Yojana",
        category="health",
    ),
    SchemeSource(
        slug="pmuy",
        short_name="PMUY",
        name="Pradhan Mantri Ujjwala Yojana",
        category="household",
    ),
    SchemeSource(
        slug="pm-svanidhi",
        short_name="PM SVANidhi",
        name="PM Street Vendor's AtmaNirbhar Nidhi",
        category="livelihood",
    ),
    SchemeSource(
        slug="pmv",
        short_name="PM Vishwakarma",
        name="PM Vishwakarma",
        category="livelihood",
    ),
    # --- Scaling batch (2026-07-13): 35 additional central schemes from the
    # --- discovery index; rules arrive via the extraction review queue only.
    SchemeSource(
        slug="pm-sym",
        short_name="PM-SYM",
        name="Pradhan Mantri Shram Yogi Maan-dhan",
        category="pension",
    ),
    SchemeSource(
        slug="nfbs",
        short_name="NFBS",
        name="National Family Benefit Scheme",
        category="pension",
    ),
    SchemeSource(
        slug="pmjdy",
        short_name="PMJDY",
        name="Pradhan Mantri Jan Dhan Yojana",
        category="savings",
    ),
    SchemeSource(
        slug="pmegp",
        short_name="PMEGP",
        name="Prime Minister's Employment Generation Programme",
        category="livelihood",
    ),
    SchemeSource(
        slug="pmmy",
        short_name="PMMY",
        name="Pradhan Mantri Mudra Yojana",
        category="livelihood",
    ),
    SchemeSource(
        slug="pm-daksh",
        short_name="PM-DAKSH",
        name="Pradhan Mantri Dakshta Aur Kushalta Sampann Hitgrahi (PM-DAKSH)",
        category="livelihood",
    ),
    SchemeSource(
        slug="pmmvy",
        short_name="PMMVY",
        name="Pradhan Mantri Matru Vandana Yojana",
        category="household",
    ),
    SchemeSource(
        slug="hepsn",
        short_name="HEPSN",
        name=(
            "Persons With Disabilities Scheme In Colleges: Higher Education For Persons "
            "With Special Needs"
        ),
        category="education",
    ),
    SchemeSource(
        slug="sag",
        short_name="SAG",
        name="Scheme For Adolescent Girls",
        category="household",
    ),
    SchemeSource(
        slug="pg-igssgc",
        short_name="PG-IGSSGC",
        name="Post Graduate Indira Gandhi Scholarship For Single Girl Child",
        category="education",
    ),
    SchemeSource(
        slug="bhmnsp",
        short_name="BHMNSP",
        name="Begum Hazrat Mahal National Scholarship Program",
        category="education",
    ),
    SchemeSource(
        slug="pre-sc",
        short_name="PRE-SC",
        name="Pre-Matric Scholarship for Scheduled Caste Students",
        category="education",
    ),
    SchemeSource(
        slug="post-st",
        short_name="POST-ST",
        name=(
            "Post Matric Scholarship Scheme For The Students Belonging To Scheduled "
            "Tribe For Studies In India"
        ),
        category="education",
    ),
    SchemeSource(
        slug="csspremsobcsi",
        short_name="PRE-OBC",
        name=(
            "Centrally Sponsored Scheme of Pre-matric Scholarship to Other Backward "
            "Classes (OBC) for Studies in India"
        ),
        category="education",
    ),
    SchemeSource(
        slug="post-dis",
        short_name="POST-DIS",
        name="Post Matric Scholarship Students With Disabilities",
        category="education",
    ),
    SchemeSource(
        slug="pre-dis",
        short_name="PRE-DIS",
        name="Pre Matric Scholarship For Students With Disabilities",
        category="education",
    ),
    SchemeSource(
        slug="tce-sc",
        short_name="TCE-SC",
        name="Top Class Education For Scheduled Caste Students",
        category="education",
    ),
    SchemeSource(
        slug="tce-swd",
        short_name="TCE-SWD",
        name="Top Class Education For Students With Disabilities",
        category="education",
    ),
    SchemeSource(
        slug="nmmss",
        short_name="NMMSS",
        name="National Means-cum-Merit Scholarship Scheme",
        category="education",
    ),
    SchemeSource(
        slug="csss-cus",
        short_name="PM-USP CSSS",
        name=(
            "Pradhan Mantri Uchchatar Shiksha Protsahan (PM-USP) Central Sector Scheme "
            "of Scholarship for College and University students"
        ),
        category="education",
    ),
    SchemeSource(
        slug="sak-deg",
        short_name="SAKSHAM",
        name="AICTE – Saksham Scholarship Scheme For Specially-Abled Student (Degree)",
        category="education",
    ),
    SchemeSource(
        slug="psgs-dip",
        short_name="PRAGATI-DIP",
        name="Pragati Scholarship Scheme For Girl Students (Technical Diploma)",
        category="education",
    ),
    SchemeSource(
        slug="dacssiselosobcebc",
        short_name="DACSSIS",
        name=(
            "Dr Ambedkar Central Sector Scheme of Interest Subsidy on Educational Loans "
            "for Overseas Studies for Other Backward Classes (OBCs) and Economically "
            "Backward Classes (EBCs)"
        ),
        category="education",
    ),
    SchemeSource(
        slug="nts-ug",
        short_name="NTS-UG",
        name="National Talent Scholarship Undergraduate",
        category="education",
    ),
    SchemeSource(
        slug="inspire-she",
        short_name="INSPIRE-SHE",
        name=(
            "Innovation In Science Pursuit For Inspired Research (INSPIRE) - Scholarship "
            "For Higher Education (SHE)"
        ),
        category="education",
    ),
    SchemeSource(
        slug="kcc",
        short_name="KCC",
        name="Kisan Credit Card",
        category="farmers",
    ),
    SchemeSource(
        slug="rkvyshfshc",
        short_name="SHC",
        name="RKVY Soil Health and Fertility - Soil Health Card",
        category="farmers",
    ),
    SchemeSource(
        slug="nswf",
        short_name="NSWF",
        name="National Scheme Of Welfare Of Fishermen",
        category="livelihood",
    ),
    SchemeSource(
        slug="gispw",
        short_name="GISPW",
        name="Group Insurance Scheme for Powerloom Weavers",
        category="insurance",
    ),
    SchemeSource(
        slug="lws-h",
        short_name="LWS-H",
        name="Labour Welfare Scheme (Health)",
        category="health",
    ),
    SchemeSource(
        slug="vdcspds",
        short_name="VIKAAS",
        name="Vikaas-Day Care Scheme For Person with Disability Children",
        category="household",
    ),
    SchemeSource(
        slug="cmhtp-crwtp-smile",
        short_name="SMILE",
        name=(
            "Support for Marginalized Individuals for Livelihood and Enterprise (SMILE): "
            "Composite Medical Health for Transgender Persons"
        ),
        category="livelihood",
    ),
    SchemeSource(
        slug="pmay-u",
        short_name="PMAY-U",
        name="Pradhan Mantri Awas Yojana - Urban",
        category="housing",
    ),
    SchemeSource(
        slug="mssc",
        short_name="MSSC",
        name="Mahila Samman Savings Certificate",
        category="savings",
    ),
    SchemeSource(
        slug="pm-vikas",
        short_name="PM VIKAS",
        name="Pradhan Mantri Virasat ka Samvardhan",
        category="livelihood",
    ),
    # Uttar Pradesh state schemes (myScheme level "State"; every rule file
    # requires state == "Uttar Pradesh").
    SchemeSource(
        slug="upoaps",
        short_name="UP-OAPS",
        name="Uttar Pradesh Old Age Pension Scheme",
        category="pension",
    ),
    SchemeSource(
        slug="wpup",
        short_name="UP-WIDOW",
        name="Widow Pension - Uttar Pradesh",
        category="pension",
    ),
    SchemeSource(
        slug="dpyup",
        short_name="UP-DIVYANG",
        name="Divyang Pension Yojana",
        category="pension",
    ),
    SchemeSource(
        slug="ksy",
        short_name="MKSY",
        name="Kanya Sumangala Yojana",
        category="household",
    ),
    SchemeSource(
        slug="mpss",
        short_name="UP-PMS-OBC",
        name="Post-matric Scholarship Scheme- Uttar Pradesh",
        category="education",
    ),
    SchemeSource(
        slug="pmcup",
        short_name="UP-PRE-SCST",
        name="SC/ST Pre Matric Scholarship - Uttar Pradesh",
        category="education",
    ),
]


class PdfSource(BaseModel):
    """A scheme whose official text comes from a government PDF instead of myScheme.

    Two schemes need this path: Sukanya Samriddhi is absent from myscheme.gov.in
    (we ingest the gazette notification published by India Post), and the central
    Post-Matric Scholarship for SC students is listed there only as state variants
    (we ingest the Dept. of Social Justice & Empowerment guidelines).
    """

    scheme_id: str
    short_name: str
    name: str
    category: str
    pdf_url: str
    page_url: str


PDF_SOURCES: list[PdfSource] = [
    PdfSource(
        scheme_id="sukanya-samriddhi",
        short_name="SSY",
        name="Sukanya Samriddhi Yojana (Sukanya Samriddhi Account Scheme, 2019)",
        category="savings",
        pdf_url=(
            "https://www.indiapost.gov.in/documents/offerings/schemesandservices/posb/"
            "SukanyaSamriddhiAccountScheme2019English.pdf"
        ),
        page_url="https://www.indiapost.gov.in/VAS/Pages/PMODashboard/SukanyaSamriddhiAccount.aspx",
    ),
    PdfSource(
        scheme_id="pms-sc",
        short_name="PMS-SC",
        name="Post Matric Scholarship for SC Students (PM-PMS-SC)",
        category="education",
        pdf_url=(
            "https://socialjustice.gov.in/writereaddata/UploadFile/"
            "PMS_for_SCs_Scheme_Guidelines.pdf"
        ),
        page_url="https://socialjustice.gov.in/schemes/25",
    ),
]
