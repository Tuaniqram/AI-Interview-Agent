from langchain_community.vectorstores import FAISS

from langchain_huggingface import HuggingFaceEmbeddings



def get_company_vectorstore(company_id):


    embeddings = HuggingFaceEmbeddings(

        model_name=
        "sentence-transformers/all-MiniLM-L6-v2"

    )


    path = (
        f"vector_db/company_{company_id}"
    )



    db = FAISS.load_local(

        path,

        embeddings,

        allow_dangerous_deserialization=True

    )


    return db