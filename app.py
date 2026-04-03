import streamlit as st
import requests
import json
from datetime import datetime

# ========== TOOL FUNCTIONS ==========
def classify_symptom(symptom_text: str) -> str:
    """
    Classify a symptom message into medical category.
    """
    symptom_text = symptom_text.lower()

    if "fever" in symptom_text or "temperature" in symptom_text:
        return "Fever / Infection"
    elif "cough" in symptom_text or "cold" in symptom_text or "sneeze" in symptom_text:
        return "Cold / Respiratory Issue"
    elif "headache" in symptom_text or "migraine" in symptom_text:
        return "Head Pain Issue"
    elif "stomach" in symptom_text or "vomit" in symptom_text or "diarrhea" in symptom_text:
        return "Stomach / Digestion Issue"
    elif "chest pain" in symptom_text or "breathing problem" in symptom_text:
        return "Heart / Lung Serious Issue"
    elif "injury" in symptom_text or "cut" in symptom_text or "bleeding" in symptom_text:
        return "Injury / Accident"
    else:
        return "General Health Issue"

def analyze_patient_tone(symptom_text: str) -> str:
    """
    Detect patient's emotional tone based on symptom description.
    """
    worried_words = [
        "severe", "serious", "emergency", "very bad",
        "extreme", "unbearable", "can't breathe",
        "very painful", "critical"
    ]
    mild_words = [
        "little", "mild", "slight", "small pain",
        "not much", "manageable", "okay"
    ]
    positive_words = [
        "feeling better", "improving", "recovering",
        "fine now", "good"
    ]

    text = symptom_text.lower()

    if any(w in text for w in worried_words):
        return "High Concern"
    elif any(w in text for w in mild_words):
        return "Low Concern"
    elif any(w in text for w in positive_words):
        return "Recovering"
    else:
        return "Neutral"

# ========== TOOLS SCHEMA ==========
tools = [{
    "type": "function",
    "function": {
        "name": "classify_symptom",
        "description": "Classify a symptom message into medical category.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "The symptom message."},
            },
            "required": ["message"]
        },
    },
}, {
    "type": "function",
    "function": {
        "name": "analyze_patient_tone",
        "description": "Detect patient's emotional tone based on symptom description.",
        "parameters": {
            "type": "object",
            "properties": {
                "message": {"type": "string", "description": "patient condition."}
            },
            "required": ["message"]
        },
    },
}]

# ========== API URL ==========
API_URL = "https://lashanda-inturned-monstrously.ngrok-free.dev/api/chat"

# ========== MAIN FUNCTION WITH STREAMING FINAL RESPONSE ==========
def process_message(message):
    """
    Process user message and return response with streaming for final output
    """
    try:
        # Step 1: Initial message with tools (NO STREAMING)
        initial_message = [
            {"role": "user", "content": f"classify_symptom and analyze_patient_tone from patient message: {message}"}
        ]

        payload = {
            "model": "mistral:latest",
            "messages": initial_message,
            "tools": tools,
            "stream": False  # First call: NO streaming
        }

        response = requests.post(API_URL, json=payload, timeout=60)
        initial_response = response.json()

        # Step 2: Prepare for tool execution
        message_for_next_step = initial_message + [initial_response["message"]]
        tool_outputs = []

        # Step 3: Execute tools
        if "tool_calls" in initial_response["message"]:
            for tool_call in initial_response["message"]["tool_calls"]:
                func_name = tool_call["function"]["name"]
                arguments = tool_call["function"]["arguments"]
                symptom_text = arguments.get("message", message)

                if func_name == "classify_symptom":
                    result = classify_symptom(symptom_text)
                elif func_name == "analyze_patient_tone":
                    result = analyze_patient_tone(symptom_text)
                else:
                    result = f"Unknown function: {func_name}"

                tool_outputs.append({
                    "role": "tool",
                    "name": func_name,
                    "content": result
                })

        # Step 4: Send tool results back WITH STREAMING
        if tool_outputs:
            message_for_next_step.extend(tool_outputs)
            
            final_payload = {
                "model": "mistral:latest",
                "messages": message_for_next_step,
                "stream": True  # Second call: YES streaming!
            }
            
            final_response = requests.post(API_URL, json=final_payload, stream=True, timeout=120)
            
            # Yield tokens as they arrive
            for line in final_response.iter_lines():
                if line:
                    try:
                        data = json.loads(line)
                        if "message" in data and "content" in data["message"]:
                            content = data["message"]["content"]
                            if content:
                                yield content
                    except json.JSONDecodeError:
                        continue
        
        else:
            yield "Sorry, I couldn't process your request."

    except Exception as e:
        yield f"Error: {str(e)}"

# ========== STREAMLIT UI ==========
def main():
    # Page configuration
    st.set_page_config(
        page_title="Medical Symptom Chatbot",
        page_icon="🏥",
        layout="wide"
    )

    # Header
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        st.title("🏥 Medical Symptom Chatbot")
        st.caption("AI-Powered Health Assistant")
    
    st.divider()
    
    # Sidebar
    with st.sidebar:
        st.header("ℹ️ About")
        st.info(
            """This chatbot helps analyze your symptoms and provides preliminary medical advice.
            
            **Features:**
            - 🔍 Symptom classification
            - 🎭 Emotional tone analysis
            - 💊 Personalized medical advice
            - ⚡ Streaming responses
            - ⚠️ Emergency detection
            """
        )
        
        st.warning(
            """**⚠️ Disclaimer:**
            This is an AI assistant. Always consult a real doctor for serious medical conditions.
            """
        )
        
        st.divider()
        
        # Quick symptom buttons
        st.subheader("🔘 Quick Symptoms")
        
        quick_symptoms = {
            "🤒 Fever & Headache": "I have fever and headache",
            "🤢 Stomach pain & vomiting": "I have stomach pain and vomiting",
            "🫁 Chest pain & breathing difficulty": "I have chest pain and breathing difficulty",
            "🤕 Severe migraine": "I have a severe migraine",
            "🩹 Minor cut on finger": "I have a minor cut on my finger"
        }
        
        for btn_label, symptom_text in quick_symptoms.items():
            if st.button(btn_label, use_container_width=True, key=btn_label):
                st.session_state.user_input = symptom_text
                st.rerun()
        
        st.divider()
        
        # Chat history clear button
        if st.button("🗑️ Clear Chat History", use_container_width=True, type="secondary"):
            st.session_state.messages = []
            st.session_state.user_input = ""
            st.rerun()
        
        # Statistics
        if "messages" in st.session_state:
            st.divider()
            st.subheader("📊 Session Stats")
            col_a, col_b = st.columns(2)
            with col_a:
                st.metric("Messages", len(st.session_state.messages))
            with col_b:
                st.metric("Last Active", datetime.now().strftime("%H:%M"))

    # Main chat area
    st.subheader("💬 Chat with Medical Assistant")
    
    # Initialize chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []
        welcome_msg = "Hello! I'm your medical assistant. Please describe your symptoms, and I'll help analyze them and provide advice. Remember, I'm not a replacement for a real doctor!"
        st.session_state.messages.append({"role": "assistant", "content": welcome_msg})

    # Display chat history
    for msg in st.session_state.messages:
        if msg["role"] == "user":
            with st.chat_message("user"):
                st.write(msg["content"])
        else:
            with st.chat_message("assistant"):
                st.write(msg["content"])
    
    # Chat input
    if "user_input" not in st.session_state:
        st.session_state.user_input = ""
    
    user_input = st.chat_input("Describe your symptoms here...")
    
    if user_input:
        # Add user message
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Display user message immediately
        with st.chat_message("user"):
            st.write(user_input)
        
        # Display assistant message with streaming
        with st.chat_message("assistant"):
            response_container = st.empty()
            full_response = ""
            
            # Show initial spinner while first API call happens
            with st.spinner("🔍 Analyzing symptoms and preparing response..."):
                # Stream the final response
                for token in process_message(user_input):
                    full_response += token
                    response_container.markdown(full_response + "▌")
            
            # Final response without cursor
            response_container.markdown(full_response)
        
        # Add to chat history
        st.session_state.messages.append({"role": "assistant", "content": full_response})
        
        st.rerun()
    
    # Footer
    st.divider()
    st.error(
        "⚠️ **Emergency Warning:** If you're experiencing severe symptoms like chest pain, "
        "difficulty breathing, severe bleeding, or loss of consciousness, "
        "please call emergency services immediately!"
    )

if __name__ == "__main__":
    main()