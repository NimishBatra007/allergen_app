import streamlit as st
import pandas as pd
import re
import psycopg2

st.sidebar.header("Database Credentials")
DB_USERNAME = st.sidebar.text_input("DB Username")
DB_PASSWORD = st.sidebar.text_input("DB Password", type="password")
DB_HOST = st.sidebar.text_input("DB Host")
DB_NAME = st.sidebar.text_input("DB Name")


# ---------------- DB CONNECTION ----------------
def get_db_connection():
    return psycopg2.connect(
        dbname=DB_NAME,
        user=DB_USERNAME,
        password=DB_PASSWORD,
        host=DB_HOST,
        port="5432"
    )
if st.sidebar.button("Connect to Database"):
    try:
        conn = get_db_connection()
        conn.close()
        st.sidebar.success("✅ Connection Successful!")
    except Exception as e:
        st.sidebar.error(f"❌ Connection Failed: {str(e)}")

# ---------------- HELPERS ----------------
def fetch_material_info(material_nos):
    conn = get_db_connection()
    cursor = conn.cursor()
    ids_str = "', '".join(material_nos)
    query = f"""
        SELECT material_no, ingredients, allergen, allergen_may_contain, nutritional_information
        FROM public.allergen_info
        WHERE material_no IN ('{ids_str}');
    """
    cursor.execute(query)
    rows = cursor.fetchall()
    conn.close()
    columns = ["material_no", "ingredients", "allergen", "allergen_may_contain", "nutritional_information"]
    return pd.DataFrame(rows, columns=columns)


def parse_nutrition_string(text):
    """
    Parses nutrition string like:
    'Energy: 342 kcal, protein: 8.1g, carbohydrate: 73.8g, fat: 3.8g sodium 15mg'
    into a proper dictionary.
    """
    if not text or not isinstance(text, str):
        return {}

    nutrition = {}
    # Split on comma and space to get individual parts
    parts = re.split(r'[;,]', text)
    for part in parts:
        # Match things like: "Protein: 8.1g" or "fat 3.8g"
        match = re.match(r"\s*([\w\s\-]+?)[:\s]+([<\d\.]+)\s*([a-zA-Zμ%]*)", part.strip())
        if match:
            key, val, unit = match.groups()
            key = key.strip().capitalize()
            val = val.strip()
            nutrition[key] = f"{val} {unit}".strip()
    return nutrition


def parse_fields(df):
    def to_list(x):
        if pd.isna(x) or not x:
            return []
        # split by comma or 'and'
        return [i.strip().lower() for i in re.split(r',| and ', str(x)) if i.strip()]

    df['ingredients'] = df.get('ingredients', '').apply(to_list)
    df['allergen'] = df.get('allergen', '').apply(to_list)
    df['allergen_may_contain'] = df.get('allergen_may_contain', '').apply(to_list)
    df['nutritional_information'] = df['nutritional_information'].apply(parse_nutrition_string)
    return df


def calculate_nutrition(df, weights=None):
    total = {}
    units = {}

    for _, row in df.iterrows():
        nutrition = row['nutritional_information']  # or 'nutritional_information'
        material_no = row['material_no']
        weight = weights.get(material_no, 100) if weights else 100

        for k, v in nutrition.items():
            # Extract numeric value and unit
            match = re.match(r"([<\d\.]+)\s*([a-zA-Zμ%]*)", str(v).strip())
            if not match:
                continue
            val_str, unit = match.groups()
            try:
                val = float(val_str.replace("<", "").strip())
            except:
                val = 0.0

            scaled_val = val * (weight / 100.0)
            total[k] = total.get(k, 0.0) + scaled_val
            units[k] = unit or ("kcal" if "Energy" in k else "g")

    return {k: f"{v:.2f} {units[k]}" for k, v in total.items()}


# ---------------- STREAMLIT UI ----------------
st.set_page_config(
    page_title="🍃 Food Analyzer Pro",
    layout="wide",
    initial_sidebar_state="collapsed"
)

# Modern CSS with enhanced drag-drop functionality
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Poppins:wght@300;400;500;600;700&display=swap');

    /* Reset and base styles */
    * {
        margin: 0;
        padding: 0;
        box-sizing: border-box;
    }

    .stApp {
        font-family: 'Poppins', sans-serif;
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        min-height: 100vh;
        overflow-x: hidden;
    }

    /* Animated background elements */
    .bg-animation {
        position: fixed;
        top: 0;
        left: 0;
        width: 100%;
        height: 100%;
        z-index: -1;
        overflow: hidden;
    }

    .bg-circle {
        position: absolute;
        border-radius: 50%;
        opacity: 0.1;
        animation: float 6s ease-in-out infinite;
    }

    .bg-circle:nth-child(1) {
        width: 200px;
        height: 200px;
        background: linear-gradient(45deg, #667eea, #764ba2);
        top: 10%;
        left: 10%;
        animation-delay: 0s;
    }

    .bg-circle:nth-child(2) {
        width: 150px;
        height: 150px;
        background: linear-gradient(45deg, #f093fb, #f5576c);
        top: 20%;
        right: 20%;
        animation-delay: 2s;
    }

    .bg-circle:nth-child(3) {
        width: 100px;
        height: 100px;
        background: linear-gradient(45deg, #4facfe, #00f2fe);
        bottom: 20%;
        left: 20%;
        animation-delay: 4s;
    }

    .bg-circle:nth-child(4) {
        width: 120px;
        height: 120px;
        background: linear-gradient(45deg, #43e97b, #38f9d7);
        bottom: 10%;
        right: 10%;
        animation-delay: 1s;
    }

    /* Main container */
    .main-wrapper {
        max-width: 1200px;
        padding-top: 0.5rem;
        margin: 0 auto;
        position: relative;
        z-index: 1;
    }

    /* Header section */
    .header-container {
        text-align: center;
        margin-bottom: 1rem;
        animation: slideInDown 0.8s ease-out;
    }

    .main-title {
        font-size: clamp(2.5rem, 5vw, 4rem);
        font-weight: 700;
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin-bottom: 1rem;
        position: relative;
        animation: titleGlow 2s ease-in-out infinite alternate;
    }

    .subtitle {
        font-size: 1.2rem;
        color: #6b7280;
        font-weight: 400;
        margin-bottom: 2rem;
        animation: fadeInUp 1s ease-out 0.3s both;
    }

    /* Get Started section */
.get-started-section {
    background: rgba(255, 255, 255, 0.9);
    backdrop-filter: blur(10px);
    border-radius: 20px;
    margin: 0.5rem auto 0.5rem auto;
    padding: 1rem 1rem;
    border: 2px solid rgba(255, 255, 255, 0.3);
    box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
    text-align: center;
    animation: slideInUp 0.8s ease-out 0.7s both;
}

    .get-started-title {
        font-size: 2rem;
        font-weight: 600;
        color: #374151;
        margin-top: 1rem;
    }

    .get-started-description {
        font-size: 1.1rem;
        color: #6b7280;
        margin-bottom: 2rem;
        line-height: 1.6;
    }

    .features-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        gap: 2rem;
        margin-top: 2rem;
    }

    .feature-item {
        padding: 1.5rem;
        border-radius: 12px;
        background: rgba(248, 250, 252, 0.8);
        border: 1px solid rgba(226, 232, 240, 0.5);
        transition: all 0.3s ease;
    }

    .feature-item:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
    }

    .feature-icon {
        font-size: 2.5rem;
        margin-bottom: 1rem;
        animation: bounce 2s infinite;
    }

    .feature-title {
        font-size: 1rem;
        font-weight: 500;
        color: #374151;
    }

    /* Upload section - enhanced with drag-drop */
    .upload-container {
        background: rgba(255, 255, 255, 0.9);
        backdrop-filter: blur(10px);
        border-radius: 20px;
        border: 2px dashed rgba(102, 126, 234, 0.3);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.1);
        text-align: center;
        position: relative;
        overflow: hidden;
        animation: slideInUp 0.8s ease-out 0.5s both;
        transition: all 0.3s ease;
        cursor: pointer;
        display: flex;
        flex-direction: column;
        justify-content: center;
        align-items: center;
        .upload-container {
        margin-top: 1rem;
        margin-bottom: 1.5rem;
        padding: 2rem 2rem;
        min-height: 220px;
}
    }

    .upload-container:hover {
        transform: translateY(-5px);
        box-shadow: 0 25px 50px rgba(0, 0, 0, 0.15);
        border-color: rgba(102, 126, 234, 0.5);
        background: rgba(240, 242, 255, 0.9);
    }

    .upload-container.drag-over {
        border-color: #667eea;
        background: rgba(230, 235, 255, 0.95);
        transform: scale(1.02);
    }

    .upload-container::before {
        content: '';
        position: absolute;
        top: -50%;
        left: -50%;
        width: 200%;
        height: 200%;
        background: linear-gradient(45deg, transparent, rgba(102, 126, 234, 0.1), transparent);
        animation: shimmer 3s infinite;
        pointer-events: none;
    }

    .upload-icon {
        font-size: 4rem;
        margin-bottom: 1rem;
        animation: bounce 2s infinite;
        color: #667eea;
    }

    .upload-title {
        font-size: 1.5rem;
        font-weight: 600;
        color: #374151;
        margin-bottom: 0.5rem;
    }

    .upload-description {
        color: #6b7280;
        font-size: 1rem;
        margin-bottom: 1rem;
        line-height: 1.6;
    }

    .upload-hint {
        color: #9ca3af;
        font-size: 0.9rem;
        font-style: italic;
    }

    /* Results grid */
    .results-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
        gap: 2rem;
        margin: 2rem 0;
    }

    .result-card {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        position: relative;
        overflow: hidden;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1);
        animation: slideInUp 0.6s ease-out;
    }

    .result-card:hover {
        transform: translateY(-8px);
        box-shadow: 0 20px 40px rgba(0, 0, 0, 0.15);
    }

    .result-card::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 4px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        animation: slideInLeft 0.8s ease-out;
    }

    .card-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        font-size: 1.25rem;
        font-weight: 600;
        color: #374151;
    }

    .card-icon {
        font-size: 1.5rem;
    }

    .card-content {
        color: #6b7280;
        font-size: 0.95rem;
        line-height: 1.6;
        background: rgba(248, 250, 252, 0.8);
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid rgba(226, 232, 240, 0.5);
        min-height: 60px;
        display: flex;
        align-items: center;
        transition: all 0.3s ease;
    }

    .card-content:hover {
        background: rgba(241, 245, 249, 0.9);
    }

    /* Ingredients card */
    .ingredients-card::before {
        background: linear-gradient(90deg, #10b981, #34d399);
    }

    .ingredients-card .card-icon {
        color: #10b981;
    }

    /* Allergens card */
    .allergens-card::before {
        background: linear-gradient(90deg, #f59e0b, #fbbf24);
    }

    .allergens-card .card-icon {
        color: #f59e0b;
    }

    /* May contain card */
    .may-contain-card::before {
        background: linear-gradient(90deg, #ef4444, #f87171);
    }

    .may-contain-card .card-icon {
        color: #ef4444;
    }

    /* Nutrition section */
    .nutrition-section {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        animation: slideInUp 0.6s ease-out 0.8s both;
    }

    .nutrition-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 2rem;
        font-size: 1.5rem;
        font-weight: 600;
        color: #374151;
    }

    .nutrition-grid {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 1rem;
    }

    .nutrition-item {
        background: linear-gradient(135deg, #f8fafc 0%, #f1f5f9 100%);
        border-radius: 12px;
        padding: 1.5rem;
        text-align: center;
        border: 1px solid rgba(226, 232, 240, 0.5);
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }

    .nutrition-item:hover {
        transform: translateY(-3px);
        box-shadow: 0 10px 25px rgba(0, 0, 0, 0.1);
        background: linear-gradient(135deg, #f1f5f9 0%, #e2e8f0 100%);
    }

    .nutrition-item::before {
        content: '';
        position: absolute;
        top: 0;
        left: 0;
        width: 100%;
        height: 3px;
        background: linear-gradient(90deg, #667eea, #764ba2);
        transform: scaleX(0);
        transition: transform 0.3s ease;
    }

    .nutrition-item:hover::before {
        transform: scaleX(1);
    }

    .nutrition-label {
        font-size: 0.9rem;
        font-weight: 500;
        color: #6b7280;
        margin-bottom: 0.5rem;
    }

    .nutrition-value {
        font-size: 1.2rem;
        font-weight: 600;
        color: #374151;
    }

    /* Data table styling */
    .data-table-container {
        background: rgba(255, 255, 255, 0.95);
        backdrop-filter: blur(10px);
        border-radius: 16px;
        padding: 2rem;
        margin: 2rem 0;
        border: 1px solid rgba(255, 255, 255, 0.3);
        box-shadow: 0 10px 30px rgba(0, 0, 0, 0.1);
        animation: slideInUp 0.6s ease-out 0.6s both;
    }

    .table-header {
        display: flex;
        align-items: center;
        gap: 0.75rem;
        margin-bottom: 1.5rem;
        font-size: 1.25rem;
        font-weight: 600;
        color: #374151;
    }

    /* File uploader styling - hide default and use custom */
    .stFileUploader > label {
    display: none !important;
}

    .stFileUploader > div {
        border: none;
        padding: 0;
        background: transparent;
    }

    /* Loading animations */
    .loading-spinner {
        display: inline-block;
        width: 20px;
        height: 20px;
        border: 3px solid #f3f4f6;
        border-radius: 50%;
        border-top-color: #667eea;
        animation: spin 1s ease-in-out infinite;
        margin-right: 0.5rem;
    }

    /* Hide streamlit elements */
    .stDeployButton, #MainMenu, footer {
        display: none !important;
    }

    /* Keyframe animations */
    @keyframes float {
        0%, 100% {
            transform: translateY(0px) rotate(0deg);
        }
        50% {
            transform: translateY(-20px) rotate(180deg);
        }
    }

    @keyframes slideInDown {
        from {
            opacity: 0;
            transform: translateY(-30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInUp {
        from {
            opacity: 0;
            transform: translateY(30px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes slideInLeft {
        from {
            opacity: 0;
            transform: translateX(-30px);
        }
        to {
            opacity: 1;
            transform: translateX(0);
        }
    }

    @keyframes fadeInUp {
        from {
            opacity: 0;
            transform: translateY(20px);
        }
        to {
            opacity: 1;
            transform: translateY(0);
        }
    }

    @keyframes titleGlow {
        from {
            filter: drop-shadow(0 0 10px rgba(102, 126, 234, 0.3));
        }
        to {
            filter: drop-shadow(0 0 20px rgba(102, 126, 234, 0.5));
        }
    }

    @keyframes shimmer {
        0% {
            transform: translateX(-100%) translateY(-100%) rotate(45deg);
        }
        100% {
            transform: translateX(100%) translateY(100%) rotate(45deg);
        }
    }

    @keyframes bounce {
        0%, 20%, 50%, 80%, 100% {
            transform: translateY(0);
        }
        40% {
            transform: translateY(-10px);
        }
        60% {
            transform: translateY(-5px);
        }
    }

    @keyframes rotate {
        0% {
            transform: rotate(0deg);
        }
        100% {
            transform: rotate(360deg);
        }
    }

    @keyframes spin {
        0% {
            transform: rotate(0deg);
        }
        100% {
            transform: rotate(360deg);
        }
    }

    /* Responsive design */
    @media (max-width: 768px) {
        .main-wrapper {
            padding: 1rem;
        }

        .upload-container {
            padding: 2rem;
        }

        .results-grid {
            grid-template-columns: 1fr;
        }

        .nutrition-grid {
            grid-template-columns: repeat(auto-fit, minmax(150px, 1fr));
        }
    }
</style>
""", unsafe_allow_html=True)

# Enhanced JavaScript for drag and drop functionality
st.markdown("""
<script>
document.addEventListener('DOMContentLoaded', function() {
    const uploadContainer = document.querySelector('.upload-container');
    const fileInput = document.querySelector('.stFileUploader input[type="file"]');


    if (uploadContainer && fileInput) {
        // Click to upload
        uploadContainer.addEventListener('click', function(e) {
            if (e.target === uploadContainer || uploadContainer.contains(e.target)) {
                fileInput.click();
            }
        });

        // Drag and drop events
        uploadContainer.addEventListener('dragover', function(e) {
            e.preventDefault();
            uploadContainer.classList.add('drag-over');
        });

        uploadContainer.addEventListener('dragleave', function(e) {
            e.preventDefault();
            uploadContainer.classList.remove('drag-over');
        });

        uploadContainer.addEventListener('drop', function(e) {
            e.preventDefault();
            uploadContainer.classList.remove('drag-over');

            const files = e.dataTransfer.files;
            if (files.length > 0) {
                fileInput.files = files;
                fileInput.dispatchEvent(new Event('change', { bubbles: true }));
            }
        });
    }
});
</script>
""", unsafe_allow_html=True)

# Animated background
st.markdown("""
<div class="bg-animation">
    <div class="bg-circle"></div>
    <div class="bg-circle"></div>
    <div class="bg-circle"></div>
    <div class="bg-circle"></div>
</div>
""", unsafe_allow_html=True)

# Main wrapper
st.markdown('<div class="main-wrapper">', unsafe_allow_html=True)

# Header
st.markdown("""
<style>
.header-container {
    position: relative;
    top: auto;
    left: auto;
    width: auto;
    background: transparent;
    color: #374151;
    padding: 0;
    z-index: auto;
    box-shadow: none;
    display: block;
    text-align: center;
    height: auto;
    margin-bottom: 1rem;
}

.main-title {
    font-size: clamp(2.5rem, 5vw, 4rem);
    font-weight: 700;
    margin: 0 auto;
    color: #374151;
    -webkit-text-fill-color: unset !important;
    -webkit-background-clip: unset !important;
    background-clip: unset !important;
    -webkit-text-stroke: none !important;
    animation: none !important;
    white-space: normal;
    overflow: visible;
    text-overflow: unset;
}

.subtitle {
    display: none;
}

.main-wrapper {
    padding-top: 2px;
}
</style>
<div class="header-container">
    <h1 class="main-title" title="Food Analyzer Pro">🍃 Food Analyzer Pro</h1>
</div>
""", unsafe_allow_html=True)

# Get Started section
st.html("""
<div class="get-started-section">
    <h2 class="get-started-title">🚀 Get Started</h2>
    <p class="get-started-description">
        Upload your food data file to begin comprehensive analysis of ingredients, allergens, and nutritional content.
        Our advanced system will process your data and provide detailed insights.
    </p>

    <div class="features-grid">
        <div class="feature-item">
            <div class="feature-icon">🥗</div>
            <div class="feature-title">Ingredient Analysis</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">⚠️</div>
            <div class="feature-title">Allergen Detection</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">📊</div>
            <div class="feature-title">Nutrition Facts</div>
        </div>
        <div class="feature-item">
            <div class="feature-icon">📈</div>
            <div class="feature-title">Data Insights</div>
        </div>
    </div>
</div>
""")

uploaded_file = st.file_uploader("📎 Upload CSV or Excel", type=["csv", "xlsx"])


if uploaded_file:
    try:
        # Processing indicator
        with st.spinner('🔄 Processing your data...'):
            if uploaded_file.name.endswith(".csv"):
                df_input = pd.read_csv(uploaded_file)
            else:
                df_input = pd.read_excel(uploaded_file)

        if "material_no" not in df_input.columns:
            st.error("❌ The file must contain a 'material_no' column.")
        else:
            material_nos = df_input["material_no"].astype(str).tolist()
            weights = dict(
                zip(df_input["material_no"].astype(str), df_input.get("weight", pd.Series([100] * len(df_input)))))

            # Fetch and process data
            with st.spinner('📊 Analyzing material information...'):
                df_raw = fetch_material_info(material_nos)
                df_parsed = parse_fields(df_raw)

            # Display raw data
            st.markdown("""
            <div class="data-table-container">
                <div class="table-header">
                    <span>📋</span>
                    <span>Material Data Overview</span>
                </div>
            </div>
            """, unsafe_allow_html=True)

            if not df_raw.empty:
                st.dataframe(df_raw, use_container_width=True)
            else:
                st.warning("No data found for the provided material numbers.")

            # Process results if data exists
            if not df_parsed.empty:
                all_ingredients = sorted(set(i for lst in df_parsed['ingredients'] for i in lst if i))
                all_allergens = sorted(set(a for lst in df_parsed['allergen'] for a in lst if a))
                may_contain = sorted(set(a for lst in df_parsed['allergen_may_contain'] for a in lst if a))
                nutrition = calculate_nutrition(df_parsed, weights)

                # Results grid
                st.markdown('<div class="results-grid">', unsafe_allow_html=True)

                # Ingredients card
                ingredients_text = ", ".join(all_ingredients) if all_ingredients else "No ingredients detected"
                st.markdown(f"""
                <div class="result-card ingredients-card">
                    <div class="card-header">
                        <span class="card-icon">🥕</span>
                        <span>Unique Ingredients</span>
                    </div>
                    <div class="card-content">
                        {ingredients_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # Allergens card
                allergens_text = ", ".join(all_allergens) if all_allergens else "No allergens detected"
                st.markdown(f"""
                <div class="result-card allergens-card">
                    <div class="card-header">
                        <span class="card-icon">⚠️</span>
                        <span>Allergens</span>
                    </div>
                    <div class="card-content">
                        {allergens_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                # May contain card
                may_contain_text = ", ".join(may_contain) if may_contain else "No additional allergens listed"
                st.markdown(f"""
                <div class="result-card may-contain-card">
                    <div class="card-header">
                        <span class="card-icon">❗</span>
                        <span>May Contain</span>
                    </div>
                    <div class="card-content">
                        {may_contain_text}
                    </div>
                </div>
                """, unsafe_allow_html=True)

                st.markdown('</div>', unsafe_allow_html=True)  # Close results grid

                # Nutrition section
                if nutrition:
                    st.markdown("""
                    <div class="nutrition-section">
                        <div class="nutrition-header">
                            <span>📊</span>
                            <span>Nutritional Information</span>
                        </div>
                        <div class="nutrition-grid">
                    """, unsafe_allow_html=True)

                    for key, value in nutrition.items():
                        st.markdown(f"""
                        <div class="nutrition-item">
                            <div class="nutrition-label">{key}</div>
                            <div class="nutrition-value">{value}</div>
                        </div>
                        """, unsafe_allow_html=True)

                    st.markdown('</div></div>', unsafe_allow_html=True)  # Close nutrition section

    except Exception as e:
        st.error(f"❌ Error processing file: {str(e)}")
        st.markdown("""
        <div class="upload-container">
            <h3>💡 File Format Requirements</h3>
            <ul style="text-align: left; margin-top: 1rem;">
                <li>File must contain a 'material_no' column</li>
                <li>Optionally include a 'weight' column for weighted calculations</li>
                <li>Supported formats: CSV (.csv) and Excel (.xlsx)</li>
                <li>Ensure data is properly formatted without extra spaces</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
else:
    # Welcome section
    # Removed to avoid duplicate Get Started tab

    st.markdown('</div>', unsafe_allow_html=True)  # Close main wrapper
