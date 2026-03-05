"""Register a simple LangChain model in Unity Catalog.

This script is intentionally standalone and demo-oriented. It creates a tiny
LangChain runnable, logs it with MLflow, and registers it to UC as:

  <catalog>.<schema>.next_best_action_agent

Usage examples:
  python setup/register_langchain_uc_model.py --catalog bx4 --schema butterfly
  CATALOG=bx4 SCHEMA=butterfly python setup/register_langchain_uc_model.py
"""

from __future__ import annotations

import argparse
import os

import mlflow
from langchain_core.output_parsers import StrOutputParser
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnableLambda


def _build_demo_chain():
    prompt = ChatPromptTemplate.from_template(
        "You are a Next Best Action assistant. Create one concise recommendation for this customer context:\n{context}"
    )
    # Simple deterministic formatter so this demo chain has no external LLM dependency.
    formatter = RunnableLambda(
        lambda text: (
            f"Recommended action: Share role-specific follow-up resources and schedule a 15-minute check-in. "
            f"Context used: {str(text)[:300]}"
        )
    )
    return prompt | StrOutputParser() | formatter


def main() -> None:
    parser = argparse.ArgumentParser(description="Register simple LangChain model to Unity Catalog")
    parser.add_argument("--catalog", default=os.getenv("CATALOG", "bx4"))
    parser.add_argument("--schema", default=os.getenv("SCHEMA", "butterfly"))
    args = parser.parse_args()

    model_name = f"{args.catalog}.{args.schema}.next_best_action_agent"

    # Databricks + Unity Catalog model registry settings.
    mlflow.set_tracking_uri("databricks")
    mlflow.set_registry_uri("databricks-uc")

    chain = _build_demo_chain()
    input_example = {"context": "Cardiovascular surgeon at Valley Regional Hospital with high intent score."}

    with mlflow.start_run(run_name="register_next_best_action_agent_demo"):
        model_info = mlflow.langchain.log_model(
            lc_model=chain,
            artifact_path="langchain-model",
            input_example=input_example,
        )
        registered = mlflow.register_model(model_info.model_uri, model_name)
        print(f"Registered model: {registered.name} v{registered.version}")
        print(f"Model URI: models:/{registered.name}/{registered.version}")


if __name__ == "__main__":
    main()
