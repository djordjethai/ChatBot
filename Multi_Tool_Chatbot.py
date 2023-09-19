# This code is the is the chatbot OpenAI gpt-3.5-turbo model that uses embeddings it uses langchain as workflow,
# serp as google search tool, and pinecone as embedding index database all usint streamplit for web UI

import pinecone
import os
import sys
import time
from langchain.vectorstores import Pinecone
from langchain.embeddings.openai import OpenAIEmbeddings
from langchain.agents import Tool, AgentType, initialize_agent
from langchain.chains import RetrievalQA
from langchain.chat_models import ChatOpenAI
from langchain.utilities.google_search import GoogleSearchAPIWrapper
from langchain.memory import ConversationBufferMemory
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)

import streamlit as st
from myfunc.mojafunkcija import (
    st_style,
    positive_login,
    StreamHandler,
    StreamlitRedirect,
    init_cond_llm,
    open_file,
)

from langchain.callbacks.tracers.run_collector import RunCollectorCallbackHandler
from langchain.memory import ConversationBufferMemory
from langchain.schema.runnable import RunnableConfig
from langsmith import Client
from streamlit_feedback import streamlit_feedback
from langchain.callbacks.tracers.langchain import wait_for_all_tracers
from random import randint
# from custom_eval import RelevanceEvaluator

# these are the environment variables that need to be set for LangSmith to work
os.environ["LANGCHAIN_PROJECT"] = "Multi Tool Chatbot"
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_ENDPOINT"] = "https://api.langchain.plus"
os.environ.get("LANGCHAIN_API_KEY")

st.set_page_config(page_title="Multi Tool Chatbot", page_icon="👋", layout="wide")


def whoimi(input=""):
    """Positive AI asistent"""
    return "Positive doo razvija AI Asistenta. U ovaj odgovor mozemo dodati bilo koji tekst."


def new_chat():
    st.session_state["generated"] = []
    st.session_state["past"] = []
    st.session_state["input"] = ""
    st.session_state.memory.clear()
    st.session_state["messages"] = []


def main():
    client = Client()
    # our_evaluator = RelevanceEvaluator()
    st.subheader(
        "AI Asistent je povezan na internet i Positive portfolio i moze da odgovara na pitanja o Positive AI asistentu, Positive doo i njihovom portfoliu, i na pitanja o aktuelnim dogadjajima."
    )
    st.info(
        "Mozete birati model i temperaturu, a bice prikazan i streaming output. Moguc je i Download chata. Ako menjate temu, bolje je odabrati opciju New Chat"
    )

    # Initialize session states
    if "generated" not in st.session_state:
        st.session_state["generated"] = []
    if "cot" not in st.session_state:
        st.session_state["cot"] = ""
    if "past" not in st.session_state:
        st.session_state["past"] = []
    if "input" not in st.session_state:
        st.session_state["input"] = ""
    if "messages" not in st.session_state:
        st.session_state["messages"] = []

    with st.sidebar:
        st.button("New Chat", on_click=new_chat)
    download_str = []
    if "open_api_key" not in st.session_state:
        # Retrieving API keys from env
        st.session_state.open_api_key = os.environ.get("OPENAI_API_KEY")
    # Read OpenAI API key from env
    if "PINECONE_API_KEY" not in st.session_state:
        # Retrieving API keys from env
        st.session_state.PINECONE_API_KEY = os.environ.get("PINECONE_API_KEY")
    if "PINECONE_API_ENV" not in st.session_state:
        st.session_state.PINECONE_API_ENV = os.environ.get("PINECONE_API_ENV")
    if "GOOGLE_API_KEY" not in st.session_state:
        # Retrieving API keys from env
        st.session_state.GOOGLE_API_KEY = os.environ.get("GOOGLE_API_KEY")
    if "GOOGLE_CSE_ID" not in st.session_state:
        st.session_state.GOOGLE_CSE_ID = os.environ.get("GOOGLE_CSE_ID")
        # Initializing OpenAI and Pinecone APIs
    if "embeddings" not in st.session_state:
        st.session_state.embeddings = OpenAIEmbeddings(
            openai_api_key=st.session_state.open_api_key
        )
    if "index" not in st.session_state:
        # Setting index name
        st.session_state.index = pinecone.Index("embedings1")
    if "name_space" not in st.session_state:
        st.session_state.name_space = "positive"
    if "text_field" not in st.session_state:
        st.session_state.text_field = "text"
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = Pinecone(
            st.session_state.index,
            st.session_state.embeddings.embed_query,
            st.session_state.text_field,
            st.session_state.name_space,
        )
    if "memory" not in st.session_state:
        st.session_state.memory = ConversationBufferMemory(
            memory_key="chat_history", return_messages=True
        )
    if "sistem" not in st.session_state:
        st.session_state.sistem = open_file("prompt_turbo.txt")
    if "odgovor" not in st.session_state:
        st.session_state.odgovor = open_file("odgovor_turbo.txt")
    if "system_message_prompt" not in st.session_state:
        st.session_state.system_message_prompt = (
            SystemMessagePromptTemplate.from_template(st.session_state.sistem)
        )
    if "human_message_prompt" not in st.session_state:
        st.session_state.human_message_prompt = (
            HumanMessagePromptTemplate.from_template("{text}")
        )
    if "chat_prompt" not in st.session_state:
        st.session_state.chat_prompt = ChatPromptTemplate.from_messages(
            [
                st.session_state.system_message_prompt,
                st.session_state.human_message_prompt,
            ]
        )

    pinecone.init(
        api_key=st.session_state.PINECONE_API_KEY,
        environment=st.session_state.PINECONE_API_ENV,
    )

    model, temp = init_cond_llm()
    name = st.session_state.get("name")

    placeholder = st.empty()

    # 1.  Using the session state variable, we can check if the stream handler is already in the session state,
    #    if not, we create it and add it to the session state.
    # 2.  We use the reset_text function of the stream handler to reset the text of the stream handler.

    pholder = st.empty()
    with pholder.container():
        if "stream_handler" not in st.session_state:
            st.session_state.stream_handler = StreamHandler(pholder)
    st.session_state.stream_handler.reset_text()

    chat = ChatOpenAI(
        openai_api_key=st.session_state.open_api_key,
        temperature=temp,
        model=model,
        streaming=True,
        callbacks=[st.session_state.stream_handler],
    )
    upit = []

    # initializing tools Pinecone lookup and Intermediate Answer
    if "vectorstore" not in st.session_state:
        st.session_state.vectorstore = Pinecone(
            st.session_state.index,
            st.session_state.embeddings.embed_query,
            upit,
            st.session_state.name_space,
        )
    if "qa" not in st.session_state:
        st.session_state.qa = RetrievalQA.from_chain_type(
            llm=chat,
            chain_type="stuff",
            retriever=st.session_state.vectorstore.as_retriever(),
        )
    if "search" not in st.session_state:
        # initializing tools internet search
        st.session_state.search = GoogleSearchAPIWrapper()
        # initialize agent tools
    if "tools" not in st.session_state:
        st.session_state.tools = [
            Tool(
                name="search",
                func=st.session_state.search.run,
                description="Google search tool. Useful when you need to answer questions about recent events.",
            ),
            Tool(
                name="Pinecone lookup",
                func=st.session_state.qa.run,
                verbose=False,
                description="Useful for when you are asked about topics including Positive doo and their portfolio. Input should be a topic you want to lookup.",
                return_direct=True,
            ),
            Tool(
                name="Positive AI asistent",
                func=whoimi,
                description="Useful for when you need to answer questions about Positive AI asistent. Input should be Positive AI asistent ",
            ),
        ]

    agent_chain = initialize_agent(
        tools=st.session_state.tools,
        llm=chat,
        agent=AgentType.CHAT_CONVERSATIONAL_REACT_DESCRIPTION,
        messages=st.session_state.chat_prompt,
        verbose=True,
        memory=st.session_state.memory,
        handle_parsing_errors=True,
        max_iterations=4,
    )

    run_collector = RunCollectorCallbackHandler()
    runnable_config = RunnableConfig(callbacks=[run_collector], tags=["Streamlit Chat"])

    if upit := st.chat_input("Postavite pitanje"):
        formatted_prompt = st.session_state.chat_prompt.format_prompt(
            text=upit
        ).to_messages()
        # prompt[0] je system message, prompt[1] je tekuce pitanje
        pitanje = formatted_prompt[0].content + formatted_prompt[1].content
        st.session_state.feedback = None
        st.session_state.feedback_update = None
        st.session_state.our_score = None
        st.session_state.our_reasoning = None
        with placeholder.container():
            st_redirect = StreamlitRedirect()
            sys.stdout = st_redirect

            output = agent_chain.invoke(input=pitanje, config=runnable_config)
            output_text = output.get("output", "")

            # Get the captured output from the st_redirect instance
            captured_output = st_redirect.get_output()

            run = run_collector.traced_runs[0]
            run_collector.traced_runs = []
            st.session_state.run_id = run.id
            wait_for_all_tracers()

            # Print the captured output
            time.sleep(1)
            st.session_state.stream_handler.clear_text()
            st.session_state.past.append(f"{name}: {upit}")
            st.session_state.generated.append(f"AI Asistent: {output_text}")

            x = """
            pitanje_za_evaluator = pitanje.split("\n")[2]
            eval = our_evaluator.evaluate_strings(
                prediction=output_text, input=pitanje_za_evaluator
            )
            st.session_state.our_score = eval["score"]
            st.session_state.our_reasoning = eval["reasoning"]
            """
            # Calculate the length of the list
            num_messages = len(st.session_state["generated"])

            # Loop through the range in reverse order
            for i in range(num_messages - 1, -1, -1):
                # Get the index for the reversed order
                reversed_index = num_messages - i - 1
                # Display the messages in the reversed order
                st.info(st.session_state["past"][reversed_index], icon="🤔")

                st.success(st.session_state["generated"][reversed_index], icon="👩‍🎓")

                with st.expander("Chain Of Thoughts", expanded=False):
                    st.write(captured_output)
                # Append the messages to the download_str in the reversed order
                download_str.append(st.session_state["past"][reversed_index])
                download_str.append(st.session_state["generated"][reversed_index])
            download_str = "\n".join(download_str)

            with st.sidebar:
                st.download_button("Download", download_str)

    if st.session_state.get("run_id"):
        with st.chat_message("assistant", avatar="🤖"):
            message_placeholder = st.empty()
            message_placeholder.markdown(
                ":rainbow[Prvo ocenite od 1 do 5 dobijene rezultate.]"
            )
        feedback = streamlit_feedback(
            feedback_type="faces", key=f"feedback_{st.session_state.run_id}"
        )
        scores = {"😞": 1, "🙁": 2, "😐": 3, "🙂": 4, "😀": 5}
        if feedback:
            score = scores[feedback["score"]]
            feedback = client.create_feedback(
                st.session_state.run_id, "ocena", score=score
            )
            st.session_state.feedback = {
                "feedback_id": str(feedback.id),
                "score": score,
            }

    if st.session_state.get("feedback"):
        feedback = st.session_state.get("feedback")
        feedback_id = feedback["feedback_id"]

        comment = st.text_input(
            label="🚩 Sada unesite sve napomene/komentare koje imate u vezi sa performansama programa.",
            key=f"comment_{feedback_id}",
        )
        if comment:
            st.session_state.feedback_update = {
                "comment": comment,
                "feedback_id": feedback_id,
            }

    if st.session_state.get("feedback_update"):
        feedback_update = st.session_state.get("feedback_update")
        feedback_id = feedback_update.pop("feedback_id")
        client.update_feedback(feedback_id, **feedback_update)
        st.image(
            "https://test.georgemposi.com/wp-content/uploads/2023/05/positive-logo-red.jpg",
            caption="Helloooouuu!",
            width=150,
        )
        x = ["🎭", "🐯", "👺", "👻", "😸", "🤓", "🤡", "🦄", "🧟‍♀️", "☘️"]
        st.write(
            f"{x[randint(0, len(x) - 1)]} Ova aplikacija radi iterativno - možete odmah ukucati naredno pitanje!"
        )
        client.create_feedback(
            st.session_state.run_id,
            "our_evaluation",
            score=st.session_state.our_score,
            comment=st.session_state.our_reasoning,
        )

        st.session_state.feedback = None
        st.session_state.feedback_update = None
        st.session_state.our_score = None
        st.session_state.our_reasoning = None


st_style()
# Koristi se samo za deploy na streamlit.io
deployment_environment = os.environ.get("DEPLOYMENT_ENVIRONMENT")

if deployment_environment == "Streamlit":
    name, authentication_status, username = positive_login(main, "16.09.23.")
else:
    if __name__ == "__main__":
        main()