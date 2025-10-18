from pocketflow import Node, AsyncNode
from utils.call_llm import call_llm
from utils.vectordb import retrieve_documents
import asyncio

class InputNode(Node):
    def exec(self, _):
        # Get question directly from user input
        user_question = input("Enter your question: ")
        return user_question
    
    def post(self, shared, prep_res, exec_res):
        # Store the user's question
        shared["question"] = exec_res
        return "default"  # Go to the next node

class QueryDecompositionNode(Node):
    def prep(self, shared):
        # Read question from shared
        return shared["question"]
    
    def exec(self, question):
        # Create prompt for decomposition
        prompt = f"""
        Given the following question, decompose it into multiple simpler queries if needed.
        If the question is simple, return it as a single query.
        Return the queries as a JSON list.

        Question: {question}

        Response format: ["query1", "query2", ...]
        """
        response = call_llm(prompt)
        # Parse the response (assuming LLM returns valid JSON)
        import json
        try:
            queries = json.loads(response)
            if isinstance(queries, list):
                return queries
            else:
                return [question]
        except:
            return [question]
    
    def post(self, shared, prep_res, exec_res):
        # Store decomposed queries in shared
        shared["decomposed_queries"] = exec_res
        print(f"Decomposition post: stored queries {exec_res}")
        return "default"

class RetrieveDocumentsNode(Node):
    def prep(self, shared):
        # Read decomposed queries from shared
        queries = shared["decomposed_queries"]
        print(f"RetrieveDocumentsNode prep: queries {queries}")
        return queries
    
    def exec(self, queries):
        print(f"RetrieveDocumentsNode exec called with queries: {queries}")
        # Retrieve documents for each query
        results = []
        for query in queries:
            res = retrieve_documents(query, 4)
            results.append(res)
        print(f"Results: {results}")
        return results
    
    def post(self, shared, prep_res, exec_res):
        # Store retrieved contexts in shared
        print(f"Storing retrieved contexts: {exec_res}")
        shared["retrieved_contexts"] = exec_res
        return "default"

class AnswerQuestionNode(Node):
    def prep(self, shared):
        # Read question and retrieved contexts from shared
        question, contexts = shared["question"], shared["retrieved_contexts"]
        print(f"AnswerQuestionNode prep: question {question}, contexts {contexts}")
        return question, contexts
    
    def exec(self, data):
        question, contexts = data
        # Combine contexts
        combined_context = "\n\n".join(["\n".join([doc['content'] for doc in ctx]) for ctx in contexts])
        # Create prompt for answering
        prompt = f"""
        #### Personalidade do Assistente:
        Você é um assistente agronômico especializado em fornecer recomendações agronômicas detalhadas com base no conhecimento que for provido.
        Seu objetivo é ajudar os usuários com informações precisas e práticas para melhorar suas práticas agrícolas.
        Sempre que possível, utilize o conhecimento disponível para fundamentar suas respostas.
        Se o conhecimento não for suficiente, admita que não sabe a resposta.

        Seu conhecimento vem de documentos técnicos, artigos científicos e manuais agrícolas. Fornecidos pela curadoria do Instituto Agronômico de Campinas (IAC).

        #### REGRAS IMPORTANTES:
        - Responda SEMPRE em português.
        - Utilize tabelas para explicar e fundamentar suas respostas quando necessário.
        - Adicione fonte para todas as respostas baseadas no conhecimento.
        - Evite termos técnicos complexos, a menos que solicitado.
        - Seja claro e conciso, mas detalhado quando necessário.
        - Mantenha um tom amigável e profissional.

        #### Caso seja solicitado alguma recomendação agronômica, além da tabela você deve fornecer um passo a passo detalhado de como implementar a recomendação.
        E o valor especifico para o caso informado pelo usuário.

        Contexto:
        {combined_context}

        Pergunta: {question}

        Resposta:
        """
        return call_llm(prompt)
    
    def post(self, shared, prep_res, exec_res):
        # Store the answer in shared
        shared["answer"] = exec_res