
import os
from typing import Literal

from dotenv import load_dotenv
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from langchain.chat_models import init_chat_model

load_dotenv()

app = FastAPI(title="Dynamic Workflow Generator")


class WorkflowRequest(BaseModel):
    description: str = Field(min_length=5)


class WorkflowStep(BaseModel):
    id: str
    name: str
    type: Literal[
        "Input", "Approval", "Notification",
        "Decision", "Action", "End"
    ]
    sequence: int
    dependencies: list[str] = []
    description: str
    outcomes: dict[str, str] = {}


class WorkflowResponse(BaseModel):
    title: str
    description: str
    steps: list[WorkflowStep]


llm = init_chat_model(
    model="groq:openai/gpt-oss-120b",
    api_key=os.getenv("GROQ_API_KEY")
).with_structured_output(WorkflowResponse)


@app.post("/api/workflows/generate", response_model=WorkflowResponse)
def generate_workflow(request: WorkflowRequest):
    try:
        prompt = f"""
Generate a structured workflow for this business process:
{request.description}

Rules:
- Create a title and description.
- Use unique step IDs: step-1, step-2, etc.
- Break the process into individual actionable steps.
 -Include input, action, decision, notification, approval,
   and end steps whenever required by the process.
- Never skip approval, rejection, or notification actions
   explicitly required or logically necessary for the process.
- Use only Input, Approval, Notification, Decision, Action, End.
- Set sequence numbers starting from 1.
- Dependencies must reference prerequisite step IDs.
- Decision outcomes map labels to destination step IDs.
- Include a final End step.
- Return data matching the required schema.
"""
        return llm.invoke(prompt)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
