import re
import PyPDF2
from docx import Document as DocxDocument
from nltk.corpus import stopwords
from nltk.tokenize import word_tokenize
from nltk.stem import WordNetLemmatizer
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

# For more advanced sentence similarity (recommended)
try:
    from sentence_transformers import SentenceTransformer, util
    # Load a pre-trained model for sentence embeddings.
    # 'all-MiniLM-L6-v2' is small, fast, and good for general purpose.
    # It will be downloaded automatically the first time it's used if not cached.
    sentence_model = SentenceTransformer('all-MiniLM-L6-v2')
    print("SentenceTransformer model loaded successfully.")
except ImportError:
    print("SentenceTransformer library not found. TF-IDF will be used as a fallback.")
    sentence_model = None
except Exception as e:
    print(f"Warning: Could not load SentenceTransformer model. TF-IDF will be used as a fallback. Error: {e}")
    sentence_model = None


def extract_text_from_pdf(pdf_path):
    """Extracts text from a PDF file."""
    text = ""
    try:
        with open(pdf_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            for page_num in range(len(reader.pages)):
                page = reader.pages[page_num]
                text += page.extract_text() or "" # Add or "" to handle None return
    except FileNotFoundError:
        print(f"Error: PDF file not found at {pdf_path}")
    except Exception as e:
        print(f"Error reading PDF {pdf_path}: {e}")
    return text

def extract_text_from_docx(docx_path):
    """Extracts text from a DOCX file."""
    text = ""
    try:
        doc = DocxDocument(docx_path)
        for para in doc.paragraphs:
            text += para.text + "\n"
    except FileNotFoundError:
        print(f"Error: DOCX file not found at {docx_path}")
    except Exception as e:
        print(f"Error reading DOCX {docx_path}: {e}")
    return text

def get_text_from_file(file_path):
    """
    Extracts text from a file based on its extension (.pdf or .docx).
    Returns empty string if file type is unsupported or error occurs.
    """
    if not file_path:
        return ""
    
    file_path_lower = file_path.lower()
    if file_path_lower.endswith('.pdf'):
        return extract_text_from_pdf(file_path)
    elif file_path_lower.endswith('.docx'):
        return extract_text_from_docx(file_path)
    # Add more file types if needed (e.g., .doc, .txt)
    # elif file_path_lower.endswith('.txt'):
    #     try:
    #         with open(file_path, 'r', encoding='utf-8') as f:
    #             return f.read()
    #     except Exception as e:
    #         print(f"Error reading TXT {file_path}: {e}")
    #         return ""
    else:
        print(f"Unsupported file type for text extraction: {file_path}")
        return ""

def preprocess_text_for_tfidf(text):
    """Basic text preprocessing for TF-IDF: lowercasing, removing non-alphanumeric, tokenizing, removing stopwords, lemmatizing."""
    if not text:
        return ""
    text = text.lower()
    text = re.sub(r'\W+', ' ', text)  # Replace non-alphanumeric characters (and underscore) with space
    text = re.sub(r'\s+', ' ', text).strip() # Replace multiple spaces with single space and strip leading/trailing
    
    tokens = word_tokenize(text)
    stop_words = set(stopwords.words('english'))
    lemmatizer = WordNetLemmatizer()
    
    # Lemmatize and remove stopwords and short tokens
    filtered_tokens = [
        lemmatizer.lemmatize(w) for w in tokens if w not in stop_words and len(w) > 2
    ]
    return " ".join(filtered_tokens)

def calculate_similarity_tfidf(text1, text2):
    """Calculates cosine similarity between two texts using TF-IDF."""
    if not text1 or not text2:
        print("TF-IDF: One or both texts are empty.")
        return 0.0
    
    processed_text1 = preprocess_text_for_tfidf(text1)
    processed_text2 = preprocess_text_for_tfidf(text2)

    if not processed_text1 or not processed_text2: # If preprocessing results in empty strings
        print("TF-IDF: One or both texts became empty after preprocessing.")
        return 0.0

    vectorizer = TfidfVectorizer()
    try:
        # Create a TF-IDF matrix
        tfidf_matrix = vectorizer.fit_transform([processed_text1, processed_text2])
        # Calculate cosine similarity between the two text vectors
        # tfidf_matrix[0:1] is the vector for text1, tfidf_matrix[1:2] is for text2
        similarity = cosine_similarity(tfidf_matrix[0:1], tfidf_matrix[1:2])[0][0]
        return max(0.0, min(similarity * 100, 100.0)) # As a percentage, clamped 0-100
    except ValueError as e: # Can happen if vocabulary is empty after stopword removal etc.
        print(f"TF-IDF ValueError (likely empty vocabulary): {e}")
        return 0.0

def calculate_similarity_sentence_transformer(text1, text2):
    """Calculates cosine similarity using SentenceTransformer embeddings."""
    if not sentence_model:
        print("SentenceTransformer: Model not loaded.")
        return 0.0 # Or raise an error
    if not text1 or not text2:
        print("SentenceTransformer: One or both texts are empty.")
        return 0.0

    try:
        # Sentence Transformers generally work well without extensive preprocessing like stopword removal or lemmatization.
        # Basic cleaning like removing excessive whitespace might still be beneficial.
        text1_cleaned = re.sub(r'\s+', ' ', text1.strip())
        text2_cleaned = re.sub(r'\s+', ' ', text2.strip())

        if not text1_cleaned or not text2_cleaned:
            print("SentenceTransformer: One or both texts became empty after basic cleaning.")
            return 0.0

        # Generate embeddings for both texts
        embedding1 = sentence_model.encode(text1_cleaned, convert_to_tensor=True)
        embedding2 = sentence_model.encode(text2_cleaned, convert_to_tensor=True)
        
        # Compute cosine-similarity
        cosine_scores = util.pytorch_cos_sim(embedding1, embedding2)
        similarity = cosine_scores.item() # Get the single similarity score
        return max(0.0, min(similarity * 100, 100.0)) # As a percentage, clamped 0-100
    except Exception as e:
        print(f"Error with SentenceTransformer similarity calculation: {e}")
        return 0.0


def get_jd_resume_match_score(job_description_text, resume_file_path):
    """
    Calculates the match score between a job description and a resume file.
    Prefers SentenceTransformer if available, otherwise falls back to TF-IDF.
    """
    if not job_description_text:
        print("Match Score: Job description text is empty.")
        return 0.0
    if not resume_file_path:
        print("Match Score: Resume file path is empty.")
        return 0.0

    print(f"Attempting to extract text from resume: {resume_file_path}")
    resume_text = get_text_from_file(resume_file_path)
    if not resume_text:
        print(f"Match Score: Could not extract text from resume: {resume_file_path}")
        return 0.0
    
    print(f"Successfully extracted resume text (length: {len(resume_text)}).")
    print(f"Job description text length: {len(job_description_text)}.")

    if sentence_model:
        print("Calculating similarity using Sentence Transformer.")
        score = calculate_similarity_sentence_transformer(job_description_text, resume_text)
    else:
        print("Sentence Transformer model not available. Calculating similarity using TF-IDF.")
        score = calculate_similarity_tfidf(job_description_text, resume_text)
    
    print(f"Calculated raw score: {score}")
    return score