import streamlit as st
import torch
from nltk.tokenize import word_tokenize
from torch.nn import functional as F
import json
from fasttext_cnn import CNN_NLP
import gdown
from py3langid.langid import LanguageIdentifier, MODEL_FILE
import nltk

nltk.download('punkt')

cache = {
    "models": {},
    "word2idx": {}
}

drive_dict = {"ca": "1l4XB4PYsaMTX6w0uWcu4hX1EV9ovfB2U",
              "en": "1EvsBkfiA0mZTA75XPFlMu9GifMvrR8Nq",
              "es": "1dUW-9DknLwZhNH57X6A4166qRlzNFHz8",
              "eu" : "1Sdvay2OV2zsZ3m0GudwC5nLkivekTcsc", 
              "gl" : "1p41UWR43Je-Bgxw-QP-J_5ZzafZS5NHZ",
              "pt": "1r411nMfeL0Njpjhj2LL6RtWAv0903XA3"}

# Cargar modelos y word2idx desde archivos (reemplaza las rutas con las correctas)
def load_model_and_word2idx(language):
    if language in cache["models"] and language in cache["word2idx"]:
        return cache["models"][language], cache["word2idx"][language]
    
    url = f'https://drive.google.com/uc?id={drive_dict[language]}'
    output = f'modelo_{language}.pkl'
    gdown.download(url, output, quiet=False)

    model = torch.load(f'modelo_{language}.pkl', map_location=torch.device('cpu'))
    word2idx_path = f'word2idx/word2idx_{language}.json'

    with open(word2idx_path, 'r') as f:
        word2idx = json.load(f)

    cache["models"][language] = model
    cache["word2idx"][language] = word2idx

    return model, word2idx

# Prediction function
def predict(text, model, word2idx):
    """Predict probability that a review is AI generated."""
    max_len = 62

    # Tokenize, pad and encode text
    tokens = word_tokenize(text.lower())
    padded_tokens = tokens + ['<pad>'] * (max_len - len(tokens))
    input_id = [word2idx.get(token, word2idx['<unk>']) for token in padded_tokens]

    # Convert to PyTorch tensors
    input_id = torch.tensor(input_id).unsqueeze(dim=0)

    # Compute logits
    logits = model.forward(input_id)

    # Compute probability
    probs = F.softmax(logits, dim=1).squeeze(dim=0)

    return probs[1] * 100

# Language detection function
def detect_language(text):
    identifier = LanguageIdentifier.from_pickled_model(MODEL_FILE)
    identifier.set_languages(['en', 'es', 'pt', 'gl', 'eu', 'ca'])

    return identifier.classify(text)[0]

#  st.warning("Due to limited resources, the prediction may take some time (5s +-).")

def display_home():
    st.title("Detect AI Content")

    text = st.text_area("Enter your text:", height=200)

    col1, col2 = st.columns([1, 3])
    with col1:
        detect_button = st.button("Detect AI Content")
    with col2:
        st.markdown(
            """
            <style>
            .custom-checkbox {
                margin-top: -20px; /* Ajusta este valor según sea necesario */
                margin-left: -20px;
            }
            </style>
            """, 
            unsafe_allow_html=True
        )
        # Aplicar la clase custom-checkbox al checkbox
        show_details = st.checkbox("More details", key="show_details")

        # Aplicar el estilo al checkbox
        st.markdown(
            """
            <style>
            div[data-testid="stHorizontalBlock"] > div:nth-child(2) > div {
                margin-top: -10px; /* Ajusta este valor según sea necesario */
                margin-left: -20px;
            }
            </style>
            """,
            unsafe_allow_html=True
        )
    
    if detect_button:
        # Reset the state when the detect button is clicked
        st.session_state.predictions = []
        st.session_state.ai_content_percentage = None
        st.session_state.show_info = False

        if text and len(text) > 250:
            detected_language = detect_language(text)
            model, word2idx = load_model_and_word2idx(detected_language)
            
            paragraphs = text.split('\n\n')
            total_paragraphs = 0
            ai_paragraph_count = 0  # Contador para los párrafos generados por IA

            for paragraph in paragraphs:
                if paragraph.strip() != "":
                    total_paragraphs += 1
                    ai_probability = predict(paragraph, model, word2idx)
                    st.session_state.predictions.append((paragraph, ai_probability))
                    if ai_probability > 99:
                        ai_paragraph_count += 1  # Incrementar el contador si el párrafo fue generado por IA
            
            # Calcular el porcentaje de párrafos generados por IA
            ai_content_percentage = (ai_paragraph_count / total_paragraphs) * 100
            st.session_state.ai_content_percentage = ai_content_percentage
            st.session_state.show_info = True
        else:
            error_message = "Please enter text with more than 250 characters before detecting AI content." if not text else "Text must be longer than 250 characters."
            st.error(error_message)
    
    if st.session_state.get('show_info', False):
        st.markdown("<div style='text-align: center;'>AI-generated paragraphs are highlighted in <span style='color: red; font-weight: bold;'>red</span>, human-generated paragraphs are in <span style='color: green; font-weight: bold;'>green</span>.</div>", unsafe_allow_html=True)

    if "predictions" in st.session_state:
        for paragraph, ai_probability in st.session_state.predictions:
            if st.session_state.show_details:
                probability_text = f"<b>Probability: {int(ai_probability)}%</b>"
            else:
                probability_text = ""

            if ai_probability > 99:
                st.markdown(
                    f"<div style='display: flex; align-items: center;'>"
                    f"<div style='background-color: rgba(255, 0, 0, 0.05); color: red; padding: 8px; border-radius: 5px; flex: 1;'>{paragraph}</div>"
                    f"<div style='color: red; margin-left: 10px;'>{probability_text}</div>"
                    f"</div>", unsafe_allow_html=True
                )
            else:
                st.markdown(
                    f"<div style='display: flex; align-items: center;'>"
                    f"<div style='background-color: rgba(0, 255, 0, 0.05); color: green; padding: 8px; border-radius: 5px; flex: 1;'>{paragraph}</div>"
                    f"<div style='color: green; margin-left: 10px;'>{probability_text}</div>"
                    f"</div>", unsafe_allow_html=True
                )

    if "ai_content_percentage" in st.session_state and st.session_state.ai_content_percentage is not None:
        st.markdown(f"<div style='text-align: center; padding: 20px;'>AI content percentage: {st.session_state.ai_content_percentage:.2f}%</div>", unsafe_allow_html=True)

def display_problem():
    st.title("About the Problem")
    st.write("""
    <p style='text-align: justify;'>Detection of automatically generated text is a crucial challenge in the field of <b>Artificial Intelligence</b> and <b>Natural Language Processing (NLP)</b>. With the advent of large-scale language models (LLMs), such as GPT-3.5, GPT-4, LLaMA, Mistral, Cohere, among others, automated text generation has become more accessible and sophisticated than ever before.</p>

    <p style='text-align: justify;'>The sophistication of the models has made it increasingly difficult to distinguish AI-generated text from human-generated text. Precisely, in the framework of <b><a href='https://sites.google.com/view/iberautextification'>IberAuTexTification</a></b>, we face the challenge of identifying texts that have been automatically generated by these powerful language models. This includes texts in a variety of languages such as <b>Spanish, Catalan, Basque, Galician, Portuguese, and English (in Gibraltar)</b>, as well as in different domains such as news, reviews, emails, essays, dialogues, Wikipedia, among others.</p>
    """, unsafe_allow_html=True)

    st.write("<br style='line-height:10px;'>", unsafe_allow_html=True)

    # Mostrar las banderas una al lado de la otra
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    with col1:
        st.image("assets/es.png", width=100)
    with col2:
        st.image("assets/ca.png", width=100)
    with col3:
        st.image("assets/eu.png", width=100)
    with col4:
        st.image("assets/gl.png", width=100)
    with col5:
        st.image("assets/pt.png", width=100)
    with col6:
        st.image("assets/en.png", width=100)

    st.title("Why is it important?")
    st.write(
        """
        Detection of automatically generated text is essential for several reasons:
        """
    )

    st.write(
        """
        <ul style='text-align: justify; padding-left: 15px;'>
            <li style='margin-bottom: 10px;'><b>Prevention of Disinformation:</b> Automatically generated texts can be used to spread disinformation and fake news, which can have a significant impact on society and public opinion.</li>
            <li style='margin-bottom: 10px;'><b>Cyber Security:</b> The ability to identify automatically generated text is crucial to combat phishing and other forms of cyber-attacks that use automatically generated content to deceive users.</li>
            <li style='margin-bottom: 10px;'><b>Content Quality:</b> In environments such as social media and review platforms, automatically generated text detection can help ensure the quality and authenticity of content.</li>
        </ul>
        """, unsafe_allow_html=True)

def display_aboutus():
    st.title("About Us")

    # Información sobre el proyecto y el equipo
    st.write(
        """
        <p style='text-align: justify;'>
        We are third-year data science students at the Polytechnic University of Valencia (UPV). 
        This project, part of our Project 3 course, allows us to apply our data science knowledge 
        and reflect on AI's societal impact, including ethical, social, and cultural issues. 
        Collaborating on this project enhances our technical skills and encourages creativity, 
        analytical thinking, and teamwork, helping us understand the complexities of language and 
        the interplay between human creativity and machine mimicry.
        </p>
        """, unsafe_allow_html=True)

    st.title("Our Team")

    # Información sobre cada miembro del equipo
    team_members = [
        {"name": "Eurídice Corbí", "linkedin": "https://www.linkedin.com/in/eur%C3%ADdice-corb%C3%AD/", "image": "assets/euri.jpg"},
        {"name": "Natalia Hernández", "linkedin": "https://www.linkedin.com/in/natalia-hern%C3%A1ndez-23b5882b7/", "image": "assets/natalia.jpg"},
        {"name": "Nicolás Nebot", "linkedin": "https://www.linkedin.com/in/niko-nebot-silvestre-a29107293", "image": "assets/nicolás.png"},
        {"name": "Wojciech Neuman", "linkedin": "https://www.linkedin.com/in/wojciechneuman/", "image": "assets/wojciech.jpg"},
        {"name": "Aitana Sebastiá", "linkedin": "https://www.linkedin.com/in/aitana-sebasti%C3%A0-espinosa-26a8bb2a0/", "image": "assets/aitana.jpg"},
        {"name": "Carlos Torregrosa", "linkedin": "https://www.linkedin.com/in/carlos-torregrosa-alcayde-a3274330a/", "image": "assets/carlos.png"},
        {"name": "Jose Valero", "linkedin": "https://www.linkedin.com/in/jose-valero-sanchis", "image": "assets/jose.jpg"},
    ]

    # Primera fila
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 3, 3, 3, 1, 1])
    with col4:
        st.image("assets/euri_2.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/eur%C3%ADdice-corb%C3%AD/" target="_blank">Eurídice Corbí</a>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.image("assets/natalia_2.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/natalia-hern%C3%A1ndez-23b5882b7/" target="_blank">Natalia Hernández</a>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.image("assets/nicolás_2.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/niko-nebot-silvestre-a29107293" target="_blank">Nicolás Nebot</a>
        </div>
        """, unsafe_allow_html=True)

    # Segunda fila
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 3, 3, 3, 1, 1])    
    with col4:
        st.image("assets/wojciech_2.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/wojciechneuman/" target="_blank">Wojciech Neuman</a>
        </div>
        """, unsafe_allow_html=True)
    with col5:
        st.image("assets/aitana_2.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/aitana-sebasti%C3%A0-espinosa-26a8bb2a0/" target="_blank">Aitana Sebastiá</a>
        </div>
        """, unsafe_allow_html=True)
    with col6:
        st.image("assets/carlos.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/carlos-torregrosa-alcayde-a3274330a/" target="_blank">Carlos Torregrosa</a>
        </div>
        """, unsafe_allow_html=True)

    # Tercera fila
    col1, col2, col3, col4, col5, col6, col7, col8 = st.columns([1, 1, 1, 3, 3, 3, 1, 1])    
    with col5:
        st.image("assets/jose_2.png", width=100)
        st.markdown("""
        <div class="centered">
            <a href="https://www.linkedin.com/in/jose-valero-sanchis" target="_blank">Jose Valero</a>
        </div>
        """, unsafe_allow_html=True)

def display_approach():
    st.title("Our Approach")
    st.markdown("""
        <div style="text-align: justify;">
            <p>To address the problem, we have tried a large number of models as well as ways to represent the texts. Finally, the combination that gave us the best results was the following:</p>
        </div>
    """, unsafe_allow_html=True)
    
    st.markdown("<h2 style='text-align: justify;'>Text Representation</h2>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: justify;">
            <p>We have evaluated various text representation techniques, ranging from classical methods such as LSA and TF-IDF to more advanced models such as BERT and Roberta. After a thorough analysis of their ability to capture the semantics and structure of the text, as well as their computational efficiency, we determined that <strong>FastText</strong> was the most suitable option for our project.</p>
        </div>
    """, unsafe_allow_html=True)

    col1, col2, col3 = st.columns(3)
    with col1:
        st.write(' ')

    with col2:
        st.image("./assets/fasttext.png", width=200)

    with col3:
        st.write(' ')

    st.markdown("""
        <div style="text-align: justify;">
            <p>FastText offers significant advantages, thanks to its subword-based approach that allows us to capture morphological information and handle out-of-vocabulary words efficiently. In addition, its computational efficiency allows us to train and deploy models quickly and cost-effectively.</p>
            <p>To further enhance FastText's capabilities, we have integrated pre-trained models for each of the languages we work with. These models, trained on large text corpora in each language, capture general linguistic knowledge and improve the accuracy of our predictions. These models can be found on the official website of <a href="https://fasttext.cc/docs/en/pretrained-vectors.html" target="_blank">FastText</a>.</p>
        </div>
    """, unsafe_allow_html=True)

    st.markdown("<h2 style='text-align: justify; '>Model</h2>", unsafe_allow_html=True)
    st.markdown("""
        <div style="text-align: justify;">
            <p>Among several alternatives such as SVM, LSTM and transformers, we have chosen a <strong>Convolutional Neural Network (CNN)</strong> for our task. Although CNNs are typically used for images, they have also proven to be effective in text classification due to their ability to capture local patterns through convolution.</p>
            <p>A CNN consists of convolutional layers that apply filters to the inputs to detect relevant features. In the case of text, convolutional layers can identify sequences of words or n-grams that are important for classification. The filters traverse the text and respond to specific patterns, helping to capture the semantics and structure of the text.</p>
            <p>Our CNN architecture includes three convolutional layers with 100 filters each, and filter sizes of 3, 4 and 5 words. Filter size refers to the number of words the filter examines at a time. For example, a filter size 3 will capture trigrams, while a filter size 5 will capture pentagrams. This variation in filter sizes allows the network to capture a variety of contextual patterns and relationships at different scales, thus enhancing the network's ability to understand text content.</p>
        </div>
    """, unsafe_allow_html=True)

    st.image("assets/cnn.png", width=700)

    st.markdown("""
        <div style="text-align: center; font-size: x-small;">
            <p>Julian (2020). General CNN architecture for text classification [Photograph]. Squadra. <a href="https://machine-learning-company.nl/en/technical/convolutional-neural-network-text-classification-with-risk-assessment-eng/" target="_blank">https://machine-learning-company.nl/en/technical/convolutional-neural-network-text-classification-with-risk-assessment-eng/</a></p>
        </div>
    """, unsafe_allow_html=True)

def main():
    st.sidebar.title("Navigation")
    page = st.sidebar.radio("Go to", ["Home", "About the Problem", "Our Approach", "About Us"])

    if page == "Home":
        display_home()
    elif page == "About the Problem":
        display_problem()
    elif page == "About Us":
        display_aboutus()
    elif page == "Our Approach":
        display_approach()

if __name__ == "__main__":
    main()