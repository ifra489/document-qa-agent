import streamlit as st
from openai import OpenAI
import PyPDF2
import os
from dotenv import load_dotenv

load_dotenv()

# Configure Router API key

client = OpenAI(
    base_url="https://openrouter.ai/api/v1",
    api_key=os.getenv("OPENROUTER_API_KEY")
)
# Page config
st.set_page_config(
    page_title="Document QA Agent",
    page_icon="📄",
    layout="centered"
)

st.title("📄 Document QA Agent")
st.caption("Upload a document and ask questions — AI will answer with cited sections.")

# Extract PDF text
def extract_text(pdf_file):
    reader = PyPDF2.PdfReader(pdf_file)
    text = ""
    for i, page in enumerate(reader.pages):
        content = page.extract_text()
        if content:
            text += f"\n[Page {i+1}]\n{content}"
    return text

# Ask Gemini
def ask_agent(document_text, question, chat_history):
    
    # Escalation check
    escalation_keywords = ["legal", "lawsuit", "emergency", "urgent", "critical", "illegal", "danger"]
    if any(word in question.lower() for word in escalation_keywords):
        return "⚠️ This question requires human review. Please consult a relevant expert or supervisor for this matter.", True
    if len(question.strip())<3 or not any(c.isalnum() for c in question):
        return "⚠️ Your question seems unclear or incomplete. Please provide more details or clarify your question.", False
    # Build prompt
    history_text = ""
    for msg in chat_history[-4:]:
        history_text += f"{msg['role'].upper()}: {msg['content']}\n"

    prompt = f"""You are a precise Document QA Agent. Your job is to answer questions strictly based on the document provided.

DOCUMENT CONTENT:
{document_text[:15000]}

CONVERSATION HISTORY:
{history_text}

USER QUESTION: {question}

INSTRUCTIONS:
1. Answer ONLY based on the document content above.
2. Always cite the specific page or section where you found the answer. Example: (Page 3)
3. If the answer is not in the document, say exactly: "This information is not available in the uploaded document."
4. If the question is ambiguous or unclear, ask the user to clarify.
5. Keep answers clear, concise and well structured.
6. If input is messy or incomplete, handle gracefully and ask for clarification.

ANSWER:"""

    try:
      response = client.chat.completions.create(
       model="openrouter/auto",
        messages=[
            {"role": "user", "content": prompt}
        ]
    )

      return response.choices[0].message.content, False

    except Exception as e:
      return f"An error occurred: {str(e)}. Please try again.", False

# Initialize session state
if "chat_history" not in st.session_state:
    st.session_state.chat_history = []
if "document_text" not in st.session_state:
    st.session_state.document_text = ""
if "document_name" not in st.session_state:
    st.session_state.document_name = ""

# Upload section
uploaded_file = st.file_uploader("Upload your PDF document", type=["pdf"])

if uploaded_file:
    if uploaded_file.name != st.session_state.document_name:
        with st.spinner("Reading document..."):
            st.session_state.document_text = extract_text(uploaded_file)
            st.session_state.document_name = uploaded_file.name
            st.session_state.chat_history = []
        st.success(f"Document loaded: {uploaded_file.name}")

    if st.session_state.document_text:
        st.divider()
        st.subheader("💬 Ask anything about your document")

        # Display chat history
        for msg in st.session_state.chat_history:
            if msg["role"] == "user":
                with st.chat_message("user"):
                    st.write(msg["content"])
            else:
                with st.chat_message("assistant"):
                    st.write(msg["content"])

        # Input
        question = st.chat_input("Type your question here...")

        if question:
            # Add user message
            st.session_state.chat_history.append({
                "role": "user",
                "content": question
            })

            with st.chat_message("user"):
                st.write(question)

            # Get answer
            with st.chat_message("assistant"):
                with st.spinner("Thinking..."):
                    answer, escalated = ask_agent(
                        st.session_state.document_text,
                        question,
                        st.session_state.chat_history
                    )
                    st.write(answer)
                    if escalated:
                        st.warning("This query has been flagged for human review.")

            # Add assistant message
            st.session_state.chat_history.append({
                "role": "assistant",
                "content": answer
            })

else:
    st.info("👆 Please upload a PDF document to get started.")
    st.markdown("""
    **How it works:**
    - Upload any PDF document
    - Ask questions in natural language
    - Get cited answers from specific pages
    - Agent escalates sensitive queries to human review
    """)