import os
from dotenv import load_dotenv
from flask import Flask, request, jsonify, render_template
from flask_cors import CORS
import json
import re
from datetime import datetime
from langchain_core.documents import Document

from langchain_ollama import ChatOllama
from langchain_ollama import OllamaEmbeddings
from langchain_astradb import AstraDBVectorStore
from typing_extensions import TypedDict
from typing import List
from langchain_core.prompts import ChatPromptTemplate
from langgraph.graph import StateGraph, END, START

# Loading Environment Variables:
load_dotenv()
ASTRA_DB_API_ENDPOINT = os.getenv("ASTRA_DB_API_ENDPOINT")
ASTRA_DB_TOKEN = os.getenv("ASTRA_DB_TOKEN")
SUPPORT_EMAIL = "support.dantel@gmil.com"

app = Flask(__name__, template_folder='templates')
CORS(app)

# Global Components:
suggestion_graph = None
triage_graph = None
vector_store = None
triage_collection = None

# State Definitions:
class SuggestionGraphState(TypedDict):
    """ State for the advanced suggestion graph. """
    question: str
    context: List[Document]
    answer: str
    generated_questions: List[str]
    relevance: str
    hallucination_check: str
    route: str 

class TriageGraphState(TypedDict):
    """ State for the ticket creation graph. """
    subject: str
    description: str
    email: str 
    classification: str
    priority: str
    team_solution: str
    ticket_id: str

def initialize_system():
    """Initializes all models, vector stores, and graphs."""
    global suggestion_graph, triage_graph, vector_store, triage_collection

    print("Initializing Datel Support Triage System...")

    # LLM and Embeddings:
    llm = ChatOllama(model="qwen3:4b") 
    embeddings = OllamaEmbeddings(model="all-minilm:latest")

    # Vector Store for RAG:
    vector_store = AstraDBVectorStore(
        embedding=embeddings,
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_TOKEN,
        collection_name="dantelcsv",
    )
    retriever = vector_store.as_retriever(k=5)
    
    triage_collection = AstraDBVectorStore(
        embedding=embeddings,
        api_endpoint=ASTRA_DB_API_ENDPOINT,
        token=ASTRA_DB_TOKEN,
        collection_name="triage_tickets",
    )
    print("AstraDB connections established.")

    # Graph 1: Advanced Suggestion Graph 
    print("Compiling Advanced Suggestion Graph...")

    def _extract_clean_response(raw_response: str) -> str:
        return re.sub(r'<think>.*?</think>', '', raw_response, flags=re.DOTALL).strip()

    def expand_question(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Expanding question...")
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful AI assistant. Generate 5 different versions of the user's question to improve document retrieval. Provide these alternative questions separated by newlines. Original question: {question}"""
        )
        chain = prompt | llm
        raw_output = chain.invoke({"question": state["question"]}).content
        expanded_q_str = _extract_clean_response(raw_output)
        generated_questions = [q for q in expanded_q_str.split('\n') if q.strip()]
        return {"generated_questions": generated_questions}

    def retrieve_documents(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Retrieving documents...")
        all_retrieved_docs = []
        for q in state["generated_questions"]:
            docs = retriever.invoke(q)
            all_retrieved_docs.extend(docs)
        unique_docs = {doc.page_content: doc for doc in all_retrieved_docs}.values()
        return {"context": list(unique_docs)}

    def grade_documents(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Grading documents...")
        prompt = ChatPromptTemplate.from_template(
            """Grade the relevance of a retrieved document to a user question. If the question is gibberish, grade as 'no'. Grade 'yes' if relevant, otherwise 'no'.
            Document: {document}
            Question: {question}
            Answer 'yes' or 'no':"""
        )
        chain = prompt | llm
        relevance = "no"
        for doc in state["context"]:
            raw_output = chain.invoke({"question": state["question"], "document": doc.page_content}).content
            response = _extract_clean_response(raw_output)
            if "yes" in response.lower():
                relevance = "yes"
                break
        return {"relevance": relevance}

    def generate_answer(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Generating answer...")
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful AI assistant for Datel Group. Use the provided context from past support tickets to answer the question.
            
            **Instructions:**
            - Your response must be concise, with a maximum of 4 sentences.
            - Do NOT use markdown formatting like ##, ---, or **. Write in plain text.
            - If the context is insufficient to answer, simply state that you could not find a specific solution and recommend raising a ticket.

            Context: {context}
            Question: {question}"""
        )
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        chain = prompt | llm
        raw_output = chain.invoke({"question": state["question"], "context": docs_content}).content
        clean_answer = _extract_clean_response(raw_output)
        return {"answer": clean_answer, "route": "vectorstore"}

    def generate_generic_answer(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Generating generic answer...")
        prompt = ChatPromptTemplate.from_template(
            """You are a helpful AI assistant. Answer the user's question concisely, in a maximum of 3 sentences.
            
            Question: {question}"""
        )
        chain = prompt | llm
        raw_output = chain.invoke({"question": state["question"]}).content
        clean_answer = _extract_clean_response(raw_output)
        return {"answer": clean_answer, "route": "generic"}

    def generate_fallback_answer(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Generating fallback answer...")
        answer = f"I'm sorry, I couldn't find relevant information to answer your question. Please raise a formal ticket for our support team."
        return {"answer": answer, "route": "vectorstore"}

    def check_hallucination(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Checking for hallucinations...")
        prompt = ChatPromptTemplate.from_template(
            """Check if the 'Answer' is supported by the 'Context'. Respond with 'no_hallucination' if it is, or 'hallucination' if it is not.
            Context: {context}
            Answer: {answer}
            Respond with 'hallucination' or 'no_hallucination':"""
        )
        docs_content = "\n\n".join(doc.page_content for doc in state["context"])
        chain = prompt | llm
        raw_output = chain.invoke({"context": docs_content, "answer": state["answer"]}).content
        decision = _extract_clean_response(raw_output).lower()
        return {"hallucination_check": decision}

    def handle_hallucination(state: SuggestionGraphState):
        print("SUGGESTION_GRAPH: Handling hallucination...")
        answer = f"I am having trouble generating a reliable answer. Please try rephrasing your question or raise a ticket for support."
        return {"answer": answer, "route": "vectorstore"}

    def decide_to_generate(state: SuggestionGraphState):
        return "generate_answer" if state["relevance"] == "yes" else "fallback_answer"

    def decide_after_hallucination_check(state: SuggestionGraphState):
        return "handle_hallucination" if "no_hallucination" not in state["hallucination_check"] else END

    suggestion_workflow = StateGraph(SuggestionGraphState)
    suggestion_workflow.add_node("expand_question", expand_question)
    suggestion_workflow.add_node("retrieve_documents", retrieve_documents)
    suggestion_workflow.add_node("grade_documents", grade_documents)
    suggestion_workflow.add_node("generate_answer", generate_answer)
    suggestion_workflow.add_node("check_hallucination", check_hallucination)
    suggestion_workflow.add_node("generate_generic_answer", generate_generic_answer)
    suggestion_workflow.add_node("fallback_answer", generate_fallback_answer)
    suggestion_workflow.add_node("handle_hallucination", handle_hallucination)
    suggestion_workflow.add_edge(START, "expand_question") # Comment this line and use the above line if using the route_question function
    suggestion_workflow.add_edge("expand_question", "retrieve_documents")
    suggestion_workflow.add_edge("retrieve_documents", "grade_documents")
    suggestion_workflow.add_conditional_edges("grade_documents", decide_to_generate, {"generate_answer": "generate_answer", "fallback_answer": "fallback_answer"})
    suggestion_workflow.add_edge("generate_answer", "check_hallucination")
    suggestion_workflow.add_conditional_edges("check_hallucination", decide_after_hallucination_check, {"handle_hallucination": "handle_hallucination", END: END})
    suggestion_workflow.add_edge("generate_generic_answer", END)
    suggestion_workflow.add_edge("fallback_answer", END)
    suggestion_workflow.add_edge("handle_hallucination", END)
    suggestion_graph = suggestion_workflow.compile()
    print("Advanced Suggestion Graph compiled.")

    # Graph 2: Full Triage Graph
    print("Compiling Triage Graph...")

    def classify_ticket(state: TriageGraphState):
        print("TRIAGE_GRAPH: Classifying ticket...")
        prompt = ChatPromptTemplate.from_template(
            """Classify the ticket into one of these categories: Login & Authentication, Data & Export Issues, Performance & Slowdowns, Billing & Subscriptions, General Inquiry.
            Subject: {subject}, Description: {description}
            Return only the category name."""
        )
        chain = prompt | llm
        classification = chain.invoke({"subject": state["subject"], "description": state["description"]}).content
        return {"classification": _extract_clean_response(classification)}

    def assess_priority(state: TriageGraphState):
        print("TRIAGE_GRAPH: Assessing priority...")
        prompt = ChatPromptTemplate.from_template(
            """Assess ticket priority as "High", "Medium", or "Low" based on business impact.
            High: System down, financial impact, security.
            Medium: Functionality impaired.
            Low: General question.
            Subject: {subject}, Description: {description}
            Return only the priority level."""
        )
        chain = prompt | llm
        priority = chain.invoke({"subject": state["subject"], "description": state["description"]}).content
        return {"priority": _extract_clean_response(priority)}

    def generate_team_solution(state: TriageGraphState):
        print("TRIAGE_GRAPH: Generating team-facing solution...")
        question_for_retrieval = f"Subject: {state['subject']}\nDescription: {state['description']}"
        similar_docs = retriever.invoke(question_for_retrieval)
        context = "\n\n---\n\n".join([doc.page_content for doc in similar_docs])
        prompt = ChatPromptTemplate.from_template(
            """For an internal support team member, provide a concise summary of potential solutions for the new ticket based on similar past tickets. Don't write in markdown.
            Context: {context}
            New Ticket: Subject: {subject}, Description: {description}"""
        )
        chain = prompt | llm
        solution = chain.invoke({"context": context, "subject": state["subject"], "description": state["description"]}).content
        return {"team_solution": _extract_clean_response(solution)}

    def store_ticket_in_db(state: TriageGraphState):
        print("TRIAGE_GRAPH: Storing ticket in AstraDB...")
        ticket_id = f"TICKET-{int(datetime.now().timestamp())}"
        ticket_data = {
            "ticket_id": ticket_id, 
            "subject": state["subject"], 
            "description": state["description"],
            "email": state["email"], 
            "classification": state["classification"], 
            "priority": state["priority"],
            "team_solution": state["team_solution"],
            "status": "Open", 
            "created_at": datetime.now().isoformat()
        }
        
        print("\n--- DATA TO BE STORED IN ASTRADB ---")
        print(json.dumps(ticket_data, indent=2))
        print("-------------------------------------\n")

        triage_collection.add_documents([Document(
            page_content=f"Subject: {state['subject']}\nPriority: {state['priority']}",
            metadata=ticket_data
        )])
        return {"ticket_id": ticket_id}

    triage_workflow = StateGraph(TriageGraphState)
    triage_workflow.add_node("classify", classify_ticket)
    triage_workflow.add_node("prioritize", assess_priority)
    triage_workflow.add_node("generate_team_solution", generate_team_solution)
    triage_workflow.add_node("store_ticket", store_ticket_in_db)
    triage_workflow.add_edge(START, "classify")
    triage_workflow.add_edge("classify", "prioritize")
    triage_workflow.add_edge("prioritize", "generate_team_solution")
    triage_workflow.add_edge("generate_team_solution", "store_ticket")
    triage_workflow.add_edge("store_ticket", END)
    triage_graph = triage_workflow.compile()
    print("Triage Graph compiled.")
    print("--- System Initialized Successfully ---")

# API Endpoints:
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/get_suggestion', methods=['POST'])
def get_suggestion():
    if not suggestion_graph:
        return jsonify({"error": "Suggestion system not initialized"}), 500
    data = request.json
    question = f"Subject: {data['subject']}\nDescription: {data['description']}"
    try:
        response = suggestion_graph.invoke({"question": question})
        return jsonify({
            "answer": response.get("answer", "Could not generate a suggestion."),
            "route": response.get("route", "vectorstore")
        })
    except Exception as e:
        print(f"Error during suggestion graph invocation: {e}")
        return jsonify({"error": "Failed to process the suggestion request."}), 500

@app.route('/create_ticket', methods=['POST'])
def create_ticket():
    if not triage_graph:
        return jsonify({"error": "Triage system not initialized"}), 500
        
    data = request.json
    
    try:
        response = triage_graph.invoke({
            "subject": data["subject"],
            "description": data["description"],
            "email": data["email"] 
        })
        return jsonify({
            "ticket_id": response.get("ticket_id", "N/A")
        })
    except Exception as e:
        print(f"Error during triage graph invocation: {e}")
        return jsonify({"error": "Failed to create the ticket."}), 500

if __name__ == '__main__':
    initialize_system()
    # Use use_reloader as False as keeping it True was resulting in a loop bug.
    app.run(host='0.0.0.0', port=5000, debug=True, use_reloader=False)
