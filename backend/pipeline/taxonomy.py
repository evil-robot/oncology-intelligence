"""
Oncology and Rare Disease search term taxonomy.

This module defines the seed terms and taxonomy structure for oncology and rare disease searches.
Terms are organized hierarchically by category and can be expanded via related queries.
"""

from dataclasses import dataclass
from typing import Optional


@dataclass
class TaxonomyTerm:
    """A term in our search taxonomy."""

    term: str
    category: str
    subcategory: Optional[str] = None
    parent: Optional[str] = None


# Seed taxonomy - curated list of oncology and rare disease search terms
SEED_TAXONOMY: list[TaxonomyTerm] = [
    # ============================================================================
    # PEDIATRIC ONCOLOGY
    # ============================================================================

    # === PEDIATRIC - General ===
    TaxonomyTerm("pediatric oncology", "pediatric_oncology", "general"),
    TaxonomyTerm("childhood cancer", "pediatric_oncology", "general"),
    TaxonomyTerm("pediatric cancer", "pediatric_oncology", "general"),
    TaxonomyTerm("child cancer symptoms", "pediatric_oncology", "general"),

    # Pediatric Leukemias
    TaxonomyTerm("childhood leukemia", "pediatric_oncology", "leukemia"),
    TaxonomyTerm("acute lymphoblastic leukemia children", "pediatric_oncology", "leukemia"),
    TaxonomyTerm("ALL in children", "pediatric_oncology", "leukemia"),
    TaxonomyTerm("acute myeloid leukemia pediatric", "pediatric_oncology", "leukemia"),
    TaxonomyTerm("AML children", "pediatric_oncology", "leukemia"),
    TaxonomyTerm("juvenile myelomonocytic leukemia", "pediatric_oncology", "leukemia"),

    # Pediatric Brain tumors
    TaxonomyTerm("pediatric brain tumor", "pediatric_oncology", "brain_tumor"),
    TaxonomyTerm("childhood brain cancer", "pediatric_oncology", "brain_tumor"),
    TaxonomyTerm("medulloblastoma", "pediatric_oncology", "brain_tumor"),
    TaxonomyTerm("pediatric glioma", "pediatric_oncology", "brain_tumor"),
    TaxonomyTerm("DIPG", "pediatric_oncology", "brain_tumor"),
    TaxonomyTerm("diffuse intrinsic pontine glioma", "pediatric_oncology", "brain_tumor"),
    TaxonomyTerm("ependymoma children", "pediatric_oncology", "brain_tumor"),

    # Pediatric Solid tumors
    TaxonomyTerm("neuroblastoma", "pediatric_oncology", "solid_tumor"),
    TaxonomyTerm("wilms tumor", "pediatric_oncology", "solid_tumor"),
    TaxonomyTerm("rhabdomyosarcoma", "pediatric_oncology", "solid_tumor"),
    TaxonomyTerm("osteosarcoma children", "pediatric_oncology", "solid_tumor"),
    TaxonomyTerm("ewing sarcoma", "pediatric_oncology", "solid_tumor"),
    TaxonomyTerm("retinoblastoma", "pediatric_oncology", "solid_tumor"),
    TaxonomyTerm("hepatoblastoma", "pediatric_oncology", "solid_tumor"),

    # Pediatric Lymphomas
    TaxonomyTerm("childhood lymphoma", "pediatric_oncology", "lymphoma"),
    TaxonomyTerm("pediatric hodgkin lymphoma", "pediatric_oncology", "lymphoma"),
    TaxonomyTerm("non hodgkin lymphoma children", "pediatric_oncology", "lymphoma"),

    # ============================================================================
    # ADULT ONCOLOGY - COMMON CANCERS
    # ============================================================================

    # === Breast Cancer ===
    TaxonomyTerm("breast cancer", "adult_oncology", "breast"),
    TaxonomyTerm("breast cancer symptoms", "adult_oncology", "breast"),
    TaxonomyTerm("triple negative breast cancer", "adult_oncology", "breast"),
    TaxonomyTerm("HER2 positive breast cancer", "adult_oncology", "breast"),
    TaxonomyTerm("metastatic breast cancer", "adult_oncology", "breast"),
    TaxonomyTerm("breast cancer staging", "adult_oncology", "breast"),
    TaxonomyTerm("BRCA gene mutation", "adult_oncology", "breast"),
    TaxonomyTerm("inflammatory breast cancer", "adult_oncology", "breast"),
    TaxonomyTerm("ductal carcinoma in situ", "adult_oncology", "breast"),
    TaxonomyTerm("breast cancer survival rate", "adult_oncology", "breast"),

    # === Lung Cancer ===
    TaxonomyTerm("lung cancer", "adult_oncology", "lung"),
    TaxonomyTerm("lung cancer symptoms", "adult_oncology", "lung"),
    TaxonomyTerm("non small cell lung cancer", "adult_oncology", "lung"),
    TaxonomyTerm("small cell lung cancer", "adult_oncology", "lung"),
    TaxonomyTerm("NSCLC treatment", "adult_oncology", "lung"),
    TaxonomyTerm("lung cancer screening", "adult_oncology", "lung"),
    TaxonomyTerm("EGFR mutation lung cancer", "adult_oncology", "lung"),
    TaxonomyTerm("ALK positive lung cancer", "adult_oncology", "lung"),
    TaxonomyTerm("stage 4 lung cancer", "adult_oncology", "lung"),
    TaxonomyTerm("lung cancer survival rate", "adult_oncology", "lung"),

    # === Colorectal Cancer ===
    TaxonomyTerm("colon cancer", "adult_oncology", "colorectal"),
    TaxonomyTerm("colorectal cancer", "adult_oncology", "colorectal"),
    TaxonomyTerm("rectal cancer", "adult_oncology", "colorectal"),
    TaxonomyTerm("colon cancer symptoms", "adult_oncology", "colorectal"),
    TaxonomyTerm("colorectal cancer screening", "adult_oncology", "colorectal"),
    TaxonomyTerm("colonoscopy", "adult_oncology", "colorectal"),
    TaxonomyTerm("Lynch syndrome", "adult_oncology", "colorectal"),
    TaxonomyTerm("colon polyps cancer", "adult_oncology", "colorectal"),
    TaxonomyTerm("metastatic colorectal cancer", "adult_oncology", "colorectal"),

    # === Prostate Cancer ===
    TaxonomyTerm("prostate cancer", "adult_oncology", "prostate"),
    TaxonomyTerm("prostate cancer symptoms", "adult_oncology", "prostate"),
    TaxonomyTerm("PSA test", "adult_oncology", "prostate"),
    TaxonomyTerm("prostate cancer treatment", "adult_oncology", "prostate"),
    TaxonomyTerm("metastatic prostate cancer", "adult_oncology", "prostate"),
    TaxonomyTerm("Gleason score", "adult_oncology", "prostate"),
    TaxonomyTerm("prostate cancer staging", "adult_oncology", "prostate"),
    TaxonomyTerm("castration resistant prostate cancer", "adult_oncology", "prostate"),

    # === Pancreatic Cancer ===
    TaxonomyTerm("pancreatic cancer", "adult_oncology", "pancreatic"),
    TaxonomyTerm("pancreatic cancer symptoms", "adult_oncology", "pancreatic"),
    TaxonomyTerm("pancreatic adenocarcinoma", "adult_oncology", "pancreatic"),
    TaxonomyTerm("pancreatic cancer survival rate", "adult_oncology", "pancreatic"),
    TaxonomyTerm("Whipple procedure", "adult_oncology", "pancreatic"),
    TaxonomyTerm("pancreatic neuroendocrine tumor", "adult_oncology", "pancreatic"),

    # === Melanoma & Skin Cancer ===
    TaxonomyTerm("melanoma", "adult_oncology", "skin"),
    TaxonomyTerm("skin cancer", "adult_oncology", "skin"),
    TaxonomyTerm("melanoma symptoms", "adult_oncology", "skin"),
    TaxonomyTerm("basal cell carcinoma", "adult_oncology", "skin"),
    TaxonomyTerm("squamous cell carcinoma skin", "adult_oncology", "skin"),
    TaxonomyTerm("metastatic melanoma", "adult_oncology", "skin"),
    TaxonomyTerm("BRAF mutation melanoma", "adult_oncology", "skin"),
    TaxonomyTerm("melanoma staging", "adult_oncology", "skin"),

    # === Adult Leukemias ===
    TaxonomyTerm("leukemia", "adult_oncology", "leukemia"),
    TaxonomyTerm("acute myeloid leukemia", "adult_oncology", "leukemia"),
    TaxonomyTerm("AML treatment", "adult_oncology", "leukemia"),
    TaxonomyTerm("chronic lymphocytic leukemia", "adult_oncology", "leukemia"),
    TaxonomyTerm("CLL treatment", "adult_oncology", "leukemia"),
    TaxonomyTerm("chronic myeloid leukemia", "adult_oncology", "leukemia"),
    TaxonomyTerm("CML treatment", "adult_oncology", "leukemia"),
    TaxonomyTerm("acute lymphoblastic leukemia adult", "adult_oncology", "leukemia"),

    # === Lymphomas ===
    TaxonomyTerm("lymphoma", "adult_oncology", "lymphoma"),
    TaxonomyTerm("non hodgkin lymphoma", "adult_oncology", "lymphoma"),
    TaxonomyTerm("hodgkin lymphoma", "adult_oncology", "lymphoma"),
    TaxonomyTerm("diffuse large B cell lymphoma", "adult_oncology", "lymphoma"),
    TaxonomyTerm("DLBCL treatment", "adult_oncology", "lymphoma"),
    TaxonomyTerm("follicular lymphoma", "adult_oncology", "lymphoma"),
    TaxonomyTerm("mantle cell lymphoma", "adult_oncology", "lymphoma"),
    TaxonomyTerm("marginal zone lymphoma", "adult_oncology", "lymphoma"),

    # === Multiple Myeloma ===
    TaxonomyTerm("multiple myeloma", "adult_oncology", "myeloma"),
    TaxonomyTerm("multiple myeloma symptoms", "adult_oncology", "myeloma"),
    TaxonomyTerm("myeloma treatment", "adult_oncology", "myeloma"),
    TaxonomyTerm("smoldering myeloma", "adult_oncology", "myeloma"),
    TaxonomyTerm("MGUS", "adult_oncology", "myeloma"),

    # === Ovarian Cancer ===
    TaxonomyTerm("ovarian cancer", "adult_oncology", "ovarian"),
    TaxonomyTerm("ovarian cancer symptoms", "adult_oncology", "ovarian"),
    TaxonomyTerm("ovarian cancer staging", "adult_oncology", "ovarian"),
    TaxonomyTerm("epithelial ovarian cancer", "adult_oncology", "ovarian"),
    TaxonomyTerm("BRCA ovarian cancer", "adult_oncology", "ovarian"),

    # === Kidney Cancer ===
    TaxonomyTerm("kidney cancer", "adult_oncology", "kidney"),
    TaxonomyTerm("renal cell carcinoma", "adult_oncology", "kidney"),
    TaxonomyTerm("kidney cancer symptoms", "adult_oncology", "kidney"),
    TaxonomyTerm("clear cell renal carcinoma", "adult_oncology", "kidney"),

    # === Bladder Cancer ===
    TaxonomyTerm("bladder cancer", "adult_oncology", "bladder"),
    TaxonomyTerm("bladder cancer symptoms", "adult_oncology", "bladder"),
    TaxonomyTerm("transitional cell carcinoma", "adult_oncology", "bladder"),
    TaxonomyTerm("muscle invasive bladder cancer", "adult_oncology", "bladder"),

    # === Liver Cancer ===
    TaxonomyTerm("liver cancer", "adult_oncology", "liver"),
    TaxonomyTerm("hepatocellular carcinoma", "adult_oncology", "liver"),
    TaxonomyTerm("HCC treatment", "adult_oncology", "liver"),
    TaxonomyTerm("liver cancer symptoms", "adult_oncology", "liver"),

    # === Brain Tumors Adult ===
    TaxonomyTerm("brain tumor", "adult_oncology", "brain"),
    TaxonomyTerm("glioblastoma", "adult_oncology", "brain"),
    TaxonomyTerm("GBM treatment", "adult_oncology", "brain"),
    TaxonomyTerm("brain cancer symptoms", "adult_oncology", "brain"),
    TaxonomyTerm("meningioma", "adult_oncology", "brain"),
    TaxonomyTerm("astrocytoma", "adult_oncology", "brain"),

    # === Thyroid Cancer ===
    TaxonomyTerm("thyroid cancer", "adult_oncology", "thyroid"),
    TaxonomyTerm("papillary thyroid cancer", "adult_oncology", "thyroid"),
    TaxonomyTerm("thyroid nodule cancer", "adult_oncology", "thyroid"),
    TaxonomyTerm("medullary thyroid cancer", "adult_oncology", "thyroid"),

    # === Head and Neck Cancer ===
    TaxonomyTerm("head and neck cancer", "adult_oncology", "head_neck"),
    TaxonomyTerm("throat cancer", "adult_oncology", "head_neck"),
    TaxonomyTerm("oral cancer", "adult_oncology", "head_neck"),
    TaxonomyTerm("HPV related cancer", "adult_oncology", "head_neck"),
    TaxonomyTerm("laryngeal cancer", "adult_oncology", "head_neck"),

    # === Esophageal & Stomach Cancer ===
    TaxonomyTerm("esophageal cancer", "adult_oncology", "gi"),
    TaxonomyTerm("stomach cancer", "adult_oncology", "gi"),
    TaxonomyTerm("gastric cancer", "adult_oncology", "gi"),
    TaxonomyTerm("GIST tumor", "adult_oncology", "gi"),

    # === Sarcomas ===
    TaxonomyTerm("sarcoma", "adult_oncology", "sarcoma"),
    TaxonomyTerm("soft tissue sarcoma", "adult_oncology", "sarcoma"),
    TaxonomyTerm("liposarcoma", "adult_oncology", "sarcoma"),
    TaxonomyTerm("leiomyosarcoma", "adult_oncology", "sarcoma"),
    TaxonomyTerm("osteosarcoma", "adult_oncology", "sarcoma"),

    # ============================================================================
    # ONCOLOGY TREATMENT
    # ============================================================================

    TaxonomyTerm("cancer treatment options", "treatment", "general"),
    TaxonomyTerm("chemotherapy", "treatment", "chemotherapy"),
    TaxonomyTerm("chemotherapy side effects", "treatment", "chemotherapy"),
    TaxonomyTerm("radiation therapy", "treatment", "radiation"),
    TaxonomyTerm("proton therapy", "treatment", "radiation"),
    TaxonomyTerm("immunotherapy", "treatment", "immunotherapy"),
    TaxonomyTerm("CAR-T cell therapy", "treatment", "immunotherapy"),
    TaxonomyTerm("checkpoint inhibitor", "treatment", "immunotherapy"),
    TaxonomyTerm("Keytruda", "treatment", "immunotherapy"),
    TaxonomyTerm("Opdivo", "treatment", "immunotherapy"),
    TaxonomyTerm("targeted therapy", "treatment", "targeted"),
    TaxonomyTerm("hormone therapy cancer", "treatment", "hormone"),
    TaxonomyTerm("bone marrow transplant", "treatment", "transplant"),
    TaxonomyTerm("stem cell transplant", "treatment", "transplant"),
    TaxonomyTerm("cancer surgery", "treatment", "surgery"),
    TaxonomyTerm("clinical trials cancer", "treatment", "clinical_trials"),
    TaxonomyTerm("cancer drug trials", "treatment", "clinical_trials"),
    TaxonomyTerm("precision medicine cancer", "treatment", "precision"),
    TaxonomyTerm("genetic testing cancer", "treatment", "precision"),

    # ============================================================================
    # RARE DISEASES - GENETIC/METABOLIC
    # ============================================================================

    # === Lysosomal Storage Disorders ===
    TaxonomyTerm("lysosomal storage disease", "rare_genetic", "lysosomal"),
    TaxonomyTerm("Gaucher disease", "rare_genetic", "lysosomal"),
    TaxonomyTerm("Fabry disease", "rare_genetic", "lysosomal"),
    TaxonomyTerm("Pompe disease", "rare_genetic", "lysosomal"),
    TaxonomyTerm("Niemann-Pick disease", "rare_genetic", "lysosomal"),
    TaxonomyTerm("Tay-Sachs disease", "rare_genetic", "lysosomal"),
    TaxonomyTerm("mucopolysaccharidosis", "rare_genetic", "lysosomal"),
    TaxonomyTerm("MPS Hunter syndrome", "rare_genetic", "lysosomal"),
    TaxonomyTerm("MPS Hurler syndrome", "rare_genetic", "lysosomal"),
    TaxonomyTerm("Krabbe disease", "rare_genetic", "lysosomal"),

    # === Neuromuscular Disorders ===
    TaxonomyTerm("muscular dystrophy", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("Duchenne muscular dystrophy", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("spinal muscular atrophy", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("SMA treatment", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("Zolgensma", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("amyotrophic lateral sclerosis", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("ALS treatment", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("Charcot-Marie-Tooth disease", "rare_genetic", "neuromuscular"),
    TaxonomyTerm("myasthenia gravis", "rare_genetic", "neuromuscular"),

    # === Blood Disorders ===
    TaxonomyTerm("sickle cell disease", "rare_genetic", "blood"),
    TaxonomyTerm("sickle cell treatment", "rare_genetic", "blood"),
    TaxonomyTerm("thalassemia", "rare_genetic", "blood"),
    TaxonomyTerm("hemophilia", "rare_genetic", "blood"),
    TaxonomyTerm("von Willebrand disease", "rare_genetic", "blood"),
    TaxonomyTerm("aplastic anemia", "rare_genetic", "blood"),
    TaxonomyTerm("Fanconi anemia", "rare_genetic", "blood"),
    TaxonomyTerm("polycythemia vera", "rare_genetic", "blood"),
    TaxonomyTerm("myelofibrosis", "rare_genetic", "blood"),

    # === Connective Tissue Disorders ===
    TaxonomyTerm("Ehlers-Danlos syndrome", "rare_genetic", "connective"),
    TaxonomyTerm("Marfan syndrome", "rare_genetic", "connective"),
    TaxonomyTerm("osteogenesis imperfecta", "rare_genetic", "connective"),
    TaxonomyTerm("brittle bone disease", "rare_genetic", "connective"),

    # === Chromosomal/Developmental ===
    TaxonomyTerm("Down syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("Turner syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("Klinefelter syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("Prader-Willi syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("Angelman syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("Williams syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("fragile X syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("22q11 deletion syndrome", "rare_genetic", "chromosomal"),
    TaxonomyTerm("DiGeorge syndrome", "rare_genetic", "chromosomal"),

    # ============================================================================
    # RARE DISEASES - NEUROLOGICAL
    # ============================================================================

    TaxonomyTerm("Huntington disease", "rare_neurological", "degenerative"),
    TaxonomyTerm("multiple sclerosis", "rare_neurological", "autoimmune"),
    TaxonomyTerm("MS treatment", "rare_neurological", "autoimmune"),
    TaxonomyTerm("Parkinson disease", "rare_neurological", "degenerative"),
    TaxonomyTerm("early onset Parkinson", "rare_neurological", "degenerative"),
    TaxonomyTerm("Rett syndrome", "rare_neurological", "developmental"),
    TaxonomyTerm("tuberous sclerosis", "rare_neurological", "developmental"),
    TaxonomyTerm("neurofibromatosis", "rare_neurological", "developmental"),
    TaxonomyTerm("NF1", "rare_neurological", "developmental"),
    TaxonomyTerm("NF2", "rare_neurological", "developmental"),
    TaxonomyTerm("ataxia telangiectasia", "rare_neurological", "ataxia"),
    TaxonomyTerm("Friedreich ataxia", "rare_neurological", "ataxia"),
    TaxonomyTerm("spinocerebellar ataxia", "rare_neurological", "ataxia"),
    TaxonomyTerm("Batten disease", "rare_neurological", "degenerative"),
    TaxonomyTerm("leukodystrophy", "rare_neurological", "degenerative"),
    TaxonomyTerm("adrenoleukodystrophy", "rare_neurological", "degenerative"),

    # ============================================================================
    # RARE DISEASES - AUTOIMMUNE/INFLAMMATORY
    # ============================================================================

    TaxonomyTerm("lupus", "rare_autoimmune", "systemic"),
    TaxonomyTerm("systemic lupus erythematosus", "rare_autoimmune", "systemic"),
    TaxonomyTerm("scleroderma", "rare_autoimmune", "systemic"),
    TaxonomyTerm("Sjogren syndrome", "rare_autoimmune", "systemic"),
    TaxonomyTerm("vasculitis", "rare_autoimmune", "vascular"),
    TaxonomyTerm("ANCA vasculitis", "rare_autoimmune", "vascular"),
    TaxonomyTerm("Behcet disease", "rare_autoimmune", "vascular"),
    TaxonomyTerm("Kawasaki disease", "rare_autoimmune", "vascular"),
    TaxonomyTerm("dermatomyositis", "rare_autoimmune", "myositis"),
    TaxonomyTerm("polymyositis", "rare_autoimmune", "myositis"),
    TaxonomyTerm("sarcoidosis", "rare_autoimmune", "granulomatous"),
    TaxonomyTerm("amyloidosis", "rare_autoimmune", "protein"),
    TaxonomyTerm("mastocytosis", "rare_autoimmune", "mast_cell"),

    # ============================================================================
    # RARE DISEASES - PULMONARY
    # ============================================================================

    TaxonomyTerm("cystic fibrosis", "rare_pulmonary", "genetic"),
    TaxonomyTerm("CF treatment", "rare_pulmonary", "genetic"),
    TaxonomyTerm("Trikafta", "rare_pulmonary", "genetic"),
    TaxonomyTerm("pulmonary arterial hypertension", "rare_pulmonary", "vascular"),
    TaxonomyTerm("PAH treatment", "rare_pulmonary", "vascular"),
    TaxonomyTerm("idiopathic pulmonary fibrosis", "rare_pulmonary", "fibrotic"),
    TaxonomyTerm("IPF treatment", "rare_pulmonary", "fibrotic"),
    TaxonomyTerm("alpha-1 antitrypsin deficiency", "rare_pulmonary", "genetic"),
    TaxonomyTerm("lymphangioleiomyomatosis", "rare_pulmonary", "rare"),
    TaxonomyTerm("LAM disease", "rare_pulmonary", "rare"),

    # ============================================================================
    # RARE DISEASES - METABOLIC
    # ============================================================================

    TaxonomyTerm("phenylketonuria", "rare_metabolic", "amino_acid"),
    TaxonomyTerm("PKU diet", "rare_metabolic", "amino_acid"),
    TaxonomyTerm("maple syrup urine disease", "rare_metabolic", "amino_acid"),
    TaxonomyTerm("homocystinuria", "rare_metabolic", "amino_acid"),
    TaxonomyTerm("glycogen storage disease", "rare_metabolic", "carbohydrate"),
    TaxonomyTerm("galactosemia", "rare_metabolic", "carbohydrate"),
    TaxonomyTerm("Wilson disease", "rare_metabolic", "metal"),
    TaxonomyTerm("hemochromatosis", "rare_metabolic", "metal"),
    TaxonomyTerm("porphyria", "rare_metabolic", "heme"),
    TaxonomyTerm("acute intermittent porphyria", "rare_metabolic", "heme"),

    # ============================================================================
    # RARE DISEASES - IMMUNODEFICIENCY
    # ============================================================================

    TaxonomyTerm("primary immunodeficiency", "rare_immune", "pid"),
    TaxonomyTerm("SCID", "rare_immune", "pid"),
    TaxonomyTerm("severe combined immunodeficiency", "rare_immune", "pid"),
    TaxonomyTerm("common variable immunodeficiency", "rare_immune", "pid"),
    TaxonomyTerm("CVID treatment", "rare_immune", "pid"),
    TaxonomyTerm("X-linked agammaglobulinemia", "rare_immune", "pid"),
    TaxonomyTerm("chronic granulomatous disease", "rare_immune", "pid"),
    TaxonomyTerm("hereditary angioedema", "rare_immune", "complement"),
    TaxonomyTerm("HAE treatment", "rare_immune", "complement"),

    # ============================================================================
    # RARE CANCERS
    # ============================================================================

    TaxonomyTerm("rare cancer", "rare_cancer", "general"),
    TaxonomyTerm("neuroendocrine tumor", "rare_cancer", "neuroendocrine"),
    TaxonomyTerm("NET cancer", "rare_cancer", "neuroendocrine"),
    TaxonomyTerm("carcinoid tumor", "rare_cancer", "neuroendocrine"),
    TaxonomyTerm("pheochromocytoma", "rare_cancer", "neuroendocrine"),
    TaxonomyTerm("paraganglioma", "rare_cancer", "neuroendocrine"),
    TaxonomyTerm("cholangiocarcinoma", "rare_cancer", "biliary"),
    TaxonomyTerm("bile duct cancer", "rare_cancer", "biliary"),
    TaxonomyTerm("mesothelioma", "rare_cancer", "mesothelial"),
    TaxonomyTerm("thymoma", "rare_cancer", "thymus"),
    TaxonomyTerm("thymic carcinoma", "rare_cancer", "thymus"),
    TaxonomyTerm("adrenocortical carcinoma", "rare_cancer", "adrenal"),
    TaxonomyTerm("appendix cancer", "rare_cancer", "appendix"),
    TaxonomyTerm("pseudomyxoma peritonei", "rare_cancer", "appendix"),
    TaxonomyTerm("desmoid tumor", "rare_cancer", "soft_tissue"),
    TaxonomyTerm("chordoma", "rare_cancer", "bone"),
    TaxonomyTerm("ocular melanoma", "rare_cancer", "eye"),
    TaxonomyTerm("uveal melanoma", "rare_cancer", "eye"),
    TaxonomyTerm("merkel cell carcinoma", "rare_cancer", "skin"),
    TaxonomyTerm("angiosarcoma", "rare_cancer", "vascular"),
    TaxonomyTerm("Kaposi sarcoma", "rare_cancer", "vascular"),

    # ============================================================================
    # SUPPORT & RESOURCES
    # ============================================================================

    TaxonomyTerm("cancer support groups", "support", "community"),
    TaxonomyTerm("rare disease support", "support", "community"),
    TaxonomyTerm("oncologist near me", "support", "facility"),
    TaxonomyTerm("cancer center", "support", "facility"),
    TaxonomyTerm("NCI designated cancer center", "support", "facility"),
    TaxonomyTerm("clinical trial finder", "support", "research"),
    TaxonomyTerm("cancer financial assistance", "support", "financial"),
    TaxonomyTerm("rare disease foundation", "support", "organization"),
    TaxonomyTerm("NORD rare disease", "support", "organization"),
    TaxonomyTerm("patient advocacy", "support", "advocacy"),
    TaxonomyTerm("genetic counseling", "support", "professional"),
    TaxonomyTerm("palliative care", "support", "care"),
    TaxonomyTerm("hospice care", "support", "care"),

    # ============================================================================
    # SURVIVORSHIP & QUALITY OF LIFE
    # ============================================================================

    TaxonomyTerm("cancer survivor", "survivorship", "general"),
    TaxonomyTerm("cancer survivorship", "survivorship", "general"),
    TaxonomyTerm("late effects cancer treatment", "survivorship", "late_effects"),
    TaxonomyTerm("cancer fatigue", "survivorship", "symptoms"),
    TaxonomyTerm("chemo brain", "survivorship", "cognitive"),
    TaxonomyTerm("cancer and fertility", "survivorship", "fertility"),
    TaxonomyTerm("cancer recurrence", "survivorship", "monitoring"),
    TaxonomyTerm("cancer remission", "survivorship", "monitoring"),
    TaxonomyTerm("second cancer", "survivorship", "late_effects"),
    TaxonomyTerm("cancer rehabilitation", "survivorship", "recovery"),
    TaxonomyTerm("oncology nutrition", "survivorship", "nutrition"),
    TaxonomyTerm("cancer and mental health", "survivorship", "mental_health"),
    TaxonomyTerm("cancer anxiety", "survivorship", "mental_health"),
]


def get_seed_terms() -> list[TaxonomyTerm]:
    """Return the seed taxonomy terms."""
    return SEED_TAXONOMY


def get_terms_by_category(category: str) -> list[TaxonomyTerm]:
    """Get all terms in a specific category."""
    return [t for t in SEED_TAXONOMY if t.category == category]


def get_categories() -> list[str]:
    """Get all unique categories."""
    return list(set(t.category for t in SEED_TAXONOMY))


# Category display names for UI
CATEGORY_DISPLAY_NAMES = {
    "pediatric_oncology": "Pediatric Oncology",
    "adult_oncology": "Adult Oncology",
    "treatment": "Cancer Treatment",
    "rare_genetic": "Rare Genetic Diseases",
    "rare_neurological": "Rare Neurological Diseases",
    "rare_autoimmune": "Rare Autoimmune Diseases",
    "rare_pulmonary": "Rare Pulmonary Diseases",
    "rare_metabolic": "Rare Metabolic Diseases",
    "rare_immune": "Rare Immune Disorders",
    "rare_cancer": "Rare Cancers",
    "support": "Support & Resources",
    "survivorship": "Survivorship",
}


# Expansion queries for discovering related terms via Google Trends
EXPANSION_QUERIES = [
    "cancer treatment",
    "oncology",
    "rare disease",
    "childhood cancer",
    "leukemia",
    "lymphoma",
    "breast cancer",
    "lung cancer",
    "immunotherapy",
    "clinical trials",
    "genetic disease",
    "autoimmune disease",
]
