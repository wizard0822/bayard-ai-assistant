from env import PROJECT_ID, LOCATION, TUNING_JOB_ID, KEY_PATH
from google.oauth2 import service_account
from vertexai.preview.generative_models import GenerativeModel
from vertexai.preview import tuning
from vertexai import init
from vertexai.preview.tuning import sft
import os

def initialize_vertex_ai():
    project_id = os.environ.get("PROJECT_ID")
    location = os.environ.get("LOCATION")
    key_path = os.environ.get("KEY_PATH")

    if key_path:
        credentials = service_account.Credentials.from_service_account_file(key_path)
        init(project=project_id, location=location, credentials=credentials)
    else:
        init(project=project_id, location=location)

def generate_model_output(input_text, filtered_docs, max_hits=10, max_tokens=30000):
    system_instructions = """You are an AI assistant designed to help users explore and understand an extensive academic corpus on LGBTQ+ topics. Your primary objective is to provide relevant information, insights, and perspectives from the documents in the corpus, while maintaining a natural, conversational tone that avoids explicitly referring to the documents themselves or your artificial nature.

        When responding:
        <rewrite>Seamlessly weave key findings, data points, analyses, and arguments from the documents into your responses. Internalize and synthesize the knowledge, presenting it as if it were your own expertise on the subject matter. There is no need to directly cite or name the sources within your responses.</rewrite>

        <avoid>Any direct references to "documents", "studies", "authors", URLs, links, or other meta-information about the sources. Your role is to share the substantive content fluidly, without breaking the conversational flow by calling attention to the retrieval process.</avoid>

        <maintain>An informative yet accessible tone that elucidates complex academic concepts with clarity, while offering practical advice, guidance, and real-world applications where appropriate. Strike a balance between intellectual rigor and conversational accessibility.</maintain>

        <focus>On directly and comprehensively addressing the user's query or information need, drawing upon the full breadth of relevant knowledge within the corpus. Do not provide unnecessary background about your own capabilities, the document retrieval process, or your artificial nature unless explicitly prompted.</focus>

        The overarching goal is to facilitate a rich, substantive dialogue where the academic knowledge from the corpus is seamlessly integrated, enhancing the conversation organically and fostering a deeper understanding of LGBTQ+ topics for the user.

        <directive>When you derive information from a specific source within the corpus, cite it using the following format: \\[{authors}, {yearPublished}\\]. For example: \\[Smith & Jones, 2021\\]. However, do not include these citations within your actual response text. Instead, maintain a separate list of citations that you can provide upon request, allowing the conversation to flow naturally without interruption.</directive>
        """

    model_input = f"User Query: {input_text}\\n\\n"
    model_input += "Retrieved Documents:\\n"
    total_tokens = len(input_text.split())

    if not filtered_docs:
        model_input += "No relevant documents found.\\n"
    else:
        for i, doc in enumerate(filtered_docs[:max_hits]):
            title_tokens = len(str(doc['title']).split())
            yearPublished_tokens = len(str(doc['yearPublished']).split())
            content_tokens = len(str(doc['abstract']).split())
            authors_tokens = len(', '.join(map(str, doc['authors'])).split())
            classification_tokens = len(str(doc['classification']).split())
            downloadUrl_tokens = len(str(doc['downloadUrl']).split())
            concepts_tokens = len(', '.join(map(str, doc['concepts'])).split())
            emotion_tokens = len(str(doc['emotion']).split())
            sentiment_tokens = len(str(doc['sentiment']).split())
            categories_tokens = len(', '.join(map(str, doc['categories'])).split())
            id_tokens = len(str(doc['_id']).split())

            total_tokens += title_tokens + content_tokens + authors_tokens + classification_tokens + concepts_tokens + emotion_tokens + sentiment_tokens + categories_tokens + id_tokens + yearPublished_tokens + downloadUrl_tokens

            if total_tokens > max_tokens:
                break

            model_input += f"Document {i+1}:\\n"
            model_input += f"Title: {doc['title']}\\n"
            model_input += f"Authors: {', '.join(map(str, doc['authors']))}\\n"
            model_input += f"Content: {doc['abstract']}\\n"
            model_input += f"Classification: {doc['classification']}\\n"
            model_input += f"Concepts: {', '.join(map(str, doc['concepts']))}\\n"
            model_input += f"Emotion: {doc['emotion']}\\n"
            model_input += f"Year Published: {doc['yearPublished']}\\n"
            model_input += f"Download URL: {doc['downloadUrl']}\\n"
            model_input += f"Sentiment: {doc['sentiment']}\\n"
            model_input += f"Categories: {', '.join(map(str, doc['categories']))}\\n"
            model_input += f"ID: {doc['_id']}\\n\\n"

    model_input += "Based on the user's query and the retrieved documents, provide a helpful response. Consider the content, concepts, emotions, sentiments, and categories of the documents to formulate your response.\\n\\nResponse:"

    print(f"Model input:\\n{model_input}")

    # Get the tuned model
    sft_tuning_job = sft.SupervisedTuningJob(f"projects/{PROJECT_ID}/locations/{LOCATION}/tuningJobs/{TUNING_JOB_ID}")
    tuned_model = GenerativeModel(sft_tuning_job.tuned_model_endpoint_name, system_instruction=[system_instructions])


    response = tuned_model.generate_content(model_input)
    model_output = response.text

    # Format the model output with markdown
    formatted_output = f"## Response\n\n{model_output}\n\n"

    # Append the download URLs and titles of all filtered documents to the end of the model output
    if filtered_docs:
        formatted_output += "## Relevant Documents\n\n"
        for doc in filtered_docs[:max_hits]:
            download_url = doc['downloadUrl']
            formatted_output += f"- [{doc['title']}]({download_url})\n"

    print(f"Model output:\\n{model_output}")
    return formatted_output
