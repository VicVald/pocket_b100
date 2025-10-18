from pocketflow import AsyncFlow
from nodes import InputNode, QueryDecompositionNode, RetrieveDocumentsNode, AnswerQuestionNode

def create_qa_flow():
    """Create and return a question-answering flow with query decomposition and async retrieval."""
    # Create nodes
    input_node = InputNode()
    decomposition_node = QueryDecompositionNode()
    retrieve_node = RetrieveDocumentsNode()
    answer_node = AnswerQuestionNode()
    
    # Connect nodes in sequence
    input_node >> decomposition_node >> retrieve_node >> answer_node
    
    # Create flow starting with input node
    return AsyncFlow(start=input_node)

qa_flow = create_qa_flow()