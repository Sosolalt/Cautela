# **Strategic Architecture and Implementation Strategies for the Google Cloud Rapid Agent Hackathon: Leveraging Arize AI for Agentic Observability**

The artificial intelligence landscape is currently undergoing a structural evolution, moving aggressively from reactive, single-turn conversational interfaces toward autonomous, goal-oriented agents. These new architectures are capable of reasoning, complex tool execution, multi-step orchestration, and dynamic self-correction. The Google Cloud Rapid Agent Hackathon represents a pivotal proving ground for this transition, challenging developers to architect intelligent systems powered by Gemini 3 and the Google Cloud Agent Builder. With a submission deadline of June 11, 2026, and a $60,000 prize pool distributed through a unique "Partner Bucket" system, the competition actively incentivizes deep technical integration with specific enterprise solutions.1

Among the featured partner technologies, Arize AI stands out as a critical enabler of agentic reliability and enterprise readiness. As multi-agent systems scale in complexity, they become increasingly non-deterministic and opaque, leading to unpredictable failure modes, silent logic loops, and unverified hallucinations. Arize Phoenix, an open-source AI observability platform, eliminates this opacity by providing granular execution tracing, dataset management, and Large Language Model (LLM)-assisted evaluations.2 By integrating the Arize Model Context Protocol (MCP) server, developers can grant their agents the unprecedented ability to interact with their own telemetry data, effectively creating meta-reasoning systems capable of monitoring their own performance.4

The following exhaustive analysis details the technical mechanics of Arize AI, examines historical applications of the platform in winning hackathon projects, and provides advanced architectural blueprints designed to secure the Arize-specific prize bucket.

## **The Agentic Paradigm and the Hackathon Imperative**

The Google Cloud Rapid Agent Hackathon explicitly mandates that submissions must move beyond the traditional chatbot paradigm.1 Passive question-answering systems are inherently insufficient for the demands of the modern enterprise; the objective is to engineer a functional agent that solves real-world challenges through proactive action.6

A successful submission must demonstrate three core competencies to qualify for judging:

1. **Action-Oriented Execution**: The agent must utilize tools and capabilities to accomplish tasks, such as managing a local database, automating a hobbyist workflow, or interacting with live web services, rather than simply generating text.1  
2. **Multi-Step Mission Planning**: The system must digest a complex, high-level goal, autonomously decompose it into logical sub-tasks, and execute those steps sequentially while maintaining state and adhering to human oversight.1  
3. **Partner Power via MCP**: The solution must demonstrate a meaningful integration with at least one participating partner's technology using the Model Context Protocol (MCP) to provide the agent with its operational "superpowers".1

The prize structure is deliberately segmented into isolated ecosystems to encourage specialized depth rather than superficial breadth. Rather than a global leaderboard, the $60,000 pool is divided into identical $10,000 buckets for each partner (Arize, Elastic, Fivetran, GitLab, MongoDB, and Dynatrace).1 Competing in the Arize bucket guarantees that the project will be judged specifically against other builders utilizing Arize technology.1

| Prize Tier | Award Amount (Per Partner Bucket) | Eligible Tracks |
| :---- | :---- | :---- |
| **🥇 1st Place** | $5,000 Cash | Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace 1 |
| **🥈 2nd Place** | $3,000 Cash | Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace 1 |
| **🥉 3rd Place** | $2,000 Cash | Arize, Elastic, Fivetran, GitLab, MongoDB, Dynatrace 1 |

Consequently, victory in the Arize track depends not merely on utilizing the tool for basic logging, but on demonstrating a sophisticated, nuanced understanding of how observability and telemetry fundamentally alter the reliability, capability, and autonomy of an AI agent. Submissions are judged on technological implementation, design, potential impact, and quality of the idea.1 The judging panel includes prominent figures from Google Cloud and the partner organizations, including Richard Young (Director of Partner Solutions at Arize) and Clay Miner (Head of Solutions Strategy at Arize), indicating that profound technical integration will be heavily scrutinized.1

## **The Model Context Protocol (MCP): Standardizing AI Connectivity**

To understand the strategic advantage of the Arize integration, one must first analyze the Model Context Protocol (MCP). Introduced by Anthropic in late 2024, MCP is an open universal standard designed to connect AI systems securely with external data sources and execution tools.7 Prior to the widespread adoption of MCP, enabling a language model to interact with a database, a code repository, or a bespoke enterprise API required fragmented, custom-built integrations.7

MCP standardizes these interactions, functioning as a universal "USB-C for AI".7 It dictates a secure, two-way data exchange protocol between an MCP client (the AI assistant or agent) and an MCP server (the external system exposing the tool or data).8 This allows the LLM to augment its reasoning with fresh context from isolated data silos—such as files, internal knowledge bases, and SaaS platforms—using a single, unified methodology for tool-use and context injection.8

In the context of the hackathon, Gemini 3 operates as the cognitive brain, Google Cloud Agent Builder serves as the orchestration and scaling framework, and the MCP server acts as the bridge to the partner technology.1 The power of MCP lies in its abstraction; the agent simply detects the available tools exposed by the server and invokes them natively based on its system prompt and reasoning logic.8 For builders, this significantly reduces the friction of integrating third-party services and allows for the rapid prototyping of highly capable, multi-tooled autonomous agents.

## **Architectural Deep Dive: Arize Phoenix as the Agentic Nervous System**

Arize Phoenix is a developer-focused, open-source AI observability platform designed specifically for the intricacies of generative AI and agentic workflows.2 The fundamental premise of Phoenix is that as systems transition from single-prompt architectures to multi-step agentic pipelines, traditional software debugging methodologies become obsolete.

Without specialized tracing, an agent operating autonomously is effectively "flying blind".2 When a failure occurs, it is nearly impossible to determine via standard console logs why an intermediate tool call failed, why an agent entered an infinite logic loop, or where a specific hallucination was introduced into the context window.10 Phoenix addresses this through a multi-dimensional observability matrix consisting of telemetry tracing, evaluation, dataset curation, and iterative experimentation.3

### **OpenInference and Telemetry Tracing**

The foundation of Phoenix's observability is its tracing engine, which is powered by OpenInference.11 OpenInference is a set of telemetry conventions and plugins that extends the widely adopted OpenTelemetry standard specifically to enable the tracing of AI applications.11 It is designed to be transport and file-format agnostic, capturing the unique metadata associated with machine learning pipelines.11

When an agent is instrumented with OpenInference, every action it takes is recorded as a "span." For an LLM application, this involves capturing every model invocation, tool execution, external API request, and vector database retrieval.10 The telemetry meticulously records the exact inputs provided to the model, the exact outputs generated, the execution latency, and the token usage.10

These individual spans are linked hierarchically into a unified "trace" that represents the complete execution flow of the agent from the initial user prompt to the final output.10 In complex multi-agent systems, where one orchestrator agent might delegate tasks to sub-agents (e.g., routing a query to a specialized code-writing agent), OpenInference maps these communications into interactive visual flowcharts.13

This visual mapping is critical for debugging complex agentic architectures. It exposes logical breakdowns, allows engineers to identify inefficient tool usage, and isolates the specific node in a multi-step mission where an agent hallucinated or failed to parse a JSON response properly.13

| Traditional APM Metrics | OpenInference AI Telemetry | Application in Agentic Architecture |
| :---- | :---- | :---- |
| Server Latency | Generation Latency | Identifies if slow performance is due to database retrieval or LLM inference time. |
| HTTP Status Codes | Token Usage Metrics | Allows for exact cost calculation per autonomous agent run. |
| Stack Traces | Execution Trajectory | Visualizes the sequence of tools the agent decided to call to solve a goal. |
| Database Queries | Vector Store Retrieval | Captures the exact semantic search parameters and the resulting document chunks retrieved.10 |

Furthermore, the integration of MCP introduces a unique tracing challenge: actions occur across a wire protocol separating the client and the server. Arize solves this specific architectural hurdle via the openinference-instrumentation-mcp package.14 Uniquely, this package does not generate any telemetry spans of its own.14 Instead, it propagates the OpenTelemetry context across the MCP wire protocol.14 This ingenious design ensures that the spans created independently by the MCP client (the agent) and the MCP server join into a single, cohesive, unified trace within the Phoenix dashboard.14 Without this context propagation, developers would see fragmented logs that fail to tell the complete story of a multi-step execution.

### **Dynamic Evaluation via LLM-as-a-Judge**

Capturing the trajectory of an agent's execution solves the problem of visibility, but measuring the quality of that execution requires sophisticated, dynamic evaluation. Because agents execute complex, non-deterministic paths, static code tests are insufficient for measuring performance.13 A deterministic test cannot account for the variability in an LLM's phrasing or its dynamic approach to problem-solving. Consequently, Arize Phoenix natively supports LLM-assisted evaluation, commonly referred to as "LLM-as-a-judge".13

This methodology uses a secondary, highly capable LLM to evaluate the outputs and intermediate reasoning steps of the primary agent.17 The evaluator model is provided with a strict prompt template or rubric, the agent's input, and the agent's output, and is tasked with scoring the interaction.13 This is particularly necessary for subjective quality metrics where programmatic, code-based evaluation is impossible, such as identifying hallucinations, measuring response toxicity, or verifying the semantic relevance of retrieved context.19

Phoenix provides a robust suite of pre-built evaluation metrics that are pre-tested against benchmark datasets and tuned for repeatability.20 These include:

* **Toxicity:** Defines whether a comment makes hateful statements, demeans a user, or threatens violence. The judge LLM is instructed to strictly output either "toxic" or "non-toxic".20  
* **Hallucination:** Evaluates whether the agent fabricated data that was not present in the provided context.20  
* **Correctness and Faithfulness:** Measures if the final output accurately satisfies the original prompt constraints and remains faithful to the retrieved documents.20  
* **Tool Selection Accuracy:** Determines if the agent chose the correct API or database tool for the user's specific request.20

However, the true enterprise value of Phoenix lies in the ability to build custom evaluators tailored to highly specialized domains, such as medicine, finance, or agriculture, where models depend on proprietary knowledge and expectations for accuracy are exceptionally high.21 Developers can construct a custom ClassificationEvaluator to return categorical labels specific to their business logic, or an LLMEvaluator to score data on a continuous numeric scale.22

These evaluations can be run continuously across an agent's execution runs in batch processes. For example, agent trajectory evaluations use an LLM as a Judge to assess the entire sequence of tool calls an agent takes to solve a task.13 This helps catch recursive loops or unnecessary steps that inflate API costs and latency, ensuring the agent follows the expected "golden path".13

### **The AI Engineering Loop: Datasets, Prompts, and Experimentation**

The third pillar of the Phoenix ecosystem is the continuous feedback loop established through datasets and experiments. Traces and evaluations generate massive amounts of data regarding an agent's performance. Phoenix allows developers to curate versioned datasets directly from these execution traces.3

If an agent consistently fails on a specific edge case—for instance, failing to parse dates correctly from a legacy database—the developer can isolate those failed traces, append the correct annotations or ideal responses, and save them as a dataset.23 This dataset can then be exported in JSONL format for model fine-tuning, or utilized as the testing ground for Prompt Engineering experiments.23

Phoenix includes a prompt management IDE that supports version control and systematic testing.3 Developers can adjust the system prompt, swap the underlying foundation model, or tweak the retrieval logic, and then run an experiment against the curated dataset to empirically measure if the changes improved performance.2 By running what-if analyses to compare model responses side-by-side, developers transition AI engineering from prompt-guessing to rigorous, evidence-based iteration.2

### **The Meta-Agentic Superpower: The Arize Phoenix MCP Server**

While utilizing Arize to trace an agent during development is industry-standard practice, the Google Cloud Rapid Agent Hackathon explicitly requires integrating the partner technology *as an MCP server* to give the agent its "superpowers".1 This introduces a profound architectural paradigm: meta-agentic observability.

By integrating the @arizeai/phoenix-mcp server, the AI assistant is connected directly to the Phoenix observability instance.4 This exposes the entirety of the Phoenix platform's data—Projects, Traces, Spans, Sessions, Prompts, Datasets, and Experiments—as executable tools directly to the coding agent or the production agent itself.4

The implications of this integration are monumental. Traditionally, debugging LLM pipelines forces developers out of their integrated development environment (IDE) and into separate browser dashboards, creating massive context-switching friction.5 With the Phoenix MCP server running, a developer using the Gemini CLI can prompt the agent itself to analyze its own telemetry.24 The agent can execute commands to pull the latest experiment results, identify patterns in its own failures across hundreds of sessions, inspect the available annotation configurations, or synthesize new dataset examples based on historical trace data.4

For the hackathon, an implementation could architect an agent that executes a primary workflow, and then autonomously checks its own trace data via the Arize MCP to verify if its tool calls were efficient. If a hallucination evaluation metric drops below a certain threshold, the agent could autonomously optimize its own sub-prompts. This level of autonomous self-reflection and operational transparency perfectly fulfills the hackathon's mandate to demonstrate how AI can orchestrate complex, multi-step goals with deep integration of partner technologies.

## **Analysis of Historic Winning Projects Leveraging Arize**

To architect a winning submission, it is critical to analyze past projects that have successfully leveraged Arize AI to secure hackathon victories. These case studies reveal the specific design patterns and use cases that expert judges reward: primarily, applications that tackle complex, high-friction domain problems where reliability, safety, and data observability are absolutely paramount.

### **Case Study 1: OilyRAGs (Multimodal Mechanical Diagnostics)**

At the 2024 LlamaIndex Agentic RAG-a-thon hosted at 500 Global HQ in Palo Alto, a project named "OilyRAGs" secured both third place overall and the specific award for "Best use of Arize Phoenix".25 The project was designed as a highly specialized assistant for mechanics, targeting the friction involved in diagnosing engine issues, referencing massive service manuals, and sourcing parts across automotive, marine, and small engine domains.25

The architecture utilized Python, Streamlit, LlamaIndex, Pinecone for vector embeddings, and OpenAI's GPT, Whisper, and Vision models.25 By operating as an agentic Retrieval-Augmented Generation (RAG) system, OilyRAGs could ingest multimodal input—such as a user uploading a photo of a degraded part or using voice audio to describe a specific engine sound—index technical catalogs, generate real-time diagnostic reasoning, and automate the compilation of parts reports.25

The integration of Arize Phoenix was a defining factor in this project's success. Mechanical diagnostics is a high-stakes, real-world domain where a hallucination regarding a torque specification or an incorrect part number substitution could result in catastrophic engine failure or physical injury. By leveraging Phoenix, the developer ensured that every retrieval operation and generation was mathematically traced.10 This allowed the system to evaluate the relevance of the retrieved service manual sections against the user's specific query and verify the correctness of the generated diagnostic steps, providing a level of safety and reliability that a standard, unmonitored wrapper application could not achieve.

### **Case Study 2: OpsRocket (Business Operations Automation)**

At the same LlamaIndex Hackathon, another highly successful project was awarded for "Best use of Arize Phoenix" with an application titled "OpsRocket".26 OpsRocket functioned as an AI consulting tool designed to analyze business operations, identify inefficiencies, and execute strategies to improve revenue and reduce operational risk faster than humanly possible.26

In the context of business consulting, agents must ingest vast amounts of proprietary corporate data, sensitive financial reports, and complex operational metrics. An autonomous agent making financial recommendations must possess an auditable reasoning trail to be trusted by human stakeholders. Arize Phoenix provided the necessary infrastructure to trace the agent's logic paths, ensuring that its recommendations were deeply grounded in the provided operational data rather than generated from parametric assumptions or hallucinations.26 The use of Phoenix for agent observability transformed OpsRocket from an experimental prototype into a conceptually enterprise-ready application, demonstrating how observability bridges the gap between a demo and production software.

### **Case Study 3: Advanced Architectures by Two-Weeks-Team**

Projects developed by the "Two-Weeks-Team" demonstrate the absolute bleeding edge of agentic architecture and provide a glimpse into the complexity expected at the Google Cloud Rapid Agent Hackathon. Their project "Panelyst" is described as an "agentic fair-evaluation panel" that ingests a startup pitch deck and a codebase, then runs a sophisticated six-perspective AI panel to score the project against a 100-point rubric.28 The system utilizes Gemini, Google Cloud Agent Builder, Qdrant for vector storage, and Arize for observability.28 Crucially, the developers emphasize that it is "not a chatbot," but rather an orchestration of evidence-grounded, precedent-anchored evaluations managed under a live, transparent fairness monitor.28

Similarly, their "SocialSeed.ing By Agent" project functions as an autonomous social-seeding agent for TikTok marketing.28 Operating within a hard budget cap and utilizing a multi-stage fraud filter, the system is built on an Agent Development Kit (ADK) multi-agent framework, Gemini on Vertex AI, and MCP integrations.28

These projects showcase the exact architectural complexity expected in the hackathon. They highlight the absolute necessity of Arize in complex ecosystems. In Panelyst, a six-perspective AI panel requires intense multi-agent coordination; tracing these interactions via Phoenix is mandatory to prevent conflicting agent directives and to maintain the integrity of the fairness monitor. In SocialSeed.ing, executing actual financial transactions (billing per verified view) demands strict deterministic constraints, which can only be verified through continuous trajectory evaluations and guardrails managed by the observability platform.28

### **Case Study 4: Watchful.AI (Anomaly Detection and Embeddings)**

While slightly divergent from purely text-based LLM agents, the PennApps XXV winning project "Watchful.AI" won "Most Technically Complex Hack" and "Best Privacy/Security Hack" by utilizing Arize AI's concepts of embeddings and vector databases.29 The system performed real-time anomaly detection across video streams using CLIP (Contrastive Language-Image Pre-training) to generate a 512-dimensional embedding for every video frame.29

The system mapped normal operational frames against anomalous frames (e.g., detecting a threat in a corridor).29 Arize AI's visualization tools are highly capable of mapping these embedding clusters, allowing developers to visually inspect how well a model is separating safe behavior from threats.29 This case study emphasizes that Arize is not merely for text traces; it is a comprehensive machine learning observability suite capable of handling complex multimodal architectures, a key requirement for modern AI challenges.

## **Strategic Project Blueprints for the Arize Track**

Based on the capabilities of the Arize MCP, the criteria of the Google Cloud Rapid Agent Hackathon, and the precedent set by historical winners, the following project blueprints represent optimal strategies for securing the $5,000 first-place prize in the Arize bucket. These architectures are designed to heavily leverage the @arizeai/phoenix-mcp server, Gemini 3's advanced reasoning, and Google Cloud Agent Builder.

### **Blueprint 1: The Agentic Compliance & Audit Orchestrator (Financial Services Track)**

**The Real-World Challenge**: Financial institutions struggle with the immense overhead of auditing complex loan workflows and ensuring real-time fraud detection.1 Traditional static rules engines are too rigid to adapt to novel fraud vectors, while unmonitored LLMs pose unacceptable compliance risks due to their propensity for hallucination and lack of deterministic logic.

**The Solution**: An autonomous financial auditor agent built via Google Cloud Agent Builder. The agent ingests real-time transaction data and loan application workflows via an API. When an anomaly is detected, the agent autonomously requests additional documentation via email, cross-references internal compliance guidelines via a vector database, and generates a highly structured risk assessment report.

**The Arize Superpower**: In the financial sector, an un-auditable AI is a massive legal liability. This project would integrate the Arize MCP to establish a "Meta-Auditor System." Every single action taken by the primary risk agent is traced via OpenInference and logged in Phoenix. A secondary, independent LLM-as-a-judge continuously evaluates the primary agent's traces against strict financial compliance rubrics (Custom ClassificationEvaluator).

If the judge model detects a hallucinated regulation or an unauthorized tool execution, the system uses the Arize MCP to halt the transaction automatically, flag the specific trace span for human review, and synthesize a dataset of failed interactions to dynamically refine the primary agent's system prompt.3 This architecture perfectly demonstrates how AI can drive precision and trust in the modern economy by proving that the agent is governed by strict, observable parameters.1

### **Blueprint 2: Hyper-Local Facility Optimization Swarm (Brick-and-Mortar Retail Track)**

**The Real-World Challenge**: Brick-and-mortar malls lack the dynamic responsiveness of e-commerce platforms. Facility operations, tenant campaign management, and shopper navigation are isolated, manual processes that cannot rapidly adjust to real-time foot traffic.1

**The Solution**: A multi-agent swarm architecture deployed to manage a physical retail space dynamically. The system includes an Operations Agent (managing HVAC, lighting, and security APIs based on foot traffic), a Tenant Agent (coordinating hyper-local flash sales to underperforming store zones), and a Concierge Agent (navigating shoppers via mobile integration).1

**The Arize Superpower**: Managing a multi-agent swarm creates massive observability challenges. As agents interact, tracing their communication logic becomes exponentially more difficult. The project would use the Arize MCP server to monitor the communication paths between the three agents.

If the Concierge Agent routes 500 shoppers to a specific tenant, but the Operations Agent fails to increase the HVAC capacity in that specific physical zone, the execution trace will reveal the exact node where the agentic communication broke down.13 The system leverages Phoenix's interactive flowcharts to map agent interactions visually and uses trajectory evaluations to identify logical bottlenecks.13 By exposing this telemetry via the MCP, the developer can verbally query the Gemini CLI: "Show me all traces from the Operations Agent where tool execution latency exceeded 200ms during peak foot traffic," radically accelerating the development and optimization of physical retail infrastructure.5

### **Blueprint 3: Automated Self-Healing CI/CD Reliability Agent (Open Ended Track)**

**The Real-World Challenge**: Software developers spend an excessive amount of time debugging code failures, reviewing logs, and writing tests. While standard coding assistants can generate code, they cannot autonomously test, deploy, and monitor the health of their own software in a continuous pipeline.

**The Solution**: An agent that integrates directly with a codebase repository (e.g., via the GitLab MCP) and a deployment environment. When a pull request is created, the agent writes unit tests, executes the build, and monitors the runtime environment for errors.

**The Arize Superpower**: This project would heavily utilize the @arizeai/phoenix-mcp to create a truly "Self-Healing" AI system. If the primary agent generates a piece of code that causes an application to fail during the testing phase, the agent utilizes the Phoenix MCP to pull the exact execution trace of its own failure.4 The agent analyzes the spans, identifies where its logic was flawed, creates a curated dataset of the failure, and autonomously iterates on its own prompts or code logic before submitting a new, corrected commit.3 This demonstrates an agent capable of recursive self-improvement through integrated observability, fulfilling the highest ideals of the agentic paradigm.30

### **Blueprint 4: Autonomous Healthcare Diagnostics Validator (Open Ended Track)**

**The Real-World Challenge**: The integration of AI into preliminary healthcare triage is accelerating, but the risk of incorrect medical advice presents extreme liability. LLMs operating as medical chatbots require intense supervision to ensure they do not hallucinate medical facts or bypass triage protocols.

**The Solution**: An agentic system designed to conduct preliminary patient intake interviews. The agent gathers symptoms, queries a secure medical database, and suggests a triage priority level to human nursing staff.

**The Arize Superpower**: This project introduces the critical concept of Guardrails. By integrating Guardrails AI alongside Arize Phoenix, the system can block harmful responses or malicious jailbreak attempts.31 The project would trace the intake agent's outputs, and if a guardrail is triggered (e.g., the agent attempts to prescribe medication, which violates its core directive), Phoenix records the trace. Using a custom LLM-as-a-judge optimized with Few-Shot Examples and Human-in-the-Loop iteration to reduce bias 32, the system rigorously evaluates the medical faithfulness of the agent's summary before it is passed to the human doctor. The Arize integration proves to the judges that the application is not just a clever prompt wrapper, but a clinically observable and highly constrained workflow.

## **Technical Implementation Protocols for the Hackathon**

Executing these sophisticated blueprints requires a rigorous, systematic approach to technical integration. The hackathon technology stack involves Google Cloud Agent Builder, Gemini 3 via Vertex AI, OpenInference for telemetry, and the Phoenix MCP server.

### **Step 1: Core Agent Orchestration and Authentication**

The foundation of the project must be established securely using Google Cloud's enterprise infrastructure. Gemini 3, hosted on Vertex AI, serves as the primary reasoning engine, providing IAM-based authentication and project-level billing controls.1 The orchestration should be handled via Google Cloud Agent Builder or a compatible framework like the Google Agent Development Kit (ADK), which simplifies the creation of multi-agent patterns.1

Authentication is managed natively within the Google Cloud ecosystem. Developers must configure their environment using Application Default Credentials (ADC) via a service account key or by executing the gcloud auth application-default login command.34 The required libraries include the newly unified Google GenAI SDK (google-genai), which serves as the canonical replacement for legacy SDKs. This unified client library dramatically simplifies calling Gemini, handling tool execution, and managing built-in safety settings.33

### **Step 2: Instrumenting the Application with OpenInference**

To capture the agent's telemetry effectively, the application code must be instrumented using OpenInference.11 Because the project relies on the Google GenAI SDK, developers must install the specific OpenInference instrumentation library alongside the standard OpenTelemetry packages:

Bash

pip install \-U openinference-instrumentation-google-genai arize-phoenix opentelemetry-sdk opentelemetry-exporter-otlp "opentelemetry-proto\>=1.12.0"

Instrumentation requires initializing a tracer provider and connecting it to the OpenTelemetry span processor.35 This process intercepts all calls to the Gemini API (specifically the generate\_content methods) and generates OpenTelemetry-compatible traces automatically without requiring manual logging statements throughout the codebase.35

Python

from openinference.instrumentation.google\_genai import GoogleGenAIInstrumentor  
from opentelemetry.exporter.otlp.proto.grpc.trace\_exporter import OTLPSpanExporter  
from opentelemetry.sdk.trace import TracerProvider  
from opentelemetry.sdk.trace.export import SimpleSpanProcessor

endpoint \= "http://127.0.0.1:4317" \# Replace with the Arize Phoenix Cloud endpoint  
tracer\_provider \= TracerProvider()  
tracer\_provider.add\_span\_processor(SimpleSpanProcessor(OTLPSpanExporter(endpoint)))  
GoogleGenAIInstrumentor().instrument(tracer\_provider=tracer\_provider)

To route these generated traces to a hosted instance of Arize Phoenix, the environment variables must be securely configured to point to the Phoenix collector endpoint and include the necessary API keys (PHOENIX\_API\_KEY, PHOENIX\_COLLECTOR\_ENDPOINT, and PHOENIX\_PROJECT\_NAME).36

### **Step 3: Integrating the Model Context Protocol (MCP)**

If the agent invokes external partner tools—such as querying a MongoDB database, pulling metrics from Dynatrace, or accessing a GitLab repository—the interactions should be standardized via MCP. To ensure that traces remain unified across the client-server boundary, developers must install the openinference-instrumentation-mcp package.14

Bash

pip install openinference-instrumentation-mcp

While this specific package does not generate telemetry directly, it acts as the critical context bridge. It propagates the OpenTelemetry context so that spans created on the external MCP server seamlessly join the agent's primary execution trace in the Arize dashboard.14

### **Step 4: Deploying the Arize Phoenix MCP Server**

To satisfy the hackathon's core "Partner Power" requirement and unlock the advanced meta-agentic capabilities discussed in the blueprints, the @arizeai/phoenix-mcp server must be deployed and exposed to the agent. This Typescript package connects the agent directly to the Phoenix observability instance.5

The MCP server can be run via npx, passing the base URL of the Phoenix space and the API key as required runtime arguments 5:

Bash

npx \-y @arizeai/phoenix-mcp@latest \--baseUrl https://my-phoenix.com \--apiKey your-api-key

For rapid development and prototyping, this server can be integrated directly into the Gemini CLI configuration. By editing the .gemini/settings.json file to include the phoenix server block under mcpServers, the Gemini agent immediately gains access to Phoenix's internal tools as a runtime superpower.4

JSON

{  
  "mcpServers": {  
    "phoenix": {  
      "command": "npx",  
      "args": \[  
        "-y",  
        "@arizeai/phoenix-mcp@latest",  
        "--baseUrl",  
        "https://app.phoenix.arize.com/s/your-space",  
        "--apiKey",  
        "px\_live\_..."  
      \]  
    }  
  }  
}

Once configured, the agent can execute natural language queries such as "In Phoenix, show me the last 3 traces in my gemini-hackathon project," or "In Phoenix, summarize my latest experiment results".24

### **Step 5: Engineering the Evaluation Pipeline**

With the telemetry flowing successfully into Phoenix, the final phase of implementation is establishing the LLM-as-a-judge evaluation pipelines.13 Developers must identify the critical success metrics for their specific agent's domain. If building the retail swarm, the metric might be "Tool Invocation Accuracy." If building the financial auditor, the metric must prioritize "Hallucination" and "Correctness".20

Evaluations are configured within the Arize platform or via the Python SDK, specifying the judge LLM model (which can be configured as Gemini 3 via Google GenAI), the prompt template defining the grading rubric, and the mapping of the agent's input and output data to the judge's context window.18 As the agent runs during the final 3-minute hackathon demo video, the judges will see not just a successful task execution on the front end, but a real-time dashboard in Arize proving that the agent's reasoning was rigorously evaluated, verified, and explicitly validated against hallucination in the back end.19

## **Conclusion: The Strategic Path to Hackathon Dominance**

The Google Cloud Rapid Agent Hackathon represents an inflection point in the discipline of AI engineering. As the industry moves rapidly from experimental, monolithic chatbots to production-grade, multi-tool autonomous agents, the core engineering challenge fundamentally shifts from raw foundation model intelligence to system reliability, enterprise governance, and operational observability.

Participating in the Arize partner track offers developers a profound strategic advantage. It forces the builder to confront the exact friction points that currently cause 95% of enterprise AI pilots to fail before reaching production: silent logical errors, unpredictable tool execution, unverified outputs, and complex hallucination vectors.38 By fundamentally embedding Arize Phoenix into the system architecture—utilizing OpenInference for highly granular telemetry tracing, LLM-as-a-judge for dynamic trajectory evaluation, and the Phoenix MCP server for advanced meta-agentic self-correction—a hackathon project transcends a mere conceptual proof-of-concept.

A winning submission in this high-stakes environment will prove that its agent does not merely execute tasks blindly based on parametric guesses. Instead, it will demonstrate a sophisticated system that reasons carefully, acts decisively, monitors its own execution trajectory, evaluates its own performance against strict enterprise rubrics, and dynamically leverages its own historical trace data to improve its efficiency. In the rapidly approaching era of autonomous systems, the highest expression of artificial intelligence is not merely action, but verifiable, highly observable, and self-correcting action. This is the precise enterprise capability that Arize AI provides, and the definitive blueprint for dominating the Google Cloud Rapid Agent Hackathon.

#### **Sources des citations**

1. Google Cloud Rapid Agent Hackathon \- Internshala Competitions, consulté le mai 19, 2026, [https://internshala.com/competitions/google-cloud-rapid-agent-hackathon/](https://internshala.com/competitions/google-cloud-rapid-agent-hackathon/)  
2. Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/phoenix/](https://arize.com/phoenix/)  
3. Arize-ai/phoenix: AI Observability & Evaluation \- GitHub, consulté le mai 19, 2026, [https://github.com/arize-ai/phoenix](https://github.com/arize-ai/phoenix)  
4. MCP Servers \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/integrations/phoenix-mcp-server](https://arize.com/docs/phoenix/integrations/phoenix-mcp-server)  
5. Arize Phoenix MCP Server by Arize AI | LLM Observability Tools \- Augment Code, consulté le mai 19, 2026, [https://www.augmentcode.com/mcp/arize-phoenix-mcp-server](https://www.augmentcode.com/mcp/arize-phoenix-mcp-server)  
6. Google Cloud Rapid Agent Hackathon | Build the Future with AI Agents : r/ambitionarena7 \- Reddit, consulté le mai 19, 2026, [https://www.reddit.com/r/ambitionarena7/comments/1tb88gx/google\_cloud\_rapid\_agent\_hackathon\_build\_the/](https://www.reddit.com/r/ambitionarena7/comments/1tb88gx/google_cloud_rapid_agent_hackathon_build_the/)  
7. Model Context Protocol (MCP) from Anthropic \- Arize AI, consulté le mai 19, 2026, [https://arize.com/blog/model-context-protocol/](https://arize.com/blog/model-context-protocol/)  
8. Model Context Protocol (MCP) \- Arize AI, consulté le mai 19, 2026, [https://arize.com/glossary/model-context-protocol-mcp/](https://arize.com/glossary/model-context-protocol-mcp/)  
9. Tracks & Prizes – Hacker Resources \- NexHacks, consulté le mai 19, 2026, [https://www.nexhacks.com/hacker-resources/tracks](https://www.nexhacks.com/hacker-resources/tracks)  
10. Tracing Tutorial \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/tracing/tutorial](https://arize.com/docs/phoenix/tracing/tutorial)  
11. Arize-ai/openinference: OpenTelemetry Instrumentation for AI Observability \- GitHub, consulté le mai 19, 2026, [https://github.com/Arize-ai/openinference](https://github.com/Arize-ai/openinference)  
12. Understanding Tracing and Instrumentation with Arize Phoenix \- YouTube, consulté le mai 19, 2026, [https://www.youtube.com/watch?v=j5WwaknZVDY](https://www.youtube.com/watch?v=j5WwaknZVDY)  
13. Agent Observability and Tracing \- Arize AI, consulté le mai 19, 2026, [https://arize.com/ai-agents/agent-observability/](https://arize.com/ai-agents/agent-observability/)  
14. MCP \- Arize AX Docs, consulté le mai 19, 2026, [https://arize.com/docs/ax/integrations/python-agent-frameworks/model-context-protocol/mcp-tracing](https://arize.com/docs/ax/integrations/python-agent-frameworks/model-context-protocol/mcp-tracing)  
15. openinference-instrumentation-mcp \- PyPI, consulté le mai 19, 2026, [https://pypi.org/project/openinference-instrumentation-mcp/](https://pypi.org/project/openinference-instrumentation-mcp/)  
16. MCP Tracing \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/integrations/python/mcp-tracing](https://arize.com/docs/phoenix/integrations/python/mcp-tracing)  
17. The Definitive Guide to LLM App Evaluation \- Arize AI, consulté le mai 19, 2026, [https://arize.com/wp-content/uploads/2024/11/LLM-Evaluation-Ebook-v3.1.pdf](https://arize.com/wp-content/uploads/2024/11/LLM-Evaluation-Ebook-v3.1.pdf)  
18. Customize Your LLM Endpoint \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/evaluation/tutorials/customize-your-llm-endpoint](https://arize.com/docs/phoenix/evaluation/tutorials/customize-your-llm-endpoint)  
19. The Definitive Guide to LLM Evaluation \- Arize AI, consulté le mai 19, 2026, [https://arize.com/llm-evaluation/](https://arize.com/llm-evaluation/)  
20. Toxicity \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/evaluation/pre-built-metrics/toxicity](https://arize.com/docs/phoenix/evaluation/pre-built-metrics/toxicity)  
21. LLM-as-a-Judge: Example of How To Build a Custom Evaluator Using a Benchmark Dataset, consulté le mai 19, 2026, [https://arize.com/blog/llm-as-a-judge-example-of-how-to-build-a-custom-evaluator-using-a-benchmark-dataset/](https://arize.com/blog/llm-as-a-judge-example-of-how-to-build-a-custom-evaluator-using-a-benchmark-dataset/)  
22. Custom LLM Evaluators \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/evaluation/how-to-evals/custom-llm-evaluators](https://arize.com/docs/phoenix/evaluation/how-to-evals/custom-llm-evaluators)  
23. Arize Phoenix: Datasets, consulté le mai 19, 2026, [https://arize.com/resource/arize-phoenix-datasets/](https://arize.com/resource/arize-phoenix-datasets/)  
24. Arize-ai/gemini-hackathon: Starter application for Gemini ... \- GitHub, consulté le mai 19, 2026, [https://github.com/Arize-ai/gemini-hackathon](https://github.com/Arize-ai/gemini-hackathon)  
25. oilyrags.ai: OilyRAGs is launching soon\!, consulté le mai 19, 2026, [https://oilyrags.ai/](https://oilyrags.ai/)  
26. J. Davis 0xjdavis \- GitHub, consulté le mai 19, 2026, [https://github.com/0xjdavis](https://github.com/0xjdavis)  
27. Agentic RAG-a-thon 2 Winners And Recap Guide \- LlamaIndex, consulté le mai 19, 2026, [https://www.llamaindex.ai/blog/agentic-rag-a-thon-2-winners-and-recap](https://www.llamaindex.ai/blog/agentic-rag-a-thon-2-winners-and-recap)  
28. 2weeks \- GitHub, consulté le mai 19, 2026, [https://github.com/Two-Weeks-Team](https://github.com/Two-Weeks-Team)  
29. How Vector Databases and Embeddings Powered Watchful.AI to Win Big at PennApps XXV | by Ansh Agrawal | deMISTify | Medium, consulté le mai 19, 2026, [https://medium.com/demistify/how-vector-databases-and-embeddings-powered-watchful-ai-to-win-big-at-pennapps-xxv-4efeb953d079](https://medium.com/demistify/how-vector-databases-and-embeddings-powered-watchful-ai-to-win-big-at-pennapps-xxv-4efeb953d079)  
30. Alyx 2.0: The AI Agent That Actually Plans, consulté le mai 19, 2026, [https://arize.com/blog/alyx-2-0-the-ai-agent-that-actually-plans/](https://arize.com/blog/alyx-2-0-the-ai-agent-that-actually-plans/)  
31. Phoenix Guardrails AI Integration \- Arize AI, consulté le mai 19, 2026, [https://arize.com/resource/phoenix-guardrails-ai-integration/](https://arize.com/resource/phoenix-guardrails-ai-integration/)  
32. LLM-as-a-Judge Prompt Optimization \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/cookbook/prompt-engineering/llm-as-a-judge-prompt-optimization](https://arize.com/docs/phoenix/cookbook/prompt-engineering/llm-as-a-judge-prompt-optimization)  
33. Vertex AI \- Arize AX Docs, consulté le mai 19, 2026, [https://arize.com/docs/ax/integrations/llm-providers/vertexai/vertexai-tracing](https://arize.com/docs/ax/integrations/llm-providers/vertexai/vertexai-tracing)  
34. Observability for Google Gemini Models with Langfuse Integration, consulté le mai 19, 2026, [https://langfuse.com/integrations/model-providers/google-gemini](https://langfuse.com/integrations/model-providers/google-gemini)  
35. openinference-instrumentation-google-genai \- PyPI, consulté le mai 19, 2026, [https://pypi.org/project/openinference-instrumentation-google-genai/](https://pypi.org/project/openinference-instrumentation-google-genai/)  
36. Send Traces From Your App \- Phoenix \- Arize AI, consulté le mai 19, 2026, [https://arize.com/docs/phoenix/get-started/get-started-tracing](https://arize.com/docs/phoenix/get-started/get-started-tracing)  
37. Harnessing Databricks Mosaic AI Agent Framework and Arize for Next-Level GenAI Applications, consulté le mai 19, 2026, [https://arize.com/blog/harnessing-databricks-mosaic-ai-agent-framework-and-arize-for-next-level-genai-applications/](https://arize.com/blog/harnessing-databricks-mosaic-ai-agent-framework-and-arize-for-next-level-genai-applications/)  
38. 95% of AI Pilots Fail. The Ones That Succeed All Do This One Thing, consulté le mai 19, 2026, [https://dev.to/utibe\_okodi\_339fb47a13ef5/95-of-ai-pilots-fail-the-ones-that-succeed-all-do-this-one-thing-37if](https://dev.to/utibe_okodi_339fb47a13ef5/95-of-ai-pilots-fail-the-ones-that-succeed-all-do-this-one-thing-37if)  
39. Beyond models: How context and evals make agents work in production \- Arize AI, consulté le mai 19, 2026, [https://arize.com/blog/ai-agents-in-production-context-evaluation/](https://arize.com/blog/ai-agents-in-production-context-evaluation/)